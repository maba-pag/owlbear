"""The one sanitiser of command and argument text Delivery shows or persists (now line, denials, status)."""

from __future__ import annotations

import re

_NAME = r"(?:token|secret|passw(?:or)?d|pwd|key|auth|credentials?)"
_AUTH_HEADER = re.compile(r"(?i)\b(?P<h>(?:proxy-)?authorization)\s*:\s*(?:[\w.~+/-]+\s+)?[^\s\"']+")
_HEADER = re.compile(r"(?P<flag>(?:(?<!\S)-H|--header)(?:\s+|=))(?:(?P<q>[\"'])(?P<qv>.*?)(?P=q)|(?P<v>\S+))")
_HEADER_NAME = re.compile(rf"(?i){_NAME}|cookie|session")
_USERINFO = re.compile(r"(?i)\b(?P<scheme>[a-z][a-z0-9+.-]*://)[^/\s@]+@")
_GITHUB = re.compile(r"\b(?:gh[pousr]_|github_pat_)\w+")
_ASSIGN = re.compile(
    rf"(?i)(?<![\w.-])(?P<k>[\w.-]*{_NAME}(?:_\w*)?)(?P<kq>[\"']?)(?P<s>\s*[=:]\s*)"
    r"(?P<v>\"[^\"]*\"|'[^']*'|[^\s\"']+)"
)
_BLOB = re.compile(r"(?P<s>[=:]\s*)(?P<q>[\"']?)(?!//)[A-Za-z0-9+/_-]{32,}={0,2}")
_BEARER = re.compile(r"(?i)\bbearer\s+(?!\*\*\*)\S+")


def _header(m: re.Match[str]) -> str:
    q = m["q"] or ""
    value = m["qv"] if q else m["v"]
    name, colon, _ = value.partition(":")
    if colon and _HEADER_NAME.search(name):
        value = f"{name}: ***"
    return f"{m['flag']}{q}{value}{q}"


def redact(text: str) -> str:
    """Mask credentials: auth headers of any scheme, URL userinfo, GitHub tokens, secret assignments and blobs."""
    text = _AUTH_HEADER.sub(r"\g<h>: ***", text)
    text = _HEADER.sub(_header, text)
    text = _USERINFO.sub(r"\g<scheme>***@", text)
    text = _GITHUB.sub("***", text)
    text = _ASSIGN.sub(r"\g<k>\g<kq>\g<s>***", text)
    text = _BLOB.sub(r"\g<s>\g<q>***", text)
    return _BEARER.sub("Bearer ***", text)
