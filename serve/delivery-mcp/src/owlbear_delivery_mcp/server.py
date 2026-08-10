"""Live OwlBear MCP server for target delivery."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server import MCPServer
from pydantic import ValidationError

from owlbear_delivery import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    PortfolioApplication,
)
from owlbear_delivery import load_delivery_application as load_core_delivery_application
from owlbear_delivery_mcp.target_models import (
    DeliveryStartupDiagnostic,
)
from owlbear_delivery_mcp.target_server import (
    DeliveryAppContext,
    TargetMCPAdapter,
    register_target_tools,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_DELIVERY_CONFIG_PATH = Path(".owlbear/delivery/config.json")
_UNCONFIGURED = "ERR_DELIVERY_STARTUP_UNCONFIGURED"
_INVALID = "ERR_DELIVERY_STARTUP_INVALID"
_REQUIRED_TOP_LEVEL_FIELDS = {"schema_version", "integration_target"}
_live_context: DeliveryAppContext | None = None


def _delivery_config_path(workspace_root: Path) -> Path:
    path = workspace_root / _DELIVERY_CONFIG_PATH
    if not path.is_file():
        raise DeliveryStartupDiagnostic(
            _UNCONFIGURED,
            "Delivery startup configuration file is required",
            str(_DELIVERY_CONFIG_PATH),
        )
    return path


def load_delivery_config(path: Path) -> DeliveryStartupConfig:
    """Parse one strict startup document without constructing state owners."""
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise DeliveryStartupDiagnostic(
            _INVALID,
            "Delivery startup configuration cannot be read",
            str(_DELIVERY_CONFIG_PATH),
        ) from exc
    try:
        return DeliveryStartupConfig.model_validate_json(content)
    except ValidationError as exc:
        error = exc.errors(include_url=False, include_context=False, include_input=False)[0]
        field = _validation_field(error)
        code = _UNCONFIGURED if _is_missing_required(error, field) else _INVALID
        detail = (
            "required Delivery startup configuration is absent"
            if code == _UNCONFIGURED
            else "Delivery startup configuration field is invalid"
        )
        raise DeliveryStartupDiagnostic(code, detail, field) from exc


def _validation_field(error: dict[str, object]) -> str:
    location = error.get("loc")
    if not isinstance(location, tuple | list):
        return str(_DELIVERY_CONFIG_PATH)
    parts = tuple(str(part) for part in location)
    return ".".join(parts) if parts else str(_DELIVERY_CONFIG_PATH)


def _is_missing_required(error: dict[str, object], field: str) -> bool:
    if error.get("type") != "missing":
        return False
    return field.split(".", maxsplit=1)[0] in _REQUIRED_TOP_LEVEL_FIELDS


def load_delivery_application(config: DeliveryStartupConfig, workspace_root: Path) -> PortfolioApplication:
    """Delegate canonical workspace owner construction to Delivery."""
    try:
        return load_core_delivery_application(
            config,
            workspace_root=workspace_root,
        )
    except DeliveryApplicationLoadError as exc:
        raise DeliveryStartupDiagnostic(_INVALID, exc.detail, exc.field) from exc


def _live_application() -> PortfolioApplication:
    if _live_context is None:
        message = "Delivery application is unavailable outside server lifespan"
        raise RuntimeError(message)
    return _live_context.application


@asynccontextmanager
async def app_lifespan(_server: MCPServer) -> AsyncGenerator[DeliveryAppContext]:
    """Construct one explicitly configured Delivery application for this process."""
    global _live_context  # noqa: PLW0603 - process lifespan owns this binding.
    workspace_root = Path.cwd().resolve()
    config = load_delivery_config(_delivery_config_path(workspace_root))
    context = DeliveryAppContext(application=load_delivery_application(config, workspace_root))
    _live_context = context
    try:
        yield context
    finally:
        _live_context = None


mcp = MCPServer("owlbear-delivery", lifespan=app_lifespan)
register_target_tools(mcp, TargetMCPAdapter.from_provider(_live_application))

__all__ = [
    "DeliveryAppContext",
    "DeliveryStartupConfig",
    "DeliveryStartupDiagnostic",
    "TargetMCPAdapter",
    "app_lifespan",
    "load_delivery_application",
    "load_delivery_config",
    "mcp",
]
