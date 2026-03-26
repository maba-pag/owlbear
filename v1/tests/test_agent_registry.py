"""Tests for agent_registry — AgentRegistry scan, get, list."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.agent_def import AgentDefinition
from owlbear.core.agent_registry import AgentRegistry

# Block real LLM calls in the test suite.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def _write_agent_md(path: Path, name: str, description: str, *, body: str = "") -> None:
    """Helper — write a minimal agent .md definition file."""
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )


def _dummy_resolver(_tool_name: str) -> FunctionToolset:
    """Return an empty FunctionToolset for any tool name."""
    return FunctionToolset()


_TEST_MODEL = "test"
"""Use PydanticAI's built-in test model to avoid provider initialization."""


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    """Temp dir with two valid agent definitions."""
    _write_agent_md(
        tmp_path / "builder.md",
        "builder",
        "Builds code",
        body="You are a builder.\n",
    )
    _write_agent_md(
        tmp_path / "reviewer.md",
        "reviewer",
        "Reviews code",
        body="You are a reviewer.\n",
    )
    return tmp_path


class TestAgentRegistryScan:
    """Tests for scan() and list_agents()."""

    def test_scan_finds_valid_definitions(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        assert len(registry.definitions) == 2
        assert "builder" in registry.definitions
        assert "reviewer" in registry.definitions

    def test_list_agents_returns_all(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agents = registry.list_agents()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"builder", "reviewer"}

    def test_scan_empty_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        registry = AgentRegistry(empty, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        assert registry.definitions == {}
        assert registry.list_agents() == []

    def test_scan_invalid_file_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad = tmp_path / "bad.md"
        bad.write_text("---\nname: [unclosed\n---\nBody.\n", encoding="utf-8")
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        with caplog.at_level(logging.WARNING):
            registry.scan()
        assert registry.definitions == {}
        assert any("bad.md" in r.message for r in caplog.records)

    def test_definitions_is_read_only_copy(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        defs = registry.definitions
        defs["injected"] = MagicMock()  # type: ignore[assignment]
        assert "injected" not in registry.definitions


class TestAgentRegistryGet:
    """Tests for get() — lazy Agent instantiation."""

    def test_get_returns_agent(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)

    def test_get_caches_instance(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        first = registry.get("builder")
        second = registry.get("builder")
        assert first is second

    def test_get_unknown_raises_keyerror(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        with pytest.raises(KeyError, match="missing") as exc_info:
            registry.get("missing")
        # Error message should list available agent names.
        msg = str(exc_info.value)
        assert "builder" in msg
        assert "reviewer" in msg

    def test_tool_resolver_called_for_each_tool(self, tmp_path: Path) -> None:
        md = tmp_path / "tooled.md"
        md.write_text(
            "---\nname: tooled\ndescription: Has tools\n"
            "tools:\n  - file_read\n  - file_write\n---\nBody.\n",
            encoding="utf-8",
        )
        resolver = MagicMock(return_value=FunctionToolset())
        registry = AgentRegistry(tmp_path, resolver, default_model=_TEST_MODEL)
        registry.scan()
        registry.get("tooled")
        resolver.assert_any_call("file_read")
        resolver.assert_any_call("file_write")
        assert resolver.call_count == 2

    def test_get_applies_role_policy_for_non_builder(self, tmp_path: Path) -> None:
        md = tmp_path / "validator.md"
        md.write_text(
            "---\nname: val\ndescription: Validates\nrole: validator\n---\nBody.\n",
            encoding="utf-8",
        )
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        # Should not raise — role policy is applied internally.
        agent = registry.get("val")
        assert isinstance(agent, Agent)

    def test_get_uses_default_model_when_none(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)

    def test_get_accepts_model_object_as_default(self, agents_dir: Path) -> None:
        """default_model can be a PydanticAI Model instance (e.g. Copilot model)."""
        fn_model = FunctionModel(lambda _messages, _info: "ok")
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=fn_model)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)


class TestBuildAgentMissingTools:
    """Tests that _build_agent degrades gracefully when tools are missing."""

    def test_build_agent_skips_unavailable_tool(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Agent def with tools=['a','b'], resolver raises KeyError for 'b'.

        Expected: agent created with 1 toolset (only 'a'), warning logged, no exception.
        """
        md = tmp_path / "partial.md"
        md.write_text(
            "---\nname: partial\ndescription: Has two tools\ntools:\n  - a\n  - b\n---\nBody.\n",
            encoding="utf-8",
        )

        good_toolset = FunctionToolset()

        def selective_resolver(name: str) -> FunctionToolset:
            if name == "b":
                raise KeyError(name)
            return good_toolset

        registry = AgentRegistry(tmp_path, selective_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("partial")

        assert isinstance(agent, Agent)
        # Should have logged a warning about the missing tool 'b'.
        assert any("b" in r.message for r in caplog.records)

    def test_build_agent_skips_mcp_tool_when_missing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Agent def has tools=['mcp:missing'], no MCP registry configured.

        Expected: KeyError caught, agent still created (0 toolsets), warning logged.
        """
        md = tmp_path / "mcp_agent.md"
        md.write_text(
            "---\nname: mcp_agent\ndescription: Uses MCP tool\n"
            "tools:\n  - mcp:missing\n---\nBody.\n",
            encoding="utf-8",
        )

        registry = AgentRegistry(
            tmp_path, _dummy_resolver, default_model=_TEST_MODEL, mcp_registry=None
        )
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("mcp_agent")

        assert isinstance(agent, Agent)
        # Should have logged a warning about the missing MCP tool.
        assert any("mcp:missing" in r.message for r in caplog.records)

    def test_build_agent_logs_warning_for_skipped_tool(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warning message must include both the agent name and the tool name."""
        md = tmp_path / "test_agent.md"
        md.write_text(
            "---\nname: test_agent\ndescription: Agent for log test\n"
            "tools:\n  - good_tool\n  - bad_tool\n---\nBody.\n",
            encoding="utf-8",
        )

        def selective_resolver(name: str) -> FunctionToolset:
            if name == "bad_tool":
                raise KeyError(name)
            return FunctionToolset()

        registry = AgentRegistry(tmp_path, selective_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            registry.get("test_agent")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) >= 1
        msg = warnings[0].message
        assert "test_agent" in msg
        assert "bad_tool" in msg

    def test_build_agent_all_tools_present_unchanged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When all tools resolve, agent gets the full toolset with no warnings."""
        md = tmp_path / "full.md"
        md.write_text(
            "---\nname: full\ndescription: All tools resolve\n"
            "tools:\n  - x\n  - y\n  - z\n---\nBody.\n",
            encoding="utf-8",
        )

        resolved: list[str] = []

        def tracking_resolver(name: str) -> FunctionToolset:
            resolved.append(name)
            return FunctionToolset()

        registry = AgentRegistry(tmp_path, tracking_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("full")

        assert isinstance(agent, Agent)
        # All three tools were resolved.
        assert resolved == ["x", "y", "z"]
        # No warnings logged.
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == []


class TestFromAC_SingleAgentConstruction:
    """Tests that _build_agent constructs exactly one Agent() per call (#827).

    Contract: regardless of role, _build_agent must call Agent() exactly once.
    Role-policy filtering must happen BEFORE the single Agent() construction.
    """

    def test_validator_role_calls_agent_exactly_once(self, tmp_path: Path) -> None:
        """Validator role must construct Agent() exactly once, not twice."""
        md = tmp_path / "val.md"
        md.write_text(
            "---\nname: val\ndescription: Validates\nrole: validator\ntools:\n  - t1\n---\nBody.\n",
            encoding="utf-8",
        )

        mock_agent = MagicMock()
        with patch("owlbear.core.agent_registry.Agent", return_value=mock_agent) as cls:
            registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
            registry.scan()
            registry.get("val")

        assert cls.call_count == 1

    def test_builder_role_calls_agent_exactly_once(self, tmp_path: Path) -> None:
        """Builder role must construct Agent() exactly once (regression guard)."""
        md = tmp_path / "builder.md"
        md.write_text(
            "---\nname: builder\ndescription: Builds\nrole: builder\ntools:\n  - t1\n---\nBody.\n",
            encoding="utf-8",
        )

        mock_agent = MagicMock()
        with patch("owlbear.core.agent_registry.Agent", return_value=mock_agent) as cls:
            registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
            registry.scan()
            registry.get("builder")

        assert cls.call_count == 1

    def test_validator_role_passes_filtered_toolsets(self, tmp_path: Path) -> None:
        """Validator role must pass role-filtered toolsets to Agent(), not raw ones."""
        md = tmp_path / "val2.md"
        md.write_text(
            "---\nname: val2\ndescription: Validates\nrole: validator\n"
            "tools:\n  - t1\n  - t2\n---\nBody.\n",
            encoding="utf-8",
        )

        raw_ts1 = FunctionToolset()
        raw_ts2 = FunctionToolset()
        filtered_ts1 = MagicMock(name="filtered_ts1")
        filtered_ts2 = MagicMock(name="filtered_ts2")

        def resolver(name: str) -> FunctionToolset:
            return raw_ts1 if name == "t1" else raw_ts2

        def mock_apply(ts: object, _policy: object) -> object:
            if ts is raw_ts1:
                return filtered_ts1
            if ts is raw_ts2:
                return filtered_ts2
            return ts

        mock_agent = MagicMock()
        with (
            patch("owlbear.core.agent_registry.Agent", return_value=mock_agent) as cls,
            patch("owlbear.core.agent_registry.apply_role_policy", side_effect=mock_apply),
        ):
            registry = AgentRegistry(tmp_path, resolver, default_model=_TEST_MODEL)
            registry.scan()
            registry.get("val2")

        # Single Agent() call must receive the filtered toolsets.
        assert cls.call_count == 1
        _, kwargs = cls.call_args
        toolsets_arg = kwargs.get(
            "toolsets",
            cls.call_args[0][1] if len(cls.call_args[0]) > 1 else None,
        )
        assert toolsets_arg is not None
        assert filtered_ts1 in toolsets_arg
        assert filtered_ts2 in toolsets_arg
        # Raw (unfiltered) toolsets must NOT appear in the single call.
        assert raw_ts1 not in toolsets_arg
        assert raw_ts2 not in toolsets_arg


class TestBuilderDiscovered:
    """Builder-discovered edge-case tests for _build_agent (#561)."""

    def test_empty_policy_skips_apply_role_policy(self, tmp_path: Path) -> None:
        """When role policy has empty denied_tools AND allowed_tools.

        apply_role_policy must NOT be called (guard condition).
        """
        md = tmp_path / "custom.md"
        md.write_text(
            "---\nname: custom\ndescription: Custom role\nrole: validator\n"
            "tools:\n  - t1\n---\nBody.\n",
            encoding="utf-8",
        )

        empty_policy = MagicMock()
        empty_policy.denied_tools = frozenset()
        empty_policy.allowed_tools = frozenset()

        mock_agent = MagicMock()
        with (
            patch("owlbear.core.agent_registry.Agent", return_value=mock_agent),
            patch(
                "owlbear.core.agent_registry._ROLE_POLICIES",
                {"validator": empty_policy},
            ),
            patch("owlbear.core.agent_registry.apply_role_policy") as mock_apply,
        ):
            registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
            registry.scan()
            registry.get("custom")

        mock_apply.assert_not_called()


# ---------------------------------------------------------------------------
# TDD RED: Task #890 — AgentRegistry.register() programmatic registration
# ---------------------------------------------------------------------------


def _make_defn(name: str, description: str = "A test agent") -> AgentDefinition:
    """Construct a minimal AgentDefinition without reading a file."""
    return AgentDefinition(name=name, description=description, system_prompt="You help.")


class TestFromAC_ProgrammaticRegistration:
    """Tests for AgentRegistry.register(defn) — programmatic registration.

    All tests in this class target the new ``register()`` method specified in
    task #890.  Since ``register()`` does not exist yet, every test must FAIL
    with ``AttributeError`` until the builder implements it.
    """

    # ------------------------------------------------------------------
    # AC: register() stores defn under defn.name
    # ------------------------------------------------------------------

    def test_register_stores_definition_under_name(self, tmp_path: Path) -> None:
        """register(defn) must store ``defn`` in definitions[defn.name]."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("my_agent")

        registry.register(defn)

        assert "my_agent" in registry.definitions
        assert registry.definitions["my_agent"] is defn

    def test_register_multiple_definitions_stored(self, tmp_path: Path) -> None:
        """Registering two distinct agents stores both under their respective names."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn_a = _make_defn("alpha")
        defn_b = _make_defn("beta")

        registry.register(defn_a)
        registry.register(defn_b)

        assert registry.definitions["alpha"] is defn_a
        assert registry.definitions["beta"] is defn_b

    # ------------------------------------------------------------------
    # AC: get() returns an Agent for a programmatically registered definition
    # ------------------------------------------------------------------

    def test_get_returns_agent_for_registered_defn(self, tmp_path: Path) -> None:
        """After register(defn), get(defn.name) must return an Agent instance."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("prog_agent")

        registry.register(defn)
        agent = registry.get("prog_agent")

        assert isinstance(agent, Agent)

    def test_get_caches_programmatically_registered_agent(self, tmp_path: Path) -> None:
        """Two consecutive get() calls on a registered defn return the same object."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("cached_prog")

        registry.register(defn)
        first = registry.get("cached_prog")
        second = registry.get("cached_prog")

        assert first is second

    # ------------------------------------------------------------------
    # AC: re-registering the same name evicts the stale cached Agent
    # ------------------------------------------------------------------

    def test_reregistration_evicts_stale_cache(self, tmp_path: Path) -> None:
        """After a second register() with the same name, get() returns a fresh instance."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn_v1 = _make_defn("agent_x", "Version 1")
        defn_v2 = _make_defn("agent_x", "Version 2")

        registry.register(defn_v1)
        first = registry.get("agent_x")

        registry.register(defn_v2)  # should evict the cached instance
        second = registry.get("agent_x")

        assert first is not second

    def test_reregistration_updates_stored_definition(self, tmp_path: Path) -> None:
        """After a second register(), definitions[name] reflects the new defn."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn_v1 = _make_defn("shared_name", "Old description")
        defn_v2 = _make_defn("shared_name", "New description")

        registry.register(defn_v1)
        registry.register(defn_v2)

        assert registry.definitions["shared_name"] is defn_v2

    # ------------------------------------------------------------------
    # AC: scan() clears programmatic registrations, keeps only file-scanned
    # ------------------------------------------------------------------

    def test_scan_clears_programmatic_registrations(self, agents_dir: Path) -> None:
        """scan() must remove programmatically registered agents not on disk."""
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("ephemeral")
        registry.register(defn)
        assert "ephemeral" in registry.definitions

        registry.scan()

        assert "ephemeral" not in registry.definitions

    def test_scan_leaves_only_file_scanned_definitions(self, agents_dir: Path) -> None:
        """After scan(), definitions contains exactly the file-scanned agents."""
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.register(_make_defn("extra_prog"))

        registry.scan()

        # agents_dir fixture contains "builder" and "reviewer".
        assert set(registry.definitions.keys()) == {"builder", "reviewer"}

    def test_scan_on_empty_dir_clears_programmatic_registrations(self, tmp_path: Path) -> None:
        """scan() on an empty dir removes all programmatic registrations."""
        empty = tmp_path / "empty"
        empty.mkdir()
        registry = AgentRegistry(empty, _dummy_resolver, default_model=_TEST_MODEL)
        registry.register(_make_defn("will_be_gone"))

        registry.scan()

        assert registry.definitions == {}

    def test_scan_evicts_cached_agent_for_programmatic_registration(self, agents_dir: Path) -> None:
        """scan() must clear the cached Agent built from a programmatic registration.

        Verifies that after register() + get() (which populates _cache) a
        subsequent scan() makes get() raise KeyError rather than returning the
        stale cached Agent — i.e. _cache as well as _definitions is cleared.
        """
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("temp_cached")
        registry.register(defn)
        # Populate _cache explicitly
        _ = registry.get("temp_cached")

        registry.scan()

        # The definition was not on disk, so it must be gone from both stores.
        assert "temp_cached" not in registry.definitions
        with pytest.raises(KeyError):
            registry.get("temp_cached")

    def test_rescan_invalidates_cached_file_scanned_agent(self, agents_dir: Path) -> None:
        """scan() + get() + scan() must yield a fresh Agent instance on the next get().

        Proves that _cache is cleared on every scan(), not just the first one.
        A regression that skipped cache clearing after the first scan would allow
        get() to return an Agent from the pre-second-scan snapshot.
        """
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        first_agent = registry.get("builder")

        # Second scan must evict the cached agent.
        registry.scan()
        second_agent = registry.get("builder")

        assert first_agent is not second_agent

    # ------------------------------------------------------------------
    # AC: list_agents() and definitions include programmatic registrations
    # ------------------------------------------------------------------

    def test_list_agents_includes_programmatic(self, tmp_path: Path) -> None:
        """list_agents() must include programmatically registered definitions."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("prog_listed")

        registry.register(defn)
        agents_list = registry.list_agents()

        names = {a.name for a in agents_list}
        assert "prog_listed" in names

    def test_definitions_property_includes_programmatic(self, tmp_path: Path) -> None:
        """Definitions property must include programmatically registered entries."""
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        defn = _make_defn("prop_check")

        registry.register(defn)

        assert "prop_check" in registry.definitions

    def test_programmatic_and_file_scanned_coexist_in_list_agents(self, agents_dir: Path) -> None:
        """After scan() + register(), list_agents() returns both scanned and programmatic."""
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()  # loads "builder" and "reviewer"

        defn = _make_defn("injected")
        registry.register(defn)

        names = {a.name for a in registry.list_agents()}
        assert "builder" in names
        assert "reviewer" in names
        assert "injected" in names

    def test_programmatic_and_file_scanned_coexist_in_definitions(self, agents_dir: Path) -> None:
        """After scan() + register(), definitions contains both sources."""
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        registry.register(_make_defn("extra"))

        definitions = registry.definitions
        assert "builder" in definitions
        assert "reviewer" in definitions
        assert "extra" in definitions


# ---------------------------------------------------------------------------
# TDD RED: Task #897 — Role-filter simplification without core.roles
# ---------------------------------------------------------------------------


def _write_validator_md(path: Path, name: str = "val") -> None:
    """Write a minimal validator role agent definition for #897 tests."""
    path.write_text(
        f"---\nname: {name}\ndescription: Val\nrole: validator\ntools:\n  - x\n---\nBody.\n",
        encoding="utf-8",
    )


def _write_builder_md(path: Path, name: str = "bld") -> None:
    """Write a minimal builder role agent definition for #897 tests."""
    path.write_text(
        f"---\nname: {name}\ndescription: Bld\nrole: builder\ntools:\n  - x\n---\nBody.\n",
        encoding="utf-8",
    )


class TestFromAC_ValidatorDirectFiltering:
    """Validator _build_agent must call AbstractToolset.filtered() directly.

    After #897, AgentRegistry must NOT use apply_role_policy or _ROLE_POLICIES.
    Direct ts.filtered(predicate) calls replace the indirection layer for
    validator-role agents.
    """

    def test_validator_does_not_call_apply_role_policy(self, tmp_path: Path) -> None:
        """_build_agent for a validator role must NOT call apply_role_policy."""
        _write_validator_md(tmp_path / "val.md")
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        with patch("owlbear.core.agent_registry.apply_role_policy") as mock_apply:
            registry.get("val")
        mock_apply.assert_not_called()

    def test_validator_filtered_called_when_role_policy_patched_out(self, tmp_path: Path) -> None:
        """Direct filtered() call survives even when apply_role_policy is patched out.

        If _build_agent only called filtered() via apply_role_policy, replacing
        apply_role_policy with a no-op would prevent filtered() from firing.
        After #897 refactoring, filtered() is called directly so patching
        apply_role_policy has no effect on whether filtered() is invoked.
        """
        _write_validator_md(tmp_path / "val.md")
        mock_ts = MagicMock(spec=FunctionToolset)
        mock_ts.filtered.return_value = FunctionToolset()
        registry = AgentRegistry(tmp_path, lambda _: mock_ts, default_model=_TEST_MODEL)
        registry.scan()

        # Patch apply_role_policy to a no-op that does NOT call ts.filtered().
        with patch("owlbear.core.agent_registry.apply_role_policy", return_value=FunctionToolset()):
            registry.get("val")

        # After refactor: filtered() is called directly in _build_agent.
        # Currently FAILS: filtered() only fires inside apply_role_policy, which is patched out.
        mock_ts.filtered.assert_called()

    def test_validator_filtered_despite_empty_role_policies_dict(self, tmp_path: Path) -> None:
        """Filtering must happen even when _ROLE_POLICIES is an empty dict.

        With empty _ROLE_POLICIES the current code falls back to BUILDER_POLICY
        (which has no constraints), skipping filtered(). After #897, filtering
        occurs via direct ts.filtered() calls that bypass _ROLE_POLICIES entirely.
        """
        _write_validator_md(tmp_path / "val.md")
        mock_ts = MagicMock(spec=FunctionToolset)
        mock_ts.filtered.return_value = FunctionToolset()
        registry = AgentRegistry(tmp_path, lambda _: mock_ts, default_model=_TEST_MODEL)
        registry.scan()

        with patch("owlbear.core.agent_registry._ROLE_POLICIES", {}):
            registry.get("val")

        # After refactor: direct filtering independent of _ROLE_POLICIES.
        # Currently FAILS: empty dict → BUILDER_POLICY fallback → filtered() skipped.
        mock_ts.filtered.assert_called()


class TestFromAC_BuilderFilterBypass:
    """Guard: builder agents bypass all role-filtering infrastructure.

    After removing the core.roles dependency from agent_registry.py, builders
    must continue to receive unfiltered toolsets via direct string comparison
    (role == 'validator') rather than AgentRole enum lookup.
    """

    def test_agent_registry_no_core_roles_import(self) -> None:
        """After #897: agent_registry.py must not import owlbear.core.roles."""
        import ast
        import inspect

        source = Path(inspect.getfile(AgentRegistry)).read_text(encoding="utf-8")
        tree = ast.parse(source)
        roles_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "owlbear.core.roles"
        ]
        assert roles_imports == [], (
            "agent_registry.py still imports 'owlbear.core.roles'; "
            "remove this dependency as part of #897"
        )

    def test_agent_registry_no_role_policies_dict(self) -> None:
        """After #897: _ROLE_POLICIES module-level dict must be removed."""
        import ast
        import inspect

        source = Path(inspect.getfile(AgentRegistry)).read_text(encoding="utf-8")
        tree = ast.parse(source)
        role_policies_defs = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id == "_ROLE_POLICIES"
        ]
        assert role_policies_defs == [], (
            "_ROLE_POLICIES must be removed from agent_registry.py as part of #897"
        )
