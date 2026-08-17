"""
pr_review_agent/chat_handler.py — @review-bot comment handler.

Routes @review-bot mentions to either:
  - A special "generate docstrings" flow (AST-verified, opens suggestion PR)
  - General Q&A (Gemini with PR diff + comment thread as context)

Special commands:
  @review-bot generate docstrings   → AST scan → Gemini generate → suggestion blocks
  @review-bot dismiss <rule_id>     → calls learnings.record_dismissal
  @review-bot re-review             → triggers full pipeline re-run
  @review-bot [anything else]       → general Q&A
"""
import ast
import base64
import json
import logging
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GH_API = "https://api.github.com"
_GH_HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AgenticAI-ReviewBot/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Maximum user-controlled text embedded in any LLM prompt.
_MAX_USER_INPUT_CHARS = 400

# Patterns that are telltale prompt-injection attempts.
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|user|assistant)\s*>", re.IGNORECASE),
    re.compile(r"\[\s*(INST|SYS)\s*\]", re.IGNORECASE),
    re.compile(r"\\n\\n(Human|Assistant):", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]


def _sanitize_user_input(text: str) -> str:
    """
    Sanitize user-supplied text before embedding it in an LLM prompt.

    Steps:
    1. Strip null bytes.
    2. Detect and redact known prompt-injection patterns.
    3. Hard-cap length to _MAX_USER_INPUT_CHARS.
    """
    # 1. Strip null bytes
    text = text.replace("\x00", "")

    # 2. Redact injection patterns
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)

    # 3. Cap length
    if len(text) > _MAX_USER_INPUT_CHARS:
        text = text[:_MAX_USER_INPUT_CHARS] + "...[truncated]"

    return text


def _gh_headers(token: str) -> Dict[str, str]:
    return {**_GH_HEADERS_BASE, "Authorization": f"Bearer {token}"}


