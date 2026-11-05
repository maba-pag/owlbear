"""#723: a branch's rules against what Delivery needs and OwlBear advises, and one ruleset written whole."""

import copy
import json
import subprocess

import pytest

from owlbear_delivery_next.github import branch_rules as br
from owlbear_delivery_next.github.gh_client import GhClient
from owlbear_delivery_next.github.provider import ProviderError

REPO = "boecht/sandbox"
ALL = {"merge": True, "squash": True, "rebase": True}
PLAN = "Upgrade to GitHub Pro or make this repository public to enable this feature."
# The live ha-addon-virtual-meter ruleset (GET rulesets/11391913, 2026-11-05): it meets every need and every advice.
HA = {
    "id": 11391913, "name": "default", "target": "branch", "source_type": "Repository",
    "source": "boecht/ha-addon-virtual-meter", "enforcement": "active",
    "conditions": {"ref_name": {"exclude": [], "include": ["~DEFAULT_BRANCH"]}},
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": {
            "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": True, "required_reviewers": [],
            "require_code_owner_review": False, "require_last_push_approval": False,
            "required_review_thread_resolution": True, "require_extra_approval_for_unattributed_changes": True,
            "allowed_merge_methods": ["merge", "squash", "rebase"],
        }},
        {"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True, "do_not_enforce_on_create": True,
            "required_status_checks": [
                {"context": "Dependency Review", "integration_id": 15368},
                {"context": "Lint & Static Analysis", "integration_id": 15368},
                {"context": "Lint Summary", "integration_id": 15368},
                {"context": "Scorecard analysis", "integration_id": 15368},
                {"context": "Pytest (unit) & Coverage", "integration_id": 15368},
            ],
        }},
        {"type": "code_scanning", "parameters": {"code_scanning_tools": [
            {"tool": "CodeQL", "security_alerts_threshold": "high_or_higher", "alerts_threshold": "errors"},
        ]}},
        {"type": "code_quality", "parameters": {"severity": "errors"}},
    ],
    "node_id": "RRS_lACqUmVwb3NpdG9yec5C1iEJzgCt06k", "created_at": "2025-12-25T22:51:58.493+01:00",
    "updated_at": "2025-12-26T00:57:48.148+01:00", "current_user_can_bypass": "never",
    "_links": {"self": {"href": "https://api.github.com/repos/boecht/ha-addon-virtual-meter/rulesets/11391913"}},
}  # fmt: skip


def pull(**parameters):
    defaults = {"allowed_merge_methods": ["merge", "squash", "rebase"], "required_approving_review_count": 0}
    defaults |= {"require_code_owner_review": False, "require_last_push_approval": False}
    return {"type": "pull_request", "parameters": defaults | {"required_review_thread_resolution": True} | parameters}


def ruleset(*rules, ruleset_id=7):
    return {
        "id": ruleset_id, "name": "main", "target": "branch", "enforcement": "active", "source_type": "Repository",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": ["refs/heads/release"]}},
        "bypass_actors": [{"actor_id": 5, "actor_type": "Team", "bypass_mode": "pull_request"}],
        "rules": list(rules),
    }  # fmt: skip


def effective(*whole, kind="Repository"):
    """The branch's effective rules, as `rules/branches/{b}` answers for the given whole rulesets."""
    found = [
        r | {"ruleset_source_type": kind, "ruleset_source": REPO, "ruleset_id": w["id"]}
        for w in whole
        for r in w["rules"]
    ]
    return br.Rules(tuple(found))


def body(whole):
    return {
        k: copy.deepcopy(whole[k])
        for k in ("name", "target", "enforcement", "conditions", "bypass_actors", "rules")
        if k in whole
    }


def advice(rules):
    return {i.key: i for i in br.compare(rules, "merge").advice}


def test_two_rulesets_allow_only_the_methods_both_pull_request_rules_allow():
    rules = effective(
        ruleset(pull(allowed_merge_methods=["merge", "squash"])),
        ruleset(pull(allowed_merge_methods=["merge", "rebase"]), ruleset_id=8),
    )
    assert br.allowed_methods(ALL, rules) == {"merge"}
    assert br.allowed_methods({"merge": False, "squash": True, "rebase": True}, rules) == set()
    assert br.allowed_methods({"merge": False, "squash": True, "rebase": True}, br.Rules()) == {"squash", "rebase"}


