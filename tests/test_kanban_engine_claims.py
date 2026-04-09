"""Failing tests for KanbanEngine claiming protocol and agent-name generation (#723, RED phase).

AC coverage:
  AC1 - agent_name property: generated once per instance, reused across accesses
        (identity check)
  AC2 - agent_name format: lowercase adjective-noun, both parts in ADJECTIVES/NOUNS
        pool constants from agent_names.py
  AC3 - claim_task: sets claimed_by=engine.agent_name + claimed_at (ISO string),
        rejects if already claimed by a different agent
  AC4 - release_task: clears claimed_by and claimed_at to None
  AC5 - claim on blocked task is rejected (raises before modifying claim fields)
  AC6 - claim_timeout: expired claim (claimed_at + timeout < now) is overridable by
        another agent; unexpired claim is rejected. Injectable now: datetime | None
        on claim_task for deterministic time control.

Import path: owlbear_mcp_kanban.agent_names (module does NOT exist yet — #724 creates it).
All tests must FAIL at this stage — GREEN phase is task #724.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_mcp_kanban.agent_names import ADJECTIVES, NOUNS  # type: ignore[import-not-found]
from owlbear_mcp_kanban.engine import KanbanEngine  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Shared config content — mirrors real .owlbear/kanban/config.yml
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""

# Sentinel datetimes for timeout boundary tests
_CLAIM_ORIGIN = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_EXPIRED_NOW = _CLAIM_ORIGIN + timedelta(hours=2)    # 2h after origin; 1h timeout → expired
_FRESH_NOW = _CLAIM_ORIGIN + timedelta(minutes=30)   # 30m after origin; 1h timeout → active

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine with a pinned agent_name for deterministic tests."""
    return KanbanEngine(kanban_dir, agent_name="alpha-test")


@pytest.fixture()
def rival_engine(kanban_dir: Path) -> KanbanEngine:
    """Second KanbanEngine with a different agent_name for conflict/timeout tests."""
    return KanbanEngine(kanban_dir, agent_name="beta-rival")


# ===========================================================================
# TestFromAC_AgentNameIdentity — AC1
# ===========================================================================


class TestFromAC_AgentNameIdentity:
    """Tests for AC1: agent_name generated once per engine instance, reused."""

    def test_agent_name_returns_string(self, kanban_dir: Path) -> None:
        """agent_name is a non-empty string."""
        eng = KanbanEngine(kanban_dir)
        assert isinstance(eng.agent_name, str)
        assert eng.agent_name != ""

    def test_agent_name_same_object_across_accesses(self, kanban_dir: Path) -> None:
        """The exact same string object is returned on every access (identity)."""
        eng = KanbanEngine(kanban_dir)
        first = eng.agent_name
        second = eng.agent_name
        assert first is second

    def test_agent_name_consistent_across_ten_accesses(self, kanban_dir: Path) -> None:
        """agent_name is stable across many accesses — never regenerated."""
        eng = KanbanEngine(kanban_dir)
        names = [eng.agent_name for _ in range(10)]
        assert len(set(names)) == 1

    def test_explicit_agent_name_is_used(self, kanban_dir: Path) -> None:
        """Passing agent_name kwarg to constructor pins the name exactly."""
        eng = KanbanEngine(kanban_dir, agent_name="fixed-name")
        assert eng.agent_name == "fixed-name"

    def test_explicit_name_stable_across_accesses(self, kanban_dir: Path) -> None:
        """Pinned name is also returned as the same object on every access."""
        eng = KanbanEngine(kanban_dir, agent_name="pinned-oak")
        assert eng.agent_name is eng.agent_name  # noqa: PLR0124


# ===========================================================================
# TestFromAC_AgentNameFormat — AC2
# ===========================================================================


