import subprocess
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import evidence, sdk_adapter, tools
from owlbear_delivery_next.mask import redact
from owlbear_delivery_next.models import Brief, Change, Criterion, Inputs, Names, PersonCheck, Review, Step, StepKind
from owlbear_delivery_next.sdk_adapter import NOW_LIMIT, Journal, summary
from owlbear_delivery_next.steps import check, publish, worktree


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def work(tmp_path):
    """A Change branch over ``main`` that modified a.txt and added b.txt."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "a.txt").write_text("a\n")
    (work / "c.txt").write_text("c\n")
    commit(work, "base")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(work, "switch", "-q", "-c", "owlbear/c1")
    (work / "a.txt").write_text("a2\n")
    (work / "b.txt").write_text("b\n")
    commit(work, "change")
    return work


def commit(work, message):
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", message)
    return git(work, "rev-parse", "HEAD")


def reviewed_change(work) -> Change:
    head = git(work, "rev-parse", "HEAD")
    paths = worktree.observe(work, "main").changed
    review = Review(
        commit=head,
        inputs=Inputs(criteria={"AC-1": 1}, paths=worktree.fingerprints(work, list(paths))),
        verdict="pass",
        tree=worktree.tree(work, head),
    )
    return Change(
        slug="c1",
        brief=Brief(criteria=[Criterion(id="AC-1", text="works")]),
        step=Step(kind=StepKind.PUBLISH),
        names=Names(target="main", worktree=str(work)),
        reviews=[review],
    )


def test_a_review_holds_on_its_head_and_on_a_rebase_with_an_identical_tree(work):
    c = reviewed_change(work)
    assert publish.reviewed(c, work, git(work, "rev-parse", "HEAD"))
    git(work, "commit", "-q", "--amend", "-m", "reworded")
    assert publish.reviewed(c, work, git(work, "rev-parse", "HEAD"))


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda w: (w / "d.txt").write_text("d\n"), id="added-outside-coverage"),
        pytest.param(lambda w: (w / "a.txt").unlink(), id="deleted-covered"),
        pytest.param(lambda w: git(w, "mv", "b.txt", "e.txt"), id="renamed"),
    ],
)
def test_a_review_is_void_when_the_head_leaves_its_coverage(work, edit):
    c = reviewed_change(work)
    edit(work)
    assert not publish.reviewed(c, work, commit(work, "more"))


def test_the_changed_set_names_both_ends_of_a_rename(work):
    base = git(work, "rev-parse", "HEAD")
    git(work, "mv", "c.txt", "f.txt")
    commit(work, "rename")
    assert set(worktree.diff(work, base)) == {"c.txt", "f.txt"}


def test_integrating_a_target_commit_that_adds_a_file_voids_the_final_review(work):
    c = reviewed_change(work)
    git(work, "switch", "-q", "-c", "side", "origin/main")
    (work / "z.txt").write_text("z\n")
    commit(work, "target adds z")
    git(work, "switch", "-q", "owlbear/c1")
    git(work, "merge", "-q", "--no-edit", "side")
    head = git(work, "rev-parse", "HEAD")
    assert "z.txt" in worktree.between(work, c.reviews[-1].tree, head)
    assert not publish.reviewed(c, work, head)


def test_a_mode_change_voids_a_fingerprint(work):
    before = worktree.fingerprints(work, ["a.txt"])
    (work / "a.txt").chmod(0o755)
    commit(work, "chmod")
    after = worktree.fingerprints(work, ["a.txt"])
    assert before["a.txt"].startswith("100644 blob")
    assert after["a.txt"].startswith("100755 blob")


def test_fingerprints_name_spaces_unicode_absence_and_more_than_200_paths(work):
    names = ["with space.txt", "ünï cødé.txt", *(f"many/{i}.txt" for i in range(250))]
    (work / "many").mkdir()
    for name in names:
        (work / name).write_text(name)
    commit(work, "many")
    prints = worktree.fingerprints(work, [*names, "gone.txt"])
    assert all(prints[n].startswith("100644 blob ") for n in names)
    assert (len(prints), prints["gone.txt"]) == (len(names) + 1, "")
    assert len(worktree.fingerprints(work, ["many"])) == 250


def test_a_code_review_over_more_than_200_changed_paths_needs_no_listing(work):
    for i in range(250):
        (work / f"n{i}.txt").write_text(str(i))
    commit(work, "wide")
    c = reviewed_change(work)
    assert len(c.reviews[-1].inputs.paths) > 200
    assert publish.reviewed(c, work, git(work, "rev-parse", "HEAD"))
    tree = SimpleNamespace(changed=[f"n{i}.txt" for i in range(250)])
    review = tools.ReviewResult(verdict="pass")
    assert tools.check_review(review, tree) == []
    assert tools.check_review(review, tree, visual=True) != []


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        pytest.param("Authorization: token abc123def", "abc123def", id="authorization-any-scheme"),
        pytest.param("git clone https://ada:pa55w0rd@github.com/x", "pa55w0rd", id="url-userinfo"),
        pytest.param("curl -H 'X-Api-Key: k3yv4lue' --header=\"Cookie: s=c00kie\"", "k3yv4lue", id="header-flag"),
        pytest.param("GH_TOKEN=unquoted1 x", "unquoted1", id="assignment-unquoted"),
        pytest.param("DB_PASSWORD='quoted two'", "quoted two", id="assignment-quoted"),
        pytest.param("echo ghp_abcdefghijklmnop github_pat_11AAbb", "ghp_abcdefghijklmnop", id="github-token"),
        pytest.param("sig=" + "ab12" * 10, "ab12" * 10, id="hex-blob"),
        pytest.param("data: " + "QUJD" * 10 + "==", "QUJD" * 10, id="base64-blob"),
    ],
)
def test_redact_masks_each_credential_pattern(text, secret):
    out = redact(text)
    assert secret not in out
    assert "***" in out


def test_redact_keeps_the_host_of_a_url_with_userinfo_and_ordinary_text():
    assert redact("https://ada:pw@github.com/x") == "https://***@github.com/x"
    assert redact("uv run pytest -q tests/a.py") == "uv run pytest -q tests/a.py"
    assert "github_pat_11AAbb" not in redact("github_pat_11AAbb")
    assert "c00kie" not in redact("curl --header='Cookie: s=c00kie'")


@pytest.mark.parametrize(
    ("paths", "touched", "valid"),
    [(["a.txt"], "a.txt", False), (["a.txt"], "c.txt", True), ([], "c.txt", False)],
    ids=["its-input-changed", "disjoint-change", "no-declared-inputs"],
)
def test_a_check_answer_binds_to_its_inputs(work, paths, touched, valid):
    c = reviewed_change(work)
    person = PersonCheck(id="p1", criteria=["AC-1"], paths=paths)
    recorded = evidence.check_inputs(c, person, check.fingerprints(c, person))
    (work / touched).write_text("changed\n")
    commit(work, "touch")
    assert evidence.check_valid(recorded, evidence.check_inputs(c, person, check.fingerprints(c, person))) is valid


def test_the_now_line_summarises_redacts_and_caps_a_tool_call():
    line = summary("bash", {"command": "curl -H 'Authorization: Bearer abc123' https://x/?token=s3cret ghp_abcdef12"})
    assert line.startswith("ran curl")
    assert not {"abc123", "s3cret", "ghp_abcdef12"} & set(line.replace("'", " ").replace("=", " ").split())
    assert "token=***" in line
    assert summary("view", {"path": "src/x.py"}) == "view src/x.py"
    long = summary("view", {"path": "d/" * 60})
    assert len(long) == NOW_LIMIT
    assert long.endswith("…")


def test_tool_events_write_the_now_line_at_most_once_a_second(monkeypatch):
    writes, clock = [], [100.0]
    step = object.__new__(sdk_adapter._Step)  # noqa: SLF001 - the SDK event handler under test
    step.cfg, step.shown = SimpleNamespace(journal=Journal(now=writes.append)), float("-inf")
    monkeypatch.setattr(sdk_adapter.time, "monotonic", lambda: clock[0])

    def tool_event(at, path):
        clock[0] = at
        data = SimpleNamespace(tool_name="view", arguments={"path": path})
        step.on_event(SimpleNamespace(type="tool.execution_start", data=data))

    tool_event(100.0, "one.py")
    tool_event(100.5, "two.py")
    tool_event(101.2, "three.py")
    assert [w["summary"] for w in writes] == ["view one.py", "view three.py"]
    assert all({"tool", "summary", "at"} <= w.keys() for w in writes)