def _gh_get(url: str, token: str) -> Any:
    req = urllib.request.Request(url, headers=_gh_headers(token))
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _gh_post(url: str, payload: Any, token: str, method: str = "POST") -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={**_gh_headers(token), "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Docstring generation
# ─────────────────────────────────────────────────────────────────────────────

def _find_functions_missing_docstrings(source: str) -> List[Dict[str, Any]]:
    """
    Use ast to find all top-level and method-level functions/classes that
    are missing docstrings. Returns list of {name, lineno, type}.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                node_type = "class" if isinstance(node, ast.ClassDef) else "function"
                missing.append({"name": node.name, "lineno": node.lineno, "type": node_type})
    return missing


def _generate_docstrings_for_file(
    filename: str,
    source: str,
    missing: List[Dict[str, Any]],
    gemini_client,
) -> Optional[str]:
    """Ask Gemini to insert docstrings for the missing symbols and return the updated file."""
    names = ", ".join(f"`{m['name']}`" for m in missing[:15])
    prompt = f"""You are adding Python docstrings to an existing file.

File: {filename}
Functions/classes missing docstrings: {names}

Current file content:
```python
{source[:5000]}
```

Add Google-style docstrings to all listed functions and classes. Do NOT change any other code.
Return the COMPLETE updated file content. No markdown fences, no explanation — just the code."""

    try:
        from google import genai
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-z]*\n?", "", text).rstrip("`").strip()
        return text
    except Exception as e:
        logger.warning("[chat_handler] Docstring generation failed for %s: %s", filename, e)
        return None


def _handle_generate_docstrings(
    repo_full_name: str,
    pr_number: int,
    token: str,
    gemini_client,
) -> str:
    """
    Generate docstrings for missing ones in PR-changed Python files.
    Opens suggestion blocks in a reply comment; optionally creates a fix PR.
    """
    from pr_review_agent.pipeline import fetch_pr_diff

    diff_files = fetch_pr_diff(repo_full_name, pr_number, token)
    py_files = [f for f in diff_files if f["filename"].endswith(".py")
                and not f["filename"].endswith("__init__.py")]

    if not py_files:
        return "No Python files changed in this PR — nothing to docstring."

    results = []
    for f in py_files[:5]:  # cap to 5 files per invocation
        filename = f["filename"]
        try:
            pr_info = _gh_get(f"{_GH_API}/repos/{repo_full_name}/pulls/{pr_number}", token)
            head_sha = pr_info["head"]["sha"]
            file_info = _gh_get(
                f"{_GH_API}/repos/{repo_full_name}/contents/{filename}?ref={head_sha}", token
            )
            source = base64.b64decode(file_info["content"].replace("\n", "")).decode("utf-8")
        except Exception:
            # Fallback: reconstruct from patch
            patch = f.get("patch", "")
            source_lines = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
            source = "\n".join(source_lines)

        missing = _find_functions_missing_docstrings(source)
        if not missing:
            results.append(f"✅ `{filename}` — all public functions already have docstrings.")
            continue

        updated = _generate_docstrings_for_file(filename, source, missing, gemini_client)
        if not updated:
            results.append(f"⚠️ `{filename}` — {len(missing)} missing docstrings but generation failed.")
            continue

        names = ", ".join(f"`{m['name']}`" for m in missing)
        results.append(
            f"**`{filename}`** — added docstrings for: {names}\n\n"
            f"```suggestion\n{updated[:2000]}{'...' if len(updated) > 2000 else ''}\n```"
        )

    if results:
        return "\n\n---\n\n".join(results)
    return "No functions missing docstrings in the changed Python files."


# ─────────────────────────────────────────────────────────────────────────────
# Dismiss command
# ─────────────────────────────────────────────────────────────────────────────

def _handle_dismiss(
    repo_full_name: str,
    rule_id: str,
    commenter: str,
) -> str:
    if not rule_id.strip():
        return "Please specify a rule ID to dismiss, e.g. `@review-bot dismiss ruff/E501`"
    try:
        from pr_review_agent.learnings import record_dismissal
        row_id = record_dismissal(repo_full_name, rule_id.strip(), note=f"Dismissed by @{commenter}")
        return (
            f"✅ Rule `{rule_id.strip()}` has been dismissed for `{repo_full_name}` (id={row_id}). "
            f"Future reviews will suppress this rule."
        )
    except Exception as e:
        logger.error("[chat_handler] Dismiss failed: %s", e)
        return f"❌ Failed to dismiss rule `{rule_id}`: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# General Q&A
# ─────────────────────────────────────────────────────────────────────────────

def _handle_general_qa(
    repo_full_name: str,
    pr_number: int,
    question: str,
    comment_thread: List[Dict[str, Any]],
    token: str,
    gemini_client,
) -> str:
    """Use Gemini to answer a question about the PR with full context."""
    try:
        from pr_review_agent.pipeline import fetch_pr_diff
        diff_files = fetch_pr_diff(repo_full_name, pr_number, token)
    except Exception:
        diff_files = []

    diff_summary = "\n".join(
        f"- {f['filename']} (+{f['additions']}/-{f['deletions']})"
        for f in diff_files[:20]
    )
    thread_text = "\n".join(
        f"@{c.get('user', {}).get('login', 'user')}: {c.get('body', '')[:300]}"
        for c in comment_thread[-10:]  # last 10 comments for context
    )

    prompt = f"""You are a helpful code review assistant for GitHub PR #{pr_number} in {repo_full_name}.

Changed files:
{diff_summary or 'Not available'}

Recent comment thread:
{thread_text or 'No prior comments'}

User question: {_sanitize_user_input(question)}

Answer concisely and helpfully. If asking about a specific file or function, refer to the actual diff content. Keep response under 400 words."""

    try:
        from google import genai
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error("[chat_handler] Q&A generation failed: %s", e)
        return f"I encountered an error while processing your question: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _extract_command(comment_body: str) -> tuple[str, str]:
    """
    Parse @review-bot <command> [args] from a comment body.
    Returns (command, args_string).
    """
    match = re.search(r"@review-bot\s+(.+?)(?:\n|$)", comment_body, re.IGNORECASE)
    if not match:
        return "qa", comment_body
    full_cmd = match.group(1).strip()
    parts = full_cmd.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


def handle_comment(
    repo_full_name: str,
    pr_number: int,
    comment_body: str,
    commenter: str,
    token: str,
    gemini_client=None,
) -> Dict[str, Any]:
    """
    Entry point for @review-bot comments (from webhook_handler).
    Routes to the appropriate handler and posts a reply comment.
    """
    if "@review-bot" not in comment_body.lower():
        return {"action": "ignored", "reason": "No @review-bot mention"}

    if gemini_client is None:
        try:
            from google import genai
            gemini_client = genai.Client()
        except Exception:
            pass

    cmd, args = _extract_command(comment_body)

    # Fetch comment thread for context
    comment_thread = []
    try:
        comment_thread = _gh_get(
            f"{_GH_API}/repos/{repo_full_name}/issues/{pr_number}/comments", token
        )
    except Exception:
        pass

    # Route command
    if cmd in ("generate", "docstring", "docstrings", "/add-docstrings", "add-docstrings", "/docstrings", "/docstring", "/generate-docstrings"):
        reply = _handle_generate_docstrings(repo_full_name, pr_number, token, gemini_client)
        action = "generate_docstrings"
    elif cmd == "dismiss":
        reply = _handle_dismiss(repo_full_name, args, commenter)
        action = "dismiss"
    elif cmd == "re-review":
        # Trigger full pipeline re-run (lazy import to avoid circular)
        try:
            from pr_review_agent.pipeline import run_full_pipeline
            pr_info = _gh_get(f"{_GH_API}/repos/{repo_full_name}/pulls/{pr_number}", token)
            commit_sha = pr_info["head"]["sha"]
            result = run_full_pipeline(repo_full_name, pr_number, commit_sha, token, gemini_client=gemini_client)
            reply = (
                f"♻️ Re-review complete: {result.get('findings_count', 0)} finding(s), "
                f"quality gate: `{result.get('quality_gate', 'unknown')}`."
            )
        except Exception as e:
            reply = f"❌ Re-review failed: {e}"
        action = "re_review"
    else:
        # General Q&A
        question = f"{cmd} {args}".strip()
        reply = _handle_general_qa(
            repo_full_name, pr_number, question, comment_thread, token, gemini_client
        )
        action = "qa"

    # Post reply
    reply_body = f"@{commenter} {reply}"
    try:
        url = f"{_GH_API}/repos/{repo_full_name}/issues/{pr_number}/comments"
        res = _gh_post(url, {"body": reply_body}, token)
        logger.info("[chat_handler] Posted @review-bot reply (action=%s) to %s#%s", action, repo_full_name, pr_number)
        return {"action": action, "comment_id": res.get("id"), "reply_preview": reply[:100]}
    except Exception as e:
        logger.error("[chat_handler] Failed to post reply: %s", e)
        return {"action": action, "error": str(e)}
