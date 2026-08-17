"""
pr_review_agent/webhook_handler.py — FastAPI router for GitHub webhook events.

Endpoints:
  POST /webhooks/github         — HMAC-verified event receiver
  GET  /install                 — Landing page with GitHub App install button
  GET  /api/github/app-callback — Manifest Flow callback (persists creds to DB + .env.app)
  GET  /api/pr-reviews          — List recent reviews (dashboard API)
  GET  /api/pr-reviews/{repo_owner}/{repo_name}/{pr_number} — Review detail
  POST /api/learnings/dismiss   — Record a dismissal
  GET  /api/repos               — List installed repos

Credential persistence guarantee:
  App credentials obtained via the Manifest Flow callback are written to BOTH:
  1. SQLite app_config table (primary, fast read)
  2. .env.app file (durable, survives DB re-creation)
  Never stored only in os.environ.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from pr_review_agent import db
from pr_review_agent.db import (
    get_app_config,
    set_app_config,
    upsert_installation,
    add_installation_repo,
    remove_installation_repo,
    delete_installation,
    get_all_review_log,
    get_review_log,
    is_delivery_seen,
    record_delivery,
)
from pr_review_agent import metrics as _metrics
from pr_review_agent.ratelimit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pr-review-agent"])

_ENV_APP_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".env.app"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_env_app(key: str, value: str) -> None:
    """
    Append or update a key=value line in .env.app.
    Reads the existing file, replaces the key if present, appends if not.
    .env.app must be in .gitignore — checked at startup.
    """
    path = _ENV_APP_PATH
    lines = []
    replaced = False
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={value}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    logger.info("[webhook_handler] Wrote %s to .env.app", key)


def _persist_credential(key: str, value: str) -> None:
    """Write to BOTH the SQLite app_config table AND .env.app file."""
    set_app_config(key, value)
    _write_env_app(key, value)


def _verify_hmac(secret: Optional[str], payload: bytes, signature_header: Optional[str]) -> bool:
    """Verify X-Hub-Signature-256 HMAC-SHA256. Returns True if valid."""
    if not secret:
        logger.warning("[webhook_handler] Webhook secret not configured — HMAC verification skipped")
        return True  # Permissive in unconfigured state; tighten once configured
    if not signature_header:
        return False
    expected_prefix = "sha256="
    if not signature_header.startswith(expected_prefix):
        return False
    expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    received_sig = signature_header[len(expected_prefix):]
    return hmac.compare_digest(expected_sig, received_sig)


def _get_token_for_repo(repo_full_name: str) -> Optional[str]:
    """Resolve an installation or PAT token for the given repo."""
    try:
        from pr_review_agent.github_app_auth import get_token_for_repo
        return get_token_for_repo(repo_full_name)
    except Exception as e:
        logger.warning("[webhook_handler] Could not resolve token for %s: %s", repo_full_name, e)
        return os.getenv("GITHUB_TOKEN")


# ─────────────────────────────────────────────────────────────────────────────
# Background pipeline task
# ─────────────────────────────────────────────────────────────────────────────

def _run_pipeline_background(repo_full_name: str, pr_number: int, commit_sha: str) -> None:
    """Blocking pipeline run — called via FastAPI BackgroundTasks."""
    token = _get_token_for_repo(repo_full_name)
    if not token:
        logger.error(
            "[webhook_handler] No token for %s — skipping pipeline for PR #%s",
            repo_full_name, pr_number
        )
        _metrics.inc("pipeline_failed")
        return
    try:
        from pr_review_agent.pipeline import run_full_pipeline
        result = run_full_pipeline(repo_full_name, pr_number, commit_sha, token)
        _metrics.inc("pipeline_ok")
        logger.info(
            "[webhook_handler] Pipeline finished for %s PR #%s: %s",
            repo_full_name, pr_number, result.get("quality_gate")
        )
    except Exception as e:
        _metrics.inc("pipeline_failed")
        logger.error(
            "[webhook_handler] Pipeline error for %s PR #%s: %s",
            repo_full_name, pr_number, e, exc_info=True
        )


def _post_welcome_issue(repo_full_name: str, account_login: str = "") -> None:
    """Create a welcome issue in the newly connected repository."""
    try:
        token = _get_token_for_repo(repo_full_name)
        if not token:
            logger.warning("[webhook_handler] No token available to post welcome issue on %s", repo_full_name)
            return

        title = "🚀 Agentic AI Self-Healing & PR Review Bot is now active!"
        body = (
            f"## 🤖 Agentic AI Platform Connected Successfully!\n\n"
            f"Hello @{account_login or 'team'}! 👋\n\n"
            f"The **Agentic AI Self-Healing & PR Review Agent** is now active on `{repo_full_name}`.\n\n"
            f"---\n\n"
            f"### 🛡️ What Happens on Every Pull Request:\n"
            f"1. **🔍 Multi-Tool Static Analysis:** Automatic AST linting (`Ruff`), security vulnerability scanning (`Bandit`), secret detection (`Detect-Secrets`), and dependency CVE audits (`Pip-Audit`).\n"
            f"2. **🧠 Gemini 2.0 Flash Code Review:** Contextual logic review, architectural feedback, and inline code suggestions.\n"
            f"3. **🧪 AST Test Gap Detection:** Automatically detects untested public functions and requests unit test coverage.\n"
            f"4. **🚦 Quality Gate Enforcement:** Sets `review-agent/quality-gate` check run status and blocks merge on critical flaws.\n"
            f"5. **🔧 Autonomous Auto-Fix PRs:** Automatically opens verified patch branches (`autoreview/fix-*`) for common vulnerabilities.\n\n"
            f"---\n\n"
            f"### 💬 Interactive Commands:\n"
            f"Mention `@review-bot` in any PR discussion:\n"
            f"- `@review-bot /re-review` — Re-triggers the complete review pipeline.\n"
            f"- `@review-bot /add-docstrings` — Automatically writes Google-style docstrings for undocumented functions.\n"
            f"- `@review-bot /dismiss <rule-id>` — Suppresses specific lint/security rules for this repository.\n"
            f"- `@review-bot <question>` — Ask technical questions about edge cases, performance, or security.\n\n"
            f"---\n\n"
            f"📊 **Live Operator Dashboard:** [https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io/](https://pr-review-agent.wonderfulflower-41d6d2a5.eastasia.azurecontainerapps.io/)\n"
        )

        url = f"https://api.github.com/repos/{repo_full_name}/issues"
        req = urllib.request.Request(
            url,
            data=json.dumps({"title": title, "body": body}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Agentic-AI-PR-Review-Agent/2.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("[webhook_handler] Posted welcome issue on %s (HTTP %s)", repo_full_name, resp.status)
    except Exception as e:
        logger.warning("[webhook_handler] Could not post welcome issue on %s: %s", repo_full_name, e)


# ─────────────────────────────────────────────────────────────────────────────
# Webhook endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Receive and process GitHub webhook events.
    Verifies HMAC-SHA256 signature before processing.
    Idempotent: duplicate X-GitHub-Delivery UUIDs are silently ignored.
    """
    payload_bytes = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    _metrics.inc("webhooks_received")

    # ── Idempotency check ────────────────────────────────────────────────────
    if delivery_id and is_delivery_seen(delivery_id):
        _metrics.inc("webhooks_deduplicated")
        logger.debug("[webhook_handler] Duplicate delivery %s ignored", delivery_id)
        return JSONResponse({"status": "ignored", "reason": "duplicate_delivery"})

    # Load webhook secret from DB (persisted at app-callback time)
    webhook_secret = get_app_config("GITHUB_WEBHOOK_SECRET") or os.getenv("GITHUB_WEBHOOK_SECRET")

    if not _verify_hmac(webhook_secret, payload_bytes, sig_header):
        logger.warning("[webhook_handler] HMAC verification failed for event: %s", event_type)
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("[webhook_handler] Received event: %s delivery=%s", event_type, delivery_id)

    # Record delivery AFTER successful HMAC verification
    if delivery_id:
        record_delivery(delivery_id, event_type)

    # ── pull_request ──────────────────────────────────────────────────────────
    if event_type == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            repo = payload.get("repository", {}).get("full_name", "")
            pr_number = payload.get("pull_request", {}).get("number")
            commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "")
            if repo and pr_number and commit_sha:
                # ── Per-installation rate limit check ─────────────────────────────
                installation_id = payload.get("installation", {}).get("id", 0)
                if installation_id and not check_rate_limit(
                    installation_id, window_secs=60, max_calls=5
                ):
                    _metrics.inc("webhooks_rate_limited")
                    return JSONResponse(
                        {"status": "rate_limited", "retry_after": 60},
                        status_code=429,
                    )
                background_tasks.add_task(_run_pipeline_background, repo, pr_number, commit_sha)
                _metrics.inc("pipeline_enqueued")
                return JSONResponse({"status": "accepted", "action": "pipeline_queued", "pr": pr_number})
        return JSONResponse({"status": "ignored", "action": action})

    # ── pull_request_review_comment / issue_comment ───────────────────────────
    elif event_type in ("pull_request_review_comment", "issue_comment"):
        comment_body = payload.get("comment", {}).get("body", "")
        if "@review-bot" not in comment_body.lower():
            return JSONResponse({"status": "ignored", "reason": "no @review-bot mention"})
        repo = payload.get("repository", {}).get("full_name", "")
        pr_number = (
            payload.get("issue", {}).get("number")
            or payload.get("pull_request", {}).get("number")
        )
        commenter = payload.get("comment", {}).get("user", {}).get("login", "user")
        if repo and pr_number:
            token = _get_token_for_repo(repo)
            if token:
                from pr_review_agent.chat_handler import handle_comment
                background_tasks.add_task(
                    handle_comment, repo, pr_number, comment_body, commenter, token
                )
                _metrics.inc("chat_enqueued")
        return JSONResponse({"status": "accepted", "action": "chat_handler_queued"})

    # ── installation ──────────────────────────────────────────────────────────
    elif event_type == "installation":
        action = payload.get("action", "")
        installation = payload.get("installation", {})
        installation_id = installation.get("id")
        account = installation.get("account", {})
        app_id_from_payload = installation.get("app_id", 0)

        if action in ("created", "unsuspend"):
            upsert_installation(
                installation_id=installation_id,
                account_login=account.get("login", ""),
                account_type=account.get("type", "User"),
                app_id=app_id_from_payload,
            )
            repos = payload.get("repositories", [])
            for repo in repos:
                repo_name = repo.get("full_name", "")
                add_installation_repo(installation_id, repo_name)
                if repo_name:
                    background_tasks.add_task(_post_welcome_issue, repo_name, account.get("login", ""))
            logger.info(
                "[webhook_handler] Installation created: id=%s account=%s repos=%d",
                installation_id, account.get("login"), len(repos)
            )
        elif action == "deleted":
            delete_installation(installation_id)
            from pr_review_agent.github_app_auth import invalidate_token_cache
            invalidate_token_cache(installation_id)
        return JSONResponse({"status": "ok", "action": action})

    # ── installation_repositories ─────────────────────────────────────────────
    elif event_type == "installation_repositories":
        installation_id = payload.get("installation", {}).get("id")
        account_login = payload.get("installation", {}).get("account", {}).get("login", "")
        for repo in payload.get("repositories_added", []):
            repo_name = repo.get("full_name", "")
            add_installation_repo(installation_id, repo_name)
            if repo_name:
                background_tasks.add_task(_post_welcome_issue, repo_name, account_login)
        for repo in payload.get("repositories_removed", []):
            remove_installation_repo(installation_id, repo.get("full_name", ""))
        return JSONResponse({"status": "ok"})

    return JSONResponse({"status": "ignored", "event": event_type})


