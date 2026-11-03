"""#936: GitHub's plan-limit 403 on the branch-rule reads means no rule can exist; any other 403 leaves them unknown."""

import json
import subprocess

import pytest

from owlbear_delivery_next.github.gh import GhProvider

PLAN = "Upgrade to GitHub Pro or make this repository public to enable this feature."
TEAM = "Upgrade to GitHub Team or make this repository public to enable this feature."
DENIED = "Resource not accessible by integration"


def answers(rulesets: object, protection: object):
    """A gh runner answering the rulesets read and the classic protection read: a JSON value, or ``(status, text)``."""

    def server(argv, _body, _timeout, _cwd, _env):
        said = protection if any(a.endswith("/protection") for a in argv) else rulesets
        if isinstance(said, tuple):
            status, text = said
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {text} (HTTP {status})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(said).encode(), b"")

    return server


def read(tmp_path, rulesets, protection):
    return GhProvider(tmp_path, writer=None, runner=answers(rulesets, protection)).read_rules("boecht/sandbox", "main")


@pytest.mark.parametrize(
    ("rulesets", "protection"),
    [((403, PLAN), (403, PLAN)), ([], (403, PLAN)), ((403, PLAN), (404, "Branch not protected"))],
    ids=["both", "rulesets-empty", "protection-absent"],
)
def test_the_plan_limit_403_means_no_rule_can_apply(tmp_path, rulesets, protection):
    rules = read(tmp_path, rulesets, protection)
    assert (rules.state, rules.types, rules.required_checks) == ("known", (), ())
    assert (rules.queue_required, rules.strict, rules.conversation_resolution) == (False, False, False)
    assert PLAN in rules.evidence


@pytest.mark.parametrize(
    ("rulesets", "protection", "said"),
    [
        ((403, DENIED), (403, PLAN), DENIED),
        ((403, PLAN), (403, DENIED), DENIED),
        ([], (403, DENIED), DENIED),
        ((403, TEAM), (403, TEAM), TEAM),  # the organisation variant is not the decided one
    ],
    ids=["rulesets-denied", "protection-denied", "only-protection-denied", "team-plan"],
)
def test_any_other_403_leaves_the_rules_unknown(tmp_path, rulesets, protection, said):
    rules = read(tmp_path, rulesets, protection)
    assert (rules.state, rules.evidence) == ("unknown", f"HTTP 403: {said} (HTTP 403)")
