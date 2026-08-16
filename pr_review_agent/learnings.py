"""
pr_review_agent/learnings.py — Dismissal CRUD and finding suppression.

When a reviewer dismisses a finding from the dashboard or comments
'@review-bot dismiss <rule_id>', that rule_id is persisted so future
reviews on the same repo skip it.
"""
import logging
from typing import Dict, List

from pr_review_agent import db

logger = logging.getLogger(__name__)


def record_dismissal(repo_full_name: str, rule_id: str, note: str = "") -> int:
    """
    Persist a dismissal for rule_id in repo_full_name.
    Returns the new dismissal row id.
    """
    row_id = db.add_dismissal(repo_full_name, rule_id, note or None)
    logger.info("[learnings] Dismissed rule '%s' for repo %s (id=%s)", rule_id, repo_full_name, row_id)
    return row_id


def get_suppressed_rules(repo_full_name: str) -> set:
    """Return the set of rule_ids suppressed for this repo."""
    return db.get_suppressed_rules(repo_full_name)


def filter_findings(findings: List[Dict], repo_full_name: str) -> List[Dict]:
    """
    Remove findings whose rule_id has been dismissed for this repo.
    Also removes findings with no rule_id if they have been explicitly suppressed
    via an empty string match (edge case guard).
    """
    suppressed = get_suppressed_rules(repo_full_name)
    if not suppressed:
        return findings
    filtered = [f for f in findings if f.get("rule_id", "") not in suppressed]
    dropped = len(findings) - len(filtered)
    if dropped:
        logger.info("[learnings] Suppressed %d finding(s) for %s via dismissals", dropped, repo_full_name)
    return filtered


def get_all_dismissals(repo_full_name: str) -> List[Dict]:
    """Return all dismissal records for a repo (for the dashboard)."""
    return db.get_dismissals(repo_full_name)


def remove_dismissal(dismissal_id: int) -> None:
    """Un-dismiss a rule by its row id."""
    db.remove_dismissal(dismissal_id)
    logger.info("[learnings] Removed dismissal id=%s", dismissal_id)
