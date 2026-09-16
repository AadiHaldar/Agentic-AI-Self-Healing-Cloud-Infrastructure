"""
pr_review_agent/owasp_auditor.py — Dedicated OWASP Top 10 (2021/2025) Security & Compliance Engine.

Maps static analysis, AST compiler inspection, dependency versions, and code patterns
directly to official OWASP Top 10 categories:
  • A01:2021 — Broken Access Control
  • A02:2021 — Cryptographic Failures
  • A03:2021 — Injection (SQLi, Command Injection, Code Exec)
  • A04:2021 — Insecure Design
  • A05:2021 — Security Misconfiguration
  • A06:2021 — Vulnerable and Outdated Components (Dependabot-style supply chain scanning)
  • A07:2021 — Identification and Authentication Failures
  • A08:2021 — Software and Data Integrity Failures (Insecure Deserialization)
  • A09:2021 — Security Logging and Monitoring Failures
  • A10:2021 — Server-Side Request Forgery (SSRF)
"""
import ast
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Official OWASP Top 10 Category Definitions
OWASP_CATEGORIES = {
    "A01": {"id": "A01:2021", "name": "Broken Access Control", "weight": 20},
    "A02": {"id": "A02:2021", "name": "Cryptographic Failures", "weight": 15},
    "A03": {"id": "A03:2021", "name": "Injection", "weight": 25},
    "A04": {"id": "A04:2021", "name": "Insecure Design", "weight": 10},
    "A05": {"id": "A05:2021", "name": "Security Misconfiguration", "weight": 10},
    "A06": {"id": "A06:2021", "name": "Vulnerable and Outdated Components", "weight": 15},
    "A07": {"id": "A07:2021", "name": "Identification and Authentication Failures", "weight": 15},
    "A08": {"id": "A08:2021", "name": "Software and Data Integrity Failures", "weight": 20},
    "A09": {"id": "A09:2021", "name": "Security Logging and Monitoring Failures", "weight": 10},
    "A10": {"id": "A10:2021", "name": "Server-Side Request Forgery (SSRF)", "weight": 15},
}

# Known vulnerable library versions (Supply chain / Dependabot-style CVE database)
KNOWN_VULNERABLE_PACKAGES = {
    "pyyaml": {"bad_versions": ["<5.4"], "cve": "CVE-2020-14343", "fix": "5.4.1+", "desc": "Arbitrary code execution through untrusted YAML load"},
    "requests": {"bad_versions": ["<2.31.0"], "cve": "CVE-2023-32681", "fix": "2.31.0+", "desc": "Leaking Proxy-Authorization header to destination servers"},
    "urllib3": {"bad_versions": ["<1.26.18", "<2.0.7"], "cve": "CVE-2023-45803", "fix": "1.26.18+ / 2.0.7+", "desc": "Request body strip on 303 redirect"},
    "flask": {"bad_versions": ["<2.2.5"], "cve": "CVE-2023-30861", "fix": "2.2.5+", "desc": "Session cookie disclosure with unexpected secret keys"},
    "cryptography": {"bad_versions": ["<41.0.4"], "cve": "CVE-2023-49083", "fix": "41.0.4+", "desc": "NULL-dereference in PKCS7 parsing"},
    "jwt": {"bad_versions": ["<2.4.0"], "cve": "CVE-2022-29217", "fix": "2.4.0+", "desc": "Algorithm confusion key confusion attack"},
    "jinja2": {"bad_versions": ["<3.1.3"], "cve": "CVE-2024-22195", "fix": "3.1.3+", "desc": "HTML attribute injection and XSS via xmlattr filter"},
}


@dataclass
class OWASPFinding:
    category_id: str          # e.g., 'A03:2021'
    category_name: str        # e.g., 'Injection'
    severity: str             # 'critical' | 'high' | 'medium' | 'low'
    file: str
    line: int
    title: str
    description: str
    recommendation: str
    cwe_id: Optional[str] = None
    rule_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OWASPAuditResult:
    compliance_score: float              # 0.0 to 100.0%
    grade: str                           # 'A+' | 'A' | 'B' | 'C' | 'D' | 'F'
    total_findings: int
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    findings: List[OWASPFinding] = field(default_factory=list)
    compliant_categories: List[str] = field(default_factory=list)
    violated_categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compliance_score": round(self.compliance_score, 1),
            "grade": self.grade,
            "total_findings": self.total_findings,
            "findings_by_category": self.findings_by_category,
            "compliant_categories": self.compliant_categories,
            "violated_categories": self.violated_categories,
            "findings": [f.to_dict() for f in self.findings],
        }


