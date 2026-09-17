"""
tests/test_email_notifier.py — Unit Tests for Push & PR Security Email Notifier.
"""
import os
import pytest
from pr_review_agent.email_notifier import (
    build_security_email_html,
    build_security_email_text,
    send_security_alert_email,
    get_smtp_settings,
    save_email_to_outbox,
    get_last_email_html
)


def test_smtp_settings_loaded():
    cfg = get_smtp_settings()
    assert cfg["host"] == "smtp.gmail.com"
    assert cfg["port"] == 587
    assert cfg["user"] == "aadi.haldar2006@gmail.com"
    assert cfg["default_recipient"] == "aadi.haldar2006@gmail.com"
    assert cfg["use_tls"] is True


def test_build_security_email_html_structure():
    findings = [
        {
            "category_id": "A03:2021",
            "title": "SQL Injection via f-string",
            "severity": "critical",
            "file": "services/checkout_gateway.py",
            "line": 29,
            "recommendation": "Use parameterized queries."
        },
        {
            "category_id": "A01:2021",
            "title": "Path Traversal",
            "severity": "high",
            "file": "services/checkout_gateway.py",
            "line": 52,
            "recommendation": "Use os.path.basename()."
        }
    ]

    html = build_security_email_html(
        repo_full_name="AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
        branch="feature/v2-checkout-gateway",
        commit_sha="ece1ed7",
        author_name="Aadi Haldar",
        compliance_score=0.0,
        grade="F",
        total_findings=2,
        findings=findings,
        pr_url="https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/11"
    )

    assert "AgentHeal Push Security Alert" in html
    assert "GRADE F (0.0%)" in html
    assert "A03:2021" in html
    assert "SQL Injection" in html
    assert "Path Traversal" in html
    assert "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure" in html
    assert "feature/v2-checkout-gateway" in html


def test_build_security_email_text_structure():
    findings = [
        {
            "category_id": "A05:2021",
            "title": "DEBUG = True enabled",
            "severity": "high",
            "file": "config.py",
            "line": 10,
            "recommendation": "Set DEBUG = False"
        }
    ]

    text = build_security_email_text(
        repo_full_name="test/repo",
        branch="main",
        commit_sha="abc1234",
        author_name="Developer",
        compliance_score=75.0,
        grade="C",
        total_findings=1,
        findings=findings
    )

    assert "AGENTHEAL PUSH SECURITY AUDIT ALERT" in text
    assert "DEBUG = True enabled" in text
    assert "A05:2021" in text


def test_dry_run_saves_outbox():
    findings = [{"category_id": "A02:2021", "title": "Weak Hash", "severity": "high", "file": "auth.py", "line": 5}]
    res = send_security_alert_email(
        repo_full_name="test/repo",
        branch="dev",
        commit_sha="1122334",
        author_name="Aadi",
        author_email="aadi.haldar2006@gmail.com",
        compliance_score=50.0,
        grade="D",
        total_findings=1,
        findings=findings,
        dry_run=True
    )

    assert res["status"] == "success"
    assert res["mode"] == "dry_run"
    assert os.path.exists(res["outbox_file"])

    cached_html = get_last_email_html()
    assert cached_html is not None
    assert "AgentHeal Push Security Alert" in cached_html
