"""
pr_review_agent/retry.py — Exponential backoff retry wrapper for external API calls.

Usage:
    from pr_review_agent.retry import retry_with_backoff

    data = retry_with_backoff(
        lambda: _gh_get(url, token),
        max_attempts=4,
        base_delay=1.0,
        max_delay=30.0,
        retryable_exceptions=(urllib.error.HTTPError, urllib.error.URLError),
        retryable_http_codes={429, 500, 502, 503, 504},
    )

Design choices:
- Pure stdlib — no tenacity dependency at runtime; tenacity is listed in requirements
  as an optional accelerator but this module works standalone.
- Full jitter (random delay in [0, min(max_delay, base*2^attempt)]) avoids
  thundering-herd on Gemini / GitHub API shared rate limit windows.
- Non-retryable HTTP errors (4xx except 429) are re-raised immediately so callers
  get fast feedback on auth failures, not silent infinite loops.
"""
import logging
import random
import time
import urllib.error
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)

# Default set of HTTP codes that are worth retrying (transient errors).
_DEFAULT_RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


def retry_with_backoff(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        urllib.error.URLError,
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    retryable_http_codes: frozenset = _DEFAULT_RETRYABLE_HTTP_CODES,
    jitter: bool = True,
    label: str = "",
) -> Any:
    """
    Call `fn()` and retry up to `max_attempts` times with exponential backoff.

    Args:
        fn: Zero-argument callable to execute and retry.
        max_attempts: Maximum number of total attempts (1 = no retry).
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Cap on delay between retries in seconds.
        retryable_exceptions: Exception types that trigger a retry.
        retryable_http_codes: HTTP status codes (from HTTPError) that retry.
        jitter: Apply full jitter to avoid thundering-herd (recommended).
        label: Optional string for log messages (e.g., "gh_post /repos/.../pulls").

    Returns:
        The return value of `fn()` on success.

    Raises:
        The last exception if all attempts are exhausted.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()

        except urllib.error.HTTPError as exc:
            if exc.code not in retryable_http_codes:
                # 4xx (non-429) — caller bug or auth failure; don't retry
                logger.debug(
                    "[retry] %s HTTP %s — not retrying (non-transient)", label or "call", exc.code
                )
                raise

            last_exc = exc
            if attempt == max_attempts:
                break

            delay = _compute_delay(attempt, base_delay, max_delay, jitter)
            logger.warning(
                "[retry] %s HTTP %s (attempt %d/%d) — retrying in %.1fs",
                label or "call", exc.code, attempt, max_attempts, delay,
            )
            time.sleep(delay)

        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                break

            delay = _compute_delay(attempt, base_delay, max_delay, jitter)
            logger.warning(
                "[retry] %s %s (attempt %d/%d) — retrying in %.1fs",
                label or "call", type(exc).__name__, attempt, max_attempts, delay,
            )
            time.sleep(delay)

    logger.error(
        "[retry] %s exhausted %d attempts — last error: %s",
        label or "call", max_attempts, last_exc,
    )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"retry_with_backoff: {label or 'call'} failed with no exception recorded")


def _compute_delay(attempt: int, base_delay: float, max_delay: float, jitter: bool) -> float:
    """Compute full-jitter exponential backoff delay."""
    cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
    return random.uniform(0, cap) if jitter else cap
