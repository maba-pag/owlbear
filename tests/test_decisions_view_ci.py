from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
VIEW = ROOT / ".owlbear/decisions.md"
SCRIPT = ROOT / ".github/scripts/decisions_view_hash.py"
WORKFLOWS = ROOT / ".github/workflows"
GRANT = "secrets.OWLBEAR_DATA_TOKEN"
_SPEC = importlib.util.spec_from_file_location("decisions_view_hash", SCRIPT)
view_hash = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(view_hash)


def _check(path: Path) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), str(path)]
    return subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argument vector


def test_the_committed_view_passes_its_hash_check() -> None:
    assert _check(VIEW).returncode == 0
    assert view_hash.problem(VIEW.read_bytes()) == ""


def test_the_hash_check_finds_a_hand_edit_and_a_missing_hash(tmp_path: Path) -> None:
    edited = tmp_path / "edited.md"
    view = VIEW.read_bytes()
    edited.write_bytes(view.replace(b"# Decisions", b"# Decisionz", 1))  # a heading every view has
    assert edited.read_bytes() != view
    cut = tmp_path / "cut.md"
    cut.write_bytes(view.rsplit(b"<!--", 1)[0])

    for path, message in ((edited, "edited by hand"), (cut, "last line")):
        done = _check(path)
        assert done.returncode == 1, path
        assert message in done.stderr
        assert "regenerates it by pull request" in done.stderr


def test_the_hash_covers_every_byte_above_the_last_line() -> None:
    body = b"# View\n\nA rule.\n\n"
    line = f"<!-- decisions-view sha256:{hashlib.sha256(body).hexdigest()} -->\n".encode()

    assert view_hash.problem(body + line) == ""
    assert view_hash.problem(body.replace(b"rule", b"rules") + line)
    assert view_hash.problem(body + line.rstrip(b"\n"))


def test_pull_request_ci_runs_the_hash_check_as_a_config_hook() -> None:
    """Static runs every config hook no leaf claims (TD-409), so the view's hash needs no data token in CI."""
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [hook for repo in config["repos"] if repo["repo"] == "local" for hook in repo["hooks"]]
    hook = next(hook for hook in hooks if hook["id"] == "decisions-view-hash")

    assert hook["entry"] == "python3 .github/scripts/decisions_view_hash.py"
    assert hook["files"] == r"^\.owlbear/decisions\.md$"
    assert "pass_filenames" not in hook


def test_only_the_decisions_view_workflow_holds_the_data_token_on_push_to_main_and_a_schedule() -> None:
    text = (WORKFLOWS / "decisions-view.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    steps = workflow["jobs"]["fresh"]["steps"]
    checkouts = [step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")]

    assert triggers.keys() == {"push", "schedule"}
    assert triggers["push"] == {"branches": ["main"]}
    assert workflow["permissions"] == {"contents": "read"}
    assert "permissions" not in workflow["jobs"]["fresh"]
    assert [step["with"]["persist-credentials"] for step in checkouts] == [False, False]
    assert checkouts[1]["with"]["repository"] == "maba-pag/owlbear-data"
    assert checkouts[1]["with"]["token"] == f"${{{{ {GRANT} }}}}"
    assert text.count(GRANT) == 1
    run = steps[-1]["run"]
    assert "decisions-view owlbear-data --project owlbear --out .owlbear/decisions.md --check" in run
    assert not any(word in text for word in ("git push", "gh pr", "pull_request", "contents: write"))
    for other in WORKFLOWS.glob("*.yml"):
        if other.name != "decisions-view.yml":
            assert "OWLBEAR_DATA_TOKEN" not in other.read_text(encoding="utf-8"), other.name