class TestFromAC_AgentNameFormat:
    """Tests for AC2: generated agent_name is lowercase adjective-noun from word pools."""

    def test_agent_name_matches_adjective_noun_pattern(self, kanban_dir: Path) -> None:
        """Generated agent_name matches r'^[a-z]+-[a-z]+$'."""
        eng = KanbanEngine(kanban_dir)
        assert re.fullmatch(r"^[a-z]+-[a-z]+$", eng.agent_name)

    def test_agent_name_has_exactly_one_hyphen(self, kanban_dir: Path) -> None:
        """Generated name contains exactly one hyphen separating adjective and noun."""
        eng = KanbanEngine(kanban_dir)
        assert eng.agent_name.count("-") == 1

    def test_adjective_part_is_in_adjectives_pool(self, kanban_dir: Path) -> None:
        """The first part (adjective) is drawn from ADJECTIVES constant."""
        eng = KanbanEngine(kanban_dir)
        adjective, _ = eng.agent_name.split("-", 1)
        assert adjective in ADJECTIVES

    def test_noun_part_is_in_nouns_pool(self, kanban_dir: Path) -> None:
        """The second part (noun) is drawn from NOUNS constant."""
        eng = KanbanEngine(kanban_dir)
        _, noun = eng.agent_name.split("-", 1)
        assert noun in NOUNS

    def test_adjectives_pool_is_non_empty(self) -> None:
        """ADJECTIVES constant is a non-empty sequence."""
        assert len(ADJECTIVES) > 0

    def test_nouns_pool_is_non_empty(self) -> None:
        """NOUNS constant is a non-empty sequence."""
        assert len(NOUNS) > 0

    def test_adjectives_all_lowercase(self) -> None:
        """Every entry in ADJECTIVES is lowercase."""
        assert all(a == a.lower() for a in ADJECTIVES)

    def test_nouns_all_lowercase(self) -> None:
        """Every entry in NOUNS is lowercase."""
        assert all(n == n.lower() for n in NOUNS)


# ===========================================================================
# TestFromAC_ClaimTask — AC3
# ===========================================================================