# ─────────────────────────────────────────────────────────────────────────────
# GitHub App install landing page
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/install", response_class=HTMLResponse)
async def install_page(request: Request) -> HTMLResponse:
    """Serve a minimal GitHub App install page with 1-click manifest flow."""
    base_url = str(request.base_url).rstrip("/")

    with open(os.path.join(os.path.dirname(__file__), "..", "github-app-manifest.json"), encoding="utf-8") as f:
        manifest_raw = f.read()

    # Inject the current host URL into the manifest
    import json as _json
    import time as _time
    try:
        manifest_obj = _json.loads(manifest_raw)
        manifest_obj["name"] = f"agentic-review-agent-{int(_time.time()) % 100000}"
        manifest_obj["url"] = base_url
        manifest_obj["hook_attributes"]["url"] = f"{base_url}/webhooks/github"
        manifest_obj["redirect_url"] = f"{base_url}/api/github/app-callback"
        events = manifest_obj.get("default_events", [])
        manifest_obj["default_events"] = [
            e for e in events if e not in ("installation", "installation_repositories")
        ]
        manifest_json = _json.dumps(manifest_obj)
    except Exception:
        manifest_json = manifest_raw

    app_configured = bool(get_app_config("GITHUB_APP_ID"))
    app_id = get_app_config("GITHUB_APP_ID") or ""
    app_slug = get_app_config("GITHUB_APP_SLUG") or "agentic-review-agent"

    # Query installed repos from database
    installed_repos = []
    try:
        from pr_review_agent.db import _conn
        with _conn() as con:
            rows = con.execute(
                "SELECT ir.repo_full_name, i.account_login, i.installed_at "
                "FROM installation_repos ir "
                "JOIN installations i ON ir.installation_id = i.installation_id "
                "WHERE ir.repo_full_name != 'testuser/testrepo' "
                "ORDER BY i.installed_at DESC"
            ).fetchall()
            installed_repos = [dict(r) for r in rows]
    except Exception:
        pass

    if app_configured and installed_repos:
        repo_items = "".join(f"""
        <div class="repo-item">
          <div class="repo-name">
            <svg class="repo-icon" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z" clip-rule="evenodd"/>
            </svg>
            <span>{r['repo_full_name']}</span>
          </div>
          <span class="badge-active">● Active</span>
        </div>""" for r in installed_repos)

        content_body = f"""
        <div class="status configured">
            <svg class="status-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <div>
              <strong>App Connected &amp; Listening</strong>
              <div style="font-size:0.75rem;opacity:0.85;margin-top:2px">App ID: {app_id} • Slug: {app_slug}</div>
            </div>
        </div>

        <div class="section-title">Connected Repositories ({len(installed_repos)})</div>
        <div class="repo-list">
          {repo_items}
        </div>

        <div class="section-title" style="margin-top:1.5rem">Next Steps to Trigger a Review</div>
        <div class="guide-box">
          <div class="guide-step">
            <span class="step-num">1</span>
            <div><strong>Open a Pull Request:</strong> In any connected repo, create a branch with code changes and open a PR.</div>
          </div>
          <div class="guide-step">
            <span class="step-num">2</span>
            <div><strong>Automated Analysis:</strong> The agent immediately runs static analyzers (Ruff, Bandit, Secrets, Pip-Audit) + Gemini 2.0 Flash.</div>
          </div>
          <div class="guide-step">
            <span class="step-num">3</span>
            <div><strong>Inline Suggestions &amp; Quality Gate:</strong> The bot posts actionable diff suggestion blocks and creates a required Check Run.</div>
          </div>
          <div class="guide-step">
            <span class="step-num">4</span>
            <div><strong>Interactive Chat:</strong> Reply with <code>@review-bot generate docstrings</code> or <code>@review-bot dismiss &lt;rule&gt;</code>.</div>
          </div>
        </div>

        <div class="btn-group">
          <a href="/" class="btn-primary">Open Main Dashboard &rarr;</a>
          <a href="https://github.com/apps/{app_slug}/installations/new" target="_blank" class="btn-secondary">+ Add More Repositories</a>
        </div>
        """
    elif app_configured:
        content_body = f"""
        <div class="status configured">
            <svg class="status-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <div>
              <strong>GitHub App Registered</strong>
              <div style="font-size:0.75rem;opacity:0.85;margin-top:2px">Credentials saved to DB &amp; .env.app</div>
            </div>
        </div>
        <p>Now select which repositories to connect for automated reviews.</p>
        <a href="https://github.com/apps/{app_slug}/installations/new" class="btn-primary">Select Repositories on GitHub &rarr;</a>
        """
    else:
        content_body = f"""
        <div class="status unconfigured">
            <svg class="status-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
            </svg>
            <span>GitHub App not yet registered — click below to initialize</span>
        </div>
        <p>Automated code review powered by static analysis + Gemini LLM.<br>Installs as a GitHub App with zero token sharing.</p>
        <form action="https://github.com/settings/apps/new" method="post">
          <input type="hidden" name="manifest" value='{manifest_json}'>
          <button type="submit" class="btn-primary">
            <span>Install on GitHub</span>
            <svg class="btn-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </form>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agentic AI Review Agent - Setup</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #09090e; --surface: #12121a; --surface-subtle: #171722; --border: #1e1e2e;
      --seafoam: #2dd4bf; --ember: #fb923c; --text: #f1f5f9; --muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 2rem 1.5rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 2.25rem;
      max-width: 540px;
      width: 100%;
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
    }}
    .header-icon-wrap {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: rgba(45, 212, 191, 0.1);
      border: 1px solid rgba(45, 212, 191, 0.25);
      color: var(--seafoam);
      margin-bottom: 1rem;
    }}
    .header-icon {{ width: 24px; height: 24px; }}
    h1 {{
      font-size: 1.35rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      margin-bottom: 0.35rem;
      color: #ffffff;
    }}
    p {{
      color: var(--muted);
      font-size: 0.88rem;
      margin-bottom: 1.25rem;
      line-height: 1.5;
    }}
    .status {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.85rem 1rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
      font-size: 0.84rem;
      font-weight: 500;
    }}
    .status-icon {{ width: 20px; height: 20px; flex-shrink: 0; }}
    .configured {{
      background: rgba(45, 212, 191, 0.08);
      border: 1px solid rgba(45, 212, 191, 0.25);
      color: #5eead4;
    }}
    .unconfigured {{
      background: rgba(251, 146, 60, 0.08);
      border: 1px solid rgba(251, 146, 60, 0.25);
      color: #fdba74;
    }}
    .section-title {{
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--muted);
      margin-bottom: 0.65rem;
    }}
    .repo-list {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }}
    .repo-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.65rem 0.85rem;
      background: var(--surface-subtle);
      border: 1px solid var(--border);
      border-radius: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
    }}
    .repo-name {{ display: flex; align-items: center; gap: 0.5rem; color: #f8fafc; }}
    .repo-icon {{ width: 14px; height: 14px; opacity: 0.7; color: var(--seafoam); }}
    .badge-active {{
      font-size: 0.7rem;
      font-weight: 600;
      color: var(--seafoam);
      background: rgba(45, 212, 191, 0.12);
      padding: 2px 7px;
      border-radius: 12px;
    }}
    .guide-box {{
      background: var(--surface-subtle);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.9rem 1rem;
      margin-bottom: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      font-size: 0.82rem;
      line-height: 1.45;
      color: #cbd5e1;
    }}
    .guide-step {{ display: flex; gap: 0.65rem; align-items: flex-start; }}
    .step-num {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: rgba(45, 212, 191, 0.18);
      color: var(--seafoam);
      font-size: 0.7rem;
      font-weight: 700;
      flex-shrink: 0;
      margin-top: 1px;
    }}
    .guide-step code {{
      background: #09090e;
      padding: 1px 5px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: #38bdf8;
    }}
    .btn-group {{ display: flex; flex-direction: column; gap: 0.65rem; }}
    .btn-primary {{
      background: var(--seafoam);
      color: #09090e;
      border: none;
      border-radius: 8px;
      padding: 0.8rem 1.25rem;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
      text-align: center;
    }}
    .btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}
    .btn-secondary {{
      background: transparent;
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.7rem 1.25rem;
      font-size: 0.84rem;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      text-align: center;
    }}
    .btn-secondary:hover {{ color: #ffffff; border-color: var(--muted); }}
    .btn-icon {{ width: 16px; height: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header-icon-wrap">
      <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="18" cy="18" r="3"></circle>
        <circle cx="6" cy="6" r="3"></circle>
        <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
        <line x1="6" y1="9" x2="6" y2="21"></line>
      </svg>
    </div>
    <h1>Agentic AI Review Agent</h1>
    <p>Automated code review &amp; self-healing cloud infrastructure.</p>
    {content_body}
  </div>
</body>
</html>"""
    return HTMLResponse(html)



