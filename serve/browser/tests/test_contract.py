from datetime import UTC, datetime, timedelta, timezone

import pytest

from owlbear_browser import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionStatus,
    AcquisitionSuccess,
    Diagnostics,
    content_hash,
    find_sso_extension,
    normalize_links,
    redact_url,
)
from owlbear_browser._errors import SSOExtensionNotFoundError
from owlbear_browser.contract import redact_diagnostics


def test_sso_extension_requires_an_explicit_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSO_EXTENSION_PATH", raising=False)

    with pytest.raises(SSOExtensionNotFoundError, match="SSO_EXTENSION_PATH must be set"):
        find_sso_extension()


def test_sso_extension_uses_the_explicit_path(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    extension_path = tmp_path / "extension"
    extension_path.mkdir()
    monkeypatch.setenv("SSO_EXTENSION_PATH", str(extension_path))

    assert find_sso_extension() == extension_path


def test_request_accepts_private_http_url_and_rejects_prohibited_inputs() -> None:
    request = AcquisitionRequest("http://127.0.0.1:8123/page")
    assert request.url.endswith("/page")
    assert AcquisitionRequest("file:///tmp/page.html").url == "file:///tmp/page.html"
    with pytest.raises(ValueError, match="URL credentials"):
        AcquisitionRequest("https://user:secret@example.test/page")
    with pytest.raises(ValueError, match="credentials"):
        AcquisitionRequest("https://example.test", password="secret")  # noqa: S106
    with pytest.raises(TypeError, match="include_diagnostic_html"):
        AcquisitionRequest("https://example.test", include_diagnostic_html=True)  # type: ignore[call-arg]


def test_links_are_absolute_fragmentless_and_ordered() -> None:
    assert normalize_links(
        ["/a#one", "https://example.test/a#two", "mailto:x@example.test", "b"],
        "https://example.test/root/",
    ) == ("https://example.test/a", "https://example.test/root/b")


def test_hash_is_stable_for_normalized_markdown() -> None:
    assert content_hash("# Title\r\n\nBody  text") == content_hash("# Title\n\nBody text")


def test_success_and_failure_are_discriminated_and_diagnostics_redact_secrets() -> None:
    diagnostics_url = "https://example.test/page?api_key=secret&public=value&access_token=token"
    diagnostics = Diagnostics(
        "extract",
        {
            "authorization": "Bearer abc",
            "headers": [{"name": "X-Api-Key", "value": "secret"}],
            "stage": "extract",
            "url": diagnostics_url,
        },
    )
    assert "authorization" not in diagnostics.details
    assert "headers" not in diagnostics.details
    assert diagnostics.details["url"] == (
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
    assert failure.diagnostics.details["url"] == diagnostics.details["url"]
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


def test_success_result_redacts_every_url_field_at_construction() -> None:
    def make_success(url: str) -> AcquisitionSuccess:
        return AcquisitionSuccess(
            AcquisitionStatus.SUCCESS,
            url,
            url,
            (url,),
            "Title",
            "# Content",
            (url,),
            "content-hash",
            datetime.now(UTC),
            Diagnostics("complete"),
        )

    sensitive_url = "https://u:p@h/page?code=x&state=s&view=full#frag"
    redacted_url = "https://h/page?code=%5BREDACTED%5D&state=%5BCORRELATION%5D&view=full"
    success = make_success(sensitive_url)

    assert success.requested_url == redacted_url
    assert success.canonical_url == redacted_url
    assert success.redirect_chain == (redacted_url,)
    assert success.discovered_links == (redacted_url,)

    benign_url = "https://example.test/page?view=full&lang=en"
    benign_success = make_success(benign_url)
    assert benign_success.requested_url == benign_url
    assert benign_success.canonical_url == benign_url
    assert benign_success.redirect_chain == (benign_url,)
    assert benign_success.discovered_links == (benign_url,)


def test_acquisition_urls_redact_credentials_and_preserve_document_identity() -> None:
    assert (
        redact_url("https://user:secret@example.test/page?code=oauth-code&state=csrf&public=value#fragment")
        == "https://example.test/page?code=%5BREDACTED%5D&state=%5BCORRELATION%5D&public=value"
    )

    assert redact_url("https://example.test/page?view=full&lang=en#section") == (
        "https://example.test/page?view=full&lang=en"
    )
    assert redact_diagnostics("authorization: Bearer secret") == "[REDACTED]"
    assert redact_url("https://oidc.example.test/cb?id_token=jwt&refresh_token=long-lived") == (
        "https://oidc.example.test/cb?id_token=%5BREDACTED%5D&refresh_token=%5BREDACTED%5D"
    )
    assert redact_url(
        "https://example.test/page?X-Amz-Signature=a&X-Amz-Security-Token=b&X-Amz-Credential=c&oauth_token=d"
        "&client_assertion=e"
    ) == (
        "https://example.test/page?X-Amz-Signature=%5BREDACTED%5D&X-Amz-Security-Token=%5BREDACTED%5D"
        "&X-Amz-Credential=%5BREDACTED%5D&oauth_token=%5BREDACTED%5D"
        "&client_assertion=%5BREDACTED%5D"
    )
    assert redact_url("https://shop.example.test/p?country_code=US&product_code=ABC123") == (
        "https://shop.example.test/p?country_code=US&product_code=ABC123"
    )
    assert redact_url("https://sso.example.test/cb?SAMLResponse=assertion&sid=session&state=csrf") == (
        "https://sso.example.test/cb?SAMLResponse=%5BREDACTED%5D&sid=%5BREDACTED%5D&state=%5BCORRELATION%5D"
    )
    assert redact_diagnostics("https://example.test/reset/token/abc123#fragment") == "[REDACTED]"


def test_diagnostics_reject_removed_html_option() -> None:
    with pytest.raises(TypeError):
        Diagnostics("x", {}, "<p>")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Diagnostics("x", {}, include_diagnostic_html=True)  # type: ignore[call-arg]
