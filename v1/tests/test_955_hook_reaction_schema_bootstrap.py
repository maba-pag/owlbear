"""Tests for #955 AC lines not covered by the #965 and #969 RED suites.

The #965 suite (test_hook_reaction_router.py) and #969 suite (test_config.py)
cover schema validation, routing semantics, error handling, and config-leaf
ownership.  This file covers the four AC lines that only #955 specifies:

* Router module import isolation — hook_reaction_router.py must not import
  daemon, loop_detection, channel, or bootstrap modules (AC line 5).
* _ALLOWED_ACTIONS set membership — exactly {"notify", "retry", "escalate"}
  and no other action kind is permitted (AC line 4).
* build_hooks() return-contract preserved when hook_reactions is configured
  (AC line 9 and signature contract).
* Executor-missing-from-map is silently skipped, per the architecture
  Failure Mode Map entry for #955 AC line 6.

Note: The implementation predates this test phase (it was established during
the #965 pipeline and preserved after the AC refinement in the #955
architecture review).  All tests are expected to PASS on the current HEAD.
This is consistent with AC line 11 ("All tests from #965 and #969 pass") and
with the architecture note that "Builder/reviewer/auditor will verify against
#955 AC."
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from owlbear.bootstrap.hooks import build_hooks
from owlbear.config import HookReactionRule, OwlBearSettings
from owlbear.core.hook_reaction_router import HookReactionRouter
from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROUTER_SOURCE_PATH: Path = (
    Path(__file__).resolve().parent.parent / "src" / "owlbear" / "core" / "hook_reaction_router.py"
)


def _router_imports() -> list[tuple[int, str]]:
    """Return (lineno, module) for every import in hook_reaction_router.py."""
    src = _ROUTER_SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(_ROUTER_SOURCE_PATH))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
    return found


# ---------------------------------------------------------------------------
# AC line 5 — router module import isolation
# ---------------------------------------------------------------------------


class TestFromAC_955_RouterModuleIsolation:
    """hook_reaction_router.py must not import daemon.py, loop_detection.py,
    channel modules, or bootstrap code (AC line 5).

    These are source-inspection regression guards.  They PASS on current HEAD
    because the #965 implementation already satisfies the constraint.
    """

    def test_router_does_not_import_daemon_module(self) -> None:
        """hook_reaction_router.py must not import owlbear.daemon or its submodules."""
        imports = _router_imports()
        daemon_imports = [(line, mod) for line, mod in imports if "daemon" in mod]
        assert not daemon_imports, (
            f"hook_reaction_router.py must not import daemon modules. Found: {daemon_imports}"
        )

    def test_router_does_not_import_loop_detection(self) -> None:
        """hook_reaction_router.py must not import loop_detection."""
        imports = _router_imports()
        bad = [(line, mod) for line, mod in imports if "loop_detection" in mod]
        assert not bad, f"hook_reaction_router.py must not import loop_detection. Found: {bad}"

    def test_router_does_not_import_channel_modules(self) -> None:
        """hook_reaction_router.py must not import owlbear.channels.*."""
        imports = _router_imports()
        bad = [
            (line, mod)
            for line, mod in imports
            if mod.startswith("owlbear.channels") or mod == "owlbear.channels"
        ]
        assert not bad, f"hook_reaction_router.py must not import channel modules. Found: {bad}"

    def test_router_does_not_import_bootstrap_code(self) -> None:
        """hook_reaction_router.py must not import owlbear.bootstrap.*."""
        imports = _router_imports()
        bad = [
            (line, mod)
            for line, mod in imports
            if mod.startswith("owlbear.bootstrap") or mod == "owlbear.bootstrap"
        ]
        assert not bad, f"hook_reaction_router.py must not import bootstrap code. Found: {bad}"

    def test_router_runtime_imports_limited_to_owlbear_config_and_hooks(self) -> None:
        """Runtime (non-TYPE_CHECKING) owlbear imports must be owlbear.config or owlbear.core.hooks.

        The architecture review for #955 confirms: hook_reaction_router.py imports
        owlbear.config (runtime) and owlbear.core.hooks (TYPE_CHECKING + deferred
        in register()).  All other owlbear.* imports are forbidden.
        """
        src = _ROUTER_SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(_ROUTER_SOURCE_PATH))

        # Find TYPE_CHECKING guard node line numbers
        type_checking_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
                    isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
                ):
                    for child in ast.walk(node):
                        if hasattr(child, "lineno"):
                            type_checking_lines.add(child.lineno)

        # Find all owlbear imports that are NOT inside a TYPE_CHECKING block
        # and NOT inside a function body (deferred imports inside register() are OK).
        # We only check module-level statements (depth 1 in the AST).
        allowed_prefixes = ("owlbear.config", "owlbear.core.hooks")
        forbidden: list[tuple[int, str]] = [
            (node.lineno, node.module)
            for node in ast.iter_child_nodes(tree)  # module-level only
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("owlbear.")
                and not any(node.module.startswith(p) for p in allowed_prefixes)
            )
        ]

        assert not forbidden, (
            "hook_reaction_router.py has module-level owlbear imports beyond "
            "owlbear.config / owlbear.core.hooks. "
            f"Forbidden: {forbidden}"
        )


# ---------------------------------------------------------------------------
# AC line 4 — allowed action kinds exactly {"notify", "retry", "escalate"}
# ---------------------------------------------------------------------------


class TestFromAC_955_AllowedActionsExactSet:
    """The set of permitted action kinds must be exactly {"notify", "retry", "escalate"}.

    AC line 4: "Allowed action kinds in this task are exactly notify, retry, and
    escalate as typed config values; this task does not add a more general
    workflow DSL, regex matching, nested-path matching, or templating."
    """

    def test_allowed_actions_contains_notify(self) -> None:
        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        assert "notify" in rule.actions

    def test_allowed_actions_contains_retry(self) -> None:
        rule = HookReactionRule(events=["on_error"], actions=["retry"])
        assert "retry" in rule.actions

    def test_allowed_actions_contains_escalate(self) -> None:
        rule = HookReactionRule(events=["budget_warning"], actions=["escalate"])
        assert "escalate" in rule.actions

    def test_allowed_actions_frozenset_is_exact_three_element_set(self) -> None:
        """_ALLOWED_ACTIONS must be exactly the three-element frozenset."""
        from owlbear import config as _config_module

        assert frozenset({"notify", "retry", "escalate"}) == _config_module._ALLOWED_ACTIONS, (
            f"Expected exactly {{'notify', 'retry', 'escalate'}}, "
            f"got {_config_module._ALLOWED_ACTIONS!r}"
        )
        assert len(_config_module._ALLOWED_ACTIONS) == 3

    def test_workflow_action_kind_rejected(self) -> None:
        """'workflow' is NOT an allowed action kind."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=["task_complete"], actions=["workflow"])

    def test_templating_action_kind_rejected(self) -> None:
        """'template' is NOT an allowed action kind."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=["task_complete"], actions=["template"])

    def test_action_list_must_not_be_empty(self) -> None:
        """Empty actions list is rejected by schema validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="non-empty"):
            HookReactionRule(events=["task_complete"], actions=[])


