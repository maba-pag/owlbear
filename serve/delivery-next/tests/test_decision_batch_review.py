"""Regressions for the review findings on the decision-batch journal: the Git folder probe, the absent-parent Abandon,
and a publication whose outcome is not a known refusal.

Each test drives the real temporary repository; only the probe output or the directory fsync is faulted.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_batch, decision_transaction


def test_an_empty_git_folder_answer_with_success_is_a_journal_error(shared_repo, monkeypatch):
    def empty(_self, *_args: str, until: float | None = None) -> subprocess.CompletedProcess[str]:
        assert until is None
        return subprocess.CompletedProcess(args=(), returncode=0, stdout="\n", stderr="")

    monkeypatch.setattr(DataRepo, "git", empty)
    with pytest.raises(decision_batch.JournalError, match="cannot be found"):
        decision_batch._admin(DataRepo(shared_repo[0]))  # noqa: SLF001 - the probe itself is the regression


def test_the_git_folder_of_a_real_repository_is_still_found(shared_repo):
    admin = decision_batch._admin(DataRepo(shared_repo[0]))  # noqa: SLF001
    assert admin.is_absolute()
    assert (admin / "HEAD").is_file()


def test_abandoning_a_new_file_in_an_absent_folder_fsyncs_nothing(tmp_path, monkeypatch):
    synced: list[object] = []
    monkeypatch.setattr(decision_batch, "fsync_dir", synced.append)
    monkeypatch.setattr(os, "fsync", synced.append)
    absent = tmp_path / "decisions" / "new.md"

    decision_batch.replace_file(absent, None)

    assert synced == []
    assert not absent.parent.exists()


@pytest.mark.parametrize("refused", [False, True], ids=["unknown", "known-refusal"])
def test_settlement_requires_a_known_refusal_or_exact_landing(shared_repo, refused):
    shared = DataRepo(shared_repo[0])
    shared.claim("shop-site", "github.com/acme/shop-site")
    target = shared.root / "shop-site" / "changes" / "note.json"
    target.parent.mkdir(parents=True)

    def outcome(_head: str, _fence) -> decision_transaction.Step:
        if not refused:
            target.write_text("{}", encoding="utf-8")
        return decision_transaction.Step("the commit was refused" if refused else "", refused=refused)

    head = shared.git("rev-parse", "HEAD").stdout.strip()
    notice = decision_transaction.transaction(shared, "shop-site", "changes: outcome", [(target, b"{}")], outcome, head)
    assert shared.git("rev-parse", "HEAD").stdout.strip() == head
    if refused:
        assert notice == "the commit was refused"
        assert decision_batch.pending(shared) is None
        assert not target.exists()
    else:
        assert notice.startswith("interrupted batch"), notice
        assert decision_batch.pending(shared) is not None
        assert target.read_bytes() == b"{}"
