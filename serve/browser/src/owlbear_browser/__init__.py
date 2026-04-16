"""OwlBear browser package — authenticated web content extraction via Playwright."""

from owlbear_browser._errors import (
    AuthenticationRequired,
    SSOExtensionNotFoundError,
)
from owlbear_browser.extractor import extract_content
from owlbear_browser.fetcher import BrowserContentFetcher
from owlbear_browser.playwright_launcher import PlaywrightLauncher, find_sso_extension

__all__ = [
    "AuthenticationRequired",
    "BrowserContentFetcher",
    "PlaywrightLauncher",
    "SSOExtensionNotFoundError",
    "extract_content",
    "find_sso_extension",
]
