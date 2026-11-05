"""A branch's rules for onboarding: read them, compare them with what Delivery needs, write one ruleset whole."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

from owlbear_delivery_next.github.gh import PLAN_LIMIT
from owlbear_delivery_next.github.gh_client import Json, Missing, invalid, repo
from owlbear_delivery_next.github.provider import FailureCode, ProviderError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from owlbear_delivery_next.github.gh_client import GhClient

type Source = int | str  # a ruleset id, or CLASSIC

METHODS = ("merge", "squash", "rebase")
CLASSIC = "classic"
NEEDS = ("merge_method", "linear_history")
ADVICE = {  # each key's words, as GitHub's settings name it
    "up_to_date": "Require branches to be up to date before merging",
    "conversations": "Require conversation resolution before merging",
    "pull_requests": "Require a pull request before merging",
    "no_deletion": "Restrict deletions",
    "no_force_push": "Block force pushes",
    "no_approvals": "No required approvals, code-owner review or approval of the most recent push",
}
NOTHING = "nothing to change"
_FORBIDDEN, _NOT_FOUND = 403, 404
_FIELDS = ("name", "target", "enforcement", "conditions", "bypass_actors", "rules")  # a ruleset's whole PUT body
_GITHUB_ONLY = frozenset(
    {"id", "node_id", "_links", "created_at", "updated_at", "source", "source_type", "current_user_can_bypass"}
)
_KEYED = {"rules": ("type",), "bypass_actors": ("actor_type", "actor_id"), "required_status_checks": ("context",)}
_NO_APPROVALS = {
    "required_approving_review_count": 0,
    "require_code_owner_review": False,
    "require_last_push_approval": False,
}
_GONE = object()  # a field or list item one side doesn't hold


@dataclass(frozen=True)
class Rules:
    """One branch's effective rules, each with its ``ruleset_id``, and its classic protection (``None`` if none)."""

    rules: tuple[Json, ...] = ()
    classic: Json = None
    plan_limit: str = ""  # GitHub's message where the repository's plan allows no branch rules


@dataclass(frozen=True)
class Item:
    """One need or piece of advice, in one source (``None`` where no rule bears on it), with its sentence."""

    key: str
    source: Source | None
    sentence: str
    holds: bool
    applicable: bool = True


@dataclass(frozen=True)
class Comparison:
    """What Delivery needs and what OwlBear advises, against the branch's rules."""

    needs: tuple[Item, ...]
    advice: tuple[Item, ...]

    @property
    def unmet(self) -> tuple[Item, ...]:
        """The conflicts, then the applicable advice that doesn't hold yet."""
        return tuple(i for i in (*self.needs, *self.advice) if i.applicable and not i.holds)

    @property
    def summary(self) -> str:
        """``nothing to change``, or how many conflicts and pieces of advice are left."""
        if not (unmet := self.unmet):
            return NOTHING
        conflicts = sum(i.key in NEEDS for i in unmet)
        return f"{conflicts} conflict(s) with what Delivery needs; {len(unmet) - conflicts} piece(s) of advice not set"


def _api(client: GhClient, operation: str, method: str, endpoint: str, **kw: Json) -> Json:
    return client._api(operation, method, endpoint, **kw)  # noqa: SLF001 - the github layer's one gh transport


def read(client: GhClient, repository: str, branch: str) -> Rules:
    """Read *branch*'s effective rules and classic protection; an absent branch or protection reads as none.

    GitHub's plan-limit 403 is recorded with GitHub's message; any other 403 raises with it.
    """
    op, path, b = "read_branch_rules", repo(repository), quote(branch, safe="")
    absent = {_FORBIDDEN, _NOT_FOUND}
    found = _api(client, op, "GET", f"{path}/rules/branches/{b}?per_page=100", absent=absent)
    classic = _api(client, op, "GET", f"{path}/branches/{b}/protection", absent=absent)
    denied = [f for f in (found, classic) if isinstance(f, Missing) and f.status == _FORBIDDEN]
    if other := next((f for f in denied if not f.message.startswith(PLAN_LIMIT)), None):
        raise ProviderError(FailureCode.UNAVAILABLE, op, other.message, retry_safe=True)
    rules = [] if isinstance(found, Missing) else found
    if not isinstance(rules, list) or not all(
        isinstance(r, dict) and isinstance(r.get("type"), str) and "ruleset_id" in r for r in rules
    ):
        invalid(op, f"GitHub returned invalid branch rules: {json.dumps(rules)}")
    if not isinstance(classic, dict | Missing):
        invalid(op, f"GitHub returned invalid branch protection: {json.dumps(classic)}")
    return Rules(tuple(rules), None if isinstance(classic, Missing) else classic, denied[0].message if denied else "")


