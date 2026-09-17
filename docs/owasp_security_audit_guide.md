# 🛡️ OWASP Top 10 Security & Compliance Audit Engine
**AgentHeal Shift-Left DevSecOps & Autonomous Remediation Framework**  
*Document Version:* `2.0.0` | *Standard:* `OWASP Top 10 (2021/2025 Edition)` | *Date:* September 2026  
*Authors:* Aadi Haldar, Raghuram Sekar, Aaditya Paul, Shravan Rajesh Menon  

---

## 📌 Executive Summary

Modern cloud infrastructure outages and data breaches predominantly stem from two sources:
1. **Application-Layer Vulnerabilities** slipping past pull request reviews into production microservices.
2. **Third-Party Supply Chain Vulnerabilities** in outdated dependencies.

To address this, **AgentHeal** integrates an autonomous **OWASP Top 10 Security & Compliance Audit Engine** into its Shift-Left CI/CD pipeline. Every Pull Request is statically analyzed using Python compiler grammar (AST), pattern heuristics, and Dependabot-style CVE databases before execution in Kubernetes.

---

## 🗂️ Detailed Breakdown of All 10 OWASP Categories

The table below explains all 10 standard OWASP categories, how they are detected in AgentHeal, the real-world security risk, and the autonomous remediation applied in our live PR demo.

---

### 1️⃣ A01:2021 — Broken Access Control
* **CWE Mapping:** `CWE-22` (Path Traversal), `CWE-284` (Improper Access Control)
* **The Security Risk:** Attackers manipulate input parameters or file paths to access unauthorized files on the server (e.g., passing `../../etc/passwd` or accessing other tenant files).
* **How AgentHeal Detects It:**  
  * AST / Static regex inspects `os.path.join()` or file open calls where dynamic user inputs are concatenated directly into directory paths without sanitization.
