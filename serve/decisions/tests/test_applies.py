from __future__ import annotations

import pytest

from owlbear_decisions import Applicability, Scope, State, applies, matches
from owlbear_decisions.applies import overlap

STEM = "20261021-090000-notes"


@pytest.mark.parametrize(
    ("glob", "scope", "expected"),
    [
        ("web/**", "web", True),
        ("web/**/*.css", "web", True),  # a scope directory covers what lies under it
        ("web/*.css", "web/app.css", True),
        ("web/*.css", "web/app.js", False),
        ("web", "web/app.js", True),  # a decision's directory covers its files
        ("serve/**/*.py", "serve/decisions/src/a.py", True),
        ("serve/*/src", "serve/delivery-next/src/x.py", True),
        ("api/**", "web", False),
        ("web/app.css", "web/*.css", True),  # a wildcard in the scope may name it
        ("docs/a.md", "./docs/a.md", True),
        ("a", ".", True),  # the repository root covers everything
        ("**/*.md", "docs/a.md", True),
        ("**/*.md", "docs", True),
        ("web/**/*.css", "web/styles/a.css", True),
        ("web/**", "web/app.js", True),
        ("web/**/*.css", "web/app.js", False),  # `**` keeps the rest of the glob
        ("web/**/*.css", "web/styles/app.js", False),
        ("web/**/*.css", "api/a.css", False),
        ("**/*.md", "src/a.py", False),
        ("src/*.py", "src/pkg/x.py", False),
        ("web/**/*.css", "web/app.js/", True),  # a trailing slash names a directory
    ],
)
def test_paths_overlap_generously(glob, scope, expected):
    assert overlap(glob, scope) is expected


def test_selectors_decide_by_role_step_and_paths(make):
    rule = make(applies_to=Applicability(paths=("serve/**/*.py",), roles=("builder",), steps=("build",)))

    assert applies(rule, paths=["serve/decisions"], role="builder", step="build") is True
    assert applies(rule, paths=["serve/decisions"], role=None, step=None) is True  # any role or step
    assert applies(rule, paths=["serve/decisions"], role="reviewer", step="build") is False
    assert applies(rule, paths=["serve/decisions"], role="builder", step="review") is False
    assert applies(rule, paths=["web"], role="builder", step="build") is False
    assert applies(rule, paths=[], role="builder", step="build") is None  # no scope yet: unresolved, never excluded


def test_empty_selectors_cover_the_whole_scope(make):
    rule = make(applies_to=Applicability())

    assert applies(rule, paths=[], role="planner", step="plan") is True


@pytest.mark.parametrize("state", [State.DRAFT, State.REPLACED, State.WITHDRAWN, State.SPENT])
def test_drafts_and_retired_decisions_never_apply_but_still_match(make, state):
    rule = make(applies_to=Applicability(), state=state)

    assert applies(rule, paths=["a"], role=None, step=None) is False
    assert matches(rule, paths=["a"], role=None, step=None) is True


def test_a_change_decision_applies_to_its_own_change_only(make):
    rule = make(applies_to=Applicability(), scope=Scope.CHANGE, change=STEM)

    assert applies(rule, paths=["a"], role=None, step=None, change=STEM) is True
    assert applies(rule, paths=["a"], role=None, step=None, change="20261021-100000-other") is False
    assert applies(rule, paths=["a"], role=None, step=None) is False
