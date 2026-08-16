"""
pr_review_agent/github_app_auth.py — GitHub App JWT & installation token management.

Private key is loaded from the GITHUB_APP_PRIVATE_KEY env var (base64-encoded PEM).
For production, migrate this to a real secrets manager (AWS Secrets Manager,
GCP Secret Manager, or Vault). See implementation_plan.md §Decisions Locked In #1.
"""
import base64
import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# In-memory installation token cache: {installation_id: (token, expires_at_epoch)}
_token_cache: Dict[int, tuple] = {}
_CACHE_BUFFER_SECS = 60  # refresh 60 s before actual expiry


def load_private_key_from_env() -> Optional[str]:
    """
    Decode GITHUB_APP_PRIVATE_KEY (base64-encoded RSA PEM) from the environment.
    Falls back to reading pr_review_agent/db.py app_config for persisted key.
    Returns the raw PEM string, or None if unavailable.
    """
    b64 = os.getenv("GITHUB_APP_PRIVATE_KEY")
    if b64:
        try:
            pem = base64.b64decode(b64).decode("utf-8")
            if "BEGIN" in pem:
                return pem
        except Exception as e:
            logger.warning("[github_app_auth] Failed to decode GITHUB_APP_PRIVATE_KEY: %s", e)
    # Fallback: try the DB (loaded at startup from .env.app)
    try:
        from pr_review_agent.db import get_app_config
        db_val = get_app_config("GITHUB_APP_PRIVATE_KEY")
        if db_val:
            pem = base64.b64decode(db_val).decode("utf-8")
            if "BEGIN" in pem:
                return pem
    except Exception:
        pass
    return None


def load_app_id() -> Optional[int]:
    """Load GitHub App ID from env or DB."""
    val = os.getenv("GITHUB_APP_ID")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    try:
        from pr_review_agent.db import get_app_config
        db_val = get_app_config("GITHUB_APP_ID")
        if db_val:
            return int(db_val)
    except Exception:
        pass
    return None


def generate_jwt(app_id: int, private_key_pem: str) -> str:
    """
    Generate a GitHub App JWT using RS256.
    Requires PyJWT and cryptography packages.
    """
    try:
        import jwt  # PyJWT
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
    except ImportError as e:
        raise RuntimeError(
            "PyJWT and cryptography are required for GitHub App auth. "
            "Install with: pip install PyJWT cryptography"
        ) from e

    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued 60 s ago to account for clock skew
        "exp": now + 540,  # 9 min from now (max is 10)
        "iss": str(app_id),
    }
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def get_installation_token(installation_id: int, force_refresh: bool = False) -> Optional[str]:
    """
    Exchange a JWT for an installation access token (cached 5 min before expiry).
    Returns the token string, or None if App credentials are not available.
    """
    now = int(time.time())

    # Return cached token if still valid
    if not force_refresh and installation_id in _token_cache:
        cached_token, expires_at = _token_cache[installation_id]
        if now < (expires_at - _CACHE_BUFFER_SECS):
            return cached_token

    app_id = load_app_id()
    private_key_pem = load_private_key_from_env()

    if not app_id or not private_key_pem:
        logger.warning(
            "[github_app_auth] GitHub App credentials not configured. "
            "Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY env vars, or run /api/github/app-callback first."
        )
        return None

    try:
        jwt_token = generate_jwt(app_id, private_key_pem)
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        req = urllib.request.Request(
            url,
            method="POST",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AgenticAI-ReviewBot/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        token = data.get("token")
        # GitHub tokens expire in 1 hour; parse ISO timestamp
        expires_at_str = data.get("expires_at", "")
        try:
            import datetime
            dt = datetime.datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            expires_epoch = int(dt.timestamp())
        except Exception:
            expires_epoch = now + 3600

        _token_cache[installation_id] = (token, expires_epoch)
        logger.info("[github_app_auth] Obtained installation token for installation %s", installation_id)
        return token

    except urllib.error.HTTPError as e:
        logger.error(
            "[github_app_auth] Failed to get installation token (HTTP %s): %s",
            e.code, e.read().decode("utf-8", errors="replace")
        )
        return None
    except Exception as e:
        logger.error("[github_app_auth] Unexpected error getting installation token: %s", e)
        return None


def get_token_for_repo(repo_full_name: str, fallback_pat: Optional[str] = None) -> Optional[str]:
    """
    High-level helper: resolve the best available token for a given repo.
    Priority: installation token > GITHUB_TOKEN PAT > fallback_pat.
    """
    try:
        from pr_review_agent.db import get_installation_id_for_repo
        installation_id = get_installation_id_for_repo(repo_full_name)
        if installation_id:
            token = get_installation_token(installation_id)
            if token:
                return token
    except Exception as e:
        logger.debug("[github_app_auth] Installation token lookup failed: %s", e)

    # Fallback to personal access token
    pat = fallback_pat or os.getenv("GITHUB_TOKEN")
    if pat:
        return pat

    logger.warning(
        "[github_app_auth] No token available for repo %s. "
        "Install the GitHub App or set GITHUB_TOKEN.",
        repo_full_name
    )
    return None


def invalidate_token_cache(installation_id: int) -> None:
    """Remove cached token for an installation (e.g. after uninstall)."""
    _token_cache.pop(installation_id, None)
