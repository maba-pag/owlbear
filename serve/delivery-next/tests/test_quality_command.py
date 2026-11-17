"""The offline lint command sees committed, staged, working and untracked files."""

import sys
from datetime import UTC, datetime
from pathlib import Path

from owlbear_quality import trees

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.commands import cli, project_commands
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import Store


def test_quality_lint_runs_without_host_and_reports_problems_and_broken_tools(
    change_repo: Path,
    monkeypatch,
    capsys,
) -> None:
    trees.git(change_repo, "branch", "baseline")
    (change_repo / "committed.txt").write_text("committed\n")
    trees.git(change_repo, "add", "committed.txt")
    trees.git(change_repo, "commit", "-qm", "work")
    (change_repo / "staged.txt").write_text("staged\n")
    trees.git(change_repo, "add", "staged.txt")
    (change_repo / "committed.txt").write_text("working\n")
    (change_repo / "untracked name.txt").write_text("untracked\n")
    prof = profile.confirm(Profile(), profile.DEFAULT, "baseline", datetime.now(UTC))
    prof = profile.confirm(
        prof,
        profile.LINT,
        f'{sys.executable} -c "import sys; print(sys.argv[1:]); sys.exit(1)"',
        datetime.now(UTC),
    )
    store = Store(change_repo / ".owlbear" / "delivery")
    store.write_profile(prof)
    monkeypatch.setattr(cli.Store, "open", lambda _: store)
    args = project_commands.app.meta(["--repo", str(change_repo), "quality", "lint"])
    assert cli.run(args) == 1
    output = capsys.readouterr().out
    assert all(name in output for name in ("committed.txt", "staged.txt", "untracked name.txt"))
    assert "failed" in output
    prof = profile.confirm(prof, profile.LINT, "nonexistent-quality-command", datetime.now(UTC))
    store.write_profile(prof)
    args = project_commands.app.meta(["--repo", str(change_repo), "quality", "lint", "--base", "baseline"])
    assert cli.run(args) == 2
    assert "could not start" in capsys.readouterr().out