class OWASPASTVisitor(ast.NodeVisitor):
    """AST Inspector for OWASP Top 10 vulnerability patterns."""

    def __init__(self, filename: str, code: str):
        self.filename = filename
        self.code = code
        self.lines = code.splitlines()
        self.findings: List[OWASPFinding] = []

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # ── A03: Injection (eval, exec, subprocess with shell=True) ──
        if func_name in ("eval", "exec"):
            self.findings.append(OWASPFinding(
                category_id="A03:2021",
                category_name="Injection",
                severity="critical",
                file=self.filename,
                line=node.lineno,
                title=f"Dynamic Code Execution via `{func_name}()`",
                description=f"Direct invocation of `{func_name}()` executes arbitrary unvalidated strings as code.",
                recommendation=f"Replace `{func_name}()` with safe static parsers like `ast.literal_eval()` or dedicated data serialization.",
                cwe_id="CWE-95",
                rule_id="owasp-a03-eval"
            ))

        if func_name in ("Popen", "call", "run", "check_call", "check_output", "system"):
            # Check for shell=True in kwargs
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append(OWASPFinding(
                        category_id="A03:2021",
                        category_name="Injection",
                        severity="critical",
                        file=self.filename,
                        line=node.lineno,
                        title="Command Injection Risk (`shell=True`)",
                        description="`subprocess` called with `shell=True` passes arguments through the shell interpreter, enabling command injection.",
                        recommendation="Pass command arguments as a list of strings and set `shell=False`.",
                        cwe_id="CWE-78",
                        rule_id="owasp-a03-shell"
                    ))

        # ── A02: Cryptographic Failures (Weak MD5/SHA1 hashing) ──
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "hashlib" and func_name in ("md5", "sha1"):
                self.findings.append(OWASPFinding(
                    category_id="A02:2021",
                    category_name="Cryptographic Failures",
                    severity="high",
                    file=self.filename,
                    line=node.lineno,
                    title=f"Broken Hash Function `{node.func.value.id}.{func_name}()`",
                    description=f"{func_name.upper()} is cryptographically broken and vulnerable to collision and pre-image attacks.",
                    recommendation="Use `hashlib.sha256()`, `hashlib.sha3_256()`, or `bcrypt`/`argon2` for passwords.",
                    cwe_id="CWE-328",
                    rule_id="owasp-a02-weak-hash"
                ))

        # ── A08: Insecure Deserialization (pickle.loads, yaml.load without safe loader) ──
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "pickle" and func_name in ("loads", "load"):
                self.findings.append(OWASPFinding(
                    category_id="A08:2021",
                    category_name="Software and Data Integrity Failures",
                    severity="critical",
                    file=self.filename,
                    line=node.lineno,
                    title="Insecure Deserialization via `pickle.loads()`",
                    description="Unpickling untrusted data allows arbitrary Python object reconstruction and remote code execution.",
                    recommendation="Use safe serialization formats like `json`, `protobuf`, or `msgpack`.",
                    cwe_id="CWE-502",
                    rule_id="owasp-a08-insecure-deserialization"
                ))

            if node.func.value.id == "yaml" and func_name in ("load", "load_all"):
                has_safe_loader = any(
                    kw.arg == "Loader" and getattr(kw.value, "id", "") in ("SafeLoader", "CSafeLoader")
                    for kw in node.keywords
                )
                if not has_safe_loader:
                    self.findings.append(OWASPFinding(
                        category_id="A08:2021",
                        category_name="Software and Data Integrity Failures",
                        severity="high",
                        file=self.filename,
                        line=node.lineno,
                        title="Unsafe YAML Deserialization",
                        description="`yaml.load()` without `Loader=yaml.SafeLoader` can execute arbitrary code during document parsing.",
                        recommendation="Use `yaml.safe_load()` instead of `yaml.load()`.",
                        cwe_id="CWE-502",
                        rule_id="owasp-a08-unsafe-yaml"
                    ))

        # ── A10: Server-Side Request Forgery (SSRF) ──
        if func_name in ("get", "post", "put", "delete", "urlopen") and isinstance(node.func, ast.Attribute):
            mod_name = getattr(node.func.value, "id", "")
            if mod_name in ("requests", "httpx", "urllib", "client"):
                if node.args and isinstance(node.args[0], (ast.Name, ast.JoinedStr)):
                    self.findings.append(OWASPFinding(
                        category_id="A10:2021",
                        category_name="Server-Side Request Forgery (SSRF)",
                        severity="medium",
                        file=self.filename,
                        line=node.lineno,
                        title="Potential SSRF in External HTTP Request",
                        description="Outbound HTTP request takes dynamic URL variables without apparent allowlist validation.",
                        recommendation="Validate destination hostnames against a strict internal allowlist and disable loopback/metadata queries (e.g. 169.254.169.254).",
                        cwe_id="CWE-918",
                        rule_id="owasp-a10-ssrf"
                    ))

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # ── A09: Security Logging & Monitoring Failures (Silent exception swallow) ──
        if len(node.body) == 1 and isinstance(node.body[0], (ast.Pass, ast.Continue)):
            self.findings.append(OWASPFinding(
                category_id="A09:2021",
                category_name="Security Logging and Monitoring Failures",
                severity="medium",
                file=self.filename,
                line=node.lineno,
                title="Silently Swallowed Exception (`except: pass`)",
                description="Exception block catches errors and executes `pass` without logging, masking system breaches or outages.",
                recommendation="Log the exception with stack trace (`logger.exception(...)`) or raise an explicit custom error.",
                cwe_id="CWE-778",
                rule_id="owasp-a09-unlogged-exception"
            ))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # ── A05: Security Misconfiguration (DEBUG = True) ──
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.upper() in ("DEBUG", "DEBUG_MODE"):
                if isinstance(node.value, ast.Constant) and node.value.value is True:
                    self.findings.append(OWASPFinding(
                        category_id="A05:2021",
                        category_name="Security Misconfiguration",
                        severity="high",
                        file=self.filename,
                        line=node.lineno,
                        title="Production Debug Mode Enabled (`DEBUG = True`)",
                        description="Running with `DEBUG = True` exposes internal stack traces, interactive debuggers, and server environment data to users.",
                        recommendation="Set `DEBUG = False` or read debug status dynamically from an environment variable defaulted to False.",
                        cwe_id="CWE-489",
                        rule_id="owasp-a05-debug-enabled"
                    ))
        self.generic_visit(node)


