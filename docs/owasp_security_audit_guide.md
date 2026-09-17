# 🛡️ OWASP Top 10 Security & Compliance Audit Guide
**AgentHeal Shift-Left DevSecOps & Autonomous Remediation Framework**  
*Document Version:* `2.5.0` | *Standard:* `OWASP Top 10 (2021/2025 Edition)` | *Date:* September 2026  
*Authors:* Aadi Haldar, Raghuram Sekar, Aaditya Paul, Shravan Rajesh Menon  

---

## 📌 Executive Summary

Modern cloud microservice infrastructure outages and data breaches predominantly originate from two critical vectors:
1. **Application-Layer Vulnerabilities** bypassing pull request reviews into live production Kubernetes clusters.
2. **Third-Party Supply Chain Vulnerabilities** lurking in outdated dependencies (`requirements.txt`).

To eliminate vulnerabilities before they reach production, **AgentHeal** integrates an autonomous **OWASP Top 10 Security & Compliance Audit Engine** directly into the Shift-Left CI/CD pipeline. Every Pull Request is inspected using Python compiler grammar (AST), high-entropy secret detection, heuristic SAST pattern matching, and Dependabot-style CVE databases.

---

## 🗂️ Detailed Breakdown of All 10 OWASP Top 10 Categories

The section below provides an in-depth breakdown for all **10 OWASP Top 10 categories (A01 through A10)**, featuring:
* Direct clickable **Local File Links** (`file:///...#LXX`)
* Direct clickable **GitHub Repository Links** on branch `feature/v2-checkout-gateway`
* CWE mappings, threat impact analysis, detection mechanisms, and side-by-side code remediations.

---

### 1️⃣ A01:2021 — Broken Access Control
* **CWE Mapping:** `CWE-22` (Path Traversal), `CWE-284` (Improper Access Control)
* **File Location (Local):** [`services/checkout_gateway.py (Line 49-57)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L49-L57)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 49-57)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L49-L57)
* **The Security Risk:** Attackers manipulate the `template_filename` input parameter with path traversal sequences (e.g. `../../etc/passwd` or `../../root/.ssh/id_rsa`) to access or overwrite unauthorized system files on the container filesystem.
* **How AgentHeal Detects It:**  
  * AST Call Visitor inspects `os.path.join()` invocations and flags instances where non-constant variable arguments are passed without sanitization.
* **Vulnerable Pattern (PR #11):**
  ```python
  def export_order_invoice_pdf(order_id: str, template_filename: str) -> str:
      # Vulnerable: template_filename can contain directory traversal sequences "../../"
      output_path = os.path.join("/var/log/invoices", template_filename)
      ...
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def export_order_invoice_pdf(order_id: str, template_filename: str) -> str:
      # Remediated: os.path.basename strips directory traversal sequences
      safe_filename = os.path.basename(template_filename)
      output_path = os.path.join("/var/log/invoices", safe_filename)
      ...
  ```

---

### 2️⃣ A02:2021 — Cryptographic Failures
* **CWE Mapping:** `CWE-328` (Broken/Weak Hash Algorithm), `CWE-798` (Hardcoded Credentials)
* **File Locations (Local):**
  * [`services/checkout_gateway.py (Line 20)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L20) — Hardcoded Secret
  * [`services/checkout_gateway.py (Line 35-39)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L35-L39) — Weak MD5 Digest
* **GitHub Links:**
  * [PR #11 `services/checkout_gateway.py` (Line 20)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L20)
  * [PR #11 `services/checkout_gateway.py` (Line 35-39)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L35-L39)
* **The Security Risk:** Plaintext API secrets committed into git repositories lead to automated credential harvesting. Using obsolete hash algorithms like MD5 allows attackers to forge transaction signatures via hash collision attacks.
* **How AgentHeal Detects It:**  
  * High-entropy regex and AST detectors flag hardcoded secrets and `hashlib.md5()` / `hashlib.sha1()` calls.
* **Vulnerable Pattern (PR #11):**
  ```python
  STRIPE_GATEWAY_SECRET = "sk_test_mock_dummy_checkout_secret_key_8899"

  def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
      # Vulnerable: MD5 is cryptographically broken and collision-prone
      computed_digest = hashlib.md5(order_payload.encode("utf-8")).hexdigest()
      return computed_digest == expected_signature
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  # Remediated: Secrets loaded from environment variables / Azure Key Vault
  STRIPE_GATEWAY_SECRET = os.getenv("STRIPE_GATEWAY_SECRET", "")

  def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
      # Remediated: Cryptographic HMAC using SHA-256 with constant-time comparison
      key = STRIPE_GATEWAY_SECRET.encode("utf-8")
      computed_digest = hmac.new(key, order_payload.encode("utf-8"), hashlib.sha256).hexdigest()
      return hmac.compare_digest(computed_digest, expected_signature)
  ```

---

### 3️⃣ A03:2021 — Injection (SQLi & OS Command Injection)
* **CWE Mapping:** `CWE-89` (SQL Injection), `CWE-78` (OS Command Injection)
* **File Locations (Local):**
  * [`services/checkout_gateway.py (Line 26-32)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L26-L32) — SQL Injection
  * [`services/checkout_gateway.py (Line 54-56)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L54-L56) — OS Command Injection (`shell=True`)
* **GitHub Links:**
  * [PR #11 `services/checkout_gateway.py` (Line 26-32)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L26-L32)
  * [PR #11 `services/checkout_gateway.py` (Line 54-56)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L54-L56)
* **The Security Risk:** Direct string formatting in SQL queries allows attackers to execute arbitrary SQL commands (e.g. `order_id = "1' OR '1'='1"`), dumping the full database. Invoking `subprocess` with `shell=True` allows shell metacharacters (`&&`, `;`, `|`) to execute remote shell payloads.
* **How AgentHeal Detects It:**  
  * Bandit SAST rule `B608` and AST pattern matching detect f-strings in SQL statements.
  * AST `visit_Call` flags `subprocess.Popen(..., shell=True)` and `eval()`.
* **Vulnerable Pattern (PR #11):**
  ```python
  def get_order_by_id(db_conn, order_id: str):
      # Vulnerable: f-string SQL injection
      query = f"SELECT id, user_id, amount, status FROM orders WHERE id = '{order_id}'"
      cursor.execute(query)

  def export_order_invoice_pdf(order_id: str, template_filename: str):
      cmd = f"wkhtmltopdf --order-id {order_id} {output_path}"
      subprocess.Popen(cmd, shell=True)
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def get_order_by_id(db_conn, order_id: str):
      # Remediated: Parameterized SQL placeholder
      query = "SELECT id, user_id, amount, status FROM orders WHERE id = ?"
      cursor.execute(query, (order_id,))

  def export_order_invoice_pdf(order_id: str, template_filename: str):
      # Remediated: Argument list with shell=False
      cmd = ["wkhtmltopdf", "--order-id", str(order_id), output_path]
      subprocess.Popen(cmd, shell=False)
  ```

---

### 4️⃣ A04:2021 — Insecure Design (Unbounded Memory & Missing Pagination)
* **CWE Mapping:** `CWE-400` (Uncontrolled Resource Consumption / OOM DoS)
* **File Location (Local):** [`services/checkout_gateway.py (Line 67-70)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L67-L70)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 67-70)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L67-L70)
* **The Security Risk:** Querying the entire database table without pagination limits (`LIMIT` / `OFFSET`) causes memory exhaustion (OOM), triggering container OOMKilled crashes and cluster cascading failovers.
* **How AgentHeal Detects It:**  
  * AST Visitor flags unbounded query calls (`fetch_unbounded`, `load_all_records`, `query_all`) lacking pagination bounds.
