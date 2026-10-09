"""Keep Knowledge capture status literals aligned with Browser acquisition outcomes."""

from __future__ import annotations

from typing import get_args

from owlbear_browser.contract import AcquisitionStatus
from owlbear_knowledge_mcp._types import CaptureFailureStatus


def test_knowledge_capture_failure_statuses_match_browser_contract() -> None:
    expected = {status.value for status in AcquisitionStatus if status is not AcquisitionStatus.SUCCESS} | {
        "tool_error"
    }
    assert set(get_args(CaptureFailureStatus)) == expected