# ---------------------------------------------------------------------------
# AC line 9 — build_hooks() return contract and noop-executor path
# ---------------------------------------------------------------------------


class TestFromAC_955_BuildHooksReturnContract:
    """build_hooks() must keep its existing return contract
    (tuple[HookRegistry, ProgressReporter | None]) when hook_reactions is
    configured, and must work without real retry / escalation executors
    from downstream tasks #956 / #957 (AC line 9).
    """

    def test_build_hooks_with_reactions_returns_tuple(self) -> None:
        """Return value is a two-element tuple when hook_reactions is non-empty."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify"]}],
        )
        result = build_hooks(settings, workspace_root=None)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_build_hooks_with_reactions_first_element_is_registry(self) -> None:
        """First element is a HookRegistry when hook_reactions is configured."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["on_error"], "actions": ["escalate"]}],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks, HookRegistry)

    def test_build_hooks_with_reactions_second_element_is_none_without_channel(self) -> None:
        """Second element is None (no ProgressReporter) when no channel is passed."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["budget_warning"], "actions": ["retry"]}],
        )
        _, reporter = build_hooks(settings, workspace_root=None)
        assert reporter is None

    def test_build_hooks_no_reactions_returns_same_contract(self) -> None:
        """Contract is preserved when hook_reactions is empty."""
        settings = OwlBearSettings(hook_reactions=[])
        result = build_hooks(settings, workspace_root=None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        hooks, reporter = result
        assert isinstance(hooks, HookRegistry)
        assert reporter is None

    def test_build_hooks_with_reactions_does_not_require_retry_executor(self) -> None:
        """build_hooks() with notify-only reaction works without a real retry backend."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify"]}],
        )
        # Must not raise even though no real retry / escalate backend is wired.
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks, HookRegistry)

    def test_build_hooks_with_reactions_does_not_require_escalation_executor(self) -> None:
        """build_hooks() with retry-only reaction works without a real escalation backend."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["on_error"], "actions": ["retry"]}],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks, HookRegistry)

    @pytest.mark.asyncio
    async def test_build_hooks_noop_executors_do_not_raise_on_emit(self) -> None:
        """Emitting a configured event through noop executors must not raise."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify", "retry"]}],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        # Emit without raising
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "success"})