@pytest.mark.parametrize(
    ("rules", "where"),
    [
        (effective(ruleset(pull(), {"type": "required_linear_history"})), "ruleset 7"),
        (br.Rules(classic={"required_linear_history": {"enabled": True}}), "classic protection"),
    ],
    ids=["rule", "classic"],
)
def test_linear_history_drops_merge_commits_and_conflicts(rules, where):
    assert br.allowed_methods(ALL, rules) == {"squash", "rebase"}
    conflicts = [(i.key, i.sentence) for i in br.compare(rules, "merge").unmet if i.key in br.NEEDS]
    assert conflicts == [
        ("linear_history", f"rule required_linear_history in {where} conflicts: Delivery needs merge commits")
    ]


def test_a_rule_excluding_merge_conflicts_and_ticking_changes_its_methods_only():
    whole = ruleset(
        {"type": "deletion"},
        pull(allowed_merge_methods=["squash"]),
        {"type": "merge_queue", "parameters": {"merge_method": "SQUASH"}},
        {"type": "required_linear_history"},
    )
    unmet = br.compare(effective(whole), "merge").unmet
    methods = "rule pull_request in ruleset 7 conflicts: Delivery needs merge among its allowed merge methods"
    assert [(i.key, i.source, i.sentence) for i in unmet if i.key in br.NEEDS] == [
        ("merge_method", 7, f"{methods}, now squash"),
        ("linear_history", 7, "rule required_linear_history in ruleset 7 conflicts: Delivery needs merge commits"),
    ]
    expected = body(whole)
    expected["rules"][1]["parameters"]["allowed_merge_methods"] = ["squash", "merge"]
    assert br.changed(whole, {"merge_method"}, set(), "merge") == expected
    del expected["rules"][3]
    assert br.changed(whole, set(br.NEEDS), set(), "merge") == expected
    assert [i for i in br.compare(effective(expected | {"id": 7}), "merge").needs if not i.holds] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("required_approving_review_count", 1), ("require_code_owner_review", True), ("require_last_push_approval", True)],
)
def test_no_approvals_holds_only_with_all_three_fields_off(field, value):
    assert not advice(effective(ruleset(pull(**{field: value}))))["no_approvals"].holds


def test_ticking_no_approvals_sets_all_three_fields_and_nothing_else():
    whole = ruleset(
        pull(
            required_approving_review_count=1,
            require_code_owner_review=True,
            require_last_push_approval=True,
            required_review_thread_resolution=False,
        )
    )
    expected = body(whole)
    expected["rules"][0]["parameters"] |= {
        "required_approving_review_count": 0,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
    }
    assert br.changed(whole, set(), {"no_approvals"}, "merge") == expected
    assert advice(effective(expected | {"id": 7}))["no_approvals"].holds
    assert br.changed(whole, set(), set(), "merge") == body(whole)


def checks(*contexts, strict):
    found = [{"context": c} for c in contexts]
    return {
        "type": "required_status_checks",
        "parameters": {"strict_required_status_checks_policy": strict, "required_status_checks": found},
    }


@pytest.mark.parametrize("without", [ruleset(pull()), ruleset(pull(), checks(strict=True))], ids=["no-rule", "strict"])
def test_up_to_date_is_offered_only_with_a_required_check_and_never_invents_one(without):
    item = advice(effective(without))["up_to_date"]
    assert (item.applicable, item.holds) == (False, False)
    assert item.sentence == "Require branches to be up to date before merging: takes effect only with a required check"
    assert br.changed(without, set(), {"up_to_date"}, "merge") == body(without)
    loose = ruleset(pull(), checks("CI", strict=False))
    item = advice(effective(loose))["up_to_date"]
    assert (item.applicable, item.holds, item.source) == (True, False, 7)
    expected = body(loose)
    expected["rules"][1]["parameters"]["strict_required_status_checks_policy"] = True
    assert br.changed(loose, set(), {"up_to_date"}, "merge") == expected


def test_rules_that_meet_every_need_and_advice_leave_nothing_to_change():
    comparison = br.compare(effective(HA), "merge")
    assert (comparison.unmet, comparison.summary) == ((), "nothing to change")
    assert br.changed(HA, set(), set(), "merge") == body(HA)


@pytest.mark.parametrize("require_ci", [True, False])
def test_owlbears_new_ruleset_meets_every_need_and_advice(require_ci):
    new = br.new_ruleset("main", require_ci=require_ci)
    rules = effective(new | {"id": 1})
    assert br.compare(rules, "merge").unmet == ()
    assert br.allowed_methods(ALL, rules) == {"merge"}
    checks = [r["parameters"] for r in new["rules"] if r["type"] == "required_status_checks"]
    assert checks == (
        [{"strict_required_status_checks_policy": True, "required_status_checks": [{"context": "CI"}]}]
        if require_ci
        else []
    )
    assert (new["bypass_actors"], new["conditions"]["ref_name"]["include"]) == ([], ["~DEFAULT_BRANCH"])


