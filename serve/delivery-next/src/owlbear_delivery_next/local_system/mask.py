"""The one sanitiser of command and argument text Delivery shows or persists (now line, denials, status)."""

from __future__ import annotations

import re

_NAME = r"(?:token|secret|passw(?:or)?d|pwd|key|auth|credentials?)"
_AUTH_HEADER = re.compile(r"(?i)\b(?P<h>(?:proxy-)?authorization)\s*:\s*(?:[\w.~+/-]+\s+)?[^\s\"']+")
_HEADER = re.compile(r"(?P<flag>(?:(?<!\S)-H|--header)(?:\s+|=))(?:(?P<q>[\"'])(?P<qv>.*?)(?P=q)|(?P<v>\S+))")
_HEADER_NAME = re.compile(rf"(?i){_NAME}|cookie|session")
_USERINFO = re.compile(r"(?i)\b(?P<scheme>[a-z][a-z0-9+.-]{0,31}://)[^/\s@]+@")  # a bounded scheme: linear time
_GITHUB = re.compile(r"\b(?:gh[pousr]_|github_pat_)\w+")
_KEY = re.compile(r"(?<![\w.-])(?P<k>[\w.-]++)(?P<kq>[\"']?)(?P<s>\s*[=:]\s*)")  # each word scanned once: linear
_VALUE = re.compile(r"\"[^\"]*\"|'[^']*'|[^\s\"']+")
_NAMED = re.compile(rf"(?i)(?=({_NAME}))")  # every start of a credential's name, overlapping ones too
_COOKIE = re.compile(r"(?i)\b(?P<h>(?:set-)?cookie)(?P<s>[\"']?\s*:\s*)[^\r\n]+")
_BLOB = re.compile(r"(?P<s>[=:]\s*)(?P<q>[\"']?)(?!//)[A-Za-z0-9+/_-]{32,}={0,2}")
_BEARER = re.compile(r"(?i)\bbearer\s+(?!\*\*\*)\S+")
SECRET_NAME = _NAME  # what names a credential: a key, a field or a flag
_SECRET_KEY = re.compile(rf"(?i){_NAME}|cookie|session")  # a field holding a credential, as a header names one


def secret_key(name: str) -> bool:
    """Whether a field named *name* holds a credential, as an assignment's key does."""
    return bool(_SECRET_KEY.search(name))


def _secret(key: str) -> bool:
    """Whether *key* names a credential: a name, then nothing or an underscore and word characters."""
    last = max(key.rfind("."), key.rfind("-"))  # what follows the name holds word characters only
    for m in _NAMED.finditer(key):
        end = m.start() + len(m.group(1))
        if end == len(key) or (key[end] == "_" and end > last):
            return True
    return False


def _assignments(text: str) -> str:
    """*text* with every credential assignment's value masked, in one pass; a key inside another's value counts."""
    out, at = [], 0
    for m in _KEY.finditer(text):
        if m.start() < at or not _secret(m["k"]) or not (value := _VALUE.match(text, m.end())):
            continue
        out.append(f"{text[at : m.end()]}***")
        at = value.end()
    return "".join(out) + text[at:]


def _header(m: re.Match[str]) -> str:
    q = m["q"] or ""
    value = m["qv"] if q else m["v"]
    name, colon, _ = value.partition(":")
    if colon and _HEADER_NAME.search(name):
        value = f"{name}: ***"
    return f"{m['flag']}{q}{value}{q}"


def redact(text: str, *, blobs: bool = True) -> str:
    """Mask credentials: auth and cookie headers, URL userinfo, GitHub tokens, secret assignments and blobs.

    Without *blobs*, a long value after ``=`` or ``:`` is kept unless another rule names it a credential.
    """
    text = _AUTH_HEADER.sub(r"\g<h>: ***", text)
    text = _HEADER.sub(_header, text)
    text = _USERINFO.sub(r"\g<scheme>***@", text)
    text = _GITHUB.sub("***", text)
    text = _COOKIE.sub(r"\g<h>\g<s>***", text)
    text = _assignments(text)
    text = _BLOB.sub(r"\g<s>\g<q>***", text) if blobs else text
    return _BEARER.sub("Bearer ***", text)
