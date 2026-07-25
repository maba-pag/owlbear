"""Durable PROOF-004 scenarios for native designer resume and refusal behavior."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ruamel.yaml import YAML

from owlbear_kanban import load_change
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CHANGE_ID = "replace-delivery-pipeline"
_CHALLENGED_SECTIONS = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
_CONFIG_YAML = """\
version: 10
board:
  name: DesignerProof
board_dir: .
tasks_dir: tasks
statuses:
- name: shape
- name: build
- name: verify
- name: collect
priorities: [low, medium, high]
defaults:
  status: shape
  priority: medium
claim_timeout: 1h
archive_dir: archive
activity_log: false
agent_map:
  shape: shaper
  build: builder
  verify: verifier
  collect: collector
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed]
status_predicates: {}
"""


def _copy_change(tmp_path: Path, *, pending_decision: bool) -> tuple[Path, object]:
    changes_dir = tmp_path / "changes"
    change_dir = changes_dir / _CHANGE_ID
    shutil.copytree(_REPO_ROOT / ".owlbear" / "changes" / _CHANGE_ID, change_dir)
    shutil.rmtree(change_dir / "receipts")
    shutil.rmtree(change_dir / "jobs")

    if pending_decision:
        yaml = YAML()
        decisions_path = change_dir / "decisions.yaml"
        document = yaml.load(decisions_path.read_text(encoding="utf-8"))
        decision = document["decisions"][1]
        decision["status"] = "pending"
        decision["decided_at"] = None
        decision["selected"] = None
        with decisions_path.open("w", encoding="utf-8") as stream:
            yaml.dump(document, stream)

    loaded = load_change(changes_dir, _CHANGE_ID)
    assert loaded.revision is not None
    return change_dir, loaded.revision


def _context(tmp_path: Path) -> MagicMock:
    board = tmp_path / "kanban"
    board.mkdir()
    (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    context = MagicMock()
    context.request_context.lifespan_context = AppContext(engine=server.KanbanEngine(board), kanban_dir=board)
    return context


def _evidence(revision, *, approval: bool, failing_target: str | None = None) -> dict[str, object]:
    challenge = {
        entity.id: {
            "disposition": "error" if entity.id == failing_target else "pass",
            "evidence": f"source-grounded evidence for {entity.id}",
        }
        for section in _CHALLENGED_SECTIONS
        for entity in getattr(revision.graph, section)
    }
    return {
        "digest": revision.delivery_digest,
        "challenge": challenge,
        "baseline": {"commands": [{"command": "pytest", "exit_code": 0}], "digest": revision.delivery_digest},
        "approval": ({"approved": True, "digest": revision.delivery_digest} if approval else {}),
        "limits": ["designer interaction proof"],
    }


def _publication_snapshot(change_dir: Path, board: Path) -> dict[str, bytes]:
    roots = (change_dir / "receipts", change_dir / "jobs", board / "jobs", board / "archive")
    snapshot = {
        path.relative_to(change_dir.parent.parent).as_posix(): path.read_bytes()
        for root in roots
        if root.exists()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".storage.lock"
    }
    sequence = board / "job-sequence.yaml"
    if sequence.exists():
        snapshot[sequence.relative_to(change_dir.parent.parent).as_posix()] = sequence.read_bytes()
    return snapshot


def _shipped_contracts() -> tuple[str, str, str]:
    prompt = (_REPO_ROOT / "share" / "prompts" / "design.prompt.md").read_text(encoding="utf-8")
    agent = (_REPO_ROOT / "share" / "agents" / "designer.agent.md").read_text(encoding="utf-8")
    workflow = (_REPO_ROOT / "share" / "skills" / "w-design-session" / "SKILL.md").read_text(encoding="utf-8")
    return prompt, agent, workflow


def _normalized(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.asyncio
async def test_design_resume_preserves_authority_and_one_pending_choice(tmp_path: Path) -> None:
    change_dir, revision = _copy_change(tmp_path, pending_decision=True)
    context = _context(tmp_path)
    prompt, agent, workflow = _shipped_contracts()
    intent_before = (change_dir / "intent.md").read_bytes()
    decisions_before = (change_dir / "decisions.yaml").read_bytes()

    first = await server.show_change(context, change_id=_CHANGE_ID)
    resumed = await server.show_change(context, change_id=_CHANGE_ID)

    assert "agent: designer" in prompt
    assert "Enter direct design mode through `w-design-session`" in prompt
    assert "- `w-design-session`" in agent
    assert "read all four authority parts before any mutation" in _normalized(workflow)
    assert first == resumed
    assert first["delivery_digest"] == revision.delivery_digest
    assert first["decisions"]["decisions"][0]["status"] == "accepted"
    assert first["decisions"]["decisions"][1]["status"] == "pending"
    assert (change_dir / "intent.md").read_bytes() == intent_before
    assert (change_dir / "decisions.yaml").read_bytes() == decisions_before

    decision_section = workflow.split("## Step 5 - Resolve One Material Decision", 1)[1].split(
        "## Step 6 - Review Adaptive Architecture", 1
    )[0]
    assert "Use `askQuestions` for exactly one material decision and then stop" in decision_section
    assert all(
        label in decision_section
        for label in (
            "**Status quo:**",
            "**Options:**",
            "**Tradeoffs:**",
            "**Risks:**",
            "**Recommendation:**",
            "**Confidence:**",
        )
    )
    assert "proposed second material choice remains pending" not in decision_section
    assert "fresh read-only specialists" in workflow


@pytest.mark.asyncio
async def test_unresolved_decision_validates_as_draft_without_approval_or_admission(tmp_path: Path) -> None:
    change_dir, revision = _copy_change(tmp_path, pending_decision=True)
    context = _context(tmp_path)
    _prompt, agent, workflow = _shipped_contracts()
    before = _publication_snapshot(change_dir, context.request_context.lifespan_context.kanban_dir)

    shown = await server.show_change(context, change_id=_CHANGE_ID)
    assessment = await server.validate_change(
        context,
        change_id=_CHANGE_ID,
        evidence=_evidence(revision, approval=False),
    )

    errors = [finding for finding in assessment["findings"] if finding["severity"] == "error"]
    pending_id = shown["decisions"]["decisions"][1]["id"]
    assert any(finding["code"] == "DV-010" and finding["target"] == pending_id for finding in errors)
    assert any(finding["code"] == "EV-004" for finding in errors)
    assert "Only the user can resolve material product and architecture choices" in agent
    assert (
        "Ask one final admission question only after the complete candidate and all gate evidence are ready"
        in _normalized(workflow)
    )
    assert "Do not invoke `admit_change`" in _normalized(workflow)
    assert _publication_snapshot(change_dir, context.request_context.lifespan_context.kanban_dir) == before


@pytest.mark.asyncio
async def test_failed_challenge_keeps_resolved_revision_unpublished(tmp_path: Path) -> None:
    change_dir, revision = _copy_change(tmp_path, pending_decision=False)
    context = _context(tmp_path)
    _prompt, _agent, workflow = _shipped_contracts()
    failing_target = revision.graph.requirements[0].id
    evidence = _evidence(revision, approval=True, failing_target=failing_target)
    board = context.request_context.lifespan_context.kanban_dir
    before = _publication_snapshot(change_dir, board)

    shown = await server.show_change(context, change_id=_CHANGE_ID)
    assessment = await server.validate_change(context, change_id=_CHANGE_ID, evidence=evidence)

    errors = [finding for finding in assessment["findings"] if finding["severity"] == "error"]
    assert shown["delivery_digest"] == revision.delivery_digest
    assert {(finding["code"], finding["target"]) for finding in errors} == {("EV-002", failing_target)}
    assert "Record and report the exact finding" in _normalized(workflow)
    assert "A non-pass challenge" in workflow
    assert "Do not invoke `admit_change`" in _normalized(workflow)
    assert _publication_snapshot(change_dir, board) == before