def _params(rule: Json) -> Json:
    return rule.get("parameters") or {}


def _on(classic: Json, field: str) -> bool:
    return bool((classic.get(field) or {}).get("enabled"))


def _linear(rules: Rules) -> list[Source]:
    """The sources that require linear history, which forbids merge commits."""
    found: list[Source] = [r["ruleset_id"] for r in rules.rules if r["type"] == "required_linear_history"]
    return found + ([CLASSIC] if rules.classic is not None and _on(rules.classic, "required_linear_history") else [])


def allowed_methods(settings: Mapping[str, bool], rules: Rules) -> set[str]:
    """The merge methods *settings* allow, limited by every pull-request rule, without ``merge`` under linear history.

    A pull-request rule without ``allowed_merge_methods`` limits nothing.
    """
    allowed = {m for m in METHODS if settings[m]}
    for r in rules.rules:
        if r["type"] == "pull_request" and (limit := _params(r).get("allowed_merge_methods")) is not None:
            allowed &= set(limit)
    return allowed - {"merge"} if _linear(rules) else allowed


def sources(rules: Rules) -> list[Source]:
    """The distinct sources of the branch's rules: each ruleset's id, then ``classic`` for classic protection."""
    found: list[Source] = list(dict.fromkeys(r["ruleset_id"] for r in rules.rules))
    return found + ([CLASSIC] if rules.classic is not None else [])


def one_ruleset(rules: Rules) -> int | None:
    """The id of the one repository ruleset governing the branch alone, else ``None``."""
    found = sources(rules)
    alone = len(found) == 1 and isinstance(found[0], int)
    return found[0] if alone and all(r.get("ruleset_source_type") == "Repository" for r in rules.rules) else None


def _name(rules: Rules, source: Source) -> str:
    if source == CLASSIC:
        return "classic protection"
    kind = next(r.get("ruleset_source_type") for r in rules.rules if r["ruleset_id"] == source)
    return f"ruleset {source}" if kind == "Repository" else f"{str(kind).lower()} ruleset {source}"


def _approval_free(reviews: Json, code_owner: str) -> bool:
    """No approval count, code-owner review or last-push approval; classic protection names the second differently."""
    fields = ("required_approving_review_count", code_owner, "require_last_push_approval")
    return not any(reviews.get(f) for f in fields)


def _ruleset_facts(rules: list[Json]) -> dict[str, bool]:
    types = {r["type"] for r in rules}
    pulls = [_params(r) for r in rules if r["type"] == "pull_request"]
    checks = [_params(r) for r in rules if r["type"] == "required_status_checks"]
    return {
        "checks": any(c.get("required_status_checks") for c in checks),
        "up_to_date": any(
            c.get("strict_required_status_checks_policy") and c.get("required_status_checks") for c in checks
        ),
        "conversations": any(p.get("required_review_thread_resolution") for p in pulls),
        "pull_requests": bool(pulls),
        "no_deletion": "deletion" in types,
        "no_force_push": "non_fast_forward" in types,
        "no_approvals": all(_approval_free(p, "require_code_owner_review") for p in pulls),
    }


def _classic_facts(classic: Json) -> dict[str, bool]:
    checks = classic.get("required_status_checks") or {}
    reviews = classic.get("required_pull_request_reviews")
    required = bool(checks.get("contexts") or checks.get("checks"))
    return {
        "checks": required,
        "up_to_date": required and bool(checks.get("strict")),
        "conversations": _on(classic, "required_conversation_resolution"),
        "pull_requests": reviews is not None,
        "no_deletion": not _on(classic, "allow_deletions"),
        "no_force_push": not _on(classic, "allow_force_pushes"),
        "no_approvals": reviews is None or _approval_free(reviews, "require_code_owner_reviews"),
    }


def _facts(rules: Rules) -> dict[Source, dict[str, bool]]:
    by: dict[Source, list[Json]] = {}
    for r in rules.rules:
        by.setdefault(r["ruleset_id"], []).append(r)
    facts = {s: _ruleset_facts(found) for s, found in by.items()}
    return facts | ({CLASSIC: _classic_facts(rules.classic)} if rules.classic is not None else {})