* **Vulnerable Pattern (PR #11):**
  ```python
  def fetch_unbounded_order_archive(db_conn) -> List[Dict[str, Any]]:
      # Vulnerable: Loads millions of records into RAM without limits
      return fetch_unbounded(db_conn)
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def fetch_unbounded_order_archive(db_conn, page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
      # Remediated: Enforces strict LIMIT and OFFSET pagination
      cursor = db_conn.cursor()
      offset = (page - 1) * page_size
      cursor.execute("SELECT id, user_id, amount, status FROM orders LIMIT ? OFFSET ?", (page_size, offset))
      return cursor.fetchall()
  ```

---

### 5️⃣ A05:2021 — Security Misconfiguration
* **CWE Mapping:** `CWE-489` (Active Debug Code in Production)
* **File Location (Local):** [`services/checkout_gateway.py (Line 17)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L17)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 17)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L17)
* **The Security Risk:** `DEBUG = True` enables interactive stack traces, leaks internal application topology, and exposes live environment secrets to web clients upon unhandled exceptions.
* **How AgentHeal Detects It:**  
  * AST Assignment Visitor flags static boolean assignments targeting `DEBUG` or `DEBUG_MODE`.
* **Vulnerable Pattern (PR #11):**
  ```python
  # Vulnerable: Debug mode hardcoded in production microservice
  DEBUG = True
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  # Remediated: Read dynamically from environment with safe default False
  DEBUG = os.getenv("DEBUG", "false").lower() == "true"
  ```

---

### 6️⃣ A06:2021 — Vulnerable and Outdated Components (Dependabot-Style Supply Chain)
* **CWE Mapping:** `CWE-1395` (Dependency with Known Vulnerabilities / CVEs)
* **File Location (Local):** [`requirements.txt`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/requirements.txt)
* **GitHub Link:** [PR #11 `requirements.txt`](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/requirements.txt)
* **The Security Risk:** Incorporating outdated packages introduces publicly known vulnerabilities:
  * `pyyaml==5.3`: Vulnerable to **CVE-2020-14343** (Arbitrary Code Execution through untrusted YAML load).
  * `requests==2.28.0`: Vulnerable to **CVE-2023-32681** (Leaking `Proxy-Authorization` headers to unauthorized destination servers).
* **How AgentHeal Detects It:**  
  * `OWASPAuditor.audit_requirements_txt()` parses dependency manifests and matches package versions against a curated CVE database.
* **Vulnerable Manifest (PR #11):**
  ```text
  pyyaml==5.3
  requests==2.28.0
  ```
* **Autonomous Remediation (PR #12):**
  ```text
  pyyaml>=5.4.1
  requests>=2.31.0
  ```

---

### 7️⃣ A07:2021 — Identification and Authentication Failures
* **CWE Mapping:** `CWE-287` (Improper Authentication), `CWE-798` (Hardcoded Credentials)
* **File Locations (Local):**
  * [`services/checkout_gateway.py (Line 23)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L23) — Hardcoded JWT Token
  * [`services/checkout_gateway.py (Line 60-64)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L60-L64) — Unverified Signature Decode
* **GitHub Links:**
  * [PR #11 `services/checkout_gateway.py` (Line 23)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L23)
  * [PR #11 `services/checkout_gateway.py` (Line 60-64)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L60-L64)
* **The Security Risk:** Decoding JWT authentication tokens with `verify=False` allows attackers to forge authorization claims, impersonating administrators and bypassing authentication entirely.
* **How AgentHeal Detects It:**  
  * AST Call Visitor inspects `jwt.decode()` calls for `verify=False` or missing cryptographic key arguments.
* **Vulnerable Pattern (PR #11):**
  ```python
  JWT_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_unverified_payload_secret_key_77"

  def decode_user_session_token(token: str) -> Dict[str, Any]:
      # Vulnerable: Accepts unsigned/forged authentication tokens
      user_claims = jwt.decode(token, verify=False)
      return user_claims
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def decode_user_session_token(token: str, public_key: str) -> Dict[str, Any]:
      # Remediated: Cryptographic RS256 signature verification enforced
      try:
          return jwt.decode(token, public_key, algorithms=["RS256"])
      except Exception as e:
          logger.warning(f"JWT verification failure: {e}")
          return {}
  ```

---

### 8️⃣ A08:2021 — Software and Data Integrity Failures (Insecure Deserialization)
* **CWE Mapping:** `CWE-502` (Deserialization of Untrusted Data)
* **File Location (Local):** [`services/checkout_gateway.py (Line 42-46)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L42-L46)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 42-46)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L42-L46)
* **The Security Risk:** `pickle.loads()` deserializes arbitrary Python objects and executes any bytecode embedded in the `__reduce__` method, granting remote attackers arbitrary code execution (RCE) on the server.
* **How AgentHeal Detects It:**  
  * AST Call Visitor flags any direct invocation of `pickle.loads()` or `yaml.load()` without `SafeLoader`.
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
      # Remediated: Safe JSON deserialization prevents arbitrary code execution
      try:
          return json.loads(raw_session_json)
      except (json.JSONDecodeError, TypeError) as e:
          logger.warning(f"Failed to parse cart session: {e}")
          return {}
  ```

---

### 9️⃣ A09:2021 — Security Logging and Monitoring Failures
* **CWE Mapping:** `CWE-778` (Insufficient Logging), `CWE-390` (Detection of Error Condition Without Action)
* **File Location (Local):** [`services/checkout_gateway.py (Line 90-97)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L90-L97)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 90-97)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L90-L97)
* **The Security Risk:** Silently catching exceptions with `pass` hides transaction failures, security anomalies, and exploit attempts from observability tools (Prometheus, Datadog), preventing self-healing intervention.
* **How AgentHeal Detects It:**  
  * AST `visit_ExceptHandler` inspects exception blocks containing only `pass` or `continue`.
