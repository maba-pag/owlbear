"""Graph API-based SharePoint content fetcher."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from msal import PublicClientApplication

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SCOPES = ["https://graph.microsoft.com/.default"]


def _parse_sharepoint_url(sp_url: str) -> tuple[str, str, str]:
    """Parse a SharePoint URL into (hostname, site_path, page_filename).

    For 'https://contoso.sharepoint.com/sites/Engineering/SitePages/Overview.aspx':
      hostname:       'contoso.sharepoint.com'
      site_path:      '/sites/Engineering'
      page_filename:  'Overview.aspx'
    """
    parsed = urlparse(sp_url)
    hostname = parsed.hostname or ""
    path = parsed.path  # e.g. /sites/Engineering/SitePages/Overview.aspx

    if "/SitePages/" in path:
        site_part, page_part = path.split("/SitePages/", 1)
        page_filename = page_part.rstrip("/")
    else:
        parts = path.rsplit("/", 1)
        site_part = parts[0] if len(parts) > 1 else path
        page_filename = parts[-1]

    return hostname, site_part, page_filename


def _extract_text_from_canvas(canvas_data: dict) -> str:  # type: ignore[type-arg]
    """Concatenate innerHtml text from all text web parts in canvasLayout.

    HTML tags are stripped; sections are joined with double newlines.
    Returns an empty string if canvasLayout is missing or has no sections.
    """
    canvas_layout = canvas_data.get("canvasLayout", {})
    sections = canvas_layout.get("horizontalSections", [])
    parts: list[str] = []

    for section in sections:
        for column in section.get("columns", []):
            for webpart in column.get("webparts", []):
                inner_html: str = webpart.get("innerHtml") or ""
                if inner_html:
                    text = re.sub(r"<[^>]+>", " ", inner_html).strip()
                    if text:
                        parts.append(text)

    return "\n\n".join(parts)


class GraphContentFetcher:
    """Fetches SharePoint page content via the Microsoft Graph API.

    Uses MSAL PublicClientApplication (device-code flow) for token acquisition
    and httpx for HTTP calls.  Implements the :class:`ContentFetcher` protocol.
    """

    def __init__(self, *, client_id: str, tenant_id: str) -> None:
        """Initialise with Azure AD application credentials.

        Args:
            client_id: Azure AD application (client) ID.
            tenant_id: Azure AD tenant ID.
        """
        self._client_id = client_id
        self._tenant_id = tenant_id

    async def fetch(self, url: str) -> str:
        """Fetch SharePoint page content via the Microsoft Graph API.

        Resolves the SharePoint URL to a site-id, locates the page by filename,
        then retrieves the canvas layout and extracts text from innerHtml.

        Args:
            url: SharePoint SitePage URL.

        Returns:
            Extracted page content as a plain-text/markdown string.

        Raises:
            RuntimeError: If MSAL token acquisition fails.
            httpx.HTTPStatusError: If any Graph API call returns a non-2xx status.
        """
        token = self._acquire_token()
        headers = {"Authorization": f"Bearer {token}"}

        hostname, site_path, page_filename = _parse_sharepoint_url(url)

        async with httpx.AsyncClient() as client:
            # Step 1 — resolve site-id
            site_url = f"{_GRAPH_BASE}/sites/{hostname}:{site_path}"
            site_resp = await client.get(site_url, headers=headers)
            site_resp.raise_for_status()
            site_id: str = site_resp.json()["id"]

            # Step 2 — list pages, filter to the target page by filename
            pages_url = (
                f"{_GRAPH_BASE}/sites/{site_id}/pages"
                f"?$filter=name eq '{page_filename}'"
            )
            pages_resp = await client.get(pages_url, headers=headers)
            pages_resp.raise_for_status()
            items: list[dict] = pages_resp.json().get("value", [])  # type: ignore[type-arg]
            page_id: str = items[0]["id"] if items else ""

            # Step 3 — fetch canvas layout for the page
            canvas_url = (
                f"{_GRAPH_BASE}/sites/{site_id}/pages/{page_id}"
                f"/microsoft.graph.sitePage?$expand=canvasLayout"
            )
            canvas_resp = await client.get(canvas_url, headers=headers)
            canvas_resp.raise_for_status()
            canvas_data: dict = canvas_resp.json()  # type: ignore[type-arg]

        return _extract_text_from_canvas(canvas_data)

    def _acquire_token(self) -> str:
        """Acquire a Graph API access token via MSAL device-code flow.

        Attempts silent (cached) token first; falls back to device-code flow.

        Returns:
            Access token string.

        Raises:
            RuntimeError: If the MSAL response contains an error.
        """
        authority = f"https://login.microsoftonline.com/{self._tenant_id}"
        app = PublicClientApplication(client_id=self._client_id, authority=authority)

        result = app.acquire_token_silent(scopes=_SCOPES, account=None)
        if not result:
            flow = app.initiate_device_flow(scopes=_SCOPES)
            print(flow.get("message", ""))  # noqa: T201 — user-facing device login prompt
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            desc = result.get("error_description") or result.get("error") or "unknown"
            msg = f"MSAL token acquisition failed: {desc}"
            raise RuntimeError(msg)

        return result["access_token"]  # type: ignore[return-value]