def _needs(rules: Rules, method: str) -> list[Item]:
    items = []
    for r in (r for r in rules.rules if r["type"] == "pull_request"):
        where, limit = _name(rules, r["ruleset_id"]), _params(r).get("allowed_merge_methods")
        if limit is None or method in limit:
            said = f"rule pull_request in {where} allows {method}"
        else:
            said = f"rule pull_request in {where} conflicts: Delivery needs {method} among its allowed merge methods"
            said += f", now {', '.join(limit) or 'none'}"
        items.append(Item("merge_method", r["ruleset_id"], said, holds=limit is None or method in limit))
    if not items:
        items.append(Item("merge_method", None, "no pull-request rule limits the merge method", holds=True))
    linear = _linear(rules)
    for s in linear if method == "merge" else []:
        said = f"rule required_linear_history in {_name(rules, s)} conflicts: Delivery needs merge commits"
        items.append(Item("linear_history", s, said, holds=False))
    if not linear or method != "merge":
        said = f"linear history allows {method}" if linear else "no linear history is required"
        items.append(Item("linear_history", None, said, holds=True))
    return items


def _advice(rules: Rules) -> list[Item]:
    facts = _facts(rules)
    checked = [s for s, f in facts.items() if f["checks"]]
    only = next(iter(facts)) if len(facts) == 1 else None
    items = []
    for key, label in ADVICE.items():
        if key == "no_approvals":
            offenders = [s for s, f in facts.items() if not f[key]]
            names = " and ".join(_name(rules, s) for s in offenders)
            said = f"{label}: {names} require a review, so Delivery waits for a human review on every pull request"
            source = offenders[0] if offenders else None
            items.append(Item(key, source, said if offenders else f"{label}: holds", holds=not offenders))
        elif key == "up_to_date" and not checked:
            said = f"{label}: takes effect only with a required check"
            items.append(Item(key, None, said, holds=False, applicable=False))
        else:
            holders = [s for s, f in facts.items() if f[key]]
            source = holders[0] if holders else checked[0] if key == "up_to_date" else only
            where = f" in {_name(rules, source)}" if source is not None else ""
            items.append(Item(key, source, f"{label}: {'set' if holders else 'not set'}{where}", holds=bool(holders)))
    return items


def compare(rules: Rules, method: str) -> Comparison:
    """Compare the branch's rules with what merging by *method* needs and with OwlBear's advice."""
    return Comparison(needs=tuple(_needs(rules, method)), advice=tuple(_advice(rules)))


def _pull_request(methods: list[str], *, resolution: bool) -> Json:
    parameters = {"allowed_merge_methods": methods, "dismiss_stale_reviews_on_push": False, **_NO_APPROVALS}
    return {"type": "pull_request", "parameters": parameters | {"required_review_thread_resolution": resolution}}


def new_ruleset(branch: str, *, require_ci: bool) -> Json:
    """The ``POST`` body of OwlBear's ruleset on the default branch: merge commits only through pull requests.

    It requires ``CI``, up to date, only with *require_ci*; it has no bypass actors and requires no approvals.
    """
    rules = [{"type": "deletion"}, {"type": "non_fast_forward"}, _pull_request(["merge"], resolution=True)]
    if require_ci:
        checks = {"strict_required_status_checks_policy": True, "required_status_checks": [{"context": "CI"}]}
        rules.append({"type": "required_status_checks", "parameters": checks})
    return {
        "name": f"OwlBear: {branch}",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "bypass_actors": [],
        "rules": rules,
    }


def _typed(rules: list[Json], kind: str) -> list[Json]:
    return [r.setdefault("parameters", {}) for r in rules if r["type"] == kind]


def _pull_requests(rules: list[Json], needs: Collection[str], advice: Collection[str], method: str) -> None:
    """Change every pull-request rule's fields that the named *needs* and ticked *advice* name."""
    for p in _typed(rules, "pull_request"):
        limit = p.get("allowed_merge_methods")
        if "merge_method" in needs and limit is not None and method not in limit:
            limit.append(method)
        if "conversations" in advice:
            p["required_review_thread_resolution"] = True
        if "no_approvals" in advice:
            p.update(_NO_APPROVALS)


