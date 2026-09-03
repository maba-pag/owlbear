"""Tests for transport-neutral Delivery failure classification."""

from __future__ import annotations

import pytest

from owlbear_delivery.acceptance import CompletionReceiptConflictError
from owlbear_delivery.change_workspace import (
    ChangeTargetSyncConflictError,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    CoordinationConflictError,
    PublicationBaselineUnavailableError,
)
from owlbear_delivery.completed_history import (
    CompletedHistoryDiagnostic,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryMissingError,
    CompletedHistoryStaleError,
)
from owlbear_delivery.delivery_admission import DeliveryAdmissionError
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionConflictError,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
)
from owlbear_delivery.delivery_state import (
    DeliveryStateConflictError,
    DeliveryStatePublicationError,
    DeliveryStateResponseUnknownError,
)
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.diagnostics import (
    DeliveryFailureCategory,
    classify_delivery_failure,
)
from owlbear_delivery.portfolio_application import (
    DeliveryRuntimeReconciliationError,
    DeliveryStateRepairProofError,
    PortfolioApplicationError,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
)
from owlbear_delivery.runtime_transaction import (
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)
from owlbear_delivery.target_admission import TargetAdmissionError


def _history_error(error_type: type[Exception], code: CompletedHistoryDiagnosticCode) -> Exception:
    diagnostic = CompletedHistoryDiagnostic(code=code, detail="history diagnostic", change_id="change-a")
    return error_type(diagnostic)  # type: ignore[call-arg]


def test_stale_completed_history_is_not_retry_safe_for_identical_input() -> None:
    classification = classify_delivery_failure(
        _history_error(CompletedHistoryStaleError, CompletedHistoryDiagnosticCode.STALE)
    )

    assert classification is not None
    assert classification.code == "completed-history-stale"
    assert classification.retry_safe is False
    assert classification.category is DeliveryFailureCategory.CONFLICT


def test_design_package_conflict_is_not_retry_safe() -> None:
    classification = classify_delivery_failure(DesignPackageConflictError("package identity is stale"))

    assert classification is not None
    assert classification.code == "ERR_DESIGN_PACKAGE_CONFLICT"
    assert classification.retry_safe is False


def test_provider_codes_use_delivery_namespace() -> None:
    error = PublicationProviderError(
        PublicationProviderFailureCode.RATE_LIMITED,
        "observe_checks",
        "provider rate limit reached",
        retry_safe=True,
    )

    classification = classify_delivery_failure(error)

    assert classification is not None
    assert classification.code == "ERR_DELIVERY_PROVIDER_RATE_LIMITED"
    assert classification.detail == "provider rate limit reached"
    assert classification.retry_safe is True
    assert classification.category is DeliveryFailureCategory.PROVIDER


def test_completed_history_missing_is_not_found() -> None:
    classification = classify_delivery_failure(
        _history_error(CompletedHistoryMissingError, CompletedHistoryDiagnosticCode.MISSING)
    )

    assert classification is not None
    assert classification.category is DeliveryFailureCategory.NOT_FOUND


def test_unknown_exception_is_left_for_transport_fallbacks() -> None:
    assert classify_delivery_failure(ValueError("unknown")) is None


def test_busy_change_attention_resolution_is_retryable_conflict() -> None:
    classification = classify_delivery_failure(DeliveryChangeDispositionBusyError("attention is busy"))

    assert classification is not None
    assert classification.code == "ERR_DELIVERY_ATTENTION_RESOLVE_BUSY"
    assert classification.retry_safe is True
    assert classification.category is DeliveryFailureCategory.CONFLICT


def test_repair_proof_failure_is_retryable() -> None:
    classification = classify_delivery_failure(
        DeliveryStateRepairProofError("repair-operation", "Change did not recompose")
    )

    assert classification is not None
    assert classification.code == "ERR_DELIVERY_STATE_REPAIR_PROOF"
    assert "Change did not recompose" in classification.detail
    assert classification.retry_safe is True
    assert classification.category is DeliveryFailureCategory.CONFLICT


def _known_delivery_failures() -> tuple[Exception, ...]:
    return (
        _history_error(CompletedHistoryMissingError, CompletedHistoryDiagnosticCode.MISSING),
        _history_error(CompletedHistoryStaleError, CompletedHistoryDiagnosticCode.STALE),
        PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE,
            "observe_checks",
            "provider unavailable",
            retry_safe=True,
        ),
        DeliveryStatePublicationError("state publication failed", retry_safe=True),
        DeliveryStateConflictError("state branch changed", retry_safe=True),
        DeliveryStateResponseUnknownError("state response is unknown", retry_safe=False),
        CompletionReceiptConflictError("completion receipt is inconsistent"),
        ChangeTargetSyncConflictError("change-a", "operation-a", "a" * 40, ("product.txt",)),
        ChangeWorktreeAttentionError("change-a", (ChangeWorktreeAttentionCode.WORKTREE_DIRTY,)),
        PublicationBaselineUnavailableError("change-a", "baseline unavailable"),
        CoordinationConflictError("coordination changed"),
        DeliveryRuntimeConflictError("runtime changed"),
        DeliveryChangeDispositionConflictError("attention changed"),
        DeliveryAcceptanceWaitingError("pull request remains open"),
        DeliveryRuntimeReconciliationError("change-a", "runtime changed during read"),
        DeliveryRuntimeReferenceError("outcome is absent"),
        DesignPackageConflictError("package identity is stale"),
        DeliveryAdmissionError("admission failed"),
        TargetAdmissionError("target admission failed"),
        TransactionConflictError("transaction changed"),
        TransactionManifestError("manifest is invalid"),
        TransactionPathError("path is unsafe"),
        PortfolioApplicationError("application boundary failed"),
    )


@pytest.mark.parametrize("error", _known_delivery_failures())
def test_known_delivery_failure_families_are_classified(error: Exception) -> None:
    classification = classify_delivery_failure(error)

    assert classification is not None
    assert classification.code
    assert classification.detail
