"""Cost estimation from model name, provider, and token counts.

Wraps :func:`genai_prices.calc_price` to provide a simple
``calc_estimated_cost()`` function that returns a ``float`` dollar cost
or ``None`` when the model/provider combination is not found in the
price database.

**Fallback behaviour:** the function *never* raises an exception.  When
the price lookup fails (unknown model, unknown provider, or any
unexpected error) it logs a warning via the module logger and returns
``None``.
"""

from __future__ import annotations

import logging

import genai_prices

logger = logging.getLogger(__name__)

# Providers that are not in the genai-prices database but map to a
# known provider for pricing purposes.
_PROVIDER_ALIASES: dict[str, str] = {
    "copilot": "openai",
}


def calc_estimated_cost(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Estimate the dollar cost for a single LLM call.

    Args:
        model: The model identifier (e.g. ``"gpt-4o"``).
        provider: The provider name (e.g. ``"openai"``, ``"copilot"``).
        input_tokens: Number of input/prompt tokens consumed.
        output_tokens: Number of output/completion tokens consumed.

    Returns:
        Estimated cost in US dollars, or ``None`` when the model/provider
        pair is not found in the price database.
    """
    try:
        resolved_provider = _PROVIDER_ALIASES.get(provider, provider)
        usage = genai_prices.Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        result = genai_prices.calc_price(
            usage,
            model,
            provider_id=resolved_provider,
        )
        total = float(result.total_price)
    except Exception:  # noqa: BLE001 — intentional broad catch
        logger.warning(
            "Price lookup failed for model=%r provider=%r; returning None",
            model,
            provider,
        )
        return None
    else:
        if total <= 0.0:
            return None
        return total