* **Vulnerable Pattern (PR #11):**
  ```python
  def export_order_invoice_pdf(order_id: str, template_filename: str):
      # Vulnerable: template_filename can be "../../etc/passwd"
      output_path = os.path.join("/var/log/invoices", template_filename)
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def export_order_invoice_pdf(order_id: str, template_filename: str):
      # Remediated: os.path.basename strips directory traversal sequences
      safe_filename = os.path.basename(template_filename)
      output_path = os.path.join("/var/log/invoices", safe_filename)
  ```

---

### 2️⃣ A02:2021 — Cryptographic Failures
* **CWE Mapping:** `CWE-328` (Broken/Weak Hash Algorithm), `CWE-798` (Hardcoded Credentials)
* **The Security Risk:** Sensitive credentials exposed in plaintext source files or using obsolete hash functions like MD5 and SHA-1 that are vulnerable to collision and pre-image attacks.
* **How AgentHeal Detects It:**  
  * Detect-Secrets high-entropy scanners catch API tokens (`sk_live_...`, `aws_key`).
  * AST Visitor flags `hashlib.md5()` or `hashlib.sha1()` function calls.
* **Vulnerable Pattern (PR #11):**
  ```python
  STRIPE_GATEWAY_SECRET = "sk_test_mock_dummy_checkout_secret_key_8899"

  def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
      # Vulnerable: MD5 is collision-prone
      computed_digest = hashlib.md5(order_payload.encode("utf-8")).hexdigest()
      return computed_digest == expected_signature
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  # Remediated: Credentials loaded securely from environment variables
  STRIPE_GATEWAY_SECRET = os.getenv("STRIPE_GATEWAY_SECRET", "")

  def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
      # Remediated: Cryptographic HMAC with SHA-256
      key = STRIPE_GATEWAY_SECRET.encode("utf-8")
      computed_digest = hmac.new(key, order_payload.encode("utf-8"), hashlib.sha256).hexdigest()
      return hmac.compare_digest(computed_digest, expected_signature)
  ```

---

### 3️⃣ A03:2021 — Injection (SQLi, Command Injection, Code Exec)
* **CWE Mapping:** `CWE-89` (SQL Injection), `CWE-78` (OS Command Injection), `CWE-95` (Dynamic Code Execution)
* **The Security Risk:** Untrusted user input is concatenated directly into SQL queries or shell commands, allowing attackers to bypass authentication, drop tables, or execute shell commands on the host.
* **How AgentHeal Detects It:**  
  * Bandit SAST rule `B608` + AST pattern matching detects f-strings and `%` formatting inside `cursor.execute()`.
  * AST Visitor flags `subprocess.Popen(..., shell=True)`, `eval()`, and `exec()`.
* **Vulnerable Pattern (PR #11):**
  ```python
  def get_order_by_id(db_conn, order_id: str):
      # Vulnerable: f-string allows injecting "1' OR '1'='1"
      query = f"SELECT id, user_id, amount, status FROM orders WHERE id = '{order_id}'"
      cursor.execute(query)

  def run_cmd(cmd):
      # Vulnerable: shell=True passes strings through OS shell
      subprocess.Popen(cmd, shell=True)
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def get_order_by_id(db_conn, order_id: str):
      # Remediated: Parameterized query placeholders
      query = "SELECT id, user_id, amount, status FROM orders WHERE id = ?"
      cursor.execute(query, (order_id,))

  def run_cmd(cmd_list):
      # Remediated: Tokenized arguments without shell interpreter
      subprocess.Popen(cmd_list, shell=False)
  ```

---

### 4️⃣ A04:2021 — Insecure Design
* **CWE Mapping:** `CWE-400` (Uncontrolled Resource Consumption), `CWE-799` (Improper Control of Interaction Frequency)
* **The Security Risk:** Architectural flaws such as unconstrained pagination, missing rate limiting on sensitive login/payment endpoints, or infinite recursion loops.
* **How AgentHeal Detects It:**  
  * AST checks for unbounded `SELECT *` loops, unbounded array appends, and missing rate limit decorators (`@limiter.limit()`).
* **Autonomous Remediation:**  
  * AgentHeal injects sliding-window rate limiters and pagination limits (`LIMIT 50`) on all endpoint handlers.

---

### 5️⃣ A05:2021 — Security Misconfiguration
* **CWE Mapping:** `CWE-489` (Active Debug Code in Production), `CWE-942` (Overly Permissive CORS)
* **The Security Risk:** Running servers with `DEBUG = True` leaks interactive debuggers, stack traces, and internal server environment variables to clients during exceptions.
* **How AgentHeal Detects It:**  
  * AST Assignment visitor checks for static `DEBUG = True` assignments.
* **Vulnerable Pattern (PR #11):**
  ```python
  # Vulnerable: Hardcoded debug flag
  DEBUG = True
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  # Remediated: Read dynamically with safe False fallback
  DEBUG = os.getenv("DEBUG", "false").lower() == "true"
  ```

---

### 6️⃣ A06:2021 — Vulnerable and Outdated Components (Dependabot-Style)
* **CWE Mapping:** `CWE-1395` (Dependency with Known Vulnerabilities / CVEs)
* **The Security Risk:** Utilizing third-party libraries that contain publicly disclosed CVEs (e.g., PyYAML arbitrary code execution or Requests proxy header leaks).
* **How AgentHeal Detects It:**  
  * `OWASPAuditor.audit_requirements_txt()` parses `requirements.txt` and matches package versions against a curated vulnerability database.
* **Vulnerable Manifest (PR #11):**
  ```text
  pyyaml==5.3       # Affected by CVE-2020-14343 (Arbitrary Code Execution)
  requests==2.28.0   # Affected by CVE-2023-32681 (Proxy-Authorization Header Leak)
  ```
* **Autonomous Remediation (PR #12):**
  ```text
  pyyaml==5.4.1     # Patched: SafeLoader enforced
  requests==2.31.0   # Patched: Header stripping verified
  ```

---

### 7️⃣ A07:2021 — Identification and Authentication Failures
* **CWE Mapping:** `CWE-287` (Improper Authentication), `CWE-384` (Session Fixation)
* **The Security Risk:** Weak token generation, missing MFA enforcement, hardcoded session cookies, or predictable JWT signing keys.
* **How AgentHeal Detects It:**  
  * Static secret entropy analysis and AST token validation.
* **Autonomous Remediation:**  
  * Enforces RS256 asymmetric token verification with 9-minute short-lived JWT expiry.

---

### 8️⃣ A08:2021 — Software and Data Integrity Failures
* **CWE Mapping:** `CWE-502` (Deserialization of Untrusted Data)
* **The Security Risk:** Untrusted serialized data is passed to `pickle.loads()` or `yaml.load()`, which executes arbitrary Python bytecode embedded within the payload during reconstruction.
* **How AgentHeal Detects It:**  
  * AST Call visitor flags any invocation of `pickle.loads()`, `pickle.load()`, or `yaml.load()` without `Loader=yaml.SafeLoader`.
* **Vulnerable Pattern (PR #11):**
  ```python
  def restore_user_cart_session(raw_session_bytes: bytes) -> Dict[str, Any]:
      # Vulnerable: Insecure deserialization enables Remote Code Execution (RCE)
      cart_obj = pickle.loads(raw_session_bytes)
      return cart_obj
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def restore_user_cart_session(raw_session_json: str) -> Dict[str, Any]:
      # Remediated: Standard JSON parsing prevents arbitrary object construction
      try:
          return json.loads(raw_session_json)
      except (json.JSONDecodeError, TypeError):
          return {}
  ```

---

### 9️⃣ A09:2021 — Security Logging and Monitoring Failures
* **CWE Mapping:** `CWE-778` (Insufficient Logging), `CWE-390` (Detection of Error Condition Without Action)
* **The Security Risk:** Catching exceptions and executing `pass` silently masks runtime crashes, data corruption, and active penetration attempts from observability probes.
* **How AgentHeal Detects It:**  
  * AST `ExceptHandler` visitor detects exception blocks containing only `pass` or `continue`.
* **Vulnerable Pattern (PR #11):**
  ```python
  def audit_transaction_metrics(order_id: str, amount: float):
      try:
          if amount < 0:
              raise ValueError("Negative transaction amount")
      except Exception:
          # Vulnerable: Swallowed exception masks security anomaly
          pass
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def audit_transaction_metrics(order_id: str, amount: float):
      try:
          if amount < 0:
              raise ValueError("Negative transaction amount")
      except Exception as e:
          # Remediated: Explicit telemetry logging
          logger.error(f"Audit metric error for order {order_id}: {e}")
  ```

---

### 🔟 A10:2021 — Server-Side Request Forgery (SSRF)
* **CWE Mapping:** `CWE-918` (Server-Side Request Forgery)
* **The Security Risk:** Application fetches remote resources from URLs supplied by user input without validating destination hostnames, enabling attackers to query cloud instance metadata services (e.g. `http://169.254.169.254/latest/meta-data/`).
* **How AgentHeal Detects It:**  
  * AST Call visitor checks outbound HTTP client methods (`requests.get`, `urllib.request.urlopen`) invoked with dynamic variable arguments.
* **Autonomous Remediation:**  
  * Injects strict destination hostname allowlists and blocks loopback/private RFC-1918 IP addresses.

---

## 📊 Summary of Live Demo Artifacts

| Component | Link / Location | Purpose |
|---|---|---|
| **❌ Vulnerable Demo PR** | [PR #11 on GitHub](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/11) | Demonstrates all 9 OWASP flaws, AST test gaps, Mermaid call-graph, and **Red ❌ Quality Gate**. |
| **✅ Autonomous Auto-Fix PR** | [PR #12 on GitHub](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/12) | Demonstrates autonomous 1-click remediation, parameterized queries, SHA-256 HMAC, and unit tests. |
| **💻 Local Interactive Dashboard** | `http://localhost:8000` (`🛡️ OWASP Top 10` Tab) | Live interactive scorecard, category pills, and instant AST Code & Dependency Scanner. |
| **⚙️ Core Engine Source** | [`pr_review_agent/owasp_auditor.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/owasp_auditor.py) | Python AST visitors, regex pattern checkers, and Dependabot-style CVE database. |
| **🧪 Automated Unit Tests** | [`tests/test_owasp_auditor.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/tests/test_owasp_auditor.py) | Comprehensive pytest test suite covering all 10 OWASP categories (8/8 passing). |
