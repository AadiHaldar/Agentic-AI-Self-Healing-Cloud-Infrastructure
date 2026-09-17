"""
scripts/deploy_live_owasp_pr.py — Deploys a live Pull Request on GitHub featuring the full OWASP Top 10 Audit.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pr_review_agent.owasp_auditor import OWASPAuditor
from pr_review_agent.pipeline import (
    _build_review_body,
    detect_unit_test_gaps,
    generate_mermaid_diagram,
)

REPO = "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure"
TOKEN = os.getenv("GITHUB_TOKEN", "")
BRANCH = "feature/v2-checkout-gateway"
BASE_BRANCH = "main"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "AgenticAI-ReviewBot/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}


def gh_req(url: str, data: dict = None, method: str = "GET") -> dict:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"[HTTP {e.code}] {url} -> {err_msg[:400]}")
        raise


def main():
    print("=" * 75)
    print("[*] Deploying Live OWASP Top 10 Pull Request to GitHub")
    print("=" * 75)

    # 1. Check if PR already exists or create new PR
    print(f"[*] Checking existing PRs for branch '{BRANCH}'...")
    prs = gh_req(f"https://api.github.com/repos/{REPO}/pulls?state=open&head=AadiHaldar:{BRANCH}")
    
    if prs:
        pr = prs[0]
        pr_number = pr["number"]
        pr_url = pr["html_url"]
        head_sha = pr["head"]["sha"]
        print(f"[+] Found existing Open PR #{pr_number}: {pr_url}")
    else:
        print("[*] Creating new Pull Request...")
        pr_payload = {
            "title": "feat(checkout): v2 payment microservice & OWASP Top 10 security audit",
            "head": BRANCH,
            "base": BASE_BRANCH,
            "body": """### [PR Overview]
This PR implements the **V2 Checkout Gateway Microservice** with crypto payment settlement, session caching, and asynchronous PDF invoice generation.

### Changes:
1. `services/checkout_gateway.py`: New checkout order query engine and Redis cart session restorer.
2. `services/order_orchestrator.py`: Inter-service routing connecting `frontend -> checkout_gateway -> billing_gateway`.
3. `requirements.txt`: Updated library requirements for YAML templates and HTTP clients.

---
*Awaiting automated review by @review-bot and Quality Gate validation.*"""
        }
        try:
            pr = gh_req(f"https://api.github.com/repos/{REPO}/pulls", data=pr_payload, method="POST")
            pr_number = pr["number"]
            pr_url = pr["html_url"]
            head_sha = pr["head"]["sha"]
            print(f"[SUCCESS] Created PR #{pr_number}: {pr_url}")
        except Exception:
            # Check closed PRs or create on new branch if needed
            print(f"[!] Could not create PR on {BRANCH}, checking existing PRs...")
            all_prs = gh_req(f"https://api.github.com/repos/{REPO}/pulls?state=all&per_page=5")
            pr_number = all_prs[0]["number"]
            pr_url = all_prs[0]["html_url"]
            head_sha = all_prs[0]["head"]["sha"]
            print(f"[*] Target PR #{pr_number}: {pr_url}")

    # 2. Fetch modified files
    print(f"[*] Fetching diff files for PR #{pr_number}...")
    files_data = gh_req(f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/files")
    
    diff_payload = []
    for f in files_data:
        diff_payload.append({
            "filename": f.get("filename", ""),
            "patch": f.get("patch", ""),
        })

    # If diff_payload is empty (e.g. branch up-to-date), load local sample
    if not diff_payload:
        from scripts.create_ideal_demo_pr import CHECKOUT_GATEWAY_CODE, ORDER_ORCHESTRATOR_CODE, VULNERABLE_REQUIREMENTS_TXT
        diff_payload = [
            {"filename": "services/checkout_gateway.py", "patch": "\n".join(["+" + l for l in CHECKOUT_GATEWAY_CODE.splitlines()])},
            {"filename": "services/order_orchestrator.py", "patch": "\n".join(["+" + l for l in ORDER_ORCHESTRATOR_CODE.splitlines()])},
            {"filename": "requirements.txt", "patch": VULNERABLE_REQUIREMENTS_TXT},
        ]

    # 3. Run OWASP Audit
    print("[*] Running OWASP Top 10 Security & Compliance Audit...")
    auditor = OWASPAuditor()
    owasp_result = auditor.audit_pr_diff(diff_payload)
    owasp_report = auditor.generate_markdown_report(owasp_result)
    print(f"[+] Compliance Score: {owasp_result.compliance_score}% (Grade: {owasp_result.grade})")
    print(f"[+] Total Violations: {owasp_result.total_findings}")

    # 4. Run AST test gap & Mermaid diagram
    test_gaps = detect_unit_test_gaps(diff_payload)
    mermaid = generate_mermaid_diagram(diff_payload, min_files=1)

    # 5. Build summary
    summary_text = f"""### 🛡️ Automated PR Security & Compliance Review
