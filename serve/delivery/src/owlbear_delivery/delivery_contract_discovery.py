"""Read-only discovery of persisted Delivery Change authority."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.delivery_runtime import (
    DeliveryChangeStage,
    DeliveryFrontier,
    DeliveryRuntimeMigrationError,
    derive_change_stage,
    parse_delivery_frontier,
)
from owlbear_delivery.target_admission import (
    DeliveryAdmissionConflictError,
    DeliveryAdmissionReceipt,
    _validate_delivery_frontier,
)
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from pathlib import Path


class _DiscoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryDiscoveryErrorCode(StrEnum):
    """Bounded causes retained for one unreadable persisted Change entry."""

    CONTRACT_UNAVAILABLE = "contract-unavailable"
    CONTRACT_INVALID = "contract-invalid"
    CONTRACT_IDENTITY_INVALID = "contract-identity-invalid"
    ADMISSION_UNAVAILABLE = "admission-unavailable"
    ADMISSION_INVALID = "admission-invalid"
    ADMISSION_IDENTITY_INVALID = "admission-identity-invalid"
    FRONTIER_UNAVAILABLE = "frontier-unavailable"
    FRONTIER_INVALID = "frontier-invalid"
    FRONTIER_MIGRATION_REQUIRED = "frontier-migration-required"
    FRONTIER_BINDING_INVALID = "frontier-binding-invalid"
    ADMISSION_CONTRACT_MISMATCH = "admission-contract-mismatch"
    ADMISSION_FRONTIER_MISMATCH = "admission-frontier-mismatch"


class DeliveryDiscoveryError(_DiscoveryModel):
    """Safe bounded diagnostic for one persisted Change observation."""

    code: DeliveryDiscoveryErrorCode
    detail: str = Field(min_length=1, max_length=240)


class DeliveryChangeObservation(_DiscoveryModel):
    """Persisted admission, contract, and frontier evidence for one Change."""

    change_id: str = Field(min_length=1)
    admission: DeliveryAdmissionReceipt | None = None
    contract: DeliveryContract | None = None
    contract_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    frontier: DeliveryFrontier | None = None
    stage: DeliveryChangeStage | None = None
    error: DeliveryDiscoveryError | None = None

    @model_validator(mode="after")
    def _validate_projection(self) -> DeliveryChangeObservation:
        if self.contract is None and self.contract_fingerprint is not None:
            message = "contract fingerprint requires a validated contract"
            raise ValueError(message)
        if self.frontier is None and self.stage is not None:
            message = "Change stage requires a validated frontier"
            raise ValueError(message)
        return self

    @property
    def admitted(self) -> bool:
        """Return whether validated persisted admission evidence exists."""
        return self.admission is not None

    @property
    def actionable_runtime(self) -> bool:
        """Return whether persisted evidence is sufficient for runtime composition."""
        return self.error is None and self.contract is not None and self.frontier is not None

    @property
    def diagnostic_code(self) -> str | None:
        """Return a safe projection diagnostic without exposing internal causes."""
        if self.admitted and not self.actionable_runtime:
            return "runtime_unavailable"
        return self.error.code.value if self.error is not None else None

    @property
    def diagnostic_detail(self) -> str | None:
        """Return a bounded diagnostic detail for read-side status projection."""
        if self.admitted and not self.actionable_runtime:
            if self.error is not None:
                return self.error.detail
            return "Persisted admission is valid, but actionable runtime composition is unavailable."
        return self.error.detail if self.error is not None else None


class DeliveryDiscoveryRootError(RuntimeError):
    """The persisted Change directory cannot be enumerated safely."""

    __slots__ = ("detail",)

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class DeliveryDiscoveryStartupError(RuntimeError):
    """Strict startup validation rejected one discovered Change entry."""

    __slots__ = ("observation",)

    def __init__(self, observation: DeliveryChangeObservation) -> None:
        self.observation = observation
        detail = observation.error.detail if observation.error is not None else "Delivery state is invalid"
        super().__init__(detail)


_CHANGE_FILES = ("contract.json", "frontier.json", "admission.json")
_FILE_ERROR_CODES = {
    "contract.json": DeliveryDiscoveryErrorCode.CONTRACT_UNAVAILABLE,
    "frontier.json": DeliveryDiscoveryErrorCode.FRONTIER_UNAVAILABLE,
    "admission.json": DeliveryDiscoveryErrorCode.ADMISSION_UNAVAILABLE,
}


def contract_fingerprint(contract: DeliveryContract) -> str:
    """Return the stable digest of canonical validated contract identity and content."""
    payload = (
        json.dumps(
            contract.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    return hashlib.sha256(payload).hexdigest()


def _source_bindings_fingerprint(contract: DeliveryContract) -> str:
    payload = json.dumps(
        [binding.model_dump(mode="json") for binding in contract.source_bindings],
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _error(code: DeliveryDiscoveryErrorCode, detail: str) -> DeliveryDiscoveryError:
    bounded = " ".join(detail.split())[:240]
    return DeliveryDiscoveryError(code=code, detail=bounded or "Persisted Delivery state is unavailable")


def _read_file(change_root: Path, name: str) -> tuple[bytes | None, DeliveryDiscoveryError | None]:
    path = change_root / name
    try:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            return None, _error(
                _FILE_ERROR_CODES[name],
                "Persisted Change entry contains an unreadable authority file",
            )
        if not path.exists():
            return None, None
        return path.read_bytes(), None
    except OSError:
        return None, _error(
            _FILE_ERROR_CODES[name],
            "Persisted Change entry contains an unreadable authority file",
        )


def _parse_contract(
    change_id: str,
    contents: dict[str, bytes],
    file_errors: dict[str, DeliveryDiscoveryError],
) -> tuple[DeliveryContract | None, DeliveryDiscoveryError | None]:
    if "contract.json" in file_errors:
        return None, file_errors["contract.json"]
    content = contents.get("contract.json")
    if content is None:
        return None, _error(
            DeliveryDiscoveryErrorCode.CONTRACT_UNAVAILABLE,
            "Persisted Change contract is missing",
        )
    try:
        contract = DeliveryContract.model_validate_json(content)
    except (TypeError, ValueError, ValidationError):
        return None, _error(DeliveryDiscoveryErrorCode.CONTRACT_INVALID, "Persisted Change contract is invalid")
    if contract.change_id != change_id:
        return contract, _error(
            DeliveryDiscoveryErrorCode.CONTRACT_IDENTITY_INVALID,
            "Persisted Change contract identity is invalid",
        )
    return contract, None


def _parse_frontier(
    contents: dict[str, bytes],
    file_errors: dict[str, DeliveryDiscoveryError],
) -> tuple[DeliveryFrontier | None, DeliveryChangeStage | None, DeliveryDiscoveryError | None]:
    if "frontier.json" in file_errors:
        return None, None, file_errors["frontier.json"]
    content = contents.get("frontier.json")
    if content is None:
        return (
            None,
            None,
            _error(
                DeliveryDiscoveryErrorCode.FRONTIER_UNAVAILABLE,
                "Persisted Change frontier is missing",
            ),
        )
    try:
        frontier = parse_delivery_frontier(content)[0]
    except DeliveryRuntimeMigrationError as exc:
        return (
            None,
            None,
            _error(DeliveryDiscoveryErrorCode.FRONTIER_MIGRATION_REQUIRED, str(exc)),
        )
    except (TypeError, ValueError, ValidationError):
        return (
            None,
            None,
            _error(
                DeliveryDiscoveryErrorCode.FRONTIER_INVALID,
                "Persisted Delivery frontier is invalid",
            ),
        )
    return frontier, derive_change_stage(frontier), None


def _parse_admission(
    change_id: str,
    contents: dict[str, bytes],
    file_errors: dict[str, DeliveryDiscoveryError],
) -> tuple[DeliveryAdmissionReceipt | None, DeliveryDiscoveryError | None]:
    if "admission.json" in file_errors:
        return None, file_errors["admission.json"]
    content = contents.get("admission.json")
    if content is None:
        return None, _error(
            DeliveryDiscoveryErrorCode.ADMISSION_UNAVAILABLE,
            "Persisted Delivery admission evidence is missing",
        )
    try:
        admission = DeliveryAdmissionReceipt.model_validate_json(content)
    except (TypeError, ValueError, ValidationError):
        return None, _error(
            DeliveryDiscoveryErrorCode.ADMISSION_INVALID,
            "Persisted Delivery admission evidence is invalid",
        )
    if admission.change_id != change_id:
        return admission, _error(
            DeliveryDiscoveryErrorCode.ADMISSION_IDENTITY_INVALID,
            "Persisted Delivery admission identity is invalid",
        )
    return admission, None


def _cross_validate(
    contract: DeliveryContract | None,
    admission: DeliveryAdmissionReceipt | None,
    frontier: DeliveryFrontier | None,
) -> tuple[DeliveryDiscoveryError, ...]:
    errors: list[DeliveryDiscoveryError] = []
    if contract is not None and admission is not None:
        fingerprint = contract_fingerprint(contract)
        if admission.contract_digest != fingerprint or admission.source_bindings_digest != _source_bindings_fingerprint(
            contract
        ):
            errors.append(
                _error(
                    DeliveryDiscoveryErrorCode.ADMISSION_CONTRACT_MISMATCH,
                    "Persisted admission does not match the contract",
                )
            )
    if contract is not None and frontier is not None:
        try:
            _validate_delivery_frontier(contract, frontier)
        except (DeliveryAdmissionConflictError, TypeError, ValueError):
            errors.append(
                _error(
                    DeliveryDiscoveryErrorCode.FRONTIER_BINDING_INVALID,
                    "Persisted Delivery frontier does not match the contract",
                )
            )
    if admission is not None and frontier is not None:
        frontier_ids = tuple(binding.plan_scope_id for binding in frontier.bindings)
        if admission.frontier_ids != frontier_ids:
            errors.append(
                _error(
                    DeliveryDiscoveryErrorCode.ADMISSION_FRONTIER_MISMATCH,
                    "Persisted admission does not match the frontier",
                )
            )
    return tuple(errors)


def _observe_entry(change_root: Path) -> DeliveryChangeObservation:
    change_id = change_root.name
    contents: dict[str, bytes] = {}
    file_errors: dict[str, DeliveryDiscoveryError] = {}
    for name in _CHANGE_FILES:
        content, error = _read_file(change_root, name)
        if content is not None:
            contents[name] = content
        if error is not None:
            file_errors[name] = error

    contract, contract_error = _parse_contract(change_id, contents, file_errors)
    frontier, stage, frontier_error = _parse_frontier(contents, file_errors)
    admission, admission_error = _parse_admission(change_id, contents, file_errors)
    valid_contract = contract if contract is not None and contract.change_id == change_id else None
    valid_admission = admission if admission is not None and admission.change_id == change_id else None
    errors = tuple(error for error in (contract_error, frontier_error, admission_error) if error is not None)
    errors += _cross_validate(valid_contract, valid_admission, frontier)
    fingerprint = contract_fingerprint(valid_contract) if valid_contract is not None else None
    return DeliveryChangeObservation(
        change_id=change_id,
        admission=valid_admission,
        contract=valid_contract,
        contract_fingerprint=fingerprint,
        frontier=frontier,
        stage=stage,
        error=errors[0] if errors else None,
    )


def discover_persisted_changes(runtime_root: Path) -> tuple[DeliveryChangeObservation, ...]:
    """Discover every persisted Change while containing errors to one entry."""
    changes_root = runtime_root / "changes"
    if not changes_root.exists():
        return ()
    if changes_root.is_symlink() or not changes_root.is_dir():
        message = "Delivery state root is invalid"
        raise DeliveryDiscoveryRootError(message)
    try:
        change_roots = tuple(
            sorted(
                change_root
                for change_root in changes_root.iterdir()
                if change_root.is_dir() and not change_root.is_symlink()
            )
        )
    except DeliveryDiscoveryRootError:
        raise
    except OSError as exc:
        error = DeliveryDiscoveryRootError("Delivery state is invalid")
        raise error from exc
    return tuple(_observe_entry(change_root) for change_root in change_roots)


def require_startup_contracts(
    observations: tuple[DeliveryChangeObservation, ...],
) -> dict[str, DeliveryContract]:
    """Reject any persisted observation error before composing startup owners."""
    contracts: dict[str, DeliveryContract] = {}
    for observation in observations:
        if observation.error is not None:
            raise DeliveryDiscoveryStartupError(observation)
        if observation.contract is None:
            error = _error(
                DeliveryDiscoveryErrorCode.CONTRACT_UNAVAILABLE,
                "Persisted Change contract is missing",
            )
            raise DeliveryDiscoveryStartupError(observation.model_copy(update={"error": error}))
        contracts[observation.change_id] = observation.contract
    return contracts