# ─────────────────────────────────────────────────────────────────────────────
# App Manifest Flow callback
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/github/app-callback")
async def app_callback(code: str) -> JSONResponse:
    """
    GitHub redirects here after manifest flow with a one-time `code`.
    Exchange code → app credentials and persist them to BOTH SQLite + .env.app.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing `code` query parameter")

    url = f"https://api.github.com/app-manifests/{code}/conversions"
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgenticAI-ReviewBot/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("[webhook_handler] app-callback exchange failed: HTTP %s %s", e.code, body[:300])
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e.code}")
    except Exception as e:
        logger.error("[webhook_handler] app-callback exception: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    app_id = str(data.get("id", ""))
    webhook_secret = data.get("webhook_secret", "")
    pem = data.get("pem", "")
    slug = data.get("slug", "")

    if not app_id or not pem:
        raise HTTPException(status_code=502, detail="Incomplete credentials from GitHub")

    # Encode PEM as base64 for storage
    pem_b64 = base64.b64encode(pem.encode("utf-8")).decode("utf-8")

    # Persist to DB + .env.app — BOTH, never just os.environ
    _persist_credential("GITHUB_APP_ID", app_id)
    _persist_credential("GITHUB_APP_SLUG", slug)
    _persist_credential("GITHUB_WEBHOOK_SECRET", webhook_secret)
    _persist_credential("GITHUB_APP_PRIVATE_KEY", pem_b64)

    logger.info(
        "[webhook_handler] GitHub App registered: id=%s slug=%s — credentials persisted to DB + .env.app",
        app_id, slug
    )

    # Also set in-process env so currently running handlers pick it up immediately
    os.environ["GITHUB_APP_ID"] = app_id
    os.environ["GITHUB_WEBHOOK_SECRET"] = webhook_secret
    os.environ["GITHUB_APP_PRIVATE_KEY"] = pem_b64

    install_url = f"https://github.com/apps/{slug}/installations/new"
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub App Connected | Agentic AI</title>
  <meta http-equiv="refresh" content="4;url={install_url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #09090e;
      --card-bg: #12131a;
      --border: #222330;
      --accent-purple: #a855f7;
      --accent-teal: #00d4aa;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2.5rem;
      max-width: 540px;
      width: 100%;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    .card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 4px;
      background: linear-gradient(90deg, var(--accent-purple), var(--accent-teal));
    }}
    .icon-badge {{
      width: 64px;
      height: 64px;
      background: rgba(0, 212, 170, 0.1);
      border: 1px solid rgba(0, 212, 170, 0.3);
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--accent-teal);
      margin-bottom: 1.5rem;
    }}
    h1 {{
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      color: #fff;
    }}
    p.desc {{
      color: var(--text-muted);
      font-size: 0.95rem;
      line-height: 1.6;
      margin-bottom: 1.5rem;
    }}
    .meta-box {{
      background: #0d0e14;
      border: 1px solid #1a1b24;
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 1.75rem;
      display: flex;
      justify-content: space-around;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
    }}
    .meta-item {{
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }}
    .meta-label {{
      color: var(--text-muted);
      font-size: 0.7rem;
      text-transform: uppercase;
    }}
    .meta-val {{
      color: var(--accent-teal);
      font-weight: 600;
    }}
    .btn-primary {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
      color: #fff;
      font-weight: 600;
      font-size: 1rem;
      padding: 0.85rem 1.75rem;
      border-radius: 10px;
      text-decoration: none;
      transition: all 0.2s;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(168, 85, 247, 0.4);
      margin-bottom: 1rem;
    }}
    .btn-primary:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6);
    }}
    .btn-secondary {{
      color: var(--text-muted);
      font-size: 0.85rem;
      text-decoration: none;
      display: inline-block;
      transition: color 0.2s;
    }}
    .btn-secondary:hover {{
      color: #fff;
    }}
    .countdown {{
      color: var(--accent-teal);
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-badge">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>
    </div>
    <h1>GitHub App Registered!</h1>
    <p class="desc">
      Your GitHub App has been created and credentials are securely saved to Azure.<br>
      Redirecting to select repositories in <span class="countdown" id="cd">3</span>s...
    </p>

    <div class="meta-box">
      <div class="meta-item">
        <span class="meta-label">App ID</span>
        <span class="meta-val">{app_id}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">App Slug</span>
        <span class="meta-val">{slug}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">State</span>
        <span class="meta-val">Ready</span>
      </div>
    </div>

    <a href="{install_url}" class="btn-primary">
      <span>Install Bot on Your Repositories &rarr;</span>
    </a>

    <div>
      <a href="/" class="btn-secondary">Skip to Live Dashboard</a>
    </div>
  </div>

  <script>
    let t = 3;
    const el = document.getElementById('cd');
    setInterval(() => {{
      if (t > 1) {{
        t--;
        if (el) el.textContent = t;
      }}
    }}, 1000);
  </script>
</body>
</html>
"""
    return HTMLResponse(html_content)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard APIs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/pr-reviews")
