"""Canonical consumer distribution inventory for the target control plane."""

from __future__ import annotations

import json
from pathlib import Path
import re

from owlbear_kanban import LegacyDisposition, verify_legacy_snapshot


_ROOT = Path(__file__).parent.parent

_RETIRED_PATHS = (
    Path(".github/prompts/opsx-apply.prompt.md"),
    Path(".github/prompts/opsx-archive.prompt.md"),
    Path(".github/prompts/opsx-explore.prompt.md"),
    Path(".github/prompts/opsx-propose.prompt.md"),
    Path(".github/prompts/opsx-sync.prompt.md"),
    Path(".github/prompts/opsx-update.prompt.md"),
    Path(".github/skills/openspec-apply-change"),
    Path(".github/skills/openspec-archive-change"),
    Path(".github/skills/openspec-explore"),
    Path(".github/skills/openspec-propose"),
    Path(".github/skills/openspec-sync-specs"),
    Path(".github/skills/openspec-update-change"),
    Path("openspec"),
    Path("seed/openspec"),
    Path("setup/openspec.py"),
    Path("tests/test_openspec_setup.py"),
)

_SHIPPED_OWNERS = {
    "share": Path("share"),
    "serve": Path("serve"),
    "setup": Path("setup"),
    "seed": Path("seed"),
    "infra": Path(".github/workflows/sync-to-main.yml"),
}

_SHIPPED_DIAGRAMS = {
    "mcp-topology.excalidraw",
    "mcp-topology.png",
    "memory-layers.excalidraw",
    "memory-layers.png",
}

_MAINTAINED_DOC_CONTRACTS = {
    Path("README.md"): (".owlbear/target/", "plan, build, and conditional assembly"),
    Path("README-consumer.md"): ("/design", "/orchestrate", "OWLBEAR_WORKSPACE_ROOT"),
    Path("SECURITY.md"): ("## Supported Versions", "## Reporting a Vulnerability", "## Disclosure Policy"),
    Path("setup/setup-guide.md"): ("## Target Delivery Workflow", "setup/finalize.py"),
    Path("setup/sharing-guide.md"): (".owlbear/target/changes/", "Immutable legacy inventory"),
    Path("share/README.md"): ("## Product Boundary", "WIRING.md"),
    Path("share/WIRING.md"): ("planner", "builder", "build-reviewer", "orchestrator"),
}

_MARKDOWN_LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")

_LEGACY_OPENSPEC_ITEMS = {
    "openspec:complete-browser-content-acquisition",
    "openspec:expose-memory-lifecycle-in-cockpit",
    "openspec:purge-deleted-memories",
    "openspec:redesign-workspace-health",
}


def test_retired_openspec_artifacts_are_absent() -> None:
    assert all(not (_ROOT / path).exists() for path in _RETIRED_PATHS)


def test_retired_openspec_history_is_hash_verified_and_immutable() -> None:
    snapshot = verify_legacy_snapshot(_ROOT / ".owlbear/legacy/openspec-final")
    dispositions = {item.item_id: item.disposition for item in snapshot.manifest.active_items}

    assert set(dispositions) == _LEGACY_OPENSPEC_ITEMS
    assert set(dispositions.values()) == {LegacyDisposition.COMPLETED_HISTORY}
    assert snapshot.manifest.file_count == 22


def test_consumer_sync_scopes_have_current_target_owners() -> None:
    workflow = (_ROOT / ".github/workflows/sync-to-main.yml").read_text(encoding="utf-8")

    assert all((_ROOT / path).exists() for path in _SHIPPED_OWNERS.values())
    assert "share serve setup seed" in workflow
    assert "README-consumer.md" in workflow
    assert "serve/cockpit/dist/" in workflow
    assert "serve/cockpit/web/" in workflow
    assert not any((_ROOT / ".github/prompts").glob("opsx-*.prompt.md"))
    assert not any((_ROOT / ".github/skills").glob("openspec-*"))

    mcp = json.loads((_ROOT / "seed/.vscode/mcp.json").read_text(encoding="utf-8"))
    assert set(mcp["servers"]) == {"ob-kanban", "ob-knowledge", "ob-memory", "ob-browser", "markitdown"}
    assert {path.name for path in (_ROOT / "share/diagrams").iterdir()} == _SHIPPED_DIAGRAMS


def test_maintained_docs_have_target_contracts_and_valid_local_links() -> None:
    for relative_path, required_phrases in _MAINTAINED_DOC_CONTRACTS.items():
        path = _ROOT / relative_path
        content = path.read_text(encoding="utf-8")
        assert all(phrase in content for phrase in required_phrases)

        for target in _MARKDOWN_LINK.findall(content):
            if target.startswith(("#", "http://", "https://")):
                continue
            local_target = target.split("#", maxsplit=1)[0]
            assert (path.parent / local_target).exists(), f"broken link in {relative_path}: {target}"
