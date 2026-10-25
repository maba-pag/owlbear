"""The memory package's pre-flight selection: recall's eligibility, a deterministic ranking and a hard budget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_memory import MemoryEntry, MemoryState, selection, storage

if TYPE_CHECKING:
    from pathlib import Path


def entry(n: int, **fields: object) -> MemoryEntry:
    data: dict[str, object] = {
        "id": f"550e8400-e29b-41d4-a716-4466554{n:05d}",
        "title": f"Lesson {n}",
        "content": f"Body {n}.",
        "categories": ["pitfall"],
        "confidence": 0.8,
        "state": MemoryState.APPROVED,
        "score": 0.8,
        "scope_agents": ["builder"],
        "source_agent": "planner",
        "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-01T10:00:00Z",
    }
    return MemoryEntry.model_validate(data | fields)


def ids(found: list[selection.Candidate] | tuple[selection.Candidate, ...]) -> list[int]:
    return [int(c.entry.id[-5:]) for c in found]


def test_eligibility_is_recalls_states_and_relevance_scope_never_authorship() -> None:
    states = {s: entry(1, state=s) for s in MemoryState}
    assert {s for s, e in states.items() if selection.eligible(e, "builder")} == {"approved", "curated", "contested"}
    assert not selection.eligible(entry(1, scope_agents=["reviewer"], source_agent="builder"), "builder")
    assert selection.eligible(entry(1, scope_agents=["*"]), "builder")
    assert not selection.eligible(entry(1, scope_agents=[]), "builder")
    assert selection.eligible(entry(1, scope_agents=["*"]), None)
    assert not selection.eligible(entry(1, scope_agents=["builder"]), None)  # an unrecognised caller
    assert not selection.eligible(entry(1, scope_agents=["builder"]), "*")


def test_global_memory_adds_only_the_ids_the_project_does_not_hold() -> None:
    project, shared = [entry(1, title="mine")], [entry(1, title="theirs"), entry(2)]
    found = selection.readable(project, shared)
    assert [(e.title, where) for e, where in found] == [("mine", "project"), ("Lesson 2", "global")]


def test_the_ranking_is_specificity_then_score_then_recency_then_id() -> None:
    late = "2026-10-05T10:00:00+02:00"
    found = [
        (entry(1, scope_agents=["*"], score=1.5), "project"),  # every agent's: after all of the role's own
        (entry(2, score=0.7), "global"),  # the role's own in Global memory: after the project's
        (entry(3, score=0.8), "project"),
        (entry(4, score=0.9), "project"),  # higher score first
        (entry(5, score=0.8, updated_at=late), "project"),  # same score: the more recent first
        (entry(6, scope_agents=["*", "builder"]), "project"),  # names the role: specific
        (entry(7, scope_agents=["*"]), "global"),
    ]
    assert ids(selection.ranked(found, "builder")) == [4, 5, 3, 6, 2, 1, 7]
    assert ids(selection.ranked(list(reversed(found)), "builder")) == [4, 5, 3, 6, 2, 1, 7]  # deterministic


def test_whole_entries_up_to_the_cap_skip_what_does_not_fit_and_fill_no_quota() -> None:
    sizes = {1: 50, 2: 900, 3: 30, 4: 30, 5: 30, 6: 30, 7: 30}
    found = [(entry(n, score=1.0 - n / 100), "project") for n in sizes]
    picked = selection.select(found, "builder", cost=lambda c: sizes[int(c.entry.id[-5:])], room=200)
    assert ids(picked.chosen) == [1, 3, 4, 5, 6]  # 2 is skipped whole; the cap of 5 ends the selection
    assert ids(picked.omitted) == [2]
    assert selection.CAP == 5
    assert selection.BUDGET == 2000
    assert selection.select([], "builder", cost=len, room=200) == selection.Selection((), ())


def test_a_memory_folder_is_read_as_recall_reads_it_and_a_missing_one_holds_nothing(tmp_path: Path) -> None:
    assert selection.stored(tmp_path / "absent") == []
    assert not (tmp_path / "absent").exists()  # reading never creates the folder
    e = entry(1)
    storage.write_entry(tmp_path / f"{e.id}.md", e, memory_dir=tmp_path)
    (tmp_path / "broken.md").write_text("not a memory")
    assert [x.id for x in selection.stored(tmp_path)] == [e.id]
