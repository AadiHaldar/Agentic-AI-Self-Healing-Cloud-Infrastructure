"""
scripts/send_push_security_alert.py — CLI tool to audit code and send push security email alerts.
"""
import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pr_review_agent.owasp_auditor import OWASPAuditor
from pr_review_agent.email_notifier import send_security_alert_email, get_smtp_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("send_push_alert")


def main():
    parser = argparse.ArgumentParser(description="Send OWASP Security Alert Email on Push")
    parser.add_argument("--repo", default="AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure")
    parser.add_argument("--branch", default="feature/v2-checkout-gateway")
    parser.add_argument("--commit", default="ece1ed7")
    parser.add_argument("--author", default="Aadi Haldar")
    parser.add_argument("--to", default=None, help="Recipient email override")
    parser.add_argument("--dry-run", action="store_true", help="Save to outbox only without sending SMTP")
    parser.add_argument("--pr-url", default="https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/11")
    args = parser.parse_args()

    print("=" * 75)
    print("[*] AgentHeal Push Security Email Dispatcher")
    print("=" * 75)

    smtp_cfg = get_smtp_settings()
    recipient = args.to or smtp_cfg["default_recipient"]
    print(f"[*] Target Recipient: {recipient}")
    print(f"[*] SMTP Server:     {smtp_cfg['host']}:{smtp_cfg['port']} (TLS: {smtp_cfg['use_tls']})")
    print(f"[*] From Address:    {smtp_cfg['from_email']}")

    # 1. Audit sample diff (with all 10 OWASP categories)
    from scripts.create_ideal_demo_pr import CHECKOUT_GATEWAY_CODE, ORDER_ORCHESTRATOR_CODE, VULNERABLE_REQUIREMENTS_TXT
    diff_payload = [
        {"filename": "services/checkout_gateway.py", "patch": "\n".join(["+" + l for l in CHECKOUT_GATEWAY_CODE.splitlines()])},
        {"filename": "services/order_orchestrator.py", "patch": "\n".join(["+" + l for l in ORDER_ORCHESTRATOR_CODE.splitlines()])},
        {"filename": "requirements.txt", "patch": VULNERABLE_REQUIREMENTS_TXT},
    ]

    print("[*] Running OWASP Top 10 Security Audit on pushed commit...")
    auditor = OWASPAuditor()
    result = auditor.audit_pr_diff(diff_payload)
    print(f"[+] Audit Complete: Compliance Score: {result.compliance_score}% (Grade: {result.grade})")
    print(f"[+] Total Flaws Detected: {result.total_findings} across {len(result.violated_categories)} categories")

    # Format findings for email
    findings_list = [f.to_dict() for f in result.findings]

    # 2. Dispatch email
    print(f"[*] Dispatching Security Alert Email to '{recipient}'...")
    email_res = send_security_alert_email(
        repo_full_name=args.repo,
        branch=args.branch,
        commit_sha=args.commit,
        author_name=args.author,
        author_email=recipient,
        compliance_score=result.compliance_score,
        grade=result.grade,
        total_findings=result.total_findings,
        findings=findings_list,
        pr_url=args.pr_url,
        to_email=recipient,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 75)
    if email_res.get("status") == "success":
        print(f"[SUCCESS] Security Alert Email successfully sent via {email_res.get('mode')} to: {recipient}")
    else:
        print(f"[STATUS] Result: {email_res.get('status')}")
        if "error" in email_res:
            print(f"[ERROR] {email_res['error']}")
    
    print(f"[OUTBOX] HTML Preview saved locally at: {email_res.get('outbox_file')}")
    print("=" * 75)


if __name__ == "__main__":
    main()