# ---------------------------------------------------------------------------
# AC line 6 expanded — executor missing from map is silently skipped
# ---------------------------------------------------------------------------


class TestFromAC_955_ExecutorMissingFromMap:
    """When a configured action kind has no entry in the executors dict,
    the action must be silently skipped (no exception, no spurious side effect).

    Architecture Failure Mode Map entry: "_make_handler dispatch |
    Executor missing from map | None check | Yes - skipped silently |
    No-op until downstream task wires real executor"

    This path is distinct from the executor-raises path tested by #965.
    """

    @pytest.mark.asyncio
    async def test_missing_action_executor_silently_skipped(self) -> None:
        """Actions whose executor is absent from the map are skipped without error."""
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        # rule requests "retry" but executors only provides "notify"
        rule = HookReactionRule(events=["task_complete"], actions=["retry"])
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify},  # retry and escalate absent
        )
        router.register(hooks)

        # Must not raise
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1"})

        # notify was not called (the action is "retry", not "notify")
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_present_executor_runs_despite_other_missing(self) -> None:
        """An executor that IS in the map runs even when other actions are missing."""
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        # rule: notify then escalate; only notify is in the map
        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify", "escalate"],
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify},  # escalate absent
        )
        router.register(hooks)

        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1"})

        mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_executors_map_does_not_raise(self) -> None:
        """An entirely empty executors map must not cause the handler to raise."""
        hooks = HookRegistry()
        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        router = HookReactionRouter(rules=[rule], executors={})
        router.register(hooks)

        # Must not raise
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1"})

    @pytest.mark.asyncio
    async def test_missing_executor_does_not_log_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A missing executor is silently skipped — no warning should be emitted."""
        import logging

        hooks = HookRegistry()
        rule = HookReactionRule(events=["task_complete"], actions=["retry"])
        router = HookReactionRouter(rules=[rule], executors={})
        router.register(hooks)

        with caplog.at_level(logging.WARNING, logger="owlbear.core.hook_reaction_router"):
            await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1"})

        # No WARNING should be emitted for a missing-but-expected noop executor
        reaction_records = [
            r for r in caplog.records if r.name == "owlbear.core.hook_reaction_router"
        ]
        assert not reaction_records, (
            f"Expected no log records for missing executor, got: {reaction_records}"
        )


# ---------------------------------------------------------------------------
# AC line 2 — HookReactionRule Pydantic validation from owlbear.config
# ---------------------------------------------------------------------------


class TestFromAC_955_HookReactionRuleCanonicalImport:
    """HookReactionRule must be importable from owlbear.config (canonical path)
    and the config-owned class must enforce the full Pydantic validation contract
    (AC line 2).  This verifies the config-leaf ownership without going through
    the router re-export.
    """

    def test_hook_reaction_rule_importable_from_config(self) -> None:
        """HookReactionRule is accessible at owlbear.config.HookReactionRule."""
        from owlbear.config import HookReactionRule as ConfigRule

        assert ConfigRule is not None

    def test_hook_reaction_rule_from_config_is_config_owned(self) -> None:
        """Config-path import yields the class whose __module__ is owlbear.config."""
        from owlbear.config import HookReactionRule as ConfigRule

        assert ConfigRule.__module__ == "owlbear.config", (
            f"Expected __module__='owlbear.config', got {ConfigRule.__module__!r}"
        )

    def test_config_rule_validates_non_empty_events(self) -> None:
        """Config-path HookReactionRule rejects empty events list."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError):
            ConfigRule(events=[], actions=["notify"])

    def test_config_rule_rejects_unknown_key(self) -> None:
        """Config-path HookReactionRule enforces extra='forbid'."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError):
            ConfigRule(events=["task_complete"], actions=["notify"], unknown_key="bad")  # type: ignore[call-arg]

    def test_config_rule_rejects_dict_match_value(self) -> None:
        """Config-path HookReactionRule rejects dict match values (must be scalar)."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError):
            ConfigRule(
                events=["task_complete"],
                actions=["notify"],
                match={"key": {"nested": "bad"}},
            )

    def test_owlbear_settings_hook_reactions_returns_config_owned_instances(self) -> None:
        """Parsed hook_reactions are instances of the config-owned HookReactionRule."""
        from owlbear.config import HookReactionRule as ConfigRule

        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify"]}]
        )
        rule = settings.hook_reactions[0]
        assert isinstance(rule, ConfigRule)
        assert type(rule).__module__ == "owlbear.config"


