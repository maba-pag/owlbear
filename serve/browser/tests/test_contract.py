from datetime import UTC, datetime

import pytest

from owlbear_browser import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionStatus,
    AcquisitionSuccess,
    Diagnostics,
    content_hash,
    normalize_links,
)


def test_request_accepts_private_http_url_and_rejects_prohibited_inputs() -> None:
    request = AcquisitionRequest("http://127.0.0.1:8123/page")
    assert request.url.endswith("/page")
    with pytest.raises(ValueError, match=r"HTTP\(S\)"):
        AcquisitionRequest("file:///tmp/page.html")
    with pytest.raises(ValueError, match="credentials"):
        AcquisitionRequest("https://example.test", password="secret")


def test_links_are_absolute_fragmentless_and_ordered() -> None:
    assert normalize_links(
        ["/a#one", "https://example.test/a#two", "mailto:x@example.test", "b"],
        "https://example.test/root/",
    ) == ("https://example.test/a", "https://example.test/root/b")


def test_hash_is_stable_for_normalized_markdown() -> None:
    assert content_hash("# Title\r\n\nBody  text") == content_hash("# Title\n\nBody text")


def test_success_and_failure_are_discriminated_and_diagnostics_redact_secrets() -> None:
    diagnostics = Diagnostics(
        "extract",
        {"authorization": "Bearer abc", "stage": "extract", "diagnostic_html_requested": True},
        "<main>ok</main>",
    )
    assert "authorization" not in diagnostics.details
    assert diagnostics.html == "<main>ok</main>"
    success = AcquisitionSuccess(
        AcquisitionStatus.SUCCESS,
        "https://example.test",
        "https://example.test/final",
        (),
        "Title",
        "# Content",
        (),
        content_hash("# Content"),
        datetime.now(UTC),
        diagnostics,
    )
    failure = AcquisitionFailure(AcquisitionStatus.AUTHENTICATION_REQUIRED, diagnostics)
    assert success.status is AcquisitionStatus.SUCCESS
    assert failure.status is AcquisitionStatus.AUTHENTICATION_REQUIRED
