"""Receipt-authorized Delivery application assembly for Cockpit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    load_delivery_application,
)
from owlbear_delivery.target_cutover import TargetCutoverError, TargetCutoverRequest, authorize_target_mutation

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.portfolio_application import PortfolioApplication


def load_target_context(workspace_root: Path, request_path: Path) -> PortfolioApplication:
    """Load one validated Delivery application after Cockpit cutover authorization."""
    try:
        request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
        authorize_target_mutation(workspace_root, request)
        config_path = workspace_root / ".owlbear/delivery/config.json"
        config = DeliveryStartupConfig.model_validate_json(config_path.read_bytes())
        authorized_target_root = (workspace_root / request.target_path).resolve()
        return load_delivery_application(
            config,
            workspace_root=workspace_root,
            authorized_target_root=authorized_target_root,
        )
    except (OSError, ValidationError, TargetCutoverError, DeliveryApplicationLoadError) as exc:
        message = "Cockpit startup requires valid target cutover authority and Delivery configuration"
        raise RuntimeError(message) from exc


__all__ = ["load_target_context"]