# ---------------------------------------------------------------------------
# AC line 2 (retry gap) — scalar-only match: non-scalar types beyond dict/list
# ---------------------------------------------------------------------------


class TestFromAC_955_ScalarMatchBoundary:
    """_scalar_match_values must reject ALL non-scalar types, not only dict and list.

    The reviewer found that the implementation only calls
    ``isinstance(val, (dict, list))`` which silently accepts tuple, frozenset,
    set, and arbitrary objects.  AC line 2 says "scalar (not a dict or list)"
    but the intent — and the AC contract — is that only Python scalar primitives
    (str, int, float, bool, None) are valid match values.

    These tests are added in the retry cycle after the reviewer's HIGH-severity
    finding.  They must FAIL until the implementation is extended to reject all
    non-scalar container and arbitrary-object values.
    """

    def test_rejects_tuple_match_value(self) -> None:
        """A tuple match value must be rejected with ValidationError."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError, match="non-scalar"):
            ConfigRule(
                events=["task_complete"],
                actions=["notify"],
                match={"key": (1, 2)},
            )

    def test_rejects_frozenset_match_value(self) -> None:
        """A frozenset match value must be rejected with ValidationError."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError, match="non-scalar"):
            ConfigRule(
                events=["task_complete"],
                actions=["notify"],
                match={"key": frozenset({"a", "b"})},
            )

    def test_rejects_set_match_value(self) -> None:
        """A set match value must be rejected with ValidationError."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        with pytest.raises(ValidationError, match="non-scalar"):
            ConfigRule(
                events=["task_complete"],
                actions=["notify"],
                match={"key": {"a", "b"}},
            )

    def test_rejects_custom_object_match_value(self) -> None:
        """An arbitrary object match value must be rejected with ValidationError."""
        from pydantic import ValidationError

        from owlbear.config import HookReactionRule as ConfigRule

        class _Obj:
            pass

        with pytest.raises(ValidationError, match="non-scalar"):
            ConfigRule(
                events=["task_complete"],
                actions=["notify"],
                match={"key": _Obj()},
            )

    def test_scalar_int_match_value_accepted(self) -> None:
        """An int match value (scalar) must be accepted."""
        from owlbear.config import HookReactionRule as ConfigRule

        rule = ConfigRule(events=["task_complete"], actions=["notify"], match={"priority": 1})
        assert rule.match == {"priority": 1}

    def test_scalar_str_match_value_accepted(self) -> None:
        """A str match value (scalar) must be accepted."""
        from owlbear.config import HookReactionRule as ConfigRule

        rule = ConfigRule(
            events=["task_complete"], actions=["notify"], match={"outcome": "success"}
        )
        assert rule.match == {"outcome": "success"}

    def test_scalar_none_match_value_accepted(self) -> None:
        """A None match value (scalar) must be accepted."""
        from owlbear.config import HookReactionRule as ConfigRule

        rule = ConfigRule(events=["task_complete"], actions=["notify"], match={"tag": None})
        assert rule.match == {"tag": None}

    def test_scalar_bool_match_value_accepted(self) -> None:
        """A bool match value (scalar) must be accepted."""
        from owlbear.config import HookReactionRule as ConfigRule

        rule = ConfigRule(events=["task_complete"], actions=["notify"], match={"urgent": True})
        assert rule.match == {"urgent": True}
