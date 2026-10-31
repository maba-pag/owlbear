"""OwlBear's protocol offer against the AHP spec's own version-negotiation cases.

``fixtures/ahp/version-negotiation.json`` and its ``LICENSE`` are byte copies from microsoft/agent-host-protocol,
tag ``spec/v1.0.0`` (commit 5f16d81bb7045b66d7bc768d244feab75002d943), path ``types/test-cases/``; refresh them with
each AHP release analysis (#849). ``negotiate`` is the host's rule as the spec's 1.0.0 changelog states it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from owlbear_delivery_next.runtimes import ahp

CASES = json.loads((Path(__file__).parent / "fixtures/ahp/version-negotiation.json").read_text())
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def negotiate(offered: list[object]) -> str | None:
    """The highest offered version within ^1.0.0 or ^0.9.0; ``ValueError`` for anything not strict MAJOR.MINOR.PATCH."""
    parsed = []
    for version in offered:
        match = SEMVER.fullmatch(version) if isinstance(version, str) else None
        if match is None:
            message = f"not strict semver: {version!r}"
            raise ValueError(message)
        parsed.append(tuple(int(part) for part in match.groups()))
    accepted = [v for v in parsed if v[0] == 1 or v[:2] == (0, 9)]
    return ".".join(map(str, max(accepted))) if accepted else None


@pytest.mark.parametrize("case", CASES, ids=[json.dumps(case["offered"]) for case in CASES])
def test_the_negotiator_matches_every_row_of_the_spec_fixture(case):
    if case.get("invalid"):
        with pytest.raises(ValueError, match="not strict semver"):
            negotiate(case["offered"])
    else:
        assert negotiate(case["offered"]) == case["expected"]


def test_owlbears_offer_is_accepted_and_the_old_one_was_not():
    assert negotiate([ahp.PROTOCOL]) == "1.0.0"
    assert negotiate(["0.10.0"]) is None
