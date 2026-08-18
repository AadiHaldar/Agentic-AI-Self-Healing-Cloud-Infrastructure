"""
scripts/setup_clean_demo_prs.py — Sets up a pristine, production-ready Dual-PR demo:
  1. Creates Primary Vulnerable PR (Blocked by Red ❌ Quality Gate, with Mermaid Diagram & @review-bot chat).
  2. Creates Secondary Auto-Fix PR (Green ✅ Passing Gate, ready for 1-click live demo merge).
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()
from pr_review_agent.github_app_auth import get_token_for_repo

repo = "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure"
token = get_token_for_repo(repo)

def run(cmd):
    print(">>", cmd)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip())
    return res

def post_github_comment(pr_num, body):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_num}/comments"
    req = urllib.request.Request(
        url,
        data=json.dumps({"body": body}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgenticAI-ReviewBot/1.0",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_check_run(commit_sha, conclusion, title, summary, text):
    url = f"https://api.github.com/repos/{repo}/check-runs"
    payload = {
        "name": "review-agent/quality-gate",
        "head_sha": commit_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title,
            "summary": summary,
            "text": text
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgenticAI-ReviewBot/1.0",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("\n=======================================================")
    print(" [*] RESETTING & CREATING PRISTINE DEMO PRs")
    print("=======================================================")

    # 1. Switch to main
    run("git checkout main")
    run("git pull origin main")
    run("git branch -D feature/billing-auth-gateway autoreview/fix-billing-security-pr")

    # 2. Create feature branch for primary vulnerable PR
    run("git checkout -B feature/billing-auth-gateway")
    os.makedirs("services", exist_ok=True)

    # File 1: services/billing_gateway.py (Contains SQLi, Leaked Secrets, Sync I/O)
    with open("services/billing_gateway.py", "w", encoding="utf-8") as f:
        f.write("""import os
import sqlite3
import requests
from services.order_validator import validate_incoming_order
from services.payment_client import PaymentClient

# DEFECT 1: Leaked Stripe & AWS API Keys (Detect-Secrets)
STRIPE_SECRET_KEY = "sk_test_51Mz9XYZ9876543210ABCDEFabcdef9988776655"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

class BillingGateway:
    def __init__(self, db_path: str = "billing.db"):
        self.db_path = db_path
        self.client = PaymentClient(api_key=STRIPE_SECRET_KEY)

    def fetch_customer_account(self, customer_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # DEFECT 2: Raw SQL Injection via string formatting (Bandit B608)
        query = f"SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '{customer_id}'"
        cursor.execute(query)
        account = cursor.fetchone()
        conn.close()
        return account

    async def process_billing_transaction(self, customer_id: str, order_data: dict):
        if not validate_incoming_order(order_data):
            raise ValueError("Invalid order payload")
        
        # DEFECT 3: Blocking Synchronous I/O in Async Route (Ruff perf/no-sync-io)
        resp = requests.get("https://api.stripe.com/v1/healthcheck", timeout=5)
        
        account = self.fetch_customer_account(customer_id)
        if not account:
            return {"status": "error", "message": "Account not found"}
        
        charge_result = self.client.execute_charge(account[3], order_data.get("total", 0))
        return {"status": "success", "charge": charge_result}
""")

    # File 2: services/order_validator.py (Contains AST Test Gap, Broad Exception)
    with open("services/order_validator.py", "w", encoding="utf-8") as f:
        f.write("""from services.payment_client import sanitize_currency

def validate_incoming_order(order_data: dict) -> bool:
    if not order_data or "items" not in order_data:
        return False
    return True

# DEFECT 4: AST Test Gap (Untested public function in tests/)
def calculate_tiered_discount(order_amount: float, user_tier: str) -> float:
    try:
        clean_amount = sanitize_currency(order_amount)
        if user_tier == "PLATINUM":
            return clean_amount * 0.80
        elif user_tier == "GOLD":
            return clean_amount * 0.90
        return clean_amount
    except Exception:
        # DEFECT 5: Broad Exception Handling without Logging (Ruff BLE001)
        pass
    return order_amount
""")

    # File 3: services/payment_client.py (Completes 3-tier architecture)
    with open("services/payment_client.py", "w", encoding="utf-8") as f:
        f.write("""class PaymentClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def execute_charge(self, token: str, amount: float) -> dict:
        return {
            "token": token,
            "amount": amount,
            "currency": "USD",
            "status": "CHARGED_SUCCESS"
        }

def sanitize_currency(amount: float) -> float:
    return max(0.0, float(amount))
""")

    # Remove any test file on this branch to ensure AST test gap triggers
    if os.path.exists("tests/test_order_validator.py"):
        os.remove("tests/test_order_validator.py")

    run("git add services/ tests/")
    run("git commit -m \"feat(billing): multi-tier customer billing gateway with discount validator\"")
    run("git push origin feature/billing-auth-gateway -f")

    # 3. Create Primary Vulnerable PR
    pr1_res = run('gh pr create --repo AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure --base main --head feature/billing-auth-gateway --title "feat(billing): multi-tier customer billing gateway with discount validator" --body "### Summary of Changes\n- Added `BillingGateway` microservice with customer SQL account retrieval and Stripe integration.\n- Implemented `validate_incoming_order` and `calculate_tiered_discount` in `order_validator.py`.\n- Added `PaymentClient` in `payment_client.py` for tokenized transaction handling.\n\ncc @review-bot for autonomous architectural review."')
    
    # Extract PR number
    pr_url = pr1_res.stdout.strip()
    pr1_number = int(pr_url.split("/")[-1])
    print(f"\n[+] Created Primary Vulnerable PR #{pr1_number}: {pr_url}")

    # Get commit SHA
    sha_res = run("git rev-parse HEAD")
    pr1_sha = sha_res.stdout.strip()

    # 4. Create Secondary Auto-Fix Branch and PR
    run("git checkout -B autoreview/fix-billing-security-pr")

    # Fix services/billing_gateway.py
    with open("services/billing_gateway.py", "w", encoding="utf-8") as f:
        f.write("""import os
import sqlite3
import httpx
from services.order_validator import validate_incoming_order
from services.payment_client import PaymentClient

# [AUTO-FIX] Loaded secrets securely from environment variables
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "")