def changed(ruleset: Json, needs: Collection[str], advice: Collection[str], method: str) -> Json:
    """The whole *ruleset* as a ``PUT`` body, changed only in the fields the named *needs* and ticked *advice* name.

    A pull-request rule is added, allowing every method, only where the advice needs one; a required check is never
    invented for being up to date.
    """
    body = {k: copy.deepcopy(ruleset[k]) for k in _FIELDS if k in ruleset}
    rules = body["rules"]
    if "linear_history" in needs:
        rules[:] = [r for r in rules if r["type"] != "required_linear_history"]
    if not _typed(rules, "pull_request") and not {"pull_requests", "conversations"}.isdisjoint(advice):
        rules.append(_pull_request(list(METHODS), resolution=False))
    _pull_requests(rules, needs, advice, method)
    for p in _typed(rules, "required_status_checks") if "up_to_date" in advice else []:
        if p.get("required_status_checks"):
            p["strict_required_status_checks_policy"] = True
    for key, kind in (("no_deletion", "deletion"), ("no_force_push", "non_fast_forward")):
        if key in advice and all(r["type"] != kind for r in rules):
            rules.append({"type": kind})
    return body


def _show(value: Json) -> str:
    return "nothing" if value is _GONE else json.dumps(value, sort_keys=True)


def _line(path: str, sent: Json, answer: Json) -> str:
    return f"{path or 'ruleset'}: sent {_show(sent)}, GitHub has {_show(answer)}"


def _keyed(path: str, fields: tuple[str, ...], sent: list[Json], answer: list[Json]) -> list[str]:
    def ident(item: Json) -> tuple[Json, ...]:
        return tuple(item.get(f) for f in fields) if isinstance(item, dict) else (item,)

    theirs = {ident(a): a for a in answer}
    lines = []
    for item in sent:
        lines += _diff(f"{path}[{' '.join(map(str, ident(item)))}]", item, theirs.pop(ident(item), _GONE))
    return lines + [_line(f"{path}[{' '.join(map(str, k))}]", _GONE, a) for k, a in theirs.items()]


def _diff(path: str, sent: Json, answer: Json) -> list[str]:
    if isinstance(sent, dict) and isinstance(answer, dict):
        lines = []
        for k, v in sent.items():
            if k not in _GITHUB_ONLY:
                lines += _diff(f"{path}.{k}" if path else k, v, answer.get(k, _GONE))
        return lines
    if isinstance(sent, list) and isinstance(answer, list):
        if (fields := _KEYED.get(path.rsplit(".", 1)[-1])) is not None:
            return _keyed(path, fields, sent, answer)
        return [] if sorted(map(_show, sent)) == sorted(map(_show, answer)) else [_line(path, sent, answer)]
    return [] if sent == answer else [_line(path, sent, answer)]


def differences(sent: Json, answer: Json) -> list[str]:
    """Each field *sent* that GitHub's *answer* holds differently, one readable line each.

    Only the fields sent count, so the defaults GitHub adds and its own fields (id, links, times) are ignored. Rules,
    bypass actors and required checks are matched by identity, so their order doesn't count and one only GitHub holds
    is a difference too; other lists are compared as sets.
    """
    return _diff("", sent, answer)


def create(client: GhClient, repository: str, body: Json) -> Json:
    """Create a ruleset from *body* and return GitHub's answer, the whole ruleset."""
    return _api(client, "create_ruleset", "POST", f"{repo(repository)}/rulesets", body=body, write=True)


def replace(client: GhClient, repository: str, ruleset_id: int, body: Json) -> Json:
    """Replace ruleset *ruleset_id* with *body* and return GitHub's answer, the whole ruleset."""
    return _api(client, "replace_ruleset", "PUT", f"{repo(repository)}/rulesets/{ruleset_id}", body=body, write=True)


def read_ruleset(client: GhClient, repository: str, ruleset_id: int) -> Json:
    """Read the whole ruleset *ruleset_id*: its rules, conditions and bypass actors."""
    return _api(client, "read_ruleset", "GET", f"{repo(repository)}/rulesets/{ruleset_id}")


def settings_url(repository: str, source: Source) -> str:
    """The GitHub settings page where the owner changes *source*: rulesets, or classic branch protection."""
    return f"https://github.com/{repository}/settings/{'branches' if source == CLASSIC else 'rules'}"
