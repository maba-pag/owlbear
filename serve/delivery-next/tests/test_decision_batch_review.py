"""Regressions for the review findings on the decision-batch journal: the Git folder probe, the absent-parent Abandon,
and a publication whose outcome is not a known refusal.

Each test drives the real temporary repository; only the probe output or the directory fsync is faulted.
"""

from __future__ import annotations

import subprocess

import pytest

from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_transaction


def test_an_empty_git_folder_answer_with_success_is_a_journal_error(picking, monkeypatch):
    def empty(_self, *_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=(), returncode=0, stdout="\n", stderr="")

    monkeypatch.setattr(DataRepo, "git", empty)
    with pytest.raises(decision_batch.JournalError, match="cannot be found"):
        decision_batch._admin(picking.shared)  # noqa: SLF001 - the probe itself is the regression


def test_the_git_folder_of_a_real_repository_is_still_found(picking):
    admin = decision_batch._admin(picking.shared)  # noqa: SLF001
    assert admin.is_absolute()
    assert (admin / "HEAD").is_file()


def test_abandoning_a_new_file_in_an_absent_folder_fsyncs_nothing(tmp_path, monkeypatch):
    synced: list[object] = []
    monkeypatch.setattr(decision_batch, "fsync_dir", synced.append)
    absent = tmp_path / "decisions" / "new.md"

    decision_batch.replace_file(absent, None)

    assert synced == []
    assert not absent.parent.exists()


def test_removing_a_file_from_an_existing_folder_still_fsyncs_its_parent(tmp_path, monkeypatch):
    synced: list[object] = []
    monkeypatch.setattr(decision_batch, "fsync_dir", synced.append)
    folder = tmp_path / "decisions"
    folder.mkdir()
    (folder / "old.md").write_text("x", encoding="utf-8")

    decision_batch.replace_file(folder / "old.md", None)

    assert not (folder / "old.md").exists()
    assert synced == [folder]


def test_an_empty_publication_outcome_is_not_a_known_refusal_and_stays_interrupted(picking):
    shared = picking.shared
    target = shared.root / "shop-site" / "changes" / "note.json"
    target.parent.mkdir(parents=True)

    def silent(_head: str, _fence) -> decision_transaction.Step:
        target.write_text("{}", encoding="utf-8")
        return decision_transaction.Step("")  # success-looking, no landing proof, no refusal

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    notice = decision_transaction.transaction(shared, "shop-site", "changes: silent", [(target, b"{}")], silent, head)

    assert notice.startswith("interrupted batch"), notice
    assert decision_batch.pending(shared) is not None
    assert target.is_file()  # never restored or completed on a guess


def test_a_known_refusal_with_unmoved_head_puts_the_files_back_and_completes(picking):
    shared = picking.shared
    target = shared.root / "shop-site" / "changes" / "refused.json"
    target.parent.mkdir(parents=True)

    def refused(_head: str, _fence) -> decision_transaction.Step:
        return decision_transaction.Step("the commit was refused", refused=True)

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    notice = decision_transaction.transaction(shared, "shop-site", "changes: refused", [(target, b"{}")], refused, head)

    assert notice == "the commit was refused"
    assert decision_batch.pending(shared) is None
    assert not target.exists()
