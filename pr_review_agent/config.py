"""
pr_review_agent/config.py — Per-repository .review-agent.yml configuration loader.

Fetches from GitHub API and provides a typed ReviewConfig dataclass with
sensible defaults. All fields are optional in the YAML.
"""
import base64
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = ".review-agent.yml"


@dataclass
class ReviewConfig:
    """Typed configuration resolved from .review-agent.yml + defaults."""
    # Glob patterns of files to skip entirely (e.g. 'tests/**', '*.md')
    ignore_globs: List[str] = field(default_factory=list)
    # Minimum severity level to report: 'info' | 'warning' | 'error' | 'critical'
    severity_threshold: str = "warning"
    # Checker IDs to disable (e.g. ['detect-secrets', 'ruff'])
    disabled_checks: List[str] = field(default_factory=list)
    # Min changed files before generating a Mermaid call-graph diagram
    diagram_min_files: int = 3
    # Block PR merge (via Check Run failure) if any critical findings exist
    quality_gate_on_critical: bool = True
    # Maximum number of diff hunks before chunking guard truncates
    max_hunks: int = 50
    # LLM confidence threshold below which findings are dropped
    llm_confidence_threshold: float = 0.7
    # Whether to post inline suggestion blocks for auto-fixable findings
    post_suggestions: bool = True
    # Whether to auto-create a fix PR for non-deterministic LLM fixes
    auto_fix_pr: bool = False


_SEVERITY_ORDER = ["info", "warning", "error", "critical"]


def severity_meets_threshold(severity: str, threshold: str) -> bool:
    """Return True if severity is at or above threshold."""
    try:
        return _SEVERITY_ORDER.index(severity.lower()) >= _SEVERITY_ORDER.index(threshold.lower())
    except ValueError:
        return True  # Unknown severities always pass through


def _fetch_github_file(repo_full_name: str, path: str, token: str) -> Optional[str]:
    """Fetch a file from a GitHub repo and return its decoded content, or None."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgenticAI-ReviewBot/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content_b64 = data.get("content", "").replace("\n", "")
        return base64.b64decode(content_b64).decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # File doesn't exist — use defaults
        logger.warning("[config] HTTP %s fetching %s from %s", e.code, path, repo_full_name)
        return None
    except Exception as e:
        logger.warning("[config] Failed to fetch %s from %s: %s", path, repo_full_name, e)
        return None


def _parse_yaml(text: str) -> dict:
    """Parse YAML using PyYAML if available, else fall back to a minimal parser."""
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    # Minimal fallback: parse key: value pairs (no nested structures)
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()
    return result


def _coerce_list(val) -> List[str]:
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str):
        return [x.strip() for x in val.split(",") if x.strip()]
    return []


def fetch_repo_config(repo_full_name: str, token: str) -> ReviewConfig:
    """
    Fetch and parse .review-agent.yml from the repo's default branch.
    Returns a ReviewConfig with defaults merged with any overrides found.
    """
    raw = _fetch_github_file(repo_full_name, CONFIG_FILE_NAME, token)
    if not raw:
        logger.debug("[config] No .review-agent.yml in %s — using defaults", repo_full_name)
        return ReviewConfig()

    try:
        data = _parse_yaml(raw)
    except Exception as e:
        logger.warning("[config] Could not parse .review-agent.yml in %s: %s — using defaults", repo_full_name, e)
        return ReviewConfig()

    cfg = ReviewConfig()
    if "ignore_globs" in data:
        cfg.ignore_globs = _coerce_list(data["ignore_globs"])
    if "severity_threshold" in data:
        val = str(data["severity_threshold"]).lower()
        if val in _SEVERITY_ORDER:
            cfg.severity_threshold = val
    if "disabled_checks" in data:
        cfg.disabled_checks = _coerce_list(data["disabled_checks"])
    if "diagram_min_files" in data:
        try:
            cfg.diagram_min_files = int(data["diagram_min_files"])
        except (ValueError, TypeError):
            pass
    if "quality_gate_on_critical" in data:
        val = data["quality_gate_on_critical"]
        cfg.quality_gate_on_critical = str(val).lower() not in ("false", "0", "no")
    if "max_hunks" in data:
        try:
            cfg.max_hunks = max(1, int(data["max_hunks"]))
        except (ValueError, TypeError):
            pass
    if "llm_confidence_threshold" in data:
        try:
            cfg.llm_confidence_threshold = float(data["llm_confidence_threshold"])
        except (ValueError, TypeError):
            pass
    if "post_suggestions" in data:
        cfg.post_suggestions = str(data["post_suggestions"]).lower() not in ("false", "0", "no")
    if "auto_fix_pr" in data:
        cfg.auto_fix_pr = str(data["auto_fix_pr"]).lower() in ("true", "1", "yes")

    logger.info("[config] Loaded .review-agent.yml for %s: threshold=%s, max_hunks=%s",
                repo_full_name, cfg.severity_threshold, cfg.max_hunks)
    return cfg
