"""Copilot premium request multiplier lookup.

GitHub Copilot charges "premium requests" per model interaction. Different
models consume different amounts of premium requests, expressed as a
multiplier of the base rate (1.0 = one premium request).

The ``COPILOT_MULTIPLIERS`` dict maps canonical model names to their
multiplier.  For models not in the dict the default is **1.0**.

**Update cadence:** check the GitHub Copilot docs quarterly (Mar / Jun /
Sep / Dec) and update the multiplier values.  Source:
https://docs.github.com/en/copilot/managing-copilot/monitoring-usage-and-spending/
"""

from __future__ import annotations

COPILOT_MULTIPLIERS: dict[str, float] = {
    "gpt-4o": 1.0,
    "gpt-4o-mini": 0.25,
    "o1": 10.0,
    "o1-mini": 0.33,
    "o3-mini": 3.0,
    "claude-3.5-sonnet": 1.0,
    "claude-3.7-sonnet": 1.0,
}
"""Mapping of model name → premium-request multiplier.

Base models cost 1.0 premium request.  Reasoning models (o1, o3-mini) cost
more.  Values sourced from GitHub Copilot public docs, Feb 2026.
"""

_KNOWN_PREFIXES = ("openai:", "copilot:")


def get_premium_requests(model: str) -> float:
    """Return the premium-request multiplier for *model*.

    The function strips known provider prefixes (``openai:``, ``copilot:``)
    before looking up the canonical name.  Unknown models default to **1.0**.

    Args:
        model: Model identifier, optionally prefixed with a provider tag.

    Returns:
        Premium-request multiplier as a :class:`float`.
    """
    for prefix in _KNOWN_PREFIXES:
        if model.startswith(prefix):
            model = model[len(prefix) :]
            break

    return COPILOT_MULTIPLIERS.get(model, 1.0)
