"""Shared transient-error retry decorator for external HTTP calls.

Provides :data:`TRANSIENT_RETRY` — a pre-configured :func:`tenacity.retry`
decorator for ``async`` functions that make outbound HTTP requests.

The retry predicate delegates to :func:`owlbear.core.errors.classify_error`
so that classification logic stays in one place.
"""

from __future__ import annotations

import logging

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from owlbear.core.errors import ErrorCategory, classify_error

__all__ = ["TRANSIENT_RETRY"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Predicate
# ---------------------------------------------------------------------------


def _is_transient_http(exc: BaseException) -> bool:
    """Return ``True`` if *exc* is a transient HTTP error worth retrying."""
    return isinstance(exc, Exception) and classify_error(exc) == ErrorCategory.TRANSIENT


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

TRANSIENT_RETRY = retry(
    retry=retry_if_exception(_is_transient_http),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=5),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