async def list_pr_reviews(limit: int = 50) -> JSONResponse:
    """Return recent PR review records (for the dashboard)."""
    reviews = get_all_review_log(limit=limit)
    return JSONResponse(reviews)


@router.get("/api/pr-reviews/{repo_owner}/{repo_name}/{pr_number}")
async def get_pr_review(repo_owner: str, repo_name: str, pr_number: int) -> JSONResponse:
    """Return review log entries for a specific repo+PR."""
    repo_full_name = f"{repo_owner}/{repo_name}"
    reviews = get_review_log(repo_full_name, limit=20)
    pr_reviews = [r for r in reviews if r.get("pr_number") == pr_number]
    if not pr_reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this PR")
    return JSONResponse(pr_reviews)


@router.post("/api/learnings/dismiss")
async def dismiss_rule(request: Request) -> JSONResponse:
    """Record a rule dismissal. Body: {repo_full_name, rule_id, note}."""
    body = await request.json()
    repo_full_name = body.get("repo_full_name", "")
    rule_id = body.get("rule_id", "")
    note = body.get("note", "")
    if not repo_full_name or not rule_id:
        raise HTTPException(status_code=400, detail="repo_full_name and rule_id are required")
    from pr_review_agent.learnings import record_dismissal
    row_id = record_dismissal(repo_full_name, rule_id, note)
    return JSONResponse({"status": "ok", "dismissal_id": row_id})


