"""
pr_review_agent — GitHub PR Review Agent (Product A).

Provides automated code review via static analysis + LLM, GitHub App auth,
per-repo config, inline comments with suggestion blocks, quality gate Check Runs,
and a learnings loop for dismissals.

Products:
  A (this module) — PR Review Agent
  B (agentic_engine/) — Infra Self-Healing Agent (separate, unchanged)
"""
from pr_review_agent import db

# Initialise the SQLite database on first import.
# This is idempotent (CREATE TABLE IF NOT EXISTS) and safe to call multiple times.
db.init_db()
db.load_env_app_into_db()
