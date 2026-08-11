"""Canonical Delivery application assembly for Cockpit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    load_delivery_application,
)
from owlbear_delivery_github import GitHubCliPublicationProvider

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.portfolio_application import PortfolioApplication


def load_target_context(workspace_root: Path) -> PortfolioApplication:
    """Load one validated Delivery application from the canonical workspace root."""
    try:
        config_path = workspace_root / ".owlbear/delivery/config.json"
        config = DeliveryStartupConfig.model_validate_json(config_path.read_bytes())
        return load_delivery_application(
            config,
            workspace_root=workspace_root,
            publication_provider=GitHubCliPublicationProvider(),
        )
    except DeliveryApplicationLoadError as exc:
        message = f"Cockpit Delivery startup failed for {exc.field}: {exc.detail}"
        raise RuntimeError(message) from exc
    except (OSError, ValidationError) as exc:
        message = "Cockpit startup requires valid Delivery configuration"
        raise RuntimeError(message) from exc


__all__ = ["load_target_context"]
