# ruff: noqa: INP001
"""Create a minimal receipt-authorized target workspace for Cockpit E2E."""

from __future__ import annotations

import argparse
from pathlib import Path

from owlbear_kanban.snapshot import LegacyDisposition, inventory_legacy_source
from owlbear_kanban.target_authority import TargetAuthority
from owlbear_kanban.target_cutover import (
    TargetAdapterRef,
    TargetCutoverClassification,
    TargetCutoverReadiness,
    TargetCutoverRequest,
    TargetCutoverSource,
    TargetCutoverSubjectKind,
    cut_over_target_runtime,
    target_authority_digest,
)

_REVISION = "e" * 64


def seed_workspace(workspace: Path) -> None:
    """Publish one valid target cutover receipt under an isolated workspace."""
    source = workspace / ".owlbear/kanban"
    source.mkdir(parents=True)
    (source / "bootstrap.json").write_text('{"state":"retired"}\n', encoding="utf-8")
    adapter = workspace / ".owlbear/adapters/delivery"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("target\n", encoding="utf-8")

    authority = TargetAuthority(change_id="memory-e2e", title="Memory E2E")
    request = TargetCutoverRequest(
        sources=(
            TargetCutoverSource(
                source_path=".owlbear/kanban",
                snapshot_name="runtime",
                expected_source_digest=inventory_legacy_source(source, (), {}).source_digest,
            ),
        ),
        snapshot_path=".owlbear/legacy/target-cutover",
        target_path=".owlbear/target",
        receipt_path=".owlbear/target-cutover.json",
        adapter_refs=(TargetAdapterRef(relative_path=".owlbear/adapters/delivery", target="target"),),
        authorities=(authority,),
        classifications=(
            TargetCutoverClassification(
                change_id=authority.change_id,
                subject_kind=TargetCutoverSubjectKind.CHANGE,
                subject_id=authority.change_id,
                disposition=LegacyDisposition.REINTRODUCE_NATIVE,
            ),
        ),
        expected_authority_digest=target_authority_digest((authority,)),
        actual_code_revision=_REVISION,
        expected_code_revision=_REVISION,
        readiness=TargetCutoverReadiness(),
        approval="ACTIVATE_TARGET_RUNTIME",
    )
    request_path = workspace / ".owlbear/target-cutover-request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    cut_over_target_runtime(workspace, request, smoke=lambda _root, _request: None)


def main() -> None:
    """Parse the fixture root and seed its target cutover."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    seed_workspace(arguments.workspace.resolve())


if __name__ == "__main__":
    main()
