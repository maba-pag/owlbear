from datetime import UTC, datetime, timedelta, timezone

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
    assert AcquisitionRequest("file:///tmp/page.html").url == "file:///tmp/page.html"
    with pytest.raises(ValueError, match="URL credentials"):
        AcquisitionRequest("https://user:secret@example.test/page")
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
        {
            "authorization": "Bearer abc",
            "headers": [{"name": "X-Api-Key", "value": "secret"}],
            "stage": "extract",
            "diagnostic_html_requested": True,
        },
        "<main>ok</main>",
        include_diagnostic_html=True,
    )
    assert "authorization" not in diagnostics.details
    assert "headers" not in diagnostics.details
    assert diagnostics.html == "<main>ok</main>"
    url_diagnostics = Diagnostics(
        "navigation",
        {"url": "https://example.test/page?api_key=secret&public=value&access_token=token"},
    )
    assert url_diagnostics.details["url"] == (
        "https://example.test/page?api_key=%5BREDACTED%5D&public=value&access_token=%5BREDACTED%5D"
    )
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
    with pytest.raises(ValueError, match="UTC timestamp"):
        AcquisitionSuccess(
            AcquisitionStatus.SUCCESS,
            "https://example.test",
            "https://example.test/final",
            (),
            "Title",
            "# Content",
            (),
            content_hash("# Content"),
            datetime.now(timezone(timedelta(hours=1))),
            diagnostics,
        )


def test_opt_in_diagnostic_html_is_sanitized_and_bounded() -> None:
    diagnostics = Diagnostics(
        "extract",
        {"diagnostic_html_requested": True},
        '<main onclick="steal()"><script>window.sessionToken="secret"</script>'
        '<a href="javascript:steal()">ok</a>' + "x" * 100_001,
        include_diagnostic_html=True,
    )

    assert diagnostics.html is not None
    assert len(diagnostics.html) <= 100_000
    assert "<script" not in diagnostics.html
    assert "onclick" not in diagnostics.html
    assert "javascript:" not in diagnostics.html
    assert "sessionToken" not in diagnostics.html


def test_opt_in_diagnostic_html_redacts_session_token_attributes_and_text() -> None:
    diagnostics = Diagnostics(
        "extract",
        {"diagnostic_html_requested": True},
        '<main data-session-token="secret-value">session token: secret-value</main>',
        include_diagnostic_html=True,
    )

    assert diagnostics.html == "<main>[REDACTED]</main>"


def test_diagnostic_html_requires_request_level_opt_in() -> None:
    diagnostics = Diagnostics(
        "extract",
        {"diagnostic_html_requested": True},
        "<main>visible</main>",
    )

    assert diagnostics.html is None