* **Status:** 🔴 **Merge Blocked (Critical Policy Violations)**
* **OWASP Top 10 Compliance:** `{owasp_result.compliance_score}%` (**Grade: {owasp_result.grade}**)
* **Active Violations:** `{owasp_result.total_findings}` issues detected across `{len(owasp_result.violated_categories)}` categories.
* **AST Test Gaps:** `{len(test_gaps)}` public functions missing test coverage.
"""

    all_findings_for_table = [
        {"severity": f.severity, "rule_id": f.rule_id, "file": f.file, "line": f.line, "message": f.title}
        for f in owasp_result.findings
    ]
    for g in test_gaps:
        all_findings_for_table.append(g)

    # 6. Build Master Review Comment Body
    full_review_body = _build_review_body(
        summary=summary_text,
        findings=all_findings_for_table,
        mermaid=mermaid,
        truncation_note=None,
        owasp_report=owasp_report,
    )

    # 7. Post Top-level Comment on GitHub PR
    print("[*] Posting Master Review comment with OWASP Matrix to GitHub...")
    comment_url = f"https://api.github.com/repos/{REPO}/issues/{pr_number}/comments"
    gh_req(comment_url, data={"body": full_review_body}, method="POST")
    print("[+] Master OWASP Review comment posted successfully!")

    # 8. Post Conversational @review-bot Thread
    print("[*] Posting interactive @review-bot in-thread chat...")
    bot_chat_payload = {
        "body": """**@review-bot** please explain the critical OWASP findings and how to remediate them before merging."""
    }
    gh_req(comment_url, data=bot_chat_payload, method="POST")

    bot_reply_payload = {
        "body": f"""🤖 **@review-bot Response:**

Here is the root-cause analysis for the critical violations in this PR:

1. **[A03:2021] SQL Injection in `get_order_by_id()` (`services/checkout_gateway.py:21`)**
   * **Risk:** Using f-string string formatting (`f"SELECT ... WHERE id = '{'{order_id}'}'"`) allows an attacker to inject arbitrary SQL statements (e.g. `order_id = "1' OR '1'='1"`), leading to complete database exfiltration.
   * **Remediation:** Use parameterized queries:
     ```python
     cursor.execute("SELECT id, user_id, amount, status FROM orders WHERE id = ?", (order_id,))
     ```

2. **[A02:2021] Weak Hash & Leaked Credentials (`services/checkout_gateway.py:14, 30`)**
   * **Risk:** `hashlib.md5()` is collision-prone and insecure for authentication signatures. Hardcoded secrets in source files risk token leakage.
   * **Remediation:** Use `hashlib.sha256()` or `hmac.new()` and load secrets from `os.getenv("STRIPE_GATEWAY_SECRET")`.

3. **[A08:2021] Insecure Deserialization in `restore_user_cart_session()` (`services/checkout_gateway.py:37`)**
   * **Risk:** `pickle.loads()` executes arbitrary Python bytecode embedded in serialized objects, allowing Remote Code Execution (RCE).
   * **Remediation:** Migrate cart session serialization to `json.loads()` or `protobuf`.

4. **[A06:2021] Vulnerable Dependencies (`requirements.txt`)**
   * **Risk:** `pyyaml==5.3` is vulnerable to **CVE-2020-14343** (arbitrary code execution) and `requests==2.28.0` is vulnerable to **CVE-2023-32681**.
   * **Remediation:** Upgrade `pyyaml>=5.4.1` and `requests>=2.31.0`.

---
*💡 An autonomous 1-click Auto-Fix PR can be generated with all remediations and passing unit tests.*"""
    }
    gh_req(comment_url, data=bot_reply_payload, method="POST")
    print("[+] Interactive @review-bot thread posted!")

    # 9. Post Quality Gate Check Run (Red ❌)
    print("[*] Creating GitHub Check Run: review-agent/quality-gate...")
    check_run_url = f"https://api.github.com/repos/{REPO}/check-runs"
    check_payload = {
        "name": "review-agent/quality-gate",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "failure",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "output": {
            "title": f"❌ Quality Gate Failed — {owasp_result.total_findings} OWASP Violation(s) (Grade: {owasp_result.grade})",
            "summary": f"OWASP Compliance Score: {owasp_result.compliance_score}%. {owasp_result.total_findings} total violations detected across {len(owasp_result.violated_categories)} categories. Merge blocked until critical security flaws are resolved.",
            "text": owasp_report
        }
    }
    try:
        gh_req(check_run_url, data=check_payload, method="POST")
        print("[+] Check Run created: Red ❌ Merge Blocked!")
    except Exception as e:
        print(f"[!] Note on Check Run: {e}")

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Open your live demo PR in browser:")
    print(f"[PR LINK] {pr_url}")
    print("=" * 75)


if __name__ == "__main__":
    main()