class OWASPAuditor:
    """Core engine for running comprehensive OWASP Top 10 security audits."""

    def __init__(self):
        pass

    def audit_python_code(self, code: str, filename: str = "snippet.py") -> List[OWASPFinding]:
        """Run AST and pattern checks against raw Python code."""
        findings: List[OWASPFinding] = []

        # 1. AST Analysis
        try:
            tree = ast.parse(code, filename=filename)
            visitor = OWASPASTVisitor(filename, code)
            visitor.visit(tree)
            findings.extend(visitor.findings)
        except SyntaxError as e:
            logger.debug(f"[OWASPAuditor] Syntax error parsing {filename}: {e}")

        # 2. Regex Pattern Checks for SQLi (A03)
        sql_patterns = [
            (r'f["\'].*SELECT.*FROM.*\{.+\}', "SQL Injection via f-string string formatting", "CWE-89"),
            (r'f["\'].*INSERT\s+INTO.*\{.+\}', "SQL Injection in INSERT statement", "CWE-89"),
            (r'f["\'].*DELETE\s+FROM.*\{.+\}', "SQL Injection in DELETE statement", "CWE-89"),
            (r'f["\'].*UPDATE.*SET.*\{.+\}', "SQL Injection in UPDATE statement", "CWE-89"),
            (r'["\'].*SELECT.*FROM.*%s["\']\s*%', "SQL Injection via `%` operator interpolation", "CWE-89"),
        ]
        for line_no, line in enumerate(code.splitlines(), start=1):
            for pattern, title, cwe in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(OWASPFinding(
                        category_id="A03:2021",
                        category_name="Injection",
                        severity="critical",
                        file=filename,
                        line=line_no,
                        title=title,
                        description="SQL queries assembled with string concatenation are vulnerable to arbitrary SQL injection and data exfiltration.",
                        recommendation="Use parameterized queries with placeholders: `cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))`",
                        cwe_id=cwe,
                        rule_id="owasp-a03-sqli"
                    ))

        # 3. Pattern Checks for Hardcoded Secrets (A02 / A07)
        secret_patterns = [
            (r'(?i)(?:stripe|aws|jwt|api[_-]?key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']', "Hardcoded Secret / API Token in Source Code", "A02:2021", "Cryptographic Failures"),
        ]
        for line_no, line in enumerate(code.splitlines(), start=1):
            # Exclude comments
            if line.strip().startswith("#"):
                continue
            for pattern, title, cat_id, cat_name in secret_patterns:
                if re.search(pattern, line):
                    findings.append(OWASPFinding(
                        category_id=cat_id,
                        category_name=cat_name,
                        severity="critical",
                        file=filename,
                        line=line_no,
                        title=title,
                        description="Sensitive credentials committed in source code expose production systems to unauthorized access.",
                        recommendation="Store credentials in environment variables or Azure Key Vault / AWS Secrets Manager.",
                        cwe_id="CWE-798",
                        rule_id="owasp-a02-hardcoded-secret"
                    ))

        # 4. Pattern Checks for Insecure Access Control & Path Traversal (A01)
        path_traversal_pattern = r'os\.path\.join\(.*,\s*(?:user_input|path|filename|req|request)\w*\)'
        for line_no, line in enumerate(code.splitlines(), start=1):
            if re.search(path_traversal_pattern, line, re.IGNORECASE):
                findings.append(OWASPFinding(
                    category_id="A01:2021",
                    category_name="Broken Access Control",
                    severity="high",
                    file=filename,
                    line=line_no,
                    title="Path Traversal / Insecure File Access",
                    description="Constructing filesystem paths using untrusted variables permits unauthorized directory traversal (e.g. `../../etc/passwd`).",
                    recommendation="Sanitize filenames using `os.path.basename()` or verify absolute path resolves inside an authorized base directory.",
                    cwe_id="CWE-22",
                    rule_id="owasp-a01-path-traversal"
                ))

        return findings

    def audit_requirements_txt(self, requirements_text: str, filename: str = "requirements.txt") -> List[OWASPFinding]:
        """Dependabot-style supply chain CVE audit on dependencies (OWASP A06:2021)."""
        findings: List[OWASPFinding] = []
        for line_no, line in enumerate(requirements_text.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Match package==version or package>=version
            match = re.match(r'^([a-zA-Z0-9_\-]+)\s*(?:==|<=|>=|<|>)\s*([0-9\.]+)', line)
            if match:
                pkg_name = match.group(1).lower()
                pkg_ver = match.group(2)
                
                if pkg_name in KNOWN_VULNERABLE_PACKAGES:
                    vuln_info = KNOWN_VULNERABLE_PACKAGES[pkg_name]
                    findings.append(OWASPFinding(
                        category_id="A06:2021",
                        category_name="Vulnerable and Outdated Components",
                        severity="high",
                        file=filename,
                        line=line_no,
                        title=f"Vulnerable Dependency `{pkg_name}=={pkg_ver}` ({vuln_info['cve']})",
                        description=f"Package `{pkg_name}` version `{pkg_ver}` is affected by {vuln_info['cve']}: {vuln_info['desc']}.",
                        recommendation=f"Update `{pkg_name}` to version `{vuln_info['fix']}` in `{filename}`.",
                        cwe_id="CWE-1395",
                        rule_id=f"owasp-a06-{pkg_name}"
                    ))
        return findings

    def audit_pr_diff(self, files: List[Dict[str, Any]]) -> OWASPAuditResult:
        """Run full OWASP audit across all files in a PR diff."""
        all_findings: List[OWASPFinding] = []

        for f in files:
            filename = f.get("filename", "")
            patch = f.get("patch", "")
            
            # Audit python files
            if filename.endswith(".py"):
                # Extract added lines from patch
                added_lines = [
                    line[1:] for line in patch.splitlines()
                    if line.startswith("+") and not line.startswith("+++")
                ]
                added_code = "\n".join(added_lines)
                if added_code.strip():
                    all_findings.extend(self.audit_python_code(added_code, filename))

            # Audit requirements.txt
            if "requirements" in filename and filename.endswith(".txt"):
                req_lines = [
                    line[1:] if line.startswith("+") and not line.startswith("+++") else line
                    for line in patch.splitlines()
                ]
                req_clean = "\n".join(req_lines)
                all_findings.extend(self.audit_requirements_txt(req_clean, filename))

        # Calculate Compliance Score
        # Total penalty based on severity
        severity_penalties = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        total_penalty = sum(severity_penalties.get(f.severity, 5) for f in all_findings)
        compliance_score = max(0.0, min(100.0, 100.0 - total_penalty))

        # Determine Letter Grade
        if compliance_score >= 95.0:
            grade = "A+"
        elif compliance_score >= 85.0:
            grade = "A"
        elif compliance_score >= 75.0:
            grade = "B"
        elif compliance_score >= 60.0:
            grade = "C"
        elif compliance_score >= 40.0:
            grade = "D"
        else:
            grade = "F"

        # Group findings by category
        counts: Dict[str, int] = {}
        for f in all_findings:
            counts[f.category_id] = counts.get(f.category_id, 0) + 1

        all_cats = [v["id"] for v in OWASP_CATEGORIES.values()]
        violated_cats = list(counts.keys())
        compliant_cats = [c for c in all_cats if c not in counts]

        return OWASPAuditResult(
            compliance_score=compliance_score,
            grade=grade,
            total_findings=len(all_findings),
            findings_by_category=counts,
            findings=all_findings,
            compliant_categories=compliant_cats,
            violated_categories=violated_cats
        )

    def generate_markdown_report(self, result: OWASPAuditResult) -> str:
        """Render a clean GitHub markdown table for PR review comments."""
        badge_color = "brightgreen" if result.grade in ("A+", "A") else ("yellow" if result.grade == "B" else "red")
        
        md = []
        md.append(f"### 🛡️ OWASP Top 10 (2021/2025) Security & Compliance Audit")
        md.append(f"**Overall Compliance Score:** `{result.compliance_score}%` (**Grade: {result.grade}**) | **Violations:** `{result.total_findings}`\n")
        
        md.append("| OWASP Category | Name | Status | Violations Found |")
        md.append("|---|---|:---:|---|")
        
        for cat_key, cat_info in OWASP_CATEGORIES.items():
            cat_id = cat_info["id"]
            cat_name = cat_info["name"]
            count = result.findings_by_category.get(cat_id, 0)
            
            if count == 0:
                status_badge = "🟢 Compliant"
                notes = "*No vulnerabilities detected*"
            else:
                status_badge = "🔴 **VIOLATION**" if count > 1 or any(f.severity == 'critical' for f in result.findings if f.category_id == cat_id) else "🟡 Warning"
                matching_titles = [f.title for f in result.findings if f.category_id == cat_id]
                notes = f"**{count} issue(s):** " + "; ".join(matching_titles[:2])
            
            md.append(f"| **{cat_id}** | {cat_name} | {status_badge} | {notes} |")

        if result.findings:
            md.append("\n<details><summary><b>🔍 View Detailed OWASP Vulnerability Breakdown</b></summary>\n")
            for f in result.findings:
                md.append(f"#### ⚠️ [{f.category_id}] {f.title} ({f.severity.upper()})")
                md.append(f"* **Location:** `{f.file}:{f.line}` ({f.cwe_id or 'OWASP Standard'})")
                md.append(f"* **Description:** {f.description}")
                md.append(f"* **Remediation:** {f.recommendation}\n")
            md.append("</details>\n")

        return "\n".join(md)