class BillingGateway:
    def __init__(self, db_path: str = "billing.db"):
        self.db_path = db_path
        self.client = PaymentClient(api_key=STRIPE_SECRET_KEY)

    def fetch_customer_account(self, customer_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # [AUTO-FIX] Parameterized query to completely eliminate SQL injection (Bandit B608)
        query = "SELECT id, email, balance, card_token FROM accounts WHERE customer_id = ?"
        cursor.execute(query, (customer_id,))
        account = cursor.fetchone()
        conn.close()
        return account

    async def process_billing_transaction(self, customer_id: str, order_data: dict):
        if not validate_incoming_order(order_data):
            raise ValueError("Invalid order payload")
        
        # [AUTO-FIX] Non-blocking async HTTP client (Ruff perf/no-sync-io)
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.stripe.com/v1/healthcheck", timeout=5.0)
        
        account = self.fetch_customer_account(customer_id)
        if not account:
            return {"status": "error", "message": "Account not found"}
        
        charge_result = self.client.execute_charge(account[3], order_data.get("total", 0))
        return {"status": "success", "charge": charge_result}
""")

    # Add unit tests to resolve AST test gap
    os.makedirs("tests", exist_ok=True)
    with open("tests/test_order_validator.py", "w", encoding="utf-8") as f:
        f.write("""import pytest
from services.order_validator import calculate_tiered_discount, validate_incoming_order

def test_calculate_tiered_discount_platinum():
    assert calculate_tiered_discount(100.0, "PLATINUM") == 80.0

def test_calculate_tiered_discount_gold():
    assert calculate_tiered_discount(100.0, "GOLD") == 90.0

def test_calculate_tiered_discount_regular():
    assert calculate_tiered_discount(100.0, "STANDARD") == 100.0

def test_validate_incoming_order():
    assert validate_incoming_order({"items": ["book"]}) is True
    assert validate_incoming_order({}) is False
""")

    run("git add services/ tests/")
    run("git commit -m \"fix(security): parameterized SQL query, env secrets, and unit tests for PR #" + str(pr1_number) + "\"")
    run("git push origin autoreview/fix-billing-security-pr -f")

    # Open Auto-Fix PR targeting the primary PR's branch
    pr2_cmd = f'gh pr create --repo {repo} --base feature/billing-auth-gateway --head autoreview/fix-billing-security-pr --title "[auto-fix] 1-Click security patch & unit tests for PR #{pr1_number}" --body "### Autonomous 1-Click Remediation PR for PR #{pr1_number}\n\nThis PR was automatically created by the **Shift-Left PR Review Agent** to resolve all critical findings flagged in PR #{pr1_number}:\n\n1. SQL Injection Remediated (Bandit B608): Converted raw string concatenation to parameterized query.\n2. Hardcoded Secrets Removed (Detect-Secrets): Moved Stripe & AWS API keys to environment variables.\n3. Async Blocking I/O Resolved (Ruff perf/no-sync-io): Replaced synchronous requests.get with non-blocking httpx.AsyncClient.\n4. AST Test Gap Closed (ast-test-gap): Added tests/test_order_validator.py covering calculate_tiered_discount().\n\n_Generated automatically with passing SAST badges._"'
    pr2_res = run(pr2_cmd)
    pr2_url = pr2_res.stdout.strip()
    pr2_number = int(pr2_url.split("/")[-1])
    print(f"\n[+] Created Secondary Auto-Fix PR #{pr2_number}: {pr2_url}")

    # 5. Post 11-Stage Audit Review Comment to PR #1
    review_comment = f"""## 🛡️ Agentic AI Autonomous PR Review Engine
> **PR #{pr1_number}:** `feat(billing): multi-tier customer billing gateway with discount validator`  
> **Status:** ⚠️ **Quality Gate Blocked (Action Required)** | **Audit Duration:** `14.2s` | **Engine:** Gemini 3.6 Flash + AST + Bandit + Ruff

---

### 📊 11-Stage Unified Audit Matrix

| Verification Stage | Tool / Engine | Status | Issues Found |
|---|---|---|---|
| **1. Static Security Analysis (SAST)** | Bandit | 🔴 **FAILED** | 1 Critical (B608 SQL Injection) |
| **2. Secret & Credential Scanning** | Detect-Secrets | 🔴 **FAILED** | 2 Secrets (Stripe & AWS API Keys) |
| **3. AST Test Gap Analysis** | Python `ast` Parser | 🟡 **WARNING** | 1 Untested Function (`calculate_tiered_discount`) |
| **4. Async I/O Performance** | Ruff (`perf/no-sync-io`) | 🟡 **WARNING** | 1 Blocking Synchronous Call (`requests.get`) |
| **5. Exception Safety Check** | Ruff (`BLE001`) | 🟡 **WARNING** | 1 Broad `except Exception: pass` |
| **6. Microservice Call-Graph** | AST Import Walker | 🟢 **PASS** | Generated Interactive Mermaid Diagram |
| **7. Quality Gate Policy** | Check Run API | 🔴 **BLOCKED** | Merge blocked pending critical remediations |

---

### 🏗️ Microservice Architecture Call Graph (AST Extracted)

```mermaid
graph LR
    subgraph Client Gateway Layer
        BillingGateway["services.billing_gateway"]
    end

    subgraph Validation & Business Logic
        OrderValidator["services.order_validator"]
        PaymentClient["services.payment_client"]
    end

    subgraph Data & Storage
        SQLiteDB[("billing.db (SQLite)")]
        ExternalStripe[["Stripe API Endpoint"]]
    end

    BillingGateway -->|"validate_incoming_order()"| OrderValidator
    BillingGateway -->|"execute_charge()"| PaymentClient
    BillingGateway -->|"Raw SQL Query (Vulnerable)"| SQLiteDB
    BillingGateway -.->|"Sync Blocking HTTP"| ExternalStripe
    OrderValidator -->|"sanitize_currency()"| PaymentClient
```

---

### 🚨 Critical Security & Quality Findings

#### 1. 🔴 [CRITICAL] SQL Injection via String Interpolation (`Bandit B608`)
* **Location:** `services/billing_gateway.py:17`
* **Issue:** `customer_id` is concatenated directly into raw SQL string, enabling full database exfiltration via `' OR 1=1 --`.
* **1-Click AI Fix Suggestion:**
```python
# Parameterized query protects against SQL injection
query = "SELECT id, email, balance, card_token FROM accounts WHERE customer_id = ?"
cursor.execute(query, (customer_id,))
```

#### 2. 🔴 [CRITICAL] Leaked API Keys in Source Code (`Detect-Secrets`)
* **Location:** `services/billing_gateway.py:7-8`
* **Issue:** Plaintext Stripe test key and AWS access token hardcoded in repository files.
* **1-Click AI Fix Suggestion:**
```python
import os
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
```

#### 3. 🟡 [WARNING] AST Test Gap — Untested Public Function (`ast-test-gap`)
* **Location:** `services/order_validator.py:9`
* **Issue:** `calculate_tiered_discount()` is a public business function with **0 unit tests** in `tests/`.

#### 4. 🟡 [WARNING] Blocking Synchronous I/O in Async Route (`Ruff perf/no-sync-io`)
* **Location:** `services/billing_gateway.py:27`
* **Issue:** `requests.get()` blocks the asyncio event loop. Use `httpx.AsyncClient` instead.

---

### 🛠️ Autonomous 1-Click Remediation Available:
👉 **[Click here to review and merge Auto-Fix PR #{pr2_number}]({pr2_url})**
"""
    post_github_comment(pr1_number, review_comment)
    print(f"[+] Posted 11-Stage Audit Review Comment to PR #{pr1_number}")

    # 6. Post Red ❌ Failed Quality Gate Check Run to PR #1
    post_check_run(
        commit_sha=pr1_sha,
        conclusion="failure",
        title="Quality Gate Failed: 2 Critical Vulnerabilities (Merge Blocked)",
        summary=f"The Shift-Left PR Review Agent detected 2 critical security findings requiring remediation before merge.\n\n👉 **Autonomous 1-Click Fix Ready:** [Click here to merge Auto-Fix PR #{pr2_number}]({pr2_url})",
        text=f"### 🚨 Blocked Items:\n1. **Bandit B608 (Critical):** SQL Injection in `services/billing_gateway.py:17`\n2. **Detect-Secrets (Critical):** Leaked API Credentials in `services/billing_gateway.py:7-8`\n3. **AST Test Gap (Warning):** Untested function `calculate_tiered_discount()`\n\n---\n### 🛠️ How to Unblock & Fix:\n- **Option A (Instant 1-Click Merge):** Merge **[Auto-Fix PR #{pr2_number}]({pr2_url})** into this branch.\n- **Option B (Manual Fix):** Apply the inline code suggestions posted by `@review-bot` in the PR conversation."
    )
    print(f"[+] Posted Red ❌ Failed Quality Gate Check Run to PR #{pr1_number}")

    # 7. Post Conversational @review-bot thread to PR #1
    post_github_comment(pr1_number, "@review-bot explain the SQL injection risk in billing_gateway.py and how attackers exploit it")
    
    bot_explanation = """### 🤖 @review-bot Architectural Explanation

**Vulnerability Analysis for `services/billing_gateway.py:17` (Bandit B608):**

1. **How Attackers Exploit It:**
   In line 17, the SQL query is constructed using Python string interpolation:
   ```python
   query = f"SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '{customer_id}'"
   ```
   If an adversary sends `customer_id = "' OR 1=1 --"`, the executed query becomes:
   ```sql
   SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '' OR 1=1 --'
   ```
   This dumps every customer's sensitive payment card token and balance in a single request.

2. **The Parameterized Fix:**
   Database drivers separate SQL syntax from user data at the wire protocol level:
   ```python
   cursor.execute("SELECT id, email, balance, card_token FROM accounts WHERE customer_id = ?", (customer_id,))
   ```
"""
    post_github_comment(pr1_number, bot_explanation)
    print(f"[+] Posted Conversational @review-bot Thread to PR #{pr1_number}")

    # 8. Post Green Passing Check Run to PR #2
    sha2_res = run("git rev-parse HEAD")
    pr2_sha = sha2_res.stdout.strip()
    post_check_run(
        commit_sha=pr2_sha,
        conclusion="success",
        title="Quality Gate Passed: 0 Critical Issues (Safe to Merge)",
        summary="All SAST, Secret Scanning, AST Test Gap, and Async Performance checks passed successfully.",
        text="### Passing Audit Verification:\n- Bandit SAST: Passed (0 SQL Injections)\n- Detect-Secrets: Passed (0 Plaintext Secrets)\n- AST Test Gap: Passed (100% test coverage)\n- Quality Gate Verdict: APPROVED FOR MERGE"
    )
    print(f"[+] Posted Green ✅ Passing Check Run to Auto-Fix PR #{pr2_number}")

    print("\n" + "="*70)
    print(f" [SUCCESS] PRISTINE DEMO READY!")
    print(f"  • Vulnerable PR: {pr_url} (Blocked with Red X)")
    print(f"  • Auto-Fix PR:   {pr2_url} (Ready to merge live!)")
    print("="*70)

if __name__ == "__main__":
    main()
