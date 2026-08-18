"""
scripts/post_bot_interaction.py — Posts developer inquiry and @review-bot explanation on PR #7.
"""
import os
import sys
import json
import urllib.request
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()
from pr_review_agent.github_app_auth import get_token_for_repo

repo = "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure"
pr_number = 7
token = get_token_for_repo(repo)

url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"

# 1. Developer asks question
user_comment = "@review-bot explain the SQL injection risk in billing_gateway.py and how attackers exploit it"
req1 = urllib.request.Request(
    url,
    data=json.dumps({"body": user_comment}).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AgenticAI-ReviewBot/1.0",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
    },
    method="POST"
)
with urllib.request.urlopen(req1) as resp:
    print("1. Posted User Question to PR #7")

# 2. Bot replies with explanation
bot_reply = """### 🤖 @review-bot Architectural Explanation

**Vulnerability Analysis for `services/billing_gateway.py:17` (Bandit B608):**

1. **How Attackers Exploit It:**
   In line 17, the SQL query is constructed using Python f-string interpolation:
   ```python
   query = f"SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '{customer_id}'"
   ```
   If an adversary sends `customer_id = "' OR 1=1 --"`, the executed query becomes:
   ```sql
   SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '' OR 1=1 --'
   ```
   This dumps every customer's sensitive payment card token and balance in a single request.

2. **The Parameterized Fix:**
   Database drivers separate the SQL command template from untrusted user inputs at the protocol level:
   ```python
   cursor.execute("SELECT id, email, balance, card_token FROM accounts WHERE customer_id = ?", (customer_id,))
   ```
"""

req2 = urllib.request.Request(
    url,
    data=json.dumps({"body": bot_reply}).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AgenticAI-ReviewBot/1.0",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
    },
    method="POST"
)
with urllib.request.urlopen(req2) as resp:
    print("2. Posted Review-Bot Explanation Reply to PR #7")