* **Vulnerable Pattern (PR #11):**
  ```python
  def audit_transaction_metrics(order_id: str, amount: float) -> None:
      try:
          if amount < 0:
              raise ValueError("Negative transaction amount")
      except Exception:
          # Vulnerable: Swallowed exception masks security anomaly
          pass
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  def audit_transaction_metrics(order_id: str, amount: float) -> None:
      try:
          if amount < 0:
              raise ValueError("Negative transaction amount")
      except Exception as e:
          # Remediated: Structured telemetry error logging
          logger.error(f"Audit metric error for order {order_id}: {e}")
  ```

---

### 🔟 A10:2021 — Server-Side Request Forgery (SSRF)
* **CWE Mapping:** `CWE-918` (Server-Side Request Forgery)
* **File Location (Local):** [`services/checkout_gateway.py (Line 73-77)`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/services/checkout_gateway.py#L73-L77)
* **GitHub Link:** [PR #11 `services/checkout_gateway.py` (Line 73-77)](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/blob/feature/v2-checkout-gateway/services/checkout_gateway.py#L73-L77)
* **The Security Risk:** Sending HTTP requests to arbitrary user-supplied URLs allows attackers to target internal cloud metadata endpoints (e.g. `http://169.254.169.254/latest/meta-data/`) to steal IAM instance role credentials.
* **How AgentHeal Detects It:**  
  * AST Call Visitor inspects outbound HTTP methods (`requests.get`, `requests.post`, `urllib.request.urlopen`) with dynamic variable arguments lacking validation.
* **Vulnerable Pattern (PR #11):**
  ```python
  def send_payment_webhook(target_url: str, payload: Dict[str, Any]) -> int:
      # Vulnerable: Outbound HTTP request to unvalidated URL allows SSRF
      response = requests.get(target_url)
      return response.status_code
  ```
* **Autonomous Remediation (PR #12):**
  ```python
  ALLOWED_WEBHOOK_DOMAINS = {"api.partner-gateway.com", "notifications.internal.corp", "checkout.stripe.com"}

  def send_payment_webhook(target_url: str, payload: Dict[str, Any]) -> int:
      # Remediated: Hostname parsed and validated against strict allowlist
      parsed = urlparse(target_url)
      if parsed.hostname not in ALLOWED_WEBHOOK_DOMAINS:
          raise ValueError(f"Webhook destination host '{parsed.hostname}' is not authorized")
      response = requests.post(target_url, json=payload, timeout=5.0)
      return response.status_code
  ```

---

## 📊 Live Demo Pull Request Matrix

| Category | Category Name | Status (PR #11) | Detected Violations | Status (PR #12 Auto-Fix) |
|---|---|:---:|---|:---:|
| **A01:2021** | Broken Access Control | 🔴 **VIOLATION** | `Path Traversal (Line 52)` | 🟢 **Compliant** |
| **A02:2021** | Cryptographic Failures | 🔴 **VIOLATION** | `Hardcoded Secret (Line 20)` + `Weak MD5 (Line 38)` | 🟢 **Compliant** |
| **A03:2021** | Injection | 🔴 **VIOLATION** | `SQLi f-string (Line 29)` + `Command Injection (Line 56)` | 🟢 **Compliant** |
| **A04:2021** | Insecure Design | 🔴 **VIOLATION** | `Unbounded Query Memory (Line 70)` | 🟢 **Compliant** |
| **A05:2021** | Security Misconfiguration | 🔴 **VIOLATION** | `DEBUG = True (Line 17)` | 🟢 **Compliant** |
| **A06:2021** | Vulnerable Components | 🔴 **VIOLATION** | `pyyaml==5.3` + `requests==2.28.0` | 🟢 **Compliant** |
| **A07:2021** | Identification & Auth Failures | 🔴 **VIOLATION** | `JWT Token (Line 23)` + `Unverified Decode (Line 63)` | 🟢 **Compliant** |
| **A08:2021** | Software & Data Integrity | 🔴 **VIOLATION** | `pickle.loads() Insecure Deserialization (Line 45)` | 🟢 **Compliant** |
| **A09:2021** | Logging & Monitoring Failures | 🔴 **VIOLATION** | `Swallowed Exception except: pass (Line 95)` | 🟢 **Compliant** |
| **A10:2021** | Server-Side Request Forgery | 🔴 **VIOLATION** | `SSRF Dynamic Outbound Request (Line 76)` | 🟢 **Compliant** |

---

## 🔗 Live Demo Presentation Links

* **❌ Live Vulnerable Pull Request (PR #11):**  
  [https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/11](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/11)  
  *Features: Full 10/10 OWASP Table, AST Test Gaps, Mermaid Call Graph, Red ❌ Quality Gate, Interactive @review-bot Thread.*

* **✅ Live Autonomous Remediation PR (PR #12):**  
  [https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/12](https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pull/12)  
  *Features: 100% Remediated codebase, parameterized SQL queries, SHA-256 HMAC, RS256 JWT, passing unit tests.*

* **💻 Local Interactive Dashboard:**  
  `http://localhost:8000` (Navigate to `🛡️ OWASP Top 10` Tab)  
  *Features: Live interactive scorecard, category pills, instant AST Code & Dependency Scanner.*

* **⚙️ Core Engine Implementation:**  
  [`pr_review_agent/owasp_auditor.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/pr_review_agent/owasp_auditor.py)

* **🧪 Comprehensive Test Suite (12/12 Passing):**  
  [`tests/test_owasp_auditor.py`](file:///c:/Users/aadih/Desktop/desktop/work/College/Semester%205/Cloud%20Computing/Project/tests/test_owasp_auditor.py)
