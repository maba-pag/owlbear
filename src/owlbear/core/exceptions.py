"""OwlBear root exception.

All custom OwlBear exceptions inherit from :class:`OwlBearError` so that
``except OwlBearError`` catches any OwlBear-originated error without
catching third-party or stdlib exceptions.

See ``docs/research/exception-hierarchy.md`` for design rationale.
"""

from __future__ import annotations


class OwlBearError(Exception):
    """Root base class for all OwlBear-specific exceptions."""
