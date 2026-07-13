"""OwlBear browser package — authenticated web content extraction via Playwright."""

from owlbear_browser._errors import (
    AuthenticationRequired,
    SSOExtensionNotFoundError,
)
from owlbear_browser.contract import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
    AcquisitionSuccess,
    Diagnostics,
    content_hash,
    normalize_links,
    normalize_markdown,
)
from owlbear_browser.extractor import extract_content
from owlbear_browser.fetcher import BrowserContentFetcher
from owlbear_browser.playwright_launcher import (
    AuthenticationCapabilities,
    PlaywrightLauncher,
    find_sso_extension,
)

__all__ = [
    "AcquisitionFailure",
    "AcquisitionRequest",
    "AcquisitionResult",
    "AcquisitionStatus",
    "AcquisitionSuccess",
    "AuthenticationCapabilities",
    "AuthenticationRequired",
    "BrowserContentFetcher",
    "Diagnostics",
    "PlaywrightLauncher",
    "SSOExtensionNotFoundError",
    "content_hash",
    "extract_content",
    "find_sso_extension",
    "normalize_links",
    "normalize_markdown",
]