def test_differences_name_a_changed_approval_count_and_bypass_actor_and_ignore_githubs_own_fields():
    sent = br.changed(ruleset(pull(), {"type": "deletion"}), set(), set(), "merge")
    answer = copy.deepcopy(sent) | {"id": 7, "node_id": "RRS_x", "source": REPO, "updated_at": "now", "_links": {}}
    answer["rules"].reverse()
    answer["rules"][1]["parameters"]["dismiss_stale_reviews_on_push"] = False  # a default GitHub adds
    assert br.differences(sent, answer) == []
    assert br.differences(HA, HA | {"updated_at": "later", "current_user_can_bypass": "always"}) == []
    answer["rules"][1]["parameters"]["required_approving_review_count"] = 1
    theirs = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
    answer["bypass_actors"] = [theirs]
    ours = json.dumps(sent["bypass_actors"][0], sort_keys=True)
    assert br.differences(sent, answer) == [
        f"bypass_actors[Team 5]: sent {ours}, GitHub has nothing",
        f"bypass_actors[RepositoryRole 5]: sent nothing, GitHub has {json.dumps(theirs, sort_keys=True)}",
        "rules[pull_request].parameters.required_approving_review_count: sent 0, GitHub has 1",
    ]


def answers(rulesets, protection, seen=None):
    """A gh runner: a JSON value, or `(status, text)` for an error, for the rules read and the protection read."""

    def server(argv, data, _timeout, _cwd, _env):
        if seen is not None:
            seen.append(
                (
                    argv[argv.index("--method") + 1],
                    next(a for a in argv if a.startswith("repos/")),
                    data and json.loads(data),
                )
            )
        said = protection if any(a.endswith("/protection") for a in argv) else rulesets
        if isinstance(said, tuple):
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {said[1]} (HTTP {said[0]})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(said).encode(), b"")

    return server


@pytest.mark.parametrize(
    ("rulesets", "protection", "expected"),
    [
        ((403, PLAN), (403, PLAN), br.Rules(plan_limit=f"{PLAN} (HTTP 403)")),
        ((404, "Branch not found"), (404, "Branch not found"), br.Rules()),
        (
            list(effective(HA).rules),
            {"allow_deletions": {"enabled": False}},
            br.Rules(effective(HA).rules, {"allow_deletions": {"enabled": False}}),
        ),
    ],
    ids=["plan-limit", "empty-repository", "rules-and-classic"],
)
def test_reading_records_the_plan_limit_and_absent_rules_as_none(tmp_path, rulesets, protection, expected):
    assert br.read(GhClient(tmp_path, writer=None, runner=answers(rulesets, protection)), REPO, "main") == expected


def test_reading_raises_any_other_403(tmp_path):
    client = GhClient(tmp_path, writer=None, runner=answers([], (403, "Resource not accessible by integration")))
    with pytest.raises(ProviderError, match="Resource not accessible by integration"):
        br.read(client, REPO, "main")


def test_one_ruleset_only_where_one_repository_ruleset_governs_alone():
    alone = effective(ruleset(pull(), {"type": "deletion"}))
    beside = br.Rules(alone.rules, classic={"allow_deletions": {"enabled": False}})
    assert (br.sources(alone), br.one_ruleset(alone)) == ([7], 7)
    assert (br.sources(beside), br.one_ruleset(beside)) == ([7, "classic"], None)
    assert br.one_ruleset(effective(ruleset(pull()), ruleset(pull(), ruleset_id=8))) is None
    assert br.one_ruleset(effective(ruleset(pull()), kind="Organization")) is None
    assert br.settings_url(REPO, "classic") == "https://github.com/boecht/sandbox/settings/branches"
    assert br.settings_url(REPO, 7) == "https://github.com/boecht/sandbox/settings/rules"


def test_writes_send_the_whole_body_and_return_githubs_answer(tmp_path):
    seen = []
    client = GhClient(tmp_path, writer=None, runner=answers(HA, {}, seen))
    new = br.new_ruleset("main", require_ci=False)
    assert br.create(client, REPO, new) == HA
    assert br.replace(client, REPO, 7, new) == HA
    assert br.read_ruleset(client, REPO, 7) == HA
    assert seen == [
        ("POST", "repos/boecht/sandbox/rulesets", new),
        ("PUT", "repos/boecht/sandbox/rulesets/7", new),
        ("GET", "repos/boecht/sandbox/rulesets/7", None),
    ]
