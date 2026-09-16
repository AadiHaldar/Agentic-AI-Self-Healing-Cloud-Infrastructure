"""
tests/test_owasp_auditor.py — Comprehensive test suite for the OWASP Top 10 Auditor.
"""
import pytest
from pr_review_agent.owasp_auditor import OWASPAuditor, OWASP_CATEGORIES


@pytest.fixture
def auditor():
    return OWASPAuditor()


def test_owasp_a03_sql_injection(auditor):
    code = '''
def get_user_account(user_id):
    query = f"SELECT * FROM accounts WHERE id = '{user_id}'"
    return db.execute(query)
'''
    findings = auditor.audit_python_code(code, "service/db.py")
    assert any(f.category_id == "A03:2021" for f in findings)
    assert any("SQL Injection" in f.title for f in findings)


def test_owasp_a03_eval_and_shell(auditor):
    code = '''
import subprocess

def run_custom_script(cmd, expr):
    val = eval(expr)
    subprocess.Popen(cmd, shell=True)
    return val
'''
    findings = auditor.audit_python_code(code, "executor.py")
    cat_findings = [f for f in findings if f.category_id == "A03:2021"]
    assert len(cat_findings) >= 2
    assert any("eval" in f.title for f in cat_findings)
    assert any("shell=True" in f.title for f in cat_findings)


def test_owasp_a02_cryptographic_failures(auditor):
    code = '''
import hashlib

STRIPE_API_KEY = "sk_test_mock_dummy_api_key_0123456789"

def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
'''
    findings = auditor.audit_python_code(code, "auth.py")
    assert any(f.category_id == "A02:2021" for f in findings)
    assert any("Broken Hash" in f.title or "Secret" in f.title for f in findings)


def test_owasp_a05_security_misconfiguration(auditor):
    code = '''
DEBUG = True
SECRET_KEY = "supersecret"
'''
    findings = auditor.audit_python_code(code, "config.py")
    assert any(f.category_id == "A05:2021" for f in findings)
    assert any("Debug Mode Enabled" in f.title for f in findings)


def test_owasp_a08_insecure_deserialization(auditor):
    code = '''
import pickle

def load_payload(raw_data):
    return pickle.loads(raw_data)
'''
    findings = auditor.audit_python_code(code, "worker.py")
    assert any(f.category_id == "A08:2021" for f in findings)
    assert any("Insecure Deserialization" in f.title for f in findings)


def test_owasp_a09_unlogged_exception(auditor):
    code = '''
def process_order():
    try:
        do_transaction()
    except Exception:
        pass
'''
    findings = auditor.audit_python_code(code, "order.py")
    assert any(f.category_id == "A09:2021" for f in findings)
    assert any("Silently Swallowed" in f.title for f in findings)


def test_owasp_a06_vulnerable_requirements(auditor):
    reqs = """
requests==2.28.0
pyyaml==5.3
fastapi==0.115.0
"""
    findings = auditor.audit_requirements_txt(reqs, "requirements.txt")
    assert any(f.category_id == "A06:2021" for f in findings)
    assert any("pyyaml" in f.title.lower() for f in findings)


def test_audit_pr_diff_compliance_score(auditor):
    files = [
        {
            "filename": "services/billing.py",
            "patch": """
+def charge(customer_id):
+    query = f"SELECT * FROM billing WHERE id = '{customer_id}'"
+    return query
"""
        },
        {
            "filename": "requirements.txt",
            "patch": "+pyyaml==5.3\n"
        }
    ]
    result = auditor.audit_pr_diff(files)
    assert result.total_findings >= 2
    assert result.compliance_score < 100.0
    assert "A03:2021" in result.violated_categories
    assert "A06:2021" in result.violated_categories
    assert "A04:2021" in result.compliant_categories

    report_md = auditor.generate_markdown_report(result)
    assert "OWASP Top 10" in report_md
    assert "Compliance Score" in report_md
    assert "A03:2021" in report_md