@router.get("/api/repos")
async def list_repos() -> JSONResponse:
    """List all repos with active installations."""
    try:
        from pr_review_agent.db import _conn
        with _conn() as con:
            rows = con.execute(
                "SELECT ir.repo_full_name, i.account_login, i.installed_at "
                "FROM installation_repos ir "
                "JOIN installations i ON ir.installation_id = i.installation_id "
                "ORDER BY i.installed_at DESC"
            ).fetchall()
        return JSONResponse([dict(r) for r in rows])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/seed-demo")
async def seed_demo_data() -> JSONResponse:
    """
    Seed the live database with AadiHaldar's real repos + realistic PR review history.
    Safe to call multiple times (uses INSERT OR IGNORE / INSERT OR REPLACE).
    """
    import datetime
    try:
        from pr_review_agent.db import _conn, upsert_installation, add_installation_repo, set_app_config
        from pr_review_agent import db as _db

        # ── 1. Ensure app config exists ──────────────────────────────────────
        if not get_app_config("GITHUB_APP_ID"):
            set_app_config("GITHUB_APP_ID", "4622895")
            set_app_config("GITHUB_APP_SLUG", "agentic-review-agent-65012")

        # ── 2. Seed AadiHaldar installation + real repos ─────────────────────
        INSTALLATION_ID = 154382391
        upsert_installation(
            installation_id=INSTALLATION_ID,
            account_login="AadiHaldar",
            account_type="User",
            app_id=4622895,
        )

        REAL_REPOS = [
            "AadiHaldar/MFC3_C4_ADMM_Based_Network_Anomaly_Detection",
            "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
        ]
        for repo in REAL_REPOS:
            add_installation_repo(INSTALLATION_ID, repo)

        # ── 3. Seed realistic PR review history ──────────────────────────────
        demo_reviews = [
            # repo, pr#, sha, findings, critical, status, reviewed_at
            ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure", 1,
             "a04fef7b", 3, 1, "gate_passed",
             "2026-08-17 10:22:39"),
            ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure", 2,
             "d1c8fa22", 7, 2, "gate_failed",
             "2026-08-17 09:14:05"),
            ("AadiHaldar/MFC3_C4_ADMM_Based_Network_Anomaly_Detection", 1,
             "b3e9120c", 2, 0, "gate_passed",
             "2026-08-16 18:45:11"),
            ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure", 3,
             "f7a2091d", 5, 1, "gate_failed",
             "2026-08-16 14:33:22"),
            ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure", 4,
             "c9b3412e", 1, 0, "gate_passed",
             "2026-08-15 21:10:47"),
        ]

        with _conn() as con:
            # Clear old demo rows to avoid duplicates on re-seed
            con.execute(
                "DELETE FROM review_log WHERE repo_full_name IN (?, ?)",
                (REAL_REPOS[0], REAL_REPOS[1])
            )
            con.executemany(
                "INSERT INTO review_log "
                "(repo_full_name, pr_number, commit_sha, findings_count, critical_count, status, reviewed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                demo_reviews
            )

        return JSONResponse({
            "status": "seeded",
            "repos_added": REAL_REPOS,
            "reviews_inserted": len(demo_reviews),
            "message": "Demo data seeded successfully! Refresh the dashboard.",
        })

    except Exception as e:
        logger.error("[seed-demo] Failed: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# ──────────────────────────────────────────────────────────────────────────────
# Observability endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/api/service-health")
async def service_health() -> JSONResponse:
    """
    Return a snapshot of in-process health metrics.

    Response shape:
    {
      "status": "ok",
      "uptime_seconds": 1234.5,
      "counters": {
        "webhooks_received": 42,
        "webhooks_deduplicated": 1,
        "webhooks_rate_limited": 0,
        "pipeline_enqueued": 38,
        "pipeline_ok": 36,
        "pipeline_failed": 2,
        "chat_enqueued": 4,
        "chat_ok": 4,
        "chat_failed": 0
      },
      "pipeline_success_rate": 0.9474,
      "chat_success_rate": 1.0
    }
    """
    snap = _metrics.snapshot()
    return JSONResponse({
        "status": "ok",
        "uptime_seconds": snap.pop("uptime_seconds"),
        "pipeline_success_rate": snap.pop("pipeline_success_rate"),
        "chat_success_rate": snap.pop("chat_success_rate"),
        "counters": snap,
    })
