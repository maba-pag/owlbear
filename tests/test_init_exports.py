"""Public import inventory for the Delivery package."""

from __future__ import annotations

import owlbear_delivery


def test_package_root_exports_current_admission_contract() -> None:
    required = {
        "DeliveryAdmissionConflictError",
        "DeliveryAdmissionError",
        "DeliveryAdmissionReceipt",
        "DeliveryAdmissionRequest",
        "DeliveryAdmissionResult",
        "DeliveryAdmissionValidationError",
        "DeliveryAuthorityRegistry",
        "RevisionCarryForward",
    }

    assert required <= set(owlbear_delivery.__all__)
    assert all(hasattr(owlbear_delivery, name) for name in required)
