import sys
sys.path.insert(0, '.')

# Test 1: db init
from pr_review_agent import db
import sqlite3

# Verify tables were created
con = sqlite3.connect(db.DB_PATH)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
con.close()
print("DB tables:", tables)
assert "app_config" in tables, "app_config table missing"
assert "installations" in tables, "installations table missing"
assert "review_log" in tables, "review_log table missing"
assert "dismissals" in tables, "dismissals table missing"
assert "installation_repos" in tables, "installation_repos table missing"
print("PASS: db init")

# Test 2: app_config CRUD
db.set_app_config("TEST_KEY", "hello")
val = db.get_app_config("TEST_KEY")
assert val == "hello", f"Expected 'hello', got {val!r}"
db.set_app_config("TEST_KEY", "world")
val = db.get_app_config("TEST_KEY")
assert val == "world", f"Expected 'world', got {val!r}"
print("PASS: app_config CRUD")

# Test 3: installation upsert
db.upsert_installation(12345, "testuser", "User", 99)
inst = db.get_installation(12345)
assert inst["account_login"] == "testuser"
db.add_installation_repo(12345, "testuser/testrepo")
iid = db.get_installation_id_for_repo("testuser/testrepo")
assert iid == 12345
print("PASS: installation CRUD")

# Test 4: review_log
row_id = db.log_review("testuser/testrepo", 1, "abc123", 5, 2, "completed")
assert row_id > 0
logs = db.get_review_log("testuser/testrepo")
assert logs[0]["findings_count"] == 5
print("PASS: review_log")

# Test 5: dismissals / learnings
db.add_dismissal("testuser/testrepo", "ruff/E501", "too noisy")
suppressed = db.get_suppressed_rules("testuser/testrepo")
assert "ruff/E501" in suppressed
print("PASS: dismissals")

# Test 6: config dataclass
from pr_review_agent.config import ReviewConfig, severity_meets_threshold
cfg = ReviewConfig()
assert cfg.severity_threshold == "warning"
assert cfg.max_hunks == 50
assert severity_meets_threshold("error", "warning") == True
assert severity_meets_threshold("info", "error") == False
print("PASS: ReviewConfig defaults")

# Test 7: learnings filter
from pr_review_agent.learnings import filter_findings, record_dismissal
findings = [
    {"rule_id": "ruff/E501", "message": "line too long", "severity": "warning"},
    {"rule_id": "bandit/B101", "message": "assert used", "severity": "error"},
]
filtered = filter_findings(findings, "testuser/testrepo")
rule_ids = [f["rule_id"] for f in filtered]
assert "ruff/E501" not in rule_ids, f"ruff/E501 should be suppressed, got {rule_ids}"
assert "bandit/B101" in rule_ids
print("PASS: learnings filter")

# Test 8: github_app_auth with no credentials
from pr_review_agent.github_app_auth import load_private_key_from_env, load_app_id
# Should return None when not configured
import os; os.environ.pop("GITHUB_APP_PRIVATE_KEY", None); os.environ.pop("GITHUB_APP_ID", None)
key = load_private_key_from_env()
app_id = load_app_id()
# They'll find the TEST_KEY in db but not a valid key — that's fine, just no crash
key_preview = (repr(key)[:30] + "...") if key else "None"
print("  load_private_key_from_env() = " + key_preview)
print("  load_app_id() = " + repr(app_id))
print("PASS: github_app_auth graceful no-op")

# Test 9: pipeline imports
from pr_review_agent.pipeline import (
    chunk_diff_if_large, deduplicate_findings, detect_unit_test_gaps,
    _fallback_summary, generate_mermaid_diagram
)
print("PASS: pipeline imports")

# Test 10: chunk_diff_if_large
import re
def _make_file(name, hunks=5):
    patch = "\n".join([f"@@ -1,5 +1,5 @@ context\n+new line {i}" for i in range(hunks)])
    return {"filename": name, "patch": patch, "additions": hunks, "deletions": 0, "status": "modified", "sha": ""}

files = [_make_file(f"file_{i}.py", hunks=10) for i in range(7)]  # 70 hunks total
selected, note = chunk_diff_if_large(files, max_hunks=50)
assert note is not None, "Expected truncation note"
assert len(selected) < len(files)
print(f"PASS: chunk_diff_if_large (selected={len(selected)}/{len(files)} files)")

# Test 11: deduplicate_findings
static = [{"file": "a.py", "line": 5, "rule_id": "ruff/E501", "severity": "warning", "message": "long", "source": "ruff", "confidence": 1.0}]
llm = [
    {"file": "a.py", "line": 5, "rule_id": "llm/logic", "severity": "error", "message": "logic bug", "source": "llm", "confidence": 0.9},
    {"file": "b.py", "line": 10, "rule_id": "llm/sec", "severity": "critical", "message": "sqli", "source": "llm", "confidence": 0.3},  # below threshold
]
merged = deduplicate_findings(static, llm, confidence_threshold=0.7)
files_in = {f["file"] for f in merged}
assert "b.py" not in files_in, "Low-confidence finding should be dropped"
assert "a.py" in files_in
print("PASS: deduplicate_findings")

# Test 12: detect_unit_test_gaps with temp file
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    src = "def my_public_function():\n    return 42\n\ndef _private():\n    pass\n"
    fpath = os.path.join(tmp, "mymodule.py")
    with open(fpath, "w") as f:
        f.write(src)
    changed = [{"filename": "mymodule.py", "patch": "", "additions": 5, "deletions": 0, "status": "added", "sha": ""}]
    gaps = detect_unit_test_gaps(changed, repo_path=tmp)
    gap_funcs = [g["message"] for g in gaps]
    assert any("my_public_function" in m for m in gap_funcs)
    assert not any("_private" in m for m in gap_funcs)
print("PASS: detect_unit_test_gaps")

# Test 13: HMAC verification (critical security function)
import hmac as _hmac, hashlib
secret = "test-webhook-secret-xyz"
body = b'{"action": "opened"}'
sig = "sha256=" + _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

# Import the verifier function
from pr_review_agent.webhook_handler import _verify_hmac
assert _verify_hmac(secret, body, sig) == True, "Valid HMAC should pass"
assert _verify_hmac(secret, body, "sha256=deadbeef") == False, "Invalid HMAC should fail"
assert _verify_hmac(secret, body, None) == False, "Missing header should fail"
assert _verify_hmac(None, body, sig) == True, "No secret = permissive (unconfigured state)"
print("PASS: HMAC verification")

print("\n" + "="*60)
print("ALL 13 PHASE 3 TESTS PASSED")
print("="*60)