class TestFromAC_ClaimTask:
    """Tests for AC3: claim_task sets claimed_by/claimed_at; rejects concurrent claims."""

    def test_unclaimed_task_has_null_claimed_fields(self, engine: KanbanEngine) -> None:
        """Freshly created task has claimed_by=None and claimed_at=None."""
        task = engine.create_task("Unclaimed task")
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None
        assert record.claimed_at is None

    def test_claim_sets_claimed_by_to_agent_name(self, engine: KanbanEngine) -> None:
        """After claim_task, record.claimed_by equals engine.agent_name."""
        task = engine.create_task("Claim target")
        engine.claim_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_by == engine.agent_name

    def test_claim_sets_claimed_at_as_string(self, engine: KanbanEngine) -> None:
        """After claim_task, record.claimed_at is a non-None, non-empty string."""
        task = engine.create_task("Timestamp target")
        engine.claim_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert isinstance(record.claimed_at, str)
        assert record.claimed_at != ""

    def test_claim_sets_claimed_at_as_iso_string(self, engine: KanbanEngine) -> None:
        """claimed_at is parseable as an ISO datetime string."""
        task = engine.create_task("ISO timestamp task")
        engine.claim_task(str(task.id))
        record = engine.show_task(str(task.id))
        # datetime.fromisoformat must not raise
        datetime.fromisoformat(record.claimed_at)  # type: ignore[arg-type]

    def test_claim_by_different_agent_raises_when_already_claimed(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """claim_task raises when task is already claimed by a different agent."""
        task = engine.create_task("Contested task")
        engine.claim_task(str(task.id))
        with pytest.raises(Exception):  # noqa: B017, PT011
            rival_engine.claim_task(str(task.id))

    def test_reclaim_by_same_agent_does_not_raise(self, engine: KanbanEngine) -> None:
        """Reclaiming a task already held by the same agent is idempotent."""
        task = engine.create_task("Self-reclaim task")
        engine.claim_task(str(task.id))
        # Must not raise — same agent re-claiming own task
        engine.claim_task(str(task.id))

    def test_claim_raises_for_nonexistent_task(self, engine: KanbanEngine) -> None:
        """claim_task raises when the task ID does not exist."""
        with pytest.raises(Exception):  # noqa: B017, PT011
            engine.claim_task("9999")


# ===========================================================================
# TestFromAC_ReleaseTask — AC4
# ===========================================================================


class TestFromAC_ReleaseTask:
    """Tests for AC4: release_task clears claimed_by and claimed_at to None."""

    def test_release_clears_claimed_by(self, engine: KanbanEngine) -> None:
        """After claim then release, claimed_by is None."""
        task = engine.create_task("Release target")
        engine.claim_task(str(task.id))
        engine.release_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_release_clears_claimed_at(self, engine: KanbanEngine) -> None:
        """After claim then release, claimed_at is None."""
        task = engine.create_task("Release timestamp")
        engine.claim_task(str(task.id))
        engine.release_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_at is None

    def test_release_allows_reclaim_by_rival(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """After release, a different agent can claim the task."""
        task = engine.create_task("Re-claimable task")
        engine.claim_task(str(task.id))
        engine.release_task(str(task.id))
        # Must not raise
        rival_engine.claim_task(str(task.id))
        record = rival_engine.show_task(str(task.id))
        assert record.claimed_by == rival_engine.agent_name

    def test_release_unclaimed_task_does_not_raise(self, engine: KanbanEngine) -> None:
        """Releasing a task that was never claimed does not raise."""
        task = engine.create_task("Never claimed")
        # Must not raise — release is a no-op on an unclaimed task
        engine.release_task(str(task.id))


# ===========================================================================
# TestFromAC_ClaimBlockedTask — AC5
# ===========================================================================


class TestFromAC_ClaimBlockedTask:
    """Tests for AC5: claim on a blocked task is rejected before modifying state."""

    def test_claim_blocked_task_raises(self, engine: KanbanEngine) -> None:
        """claim_task raises when task.blocked is True."""
        task = engine.create_task("Blocked task")
        engine.edit_task(str(task.id), blocked=True, block_reason="Waiting on dependency")
        with pytest.raises(Exception):  # noqa: B017, PT011
            engine.claim_task(str(task.id))

    def test_claim_blocked_task_leaves_claimed_by_none(self, engine: KanbanEngine) -> None:
        """Rejected claim leaves claimed_by unchanged (None)."""
        task = engine.create_task("Blocked — claimed_by guard")
        engine.edit_task(str(task.id), blocked=True, block_reason="Blocked")
        with pytest.raises(Exception):  # noqa: B017, PT011
            engine.claim_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_claim_blocked_task_leaves_claimed_at_none(self, engine: KanbanEngine) -> None:
        """Rejected claim leaves claimed_at unchanged (None)."""
        task = engine.create_task("Blocked — claimed_at guard")
        engine.edit_task(str(task.id), blocked=True, block_reason="Blocked")
        with pytest.raises(Exception):  # noqa: B017, PT011
            engine.claim_task(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_at is None

    def test_claim_unblocked_task_succeeds(self, engine: KanbanEngine) -> None:
        """Unblocked task can be claimed without error."""
        task = engine.create_task("Unblocked task")
        engine.claim_task(str(task.id))
        assert engine.show_task(str(task.id)).claimed_by == engine.agent_name


# ===========================================================================
# TestFromAC_ClaimTimeout — AC6
# ===========================================================================


class TestFromAC_ClaimTimeout:
    """Tests for AC6: expired claim overridable; unexpired claim rejected.

    The ``now`` parameter on claim_task controls the reference time for expiry
    checking, enabling deterministic tests without real sleeps.
    """

    def test_expired_claim_can_be_overridden_by_rival(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """Expired claim (claimed_at + timeout < now) allows a different agent to claim."""
        task = engine.create_task("Timeout task")
        engine.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        # 2h later; claim_timeout=1h → expired
        rival_engine.claim_task(str(task.id), now=_EXPIRED_NOW)
        record = rival_engine.show_task(str(task.id))
        assert record.claimed_by == rival_engine.agent_name

    def test_unexpired_claim_is_rejected_by_rival(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """Unexpired claim (claimed_at + timeout > now) blocks another agent."""
        task = engine.create_task("Fresh claim task")
        engine.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        # 30m later; claim_timeout=1h → still active
        with pytest.raises(Exception):  # noqa: B017, PT011
            rival_engine.claim_task(str(task.id), now=_FRESH_NOW)

    def test_expired_claim_overrider_becomes_new_owner(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """After overriding an expired claim, claimed_by reflects only the new owner."""
        task = engine.create_task("Ownership transfer")
        engine.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        rival_engine.claim_task(str(task.id), now=_EXPIRED_NOW)
        record = rival_engine.show_task(str(task.id))
        assert record.claimed_by == rival_engine.agent_name
        assert record.claimed_by != engine.agent_name

    def test_claim_at_exact_timeout_boundary_is_expired(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """Claim at exactly claimed_at + claim_timeout is considered expired (boundary)."""
        task = engine.create_task("Boundary task")
        engine.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        exact_expiry = _CLAIM_ORIGIN + timedelta(hours=1)
        rival_engine.claim_task(str(task.id), now=exact_expiry)
        record = rival_engine.show_task(str(task.id))
        assert record.claimed_by == rival_engine.agent_name

    def test_claim_just_before_timeout_boundary_is_rejected(
        self, engine: KanbanEngine, rival_engine: KanbanEngine
    ) -> None:
        """Claim at claimed_at + claim_timeout - 1s is still active (boundary)."""
        task = engine.create_task("Near-boundary task")
        engine.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        one_second_before = _CLAIM_ORIGIN + timedelta(hours=1) - timedelta(seconds=1)
        with pytest.raises(Exception):  # noqa: B017, PT011
            rival_engine.claim_task(str(task.id), now=one_second_before)

    def test_claim_timeout_parsed_from_config_minutes(self, tmp_path: Path) -> None:
        """claim_timeout='30m' in config is parsed and applied correctly."""
        config = _BASE_CONFIG_YAML.replace("claim_timeout: 1h", "claim_timeout: 30m")
        (tmp_path / "config.yml").write_text(config, encoding="utf-8")
        (tmp_path / "tasks").mkdir()
        eng1 = KanbanEngine(tmp_path, agent_name="owner-x")
        eng2 = KanbanEngine(tmp_path, agent_name="rival-y")
        task = eng1.create_task("30m timeout task")
        eng1.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        # 35 min later → past 30m timeout → expired
        rival_now = _CLAIM_ORIGIN + timedelta(minutes=35)
        eng2.claim_task(str(task.id), now=rival_now)
        assert eng2.show_task(str(task.id)).claimed_by == eng2.agent_name

    def test_claim_timeout_parsed_from_config_hours_still_blocks(
        self, tmp_path: Path
    ) -> None:
        """claim_timeout='2h' in config; 90m later is still unexpired."""
        config = _BASE_CONFIG_YAML.replace("claim_timeout: 1h", "claim_timeout: 2h")
        (tmp_path / "config.yml").write_text(config, encoding="utf-8")
        (tmp_path / "tasks").mkdir()
        eng1 = KanbanEngine(tmp_path, agent_name="holder-a")
        eng2 = KanbanEngine(tmp_path, agent_name="rival-b")
        task = eng1.create_task("2h timeout task")
        eng1.claim_task(str(task.id), now=_CLAIM_ORIGIN)
        # 90 min later → not past 2h timeout → still active
        rival_now = _CLAIM_ORIGIN + timedelta(hours=1, minutes=30)
        with pytest.raises(Exception):  # noqa: B017, PT011
            eng2.claim_task(str(task.id), now=rival_now)
