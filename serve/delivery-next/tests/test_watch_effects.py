"""The watcher's shell effects (W1b-1): the lexer, the working directory, the verified core, heredocs and symlinks."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import watch_effects as we
from owlbear_delivery_next.change_contracts.watch_effects import (
    CWD,
    EARLIER_CWD,
    EARLIER_ENV,
    ENV,
    FORM,
    HEREDOC,
    LINK,
    PATTERN,
    PROGRAM,
    RECURSIVE,
    STARTUP,
    SYNTAX,
    VARIABLE,
    Evidence,
    Shell,
    effects,
)


@pytest.fixture
def fs(tmp_path):
    """A worktree with links out of it, and an outside folder with a protected file and links into the worktree."""
    own, outside, home, tmp = tmp_path / "wt", tmp_path / "outside", tmp_path / "home", tmp_path / "T"
    for folder in (own / "sub", own / "dest", outside / "dir", home, tmp):
        folder.mkdir(parents=True)
    (outside / "protected.txt").write_text("keep")
    (own / "a.txt").write_text("a")
    (own / "out_dir").symlink_to(outside / "dir")
    (own / "out_file").symlink_to(outside / "protected.txt")
    (outside / "in_dir").symlink_to(own / "sub")
    (outside / "in_file").symlink_to(own / "a.txt")
    (own / "dest" / "a.txt").symlink_to(outside / "protected.txt")  # cp a.txt dest/ would write through it
    return {"own": own.resolve(), "outside": outside.resolve(), "home": home, "tmp": tmp}


def run(fs, text: str, evidence: Evidence | None = None, **earlier) -> we.Effects:
    return effects(text, Shell(fs["own"], fs["home"], fs["tmp"], **earlier), evidence)


def seen(fs, text: str, evidence: Evidence | None = None, **earlier) -> tuple[list[tuple[str, str]], list[str]]:
    """Targets as (kind, path relative to the worktree, else "@outside/...", else absolute) and the reasons."""
    found = run(fs, text, evidence, **earlier)
    return [(t.kind, _short(fs, t.path)) for t in found.targets], list(found.unresolved)


def _short(fs, path: Path) -> str:
    for name, root in (("", fs["own"]), ("@outside", fs["outside"]), ("~", fs["home"].resolve())):
        if path.is_relative_to(root):
            rel = str(path.relative_to(root))
            return f"{name}/{rel}" if name else rel
    return str(path)


@pytest.mark.parametrize(
    "text",
    [
        "printf '%s\\n' '>' /x",
        "echo \"a > b\" '&&' c",
        "echo a\\> /x",
        "echo '|' \"&\" \\; '2>' x",
        'echo ">/x"',
        "cat <<'EOF'\n> /x\nEOF",
    ],
)
def test_quoted_or_escaped_operators_are_words_not_redirections(fs, text) -> None:
    found = run(fs, text)
    assert (found.targets, found.unresolved, found.redirects) == ((), (), False)


@pytest.mark.parametrize(
    ("text", "targets"),
    [
        ("echo x > o", ["o"]),
        ("echo x >> o", ["o"]),
        ("echo x >| o", ["o"]),
        ("make &> o", ["o"]),
        ("make &>> o", ["o"]),
        ("make 2> o", ["o"]),
        ("make 2>> o", ["o"]),
        ("echo 1>o", ["o"]),
        ("cat <> o", ["o"]),
        ("echo >& o", ["o"]),
        ("echo x a2>o", ["o"]),  # a2 is a word: stdout goes to o
        ("cat < in", []),
        ("echo x 2>&1", []),
        ("echo x >&2", []),
        ("echo x > /dev/null 2>/dev/stderr", []),
        ("echo x >/dev/fd/3", []),
        ("cat <<< word", []),
    ],
)
def test_redirections_that_write_are_identified_and_the_others_are_not(fs, text, targets) -> None:
    found, _ = seen(fs, text)
    assert found == [("write", t) for t in targets]


def test_newline_separated_commands_are_each_classified(fs) -> None:
    assert seen(fs, "touch a\ntouch b\n\n# touch c\ntouch d # e") == ([("write", p) for p in ("a", "b", "d")], [])
    assert seen(fs, "touch a \\\n b") == ([("write", "a"), ("write", "b")], [])  # a continued line


@pytest.mark.parametrize(
    "text",
    [
        "echo $(pwd) > o",
        "echo `pwd`",
        'echo "$(pwd)"',
        'echo "`pwd`"',
        "diff <(ls) x",
        "tee >(cat) < x",
        "(cd sub && touch a)",
        "{ touch a; }",
        "if true; then touch a; fi",
        "for f in a b; do touch $f; done",
        "while true; do break; done",
        "until false; do break; done",
        "case x in x) touch a;; esac",
        "function f { touch a; }",
        "f() { touch a; }",
        "eval touch a",
        "source env.sh",
        ". env.sh",
        "[[ a > b ]] && touch c",
        "echo $((1 + 2))",
        "echo $'a\\tb'",
        "echo 'open",
        'echo "open',
        "touch a &&",
        "touch >",
        "touch a && && touch b",
        "sh -c 'echo $(pwd)'",
        "touch a; command eval touch b",
    ],
)
def test_every_structural_construct_leaves_the_whole_call_unresolved(fs, text) -> None:
    found = run(fs, text)
    assert (found.targets, found.unresolved, found.moves, found.changes) == ((), (SYNTAX,), True, we.WATCHED)
    covered = run(fs, text, Evidence(every=True))  # the runtime's marks never cover text the lexer could not read
    read = any(w in {"eval", "source", "."} for w in text.split())  # read, but running text the watcher never sees
    assert (covered.unresolved, covered.moves, covered.changes) == (() if read else (SYNTAX,), True, we.WATCHED)


@pytest.mark.parametrize(
    ("text", "targets", "reasons"),
    [
        ("cd sub && touch a", ["sub/a"], []),
        ("cd sub && touch a && touch b", ["sub/a", "sub/b"], []),
        ("cd sub && touch a; touch b", ["sub/a"], [CWD]),
        ("cd /x; touch a", [], [CWD]),  # the cd may have failed
        ("cd sub\ntouch a", [], [CWD]),
        ("cd sub &&\ntouch a", ["sub/a"], []),
        ("cd sub || touch a", [], [CWD]),
        ("cd sub | touch a", [], [CWD]),
        ("cd sub & touch a", [], [CWD]),
        ("ls | cd sub && touch a", [], [PROGRAM, CWD]),  # a cd in a pipeline moves nothing here
        ("true || cd sub && touch a", [], [CWD]),
        ('cd "$DIR" && touch a', [], [CWD]),
        ("cd sub other && touch a", [], [CWD]),
        ("cd - && touch a", [], [CWD]),
        ("pushd sub && touch a", [], [CWD]),
        ("popd && touch a", [], [CWD]),
        ("command cd sub && touch a", [], [CWD]),
        ("cd sub && cd .. && touch a", ["a"], []),
        ("cd /x; cd {own}/sub && touch a", ["sub/a"], []),  # an absolute cd restores what follows it
        ("cd sub; touch {own}/b", ["b"], []),  # absolute targets stay identified
        ("touch a; cd sub", ["a"], []),
        ("cd && touch a", ["~/a"], []),
        ("cd ~ && touch a", ["~/a"], []),
        ("env -C sub touch a", [], [CWD]),
        ("env --chdir=sub touch {own}/b && touch c", ["b", "c"], []),
        ("sh -c 'cd sub && touch a' && touch b", ["sub/a", "b"], []),  # a nested script exports nothing
        ("cd sub && sh -c 'touch a; cd .. && touch b'", ["sub/a", "b"], []),
    ],
)
def test_cd_moves_the_working_directory_only_through_and_chains(fs, text, targets, reasons) -> None:
    assert seen(fs, text.format(own=fs["own"])) == ([("write", t) for t in targets], reasons)


@pytest.mark.parametrize("quoting", ["'EOF'", '"EOF"', "\\EOF", "E'OF'"])
def test_a_quoted_heredoc_is_literal_and_an_unquoted_one_that_substitutes_is_unresolved(fs, quoting) -> None:
    payload = "hello $(whoami) `id`\nrm -rf / > /etc/passwd\n"
    assert seen(fs, f"cat > note.md <<EOF\n{payload}EOF\ntouch b") == (
        [("write", "note.md"), ("write", "b")],
        [HEREDOC],
    )
    assert seen(fs, f"cat > note.md <<{quoting}\n{payload}EOF\ntouch b") == ([("write", "note.md"), ("write", "b")], [])
    assert seen(fs, "cat > note.md <<EOF\nhome is $HOME, ${USER}\nEOF") == ([("write", "note.md")], [])
    assert seen(fs, "cat <<-EOF > note.md\n\tbody `x`\n\tEOF\ntouch b") == (
        [("write", "note.md"), ("write", "b")],
        [HEREDOC],
    )
    assert seen(fs, "cat > x <<A > y <<'B'\n$(a)\nA\n$(b)\nB\ntouch c")[0] == [("write", p) for p in "xyc"]


@pytest.mark.parametrize(
    ("text", "targets", "reasons"),
    [
        ("touch a b", [("write", "a"), ("write", "b")], []),
        ("touch -c a", [("write", "a")], []),
        ("touch -d 2020 a", [], [FORM]),
        ("mkdir -p sub/x/y", [("write", "sub/x/y")], []),
        ("mkdir new", [("write", "new")], []),
        ("mkdir -m 700 new", [], [FORM]),
        ("mkdir --parents new", [], [FORM]),
        ("rm a.txt", [("remove", "a.txt")], []),
        ("rm -rf build -- -x", [("remove", "build"), ("remove", "-x")], []),
        ("rm -fr build", [("remove", "build")], []),
        ("rm -R -f build", [("remove", "build")], []),
        ("rm -v a", [], [FORM]),
        ("rm -i a", [], [FORM]),
        ("rm --recursive a", [], [FORM]),
        ("rmdir sub", [("remove", "sub")], []),
        ("rmdir -p sub", [], [FORM]),
        ("unlink a.txt", [("remove", "a.txt")], []),
        ("cp a.txt b.txt", [("write", "b.txt")], []),
        ("cp -p -f a.txt b.txt", [("write", "b.txt")], []),
        ("cp a.txt sub", [("write", "sub/a.txt")], []),
        ("cp a.txt x.txt sub/", [("write", "sub/a.txt"), ("write", "sub/x.txt")], []),
        ("cp -a a.txt b.txt", [], [FORM]),
        ("cp -t sub a.txt", [], [FORM]),
        ("cp -T a.txt b", [], [FORM]),
        ("cp a.txt", [], []),
        ("mv a.txt b.txt", [("remove", "a.txt"), ("write", "b.txt")], []),
        ("mv -f a.txt sub", [("remove", "a.txt"), ("write", "sub/a.txt")], []),
        ("mv -n a.txt b", [], [FORM]),
        ("mv -t sub a.txt", [], [FORM]),
        ("tee a b", [("write", "a"), ("write", "b")], []),
        ("tee -a log", [("write", "log")], []),
        ("tee -i log", [], [FORM]),
        ("cat a.txt | tee -a log > /dev/null", [("write", "log")], []),
        ("cat a.txt b.txt", [], []),
        ("echo hi; printf x; pwd; true; false; :; test -f a; [ -f a ]; sleep 1; exit 0", [], []),
        ("export A=1 && unset B && set -e", [], []),
        ("A=1 B=2", [], []),
        ("A=1 touch a", [("write", "a")], []),
        ("! touch a", [("write", "a")], []),
        ("time touch a", [("write", "a")], []),
    ],
)
def test_the_verified_core_identifies_its_forms_and_leaves_every_other_option_unresolved(
    fs, text, targets, reasons
) -> None:
    assert seen(fs, text) == (targets, reasons)


@pytest.mark.parametrize(
    "text",
    [
        "sed -i s/a/b/ a.txt",
        "ln -s a.txt b",
        "chmod +x a.txt",
        "dd if=a.txt of=b",
        "curl -o b https://x",
        "git status",
        "git commit -m x",
        "rsync -a a b",
        "install a.txt b",
        "truncate -s 0 a.txt",
        "uniq a.txt b.txt",
        "python3 -c 'print(1)'",
        "uv run pytest -q",
        "npm test",
        "bash script.sh",
        "sh",
        "sudo touch a",
        "xargs rm < list",
        "nohup touch a",
        "env -S 'touch a'",
        "$CMD a",
        "./build.sh",
        "find . -name x -delete",
    ],
)
def test_everything_else_is_unresolved_unless_the_runtime_marks_it_read_only(fs, text) -> None:
    assert seen(fs, text) == ([], [PROGRAM])
    words = tuple(shlex.split(text)[:1])
    shell = words[0] in {"bash", "sh"}  # evidence never covers a shell: what it runs is not the runtime's command
    assert seen(fs, text, Evidence(marks=((words, True),))) == ([], [PROGRAM] if shell else [])


@pytest.mark.parametrize(
    ("text", "targets"),
    [
        ("timeout 5 touch a", ["a"]),
        ("env A=1 touch a", ["a"]),
        ("env -i touch a", ["a"]),
        ("nice -n 5 touch a", ["a"]),
        ("command touch a", ["a"]),
        ("builtin echo x > o", ["o"]),
        ("exec > o", ["o"]),
        ("stdbuf -o0 tee a", ["a"]),
        ("timeout 5 env A=1 nice touch a", ["a"]),
    ],
)
def test_wrappers_are_followed_to_the_program_they_run(fs, text, targets) -> None:
    assert seen(fs, text) == ([("write", t) for t in targets], [])
    assert seen(fs, "command -v touch") == ([], [])


def test_nested_shell_scripts_are_followed_to_the_guards_depth(fs) -> None:
    assert seen(fs, "bash -c 'touch a > b' && sh -ec \"rm c\"") == (
        [("write", "b"), ("write", "a"), ("remove", "c")],
        [],
    )
    script = "touch deep"
    for _ in range(3):
        script = f"sh -c {shlex.quote(script)}"
    assert seen(fs, script) == ([("write", "deep")], [])
    assert seen(fs, f"sh -c {shlex.quote(script)}") == ([], [SYNTAX])  # one level beyond NESTING
    assert seen(fs, 'sh -c "$SCRIPT"') == ([], [SYNTAX])


@pytest.mark.parametrize(
    ("text", "targets", "reasons"),
    [
        ("touch $X", [], [VARIABLE]),
        ("touch $1 ${X:-a}", [], [VARIABLE]),
        ('touch "$HOME/x" ${HOME}/y ~/z', ["~/x", "~/y", "~/z"], []),
        ("touch $TMPDIR/x ${TMPDIR}/y", [f"{'{tmp}'}/x", f"{'{tmp}'}/y"], []),
        ("touch ~other/x", [], [VARIABLE]),
        ("touch '~/x' '$HOME'", ["~/x", "$HOME"], []),
        ("touch *.py", [], [PATTERN]),
        ("touch '*.py'", ["*.py"], []),
        ("mkdir -p src/{a,b}", [], [PATTERN]),
        ("rm -f build/*.pyc", ["build/*.pyc"], []),  # a removal's pattern lies in its folder
        ("rm -rf */cache", [], [PATTERN]),
        ("cp a.txt b*", [], [PATTERN]),
        ("cp *.txt sub", [], [PATTERN]),
        ("find . -exec rm {} \\;", [], [PROGRAM]),
    ],
)
def test_targets_with_variables_or_patterns_are_unresolved(fs, text, targets, reasons) -> None:
    found, why = seen(fs, text)
    tmp = str(fs["tmp"].resolve())
    assert ([p for _, p in found], why) == ([t.replace("{tmp}", tmp) for t in targets], reasons)


def test_writes_through_symlinks_are_resolved_and_removals_keep_the_link(fs) -> None:
    outside = fs["outside"]
    for text in ("echo x > out_file", "echo x >> out_file", "tee out_file", "touch out_file"):
        assert seen(fs, text)[0] == [("write", "@outside/protected.txt")], text
    assert seen(fs, "touch out_dir/new && mkdir -p out_dir/sub")[0] == [
        ("write", "@outside/dir/new"),
        ("write", "@outside/dir/sub"),
    ]
    assert seen(fs, f"echo x > {outside}/in_file; touch {outside}/in_dir/b")[0] == [
        ("write", "a.txt"),
        ("write", "sub/b"),
    ]
    assert seen(fs, "rm out_file; rm -rf out_dir; unlink out_file")[0] == [
        ("remove", "out_file"),
        ("remove", "out_dir"),
    ]
    assert seen(fs, "rm -rf out_dir/")[0] == [("remove", "@outside/dir")]  # a trailing slash follows the link
    assert seen(fs, f"rm {outside}/in_file; rmdir {outside}/in_dir")[0] == [
        ("remove", "@outside/in_file"),
        ("remove", "@outside/in_dir"),
    ]
    assert seen(fs, f"rm out_dir/x {outside}/in_dir/y")[0] == [("remove", "@outside/dir/x"), ("remove", "sub/y")]


def test_a_copy_or_move_onto_a_symlink_is_unresolved_never_the_link_or_its_referent(fs) -> None:
    outside = fs["outside"]
    assert seen(fs, "cp a.txt out_file") == ([], [LINK])
    assert seen(fs, "cp a.txt out_dir") == ([], [LINK])  # a link to a folder too
    assert seen(fs, f"cp a.txt {outside}/in_file") == ([], [LINK])  # a link into the worktree too
    assert seen(fs, "cp a.txt dest/") == ([], [LINK])  # dest/a.txt is a link
    assert seen(fs, "cp sub/../a.txt x.txt dest") == ([("write", "dest/x.txt")], [LINK])
    assert seen(fs, "mv a.txt out_file") == ([("remove", "a.txt")], [LINK])
    assert seen(fs, f"mv a.txt {outside}/in_dir") == ([("remove", "a.txt")], [LINK])
    assert seen(fs, "mv out_file kept") == ([("remove", "out_file"), ("write", "kept")], [])  # the source: the link
    assert seen(fs, f"cp a.txt {outside}/new.txt") == ([("write", "@outside/new.txt")], [])
    assert (fs["own"] / "dest" / "a.txt").is_symlink()
    assert (outside / "protected.txt").read_text() == "keep"


def test_a_recursive_copy_names_its_top_level_target_and_stays_unresolved(fs) -> None:
    src = fs["own"] / "tree" / "nested"
    src.mkdir(parents=True)
    (src / "file.txt").write_text("x")
    copied = fs["own"] / "dest" / "tree" / "nested"
    copied.mkdir(parents=True)
    (copied / "file.txt").symlink_to(fs["outside"] / "protected.txt")  # a copy writes through it
    assert seen(fs, "cp -r tree dest") == ([("write", "dest/tree")], [RECURSIVE])
    assert seen(fs, "cp -R tree/ new") == ([("write", "new")], [RECURSIVE])
    assert seen(fs, "cp -rf tree tree2 dest") == ([("write", "dest/tree"), ("write", "dest/tree2")], [RECURSIVE])
    assert seen(fs, "cp -a tree dest") == ([], [FORM])
    assert os.path.realpath(copied / "file.txt") == str(fs["outside"] / "protected.txt")


def test_read_only_evidence_covers_only_its_commands_non_redirect_effects(fs) -> None:
    make = Evidence(marks=((("make",), True),))
    assert seen(fs, "make > build.log 2>&1", make) == ([("write", "build.log")], [])
    assert seen(fs, "make; npm test > out", make) == ([("write", "out")], [PROGRAM])
    assert seen(fs, "git status --short", Evidence(marks=((("git", "status"), True),))) == ([], [])
    assert seen(fs, "git push", Evidence(marks=((("git", "status"), True),))) == ([], [PROGRAM])
    assert seen(fs, "touch a; make", Evidence(every=True)) == ([("write", "a")], [])  # never removes a target
    assert seen(fs, "rm -v a > log", Evidence(every=True)) == ([("write", "log")], [])
    assert seen(fs, "cat > x <<EOF\n$(id)\nEOF", Evidence(every=True)) == ([("write", "x")], [HEREDOC])
    found = run(fs, "make > out", make)
    assert found.redirects
    assert not run(fs, "make 2>&1", make).redirects


@pytest.mark.parametrize(
    ("text", "targets", "reasons"),
    [
        ('TMPDIR=/outside; touch "$TMPDIR/out"', [], [ENV]),  # an assignment alone
        ('export TMPDIR=/outside; touch "$TMPDIR/out"', [], [ENV]),
        ("export TMPDIR; touch $TMPDIR/out", [], [ENV]),
        ("unset HOME && touch ~/x", [], [ENV]),
        ("printf -v TMPDIR %s /outside; touch ${TMPDIR}/out", [], [ENV]),
        ("read -r HOME < answer; touch ~/x", [], [ENV]),
        ("declare -x HOME=/outside; touch $HOME/x", [], [ENV]),
        ("typeset TMPDIR=/o; local X; readonly HOME; touch ~/a $TMPDIR/b", [], [ENV]),
        ("HOME=/outside; cd && touch a", [], [ENV]),
        ("env TMPDIR=/outside sh -c 'touch \"$TMPDIR/out\"'", [], [ENV]),
        ("TMPDIR=/outside sh -c 'touch \"$TMPDIR/out\"'", [], [ENV]),
        ("env -u HOME sh -c 'touch ~/x'", [], [ENV]),
        ("env -i sh -c 'touch ~/x'", [], [ENV]),
        ("sh -c 'export HOME=/outside; touch ~/x'", [], [ENV]),
        ("sh -c 'HOME=/outside' && touch ~/x", ["~/x"], []),  # a nested shell exports nothing
        ('TMPDIR=/outside touch "$TMPDIR/x"', ["{tmp}/x"], []),  # its own assignment comes after the expansion
        ("export PATH=/bin:$PATH && touch ~/x", ["~/x"], []),  # not a watched variable
        ("printf '%s' HOME > o; touch ~/x", ["o", "~/x"], []),  # printf without -v sets nothing
    ],
)
def test_an_environment_change_leaves_home_and_tmpdir_expansions_after_it_unresolved(
    fs, text, targets, reasons
) -> None:
    found, why = seen(fs, text)
    tmp = str(fs["tmp"].resolve())
    assert ([p for _, p in found], why) == ([t.replace("{tmp}", tmp) for t in targets], reasons)


def test_a_text_says_whether_it_may_change_its_shell_for_later_calls(fs) -> None:
    changes = {t: (run(fs, t).moves, set(run(fs, t).changes)) for t in [
        "export TMPDIR=/o", "HOME=/o", "unset BASH_ENV", "sh -c 'export HOME=/o; cd /'", "TMPDIR=/o make",
        "cd sub && make", "ls | cd sub", "command cd sub", "touch a", "for d in a; do cd $d; done",
        "if true; then export HOME=/x; fi", "source .venv/bin/activate",
    ]}  # fmt: skip
    assert changes == {
        "export TMPDIR=/o": (False, {"TMPDIR"}), "HOME=/o": (False, {"HOME"}), "unset BASH_ENV": (False, {"BASH_ENV"}),
        "sh -c 'export HOME=/o; cd /'": (False, set()), "TMPDIR=/o make": (False, set()),
        "cd sub && make": (True, set()), "ls | cd sub": (True, set()), "command cd sub": (True, set()),
        "touch a": (False, set()), "for d in a; do cd $d; done": (True, set(we.WATCHED)),
        "if true; then export HOME=/x; fi": (True, set(we.WATCHED)),
        "source .venv/bin/activate": (True, set(we.WATCHED)),
    }  # fmt: skip


def test_what_an_earlier_call_changed_leaves_its_targets_unresolved(fs) -> None:
    own, outside = fs["own"], fs["outside"]
    assert seen(fs, f"touch a {outside}/b", drifted=True) == ([("write", "@outside/b")], [EARLIER_CWD])
    assert seen(fs, "cd sub && touch a", drifted=True) == ([], [EARLIER_CWD])
    assert seen(fs, f"cd {own}/sub && touch a", drifted=True) == ([("write", "sub/a")], [])
    assert seen(fs, "touch ~/x $TMPDIR/y", changed=frozenset({"HOME"})) == (
        [("write", str(fs["tmp"].resolve() / "y"))],
        [EARLIER_ENV],
    )
    assert seen(fs, "bash -c 'touch a'", changed=frozenset({"BASH_ENV"})) == ([], [STARTUP])


@pytest.mark.parametrize(("delimiter", "line"), [('"$HOME"', "$HOME"), ("$HOME", "$HOME"), ("'$HOME'", "$HOME"),
                                                 ("~", "~"), ('"~"', "~"), ("${TMPDIR}", "${TMPDIR}")])  # fmt: skip
def test_a_heredoc_delimiter_is_its_word_after_quote_removal_never_expanded(fs, delimiter, line) -> None:
    outside, home = fs["outside"], str(fs["home"])
    assert seen(fs, f"cat <<{delimiter}\nbody\n{line}\ntouch {outside}/hidden")[0] == [("write", "@outside/hidden")]
    hidden = f"cat <<{delimiter}\n{home}\n{fs['tmp']}\ntouch {outside}/inside_the_body\n{line}\ntouch {outside}/seen"
    assert seen(fs, hidden)[0] == [("write", "@outside/seen")]  # the expanded value does not end the body


def test_cd_keeps_the_logical_directory_as_bash_and_zsh_do(fs) -> None:
    assert seen(fs, "cd out_dir/.. && touch a") == ([("write", "a")], [])  # physically ../ of out_dir is outside
    assert seen(fs, "cd out_dir && cd .. && touch b") == ([("write", "b")], [])
    assert seen(fs, f"cd {fs['own']}/out_dir/.. && touch c") == ([("write", "c")], [])
    assert seen(fs, "cd out_dir && touch ../x") == ([("write", "@outside/x")], [])  # the kernel opens it physically
    assert seen(fs, f"cd {fs['outside']}/in_dir && cd .. && touch d") == ([("write", "@outside/d")], [])


@pytest.mark.parametrize(
    "text",
    [
        "env BASH_ENV=/dev/stdin bash -c : <<'EOF'\ntouch /outside/hidden\nEOF",
        "BASH_ENV=/x bash -c 'touch a'",
        "export BASH_ENV=/x; bash -c 'touch a'",
        "ENV=/x sh -c 'touch a'",
        "bash -lc 'touch a'",
        "bash --login -c 'touch a'",
        "bash --rcfile rc -c 'touch a'",
        "bash --init-file rc -c 'touch a'",
        "bash -ic 'touch a'",
        "zsh -c 'touch a'",
        "echo touch b | sh -c 'touch a; . /dev/stdin'",
        "sh -c 'touch a' < script",
        "sh -c 'touch a' <<< 'touch b'",
    ],
)
def test_a_nested_shell_that_may_read_startup_input_is_unresolved(fs, text) -> None:
    assert seen(fs, text) == ([], [STARTUP])
    assert seen(fs, "bash --noprofile --norc -c 'touch a'") == ([("write", "a")], [])


def test_read_only_evidence_is_bound_to_segments_and_a_non_read_only_mark_wins(fs) -> None:
    diff = (("git", "diff"), True), (("git", "diff", "--output=/outside/log"), False)
    overlapping = Evidence(marks=diff)
    assert seen(fs, "git diff", overlapping) == ([], [])
    assert seen(fs, "git diff --output=/outside/log", overlapping) == ([], [PROGRAM])
    conflicting = Evidence(segments=((("git", "diff"), False), (("git", "diff", "-p"), False)), marks=diff[:1])
    assert seen(fs, "git diff", conflicting) == ([], [PROGRAM])  # its segment's identifier is marked both ways
    bound = Evidence(segments=((("git", "log", "-p"), False),), marks=((("git",), True),))
    assert seen(fs, "git log -p", bound) == ([], [PROGRAM])
    assert seen(fs, "git status", bound) == ([], [])  # no segment of its own: its identifier's mark
    assert seen(fs, "A=1 git log -p", bound) == ([], [PROGRAM])  # by any spelling


def shell_state(fs, text: str, evidence: Evidence | None = None) -> tuple[list[str], bool, set[str]]:
    found = run(fs, text, evidence)
    return list(found.unresolved), found.moves, set(found.changes)


@pytest.mark.parametrize(
    ("text", "changes"),
    [
        ('V=TMPDIR; printf -v "$V" /outside; touch "$TMPDIR/out"', we.WATCHED),
        ('V=TMPDIR; export "$V=/outside"; touch "$TMPDIR/out"', we.WATCHED),
        ('V=HOME; unset "$V"; touch ~/out', we.WATCHED),
        ('read -p "$PROMPT" answer; touch ~/out', we.WATCHED),  # a name it cannot tell is any name
        ("declare -n R=HOME; R=/outside; touch ~/out", {"HOME"}),  # a nameref's referent
    ],
)
def test_a_setter_whose_name_is_not_literal_changes_every_watched_variable(fs, text, changes) -> None:
    assert shell_state(fs, text) == ([ENV], False, set(changes))
    assert seen(fs, f"sh -c {shlex.quote(text)}") == ([], [ENV])  # in a nested script too, kept there


@pytest.mark.parametrize(
    ("text", "reasons", "moves", "changes"),
    [
        ('TMPDIR=/outside :; touch "$TMPDIR/out"', [ENV], False, {"TMPDIR"}),  # a special builtin keeps it
        ('TMPDIR=/outside export X; touch "$TMPDIR/out"', [ENV], False, {"TMPDIR"}),
        ("HOME=/etc cd && touch a", [ENV], True, {"HOME"}),  # cd reads the HOME it was given
        ('TMPDIR=/outside touch "$TMPDIR/x"; touch "$TMPDIR/y"', [], False, set()),  # an external command's own
    ],
)
def test_a_prefix_assignment_before_a_builtin_changes_its_variable(fs, text, reasons, moves, changes) -> None:
    assert shell_state(fs, text) == (reasons, moves, changes)
    nested = run(fs, f"sh -c {shlex.quote(text)}")
    assert (list(nested.unresolved), nested.moves, set(nested.changes)) == (reasons, False, set())


def test_read_only_evidence_never_reaches_into_a_nested_script(fs) -> None:
    text = "git diff && sh -c 'git diff --output=/outside/log'"
    assert seen(fs, text, Evidence(marks=((("git", "diff"), True),))) == ([], [PROGRAM])
    assert seen(fs, text, Evidence(every=True)) == ([], [PROGRAM])
    assert seen(fs, "sh -c 'echo $(id)'", Evidence(every=True)) == ([], [SYNTAX])


def test_eval_and_source_always_change_the_shell_even_when_marked_read_only(fs) -> None:
    marked = Evidence(marks=((("eval",), True), (("source",), True), ((".",), True)))
    assert shell_state(fs, 'eval "cd /etc" && touch note', marked) == ([CWD], True, set(we.WATCHED))
    assert shell_state(fs, 'eval "TMPDIR=/outside"; touch "$TMPDIR/note"', marked) == ([ENV], True, set(we.WATCHED))
    assert shell_state(fs, "source env.sh && touch ~/note", marked) == ([ENV], True, set(we.WATCHED))
    assert shell_state(fs, ". env.sh", marked) == ([], True, set(we.WATCHED))  # its own write effect is cleared
    assert shell_state(fs, 'eval "cd /etc" && touch note') == ([SYNTAX], True, set(we.WATCHED))


@pytest.mark.parametrize(
    "text",
    [
        'CMD=cd; "$CMD" /etc && touch note',
        "$RUN /etc && touch note",
        "./*.sh && touch note",
        'command "$CMD" /etc && touch note',
        "env -S 'cd /etc' && touch note",
    ],
)
def test_a_command_that_cannot_be_named_may_be_any_builtin(fs, text) -> None:
    assert shell_state(fs, text) == ([PROGRAM, CWD], True, set(we.WATCHED))


def test_quote_removal_comes_before_naming_a_builtin_and_unread_text_changes_everything(fs) -> None:
    etc = os.path.realpath("/etc")
    assert seen(fs, "'cd' /etc && touch a") == ([("write", f"{etc}/a")], [])
    assert shell_state(fs, "'cd' /etc && touch a")[1:] == (True, set())
    assert shell_state(fs, "'cd' /etc; if true; then :; fi") == ([SYNTAX], True, set(we.WATCHED))
