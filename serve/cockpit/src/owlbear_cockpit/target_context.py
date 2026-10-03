"""Canonical Delivery application assembly for Cockpit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    load_configured_delivery_application,
)
from owlbear_delivery.state_formats import StateCapabilityError, config_capability, require_capability
from owlbear_delivery_github import GitHubCliPublicationProvider

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.portfolio_application import PortfolioApplication


def _read_config(config_path: Path) -> DeliveryStartupConfig:
    content = config_path.read_bytes()
    require_capability(config_capability(content))
    return DeliveryStartupConfig.model_validate_json(content)


def load_target_context(workspace_root: Path) -> PortfolioApplication:
    """Load one validated Delivery application; the configuration is read only inside the core fence."""
    if not (workspace_root / ".owlbear/delivery/config.json").is_file():
        message = "Cockpit startup requires valid Delivery configuration"
        raise RuntimeError(message)
    try:
        return load_configured_delivery_application(
            workspace_root,
            _read_config,
            publication_provider=GitHubCliPublicationProvider(),
        )
    except StateCapabilityError as exc:
        message = f"Cockpit Delivery startup failed for state_version: {exc.detail}"
        raise RuntimeError(message) from exc
    except DeliveryApplicationLoadError as exc:
        message = f"Cockpit Delivery startup failed for {exc.field}: {exc.detail}"
        raise RuntimeError(message) from exc
    except (OSError, ValidationError) as exc:
        message = "Cockpit startup requires valid Delivery configuration"
        raise RuntimeError(message) from exc


__all__ = ["load_target_context"]
