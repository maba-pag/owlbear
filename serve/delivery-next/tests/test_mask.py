"""The sanitiser masks exactly as its quadratic predecessor did, in linear time."""

from __future__ import annotations

import random
import re
import time

import pytest

from owlbear_delivery_next.local_system.mask import redact

_NAME = r"(?:token|secret|passw(?:or)?d|pwd|key|auth|credentials?)"
_OLD_AUTH_HEADER = re.compile(r"(?i)\b(?P<h>(?:proxy-)?authorization)\s*:\s*(?:[\w.~+/-]+\s+)?[^\s\"']+")
_OLD_HEADER = re.compile(r"(?P<flag>(?:(?<!\S)-H|--header)(?:\s+|=))(?:(?P<q>[\"'])(?P<qv>.*?)(?P=q)|(?P<v>\S+))")
_OLD_HEADER_NAME = re.compile(rf"(?i){_NAME}|cookie|session")
_OLD_USERINFO = re.compile(r"(?i)\b(?P<scheme>[a-z][a-z0-9+.-]*://)[^/\s@]+@")
_OLD_GITHUB = re.compile(r"\b(?:gh[pousr]_|github_pat_)\w+")
_OLD_ASSIGN = re.compile(
    rf"(?i)(?<![\w.-])(?P<k>[\w.-]*{_NAME}(?:_\w*)?)(?P<kq>[\"']?)(?P<s>\s*[=:]\s*)"
    r"(?P<v>\"[^\"]*\"|'[^']*'|[^\s\"']+)"
)
_OLD_BLOB = re.compile(r"(?P<s>[=:]\s*)(?P<q>[\"']?)(?!//)[A-Za-z0-9+/_-]{32,}={0,2}")
_OLD_BEARER = re.compile(r"(?i)\bbearer\s+(?!\*\*\*)\S+")


def _old_header(m: re.Match[str]) -> str:
    q = m["q"] or ""
    value = m["qv"] if q else m["v"]
    name, colon, _ = value.partition(":")
    if colon and _OLD_HEADER_NAME.search(name):
        value = f"{name}: ***"
    return f"{m['flag']}{q}{value}{q}"


def _old_redact(text: str) -> str:
    """The sanitiser before it was made linear: the reference its masking must equal."""
    text = _OLD_AUTH_HEADER.sub(r"\g<h>: ***", text)
    text = _OLD_HEADER.sub(_old_header, text)
    text = _OLD_USERINFO.sub(r"\g<scheme>***@", text)
    text = _OLD_GITHUB.sub("***", text)
    text = _OLD_ASSIGN.sub(r"\g<k>\g<kq>\g<s>***", text)
    text = _OLD_BLOB.sub(r"\g<s>\g<q>***", text)
    return _OLD_BEARER.sub("Bearer ***", text)


_WORDS = [
    "token", "TOKEN", "secret", "Secret", "password", "PASSWORD", "passwd", "pwd", "key", "KEY", "auth", "credential",
    "credentials", "author", "keyboard", "monkey", "api", "MY_", "github_pat_", "proxy-", "cookie", "session", "x",
    "a", "1", "42", "\u212a", "\u0131", "\u0130", "\u017f",
]  # fmt: skip
_MARKS = ["_", ".", "-", "=", ":", " ", "\t", '"', "'", "\n", "@", "/", "://", "+", "&", "***", "=="]
_PHRASES = [
    "Bearer ", "bearer\t", "Authorization:", "Authorization: Basic ", "Proxy-Authorization: ", "-H ", " -H '",
    '--header="', "--header=", "--header ", "https://u:p@h", "git+ssh://", "a1.b-c+d://", "1http://x@y",
]  # fmt: skip
_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/_-"


def _fragment(rng: random.Random) -> str:
    kind = rng.random()
    if kind < 0.45:
        return rng.choice(_WORDS)
    if kind < 0.8:
        return rng.choice(_MARKS)
    if kind < 0.92:
        return rng.choice(_PHRASES)
    if kind < 0.96:
        return "ghp_" + "".join(rng.choices(_B64[:62], k=32))
    return "".join(rng.choices(_B64, k=rng.randint(28, 40))) + rng.choice(["", "=", "=="])


@pytest.mark.timeout(120)  # 120,000 texts take about 10 s alone; a loaded runner needs more than 30 s
def test_redact_masks_exactly_as_the_old_patterns_over_a_random_corpus():
    rng = random.Random(20261026)  # noqa: S311
    texts = ["".join(_fragment(rng) for _ in range(rng.randint(1, 12))) for _ in range(120_000)]
    differences = [(t, _old_redact(t), redact(t)) for t in texts if _old_redact(t) != redact(t)]
    assert differences[:5] == []
    assert sum(_old_redact(t) != t for t in texts) > 30_000  # the corpus exercises the masking, not only plain text


@pytest.mark.parametrize(
    "text",
    [
        "a.://u@h", "Https://u:p@h", "x-1http://u@h", "1.a://u@h", "a+b://u@h", "\u212a://u@h", "-H 'Key: v'",
        "my.key_x=1", "my.key_x.y=1", "key_a-b=1", "credentials_x: 'v'", "keyboard=1", "monkey=1", "author=1",
        'MY_API_KEY = "v w"', "token='v\" x", 'token="v', "token=a=key=b c=d", "token='a'=key=b", 'pwd"=v',
    ],
)  # fmt: skip
def test_redact_matches_the_old_patterns_on_edge_cases(text):
    assert redact(text) == _old_redact(text)


@pytest.mark.parametrize(
    "unit",
    [
        "key_", "token_", "a.", "a-", "a.key", "x=", "a=b&", '"a=', "-H '", "--header ", "Authorization: ",
        "https://", "bearer ", "token", '"', "'", "=", "a:", "a.://", "key ", 'token="', "credentials_", "1.",
    ],
)  # fmt: skip
@pytest.mark.parametrize("tail", ["", "=x", "://u@h"])
def test_redact_takes_linear_time_on_repeated_units(unit, tail):
    text = (unit * (65_536 // len(unit) + 1))[:65_536] + tail
    start = time.thread_time()  # this thread's CPU time: a loaded machine's waiting doesn't count
    redact(text)
    assert time.thread_time() - start < 0.5
