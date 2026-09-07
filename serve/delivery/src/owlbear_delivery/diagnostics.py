"""Transport-neutral classification of Delivery failures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from owlbear_delivery.acceptance import CompletionReceiptConflictError
from owlbear_delivery.change_workspace import (
    ChangeTargetSyncConflictError,
    ChangeWorktreeAttentionError,
    CoordinationConflictError,
    PublicationBaselineUnavailableError,
)
from owlbear_delivery.completed_history import CompletedHistoryError, CompletedHistoryMissingError
from owlbear_delivery.delivery_admission import DeliveryAdmissionError
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionConflictError,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
)
from owlbear_delivery.delivery_state import DeliveryStatePublicationError
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.portfolio_application import (
    DeliveryRuntimeReconciliationError,
    PortfolioApplicationError,
)
from owlbear_delivery.publication_provider import PublicationProviderError
from owlbear_delivery.runtime_transaction import (
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)


class DeliveryFailureCategory(StrEnum):
    """Semantic category shared by transport renderers."""

    NOT_FOUND = "not-found"
    CONFLICT = "conflict"
    PROVIDER = "provider"


@dataclass(frozen=True, slots=True)
class DeliveryFailureClassification:
    """Semantic failure data before MCP or HTTP transport rendering.

    ``retry_safe`` means that replaying the identical operation with identical
    inputs may succeed. It does not mean that no side effect occurred or that
    changing the request is unnecessary.
    """

    code: str
    detail: str
    retry_safe: bool
    category: DeliveryFailureCategory


def _classification(
    error: Exception,
    *,
    category: DeliveryFailureCategory,
    retry_safe: bool,
    code: str | None = None,
) -> DeliveryFailureClassification:
    resolved_code = code or str(getattr(error, "code", type(error).__name__))
    return DeliveryFailureClassification(
        code=resolved_code,
        detail=str(error) or resolved_code,
        retry_safe=retry_safe,
        category=category,
    )


def classify_delivery_failure(error: Exception) -> DeliveryFailureClassification | None:
    """Classify one known Delivery failure without swallowing unknown errors."""
    classification: DeliveryFailureClassification | None
    if isinstance(error, CompletedHistoryError):
        category = (
            DeliveryFailureCategory.NOT_FOUND
            if isinstance(error, CompletedHistoryMissingError)
            else DeliveryFailureCategory.CONFLICT
        )
        classification = _classification(
            error,
            category=category,
            retry_safe=False,
            code=error.diagnostic.code.value,
        )
    elif isinstance(error, PublicationProviderError):
        classification = _classification(
            error,
            category=DeliveryFailureCategory.PROVIDER,
            retry_safe=error.retry_safe,
            code=f"ERR_DELIVERY_PROVIDER_{error.code.value.upper()}",
        )
    elif isinstance(error, DeliveryStatePublicationError):
        classification = _classification(
            error,
            category=DeliveryFailureCategory.CONFLICT,
            retry_safe=error.retry_safe,
        )
    elif isinstance(error, DeliveryChangeDispositionConflictError):
        classification = _classification(error, category=DeliveryFailureCategory.CONFLICT, retry_safe=False)
    elif isinstance(
        error,
        (
            DeliveryAcceptanceWaitingError,
            DeliveryRuntimeReconciliationError,
            DeliveryRuntimeConflictError,
            CoordinationConflictError,
            TransactionConflictError,
        ),
    ):
        classification = _classification(error, category=DeliveryFailureCategory.CONFLICT, retry_safe=True)
    elif isinstance(
        error,
        (
            CompletionReceiptConflictError,
            ChangeTargetSyncConflictError,
            ChangeWorktreeAttentionError,
            PublicationBaselineUnavailableError,
            DeliveryRuntimeReferenceError,
            DesignPackageConflictError,
            DeliveryAdmissionError,
            TransactionManifestError,
            TransactionPathError,
            PortfolioApplicationError,
        ),
    ):
        classification = _classification(error, category=DeliveryFailureCategory.CONFLICT, retry_safe=False)
    else:
        classification = None

    return classification


__all__ = [
    "DeliveryFailureCategory",
    "DeliveryFailureClassification",
    "classify_delivery_failure",
]
