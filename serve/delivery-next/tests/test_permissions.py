import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot.generated.session_events import PermissionRequestShell

from owlbear_delivery_next.change_contracts.permissions import Policy, Request, decide, view
from owlbear_delivery_next.local_system.shell_parse import parse
from owlbear_delivery_next.local_system.shell_programs import UnreadableError, split_string

ROOT = Path("/w")
READ, WRITE = Policy(ROOT, write=False), Policy(ROOT)
BYPASS = "which skips hooks or signing or forces history"


def shell(*texts: str) -> Request:
    return Request("shell", texts)


def sdk_shell(text: str) -> SimpleNamespace:
    """One SDK shell permission request for *text*, whose program the runtime flags read-only."""
    command = SimpleNamespace(identifier=text.split(maxsplit=1)[0], read_only=True)
    segment = SimpleNamespace(full_command_text=text)
    return SimpleNamespace(kind="shell", commands=[command], command_segments=[segment], possible_paths=())


def cli_shell(text: str, *segments: str) -> PermissionRequestShell:
    """A shell request as the CLI sends it: its segments split at pipes, redirections and here-document bodies gone."""
    return PermissionRequestShell.from_dict(
        {
            "canOfferSessionApproval": False,
            "commands": [{"identifier": text, "readOnly": False}],
            "fullCommandText": text,
            "hasWriteFileRedirection": ">" in text,
            "intention": "run it",
            "possiblePaths": [],
            "possibleUrls": [],
            "commandSegments": [{"fullCommandText": s, "identifier": s.split()[0]} for s in segments],
        }
    )


def test_the_guard_judges_the_whole_command_not_the_runtimes_segments() -> None:
    write = view(cli_shell("gh issue view 1 > f.md", "gh issue view 1"))
    piped = view(cli_shell("echo 'git commit --no-verify -m x' | sh", "echo 'git commit --no-verify -m x'", "sh"))

    assert write.commands == ("gh issue view 1",)
    assert decide(READ, write) == "`gh issue view 1 > f.md` uses a redirect, which writes in a read-only step"
    assert piped.text == "echo 'git commit --no-verify -m x' | sh"
    assert piped.commands == ("echo 'git commit --no-verify -m x'", "sh")


@pytest.mark.parametrize(
    ("text", "how"),
    [
        ("git commit -m x", "Git command 'commit'"),
        ("git -C . commit -m x", "Git command 'commit'"),
        ("git branch new", "Git command 'branch'"),
        ("rm a", "filesystem mutation 'rm'"),
        ("ls; rm a", "filesystem mutation 'rm'"),
        ("echo a > f", "a redirect"),
        ("ls >/dev/null.txt", "a redirect"),
        ("sed -i s/a/b/ f", "filesystem mutation 'sed -i'"),
        ("git diff --output=f", "Git output option --output=f"),
    ],
)
def test_a_read_only_step_refuses_every_command_that_writes(text: str, how: str) -> None:
    assert decide(READ, shell(text)) == f"`{text}` uses {how}, which writes in a read-only step"
    assert decide(WRITE, shell(text)) is None


@pytest.mark.parametrize(
    "text",
    [
        "tail -5 f",
        "cat f | wc -l",
        "git --no-pager diff",
        "git branch --show-current",
        "git log --oneline -3 2>&1",
        "ls 2>/dev/null",
        "grep -rn x src > /dev/null",
        "cat .git/HEAD",
    ],
)
def test_a_read_only_step_runs_any_command_that_only_reads(text: str) -> None:
    assert decide(READ, shell(text)) is None


@pytest.mark.parametrize(
    ("text", "how"),
    [("touch x", "filesystem mutation 'touch'"), ("git diff --output=f", "Git output option --output=f")],
)
def test_a_read_only_step_checks_writes_whatever_the_runtime_flags(text: str, how: str) -> None:
    req = view(sdk_shell(text))
    assert req.commands == (text,)
    assert decide(READ, req) == f"`{text}` uses {how}, which writes in a read-only step"


@pytest.mark.parametrize(
    ("text", "verdict"),
    [
        ("git -C x log", None),
        ("git -C log commit", "Git command 'commit'"),
        ("git --git-dir=x --no-pager show HEAD", None),
        ("git --version", None),
        ("/usr/bin/git -C x commit -m x", "Git command 'commit'"),
    ],
)
def test_a_read_only_step_parses_git_global_options(text: str, verdict: str | None) -> None:
    expected = verdict and f"`{text}` uses {verdict}, which writes in a read-only step"
    assert decide(READ, shell(text)) == expected


def test_a_read_only_step_refuses_write_tools_but_reads_anywhere() -> None:
    assert decide(READ, Request("write", paths=("a.ts",))) == "writes are not allowed in this step"
    assert decide(READ, Request("read", paths=("/etc/hosts",))) is None


def test_a_confined_step_writes_only_inside_its_folder_and_runs_no_shell(tmp_path: Path) -> None:
    confined, root = Policy(tmp_path, confined=True), tmp_path.resolve()
    assert decide(confined, Request("write", paths=("skills/a/SKILL.md",))) is None
    assert decide(confined, Request("write", paths=(str(tmp_path / "skills" / "b.md"),))) is None
    for path in ("../design-pack-update.json", "/etc/hosts", "skills/../../x"):
        said = f"{path} is outside this step's folder; write only under {root}"
        assert decide(confined, Request("write", paths=(path,))) == said
    assert decide(confined, Request("write")) == "a write must name its file"
    assert decide(confined, shell("ls")) == "this step runs no shell commands"
    assert decide(confined, Request("read", paths=("/etc/hosts",))) is None
    assert decide(WRITE, Request("write", paths=("/etc/hosts",))) is None  # only the confined step is held


def test_a_confined_step_judges_every_path_of_an_sdk_write_and_a_move(tmp_path: Path) -> None:
    def side(path: str) -> SimpleNamespace:
        return SimpleNamespace(path=path, content="x")

    move = SimpleNamespace(before=side(str(tmp_path / "a.md")), after=side("/tmp/outside.md"))  # noqa: S108
    sdk = SimpleNamespace(kind="write", resolved_path=str(tmp_path / "a.md"), file_name="a.md", file_edits=[move])

    req = view(sdk)

    assert req.paths == (str(tmp_path / "a.md"), "/tmp/outside.md")  # noqa: S108
    assert "/tmp/outside.md is outside this step's folder" in decide(Policy(tmp_path, confined=True), req)  # noqa: S108


@pytest.mark.parametrize(
    "text",
    ["git push origin main", "gh pr list", "curl https://example.com", "cat /etc/hosts", "git config user.name x"],
)
def test_a_write_step_allows_commands_beyond_the_worktree(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


def test_a_write_step_writes_outside_the_worktree() -> None:
    assert decide(WRITE, Request("write", paths=("/elsewhere/a.ts",))) is None
    assert decide(WRITE, shell("cd /opt && touch x")) is None


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("git commit --no-verify -m x", "--no-verify"),
        ("git commit -nm x", "-nm"),
        ("git commit -n -m x", "-n"),
        ("git commit -anm x", "-anm"),
        ("git commit --no-gpg-sign -m x", "--no-gpg-sign"),
        ("git merge --no-verify main", "--no-verify"),
        ("git push --force", "--force"),
        ("git push --force-with-lease", "--force-with-lease"),
        ("git push -f", "-f"),
        ("git push origin +main", "+main"),
        ("cd pkg && git commit -n -m x", "-n"),
        ("npm test;/usr/bin/git push -f", "-f"),
        ("git -C push commit -n -m x", "-n"),
        ("git commit -m x --no-verify", "--no-verify"),
        ("git push -uf origin main", "-uf"),
        ("git --no-pager -c user.name=x push --force-with-lease", "--force-with-lease"),
        ("GIT_TRACE=1 git push -f", "-f"),
        ("true\ngit push --force origin main", "--force"),
        ("echo ';' && git push -f", "-f"),
        ("ls | (git push -f)", "-f"),
        ("echo $(git push -f)", "-f"),
        ('echo "`git push -f`"', "-f"),
        ("git commit -m $(cat f) --no-verify", "--no-verify"),
        ("git commit -m x 2>&1 --no-verify", "--no-verify"),
        ("git -c core.hooksPath=/dev/null commit -m x", "-c core.hooksPath=/dev/null"),
        ("git -c core.hooksPath= push", "-c core.hooksPath="),
        ("git -c commit.gpgSign=false commit -m x", "-c commit.gpgSign=false"),
        ("git -c COMMIT.GPGSIGN=0 commit -m x", "-c COMMIT.GPGSIGN=0"),
        ("git -c tag.gpgsign=off tag v1", "-c tag.gpgsign=off"),
    ],
)
def test_every_step_refuses_hook_or_signing_bypass_and_force_push(text: str, flag: str) -> None:
    for policy in (READ, WRITE):
        assert decide(policy, shell(text)) == f"`{text}` uses {flag}, {BYPASS}"


@pytest.mark.parametrize(
    "text",
    [
        "git commit -m 'fix -n handling'",
        "git commit -mn",
        'git commit -m "--no-verify"',
        "git commit --message --no-verify",
        "git commit -am x",
        'git commit -m "x\n--no-verify"',
        'git push origin -o "+message"',
        "git push -u origin main",
        'echo ";" git push -f',
        "echo 'a && git push -f'",
        "git push origin main # --force",
        "git -c user.name=x -c commit.gpgsign=true commit -m x",
        "git commit -- --no-verify",
    ],
)
def test_quoted_text_and_option_values_are_not_a_bypass(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


@pytest.mark.parametrize(
    ("text", "inner", "flag"),
    [
        ("env GIT_TRACE=1 git push -f", "env GIT_TRACE=1 git push -f", "-f"),
        ("env -i git commit -n -m x", "env -i git commit -n -m x", "-n"),
        ("echo main | xargs git push --force origin", "echo main | xargs git push --force origin", "--force"),
        ("timeout 60 git commit --no-verify -m x", "timeout 60 git commit --no-verify -m x", "--no-verify"),
        ("find . -name x -exec git push -f \\;", "find . -name x -exec git push -f \\;", "-f"),
        ("sh -c 'git push -f'", "git push -f", "-f"),
        ('bash -lc "git commit --no-verify -m x"', "git commit --no-verify -m x", "--no-verify"),
        ("env bash -c 'git -c core.hooksPath=/x commit'", "git -c core.hooksPath=/x commit", "-c core.hooksPath=/x"),
        ("eval git push -f", "git push -f", "-f"),
        ("sh -c \"bash -c 'git push -f'\"", "git push -f", "-f"),
        ("/bin/zsh -c 'cd x && git push -f'", "cd x && git push -f", "-f"),
        ("bash -o pipefail -c 'git push -f'", "git push -f", "-f"),
        ("bash -c -- 'git push -f'", "git push -f", "-f"),
        ("eval -- 'git push -f'", "git push -f", "-f"),
        (
            "find . -exec sh -c 'git log -1' \\; -exec sh -c 'git push -f' \\;",
            "git push -f",
            "-f",
        ),
        ("find . -name git -exec sh -c 'git push -f' \\;", "git push -f", "-f"),
    ],
)
def test_a_bypass_behind_a_wrapper_or_in_a_nested_shell_is_refused(text: str, inner: str, flag: str) -> None:
    assert decide(WRITE, shell(text)) == f"`{inner}` uses {flag}, {BYPASS}"
    assert decide(READ, shell(text)) is not None


@pytest.mark.parametrize(
    "text",
    [
        "env FOO=1 npm test",
        "xargs grep git",
        "sh -c 'git push origin main'",
        "timeout 5 npm run build -- --force",
        "echo git push -f",
        "xargs grep -- git push -f",
        "bash -c ' '",
        "eval '# a comment'",
        "git config --get core.hooksPath",
        "git config --get-regexp core.hooksPath .",
        "GIT_CONFIG_PARAMETERS=\"'commit.gpgsign=true'\" git status",
        "printf '%s' 'GIT_CONFIG_KEY_0=core.hooksPath'",
        "command -v git push -f",
        "GIT_CONFIG_GLOBAL=/dev/null git status",
    ],
)
def test_wrappers_and_nested_shells_without_a_bypass_run(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("git config core.hooksPath /dev/null", "config core.hooksPath /dev/null"),
        ("git config --local commit.gpgsign false", "config commit.gpgsign false"),
        ("git config set core.hooksPath x", "config core.hooksPath x"),
        (
            "GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/dev/null'\" git commit -m x",
            "environment setting core.hooksPath=/dev/null",
        ),
        (
            "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false git commit -m x",
            "environment setting commit.gpgsign=false",
        ),
        ("HOOKS=/x git --config-env=core.hooksPath=HOOKS commit -m x", "-c core.hooksPath="),
        ("git --config-env core.hooksPath=HOOKS commit -m x", "-c core.hooksPath="),
        ("SIGN=false git --config-env=commit.gpgsign=SIGN commit -m x", "-c commit.gpgsign="),
        ("git push -- origin +main", "+main"),
        ("timeout --signal KILL 5 git push -f", "-f"),
        ("sudo -Eu x git push -f", "-f"),
        ("watch -d git push -f", "-f"),
        ("env -u X git push -f", "-f"),
        ("xargs -n1 git push -f", "-f"),
    ],
)
def test_hooks_or_signing_turned_off_by_config_is_a_bypass(text: str, flag: str) -> None:
    assert decide(WRITE, shell(text)) == f"`{text}` uses {flag}, {BYPASS}"


def test_git_named_as_data_is_not_a_git_command() -> None:
    assert decide(READ, shell("sh -c 'grep -n git README.md'")) is None
    assert decide(READ, shell("find . -name git -exec cat {} \\;")) is None
    assert decide(READ, shell("git config --list")) is None
    assert decide(READ, shell("git config --remove-section x")) is not None


def test_a_read_only_step_reads_nested_scripts_and_refuses_their_writes() -> None:
    assert (
        decide(READ, shell("sh -c 'rm x'")) == "`rm x` uses filesystem mutation 'rm', which writes in a read-only step"
    )
    assert decide(READ, shell("bash -c 'git log -1'")) is None
    deep = 'sh -c "sh -c \'sh -c \\"sh -c ls\\"\'"'
    assert decide(WRITE, shell(deep)).endswith("nests scripts more than 3 deep")


def test_unparseable_and_empty_commands_are_refused() -> None:
    assert decide(WRITE, shell("echo 'open")) == "`echo 'open` cannot be parsed"
    assert decide(WRITE, shell("")) == "the shell request names no command"


def test_mcp_and_custom_tools_stay_bound_to_the_role() -> None:
    offered = frozenset({"owlbear-memory/save_memory"})
    mcp = Request("mcp", tool="owlbear-memory-save_memory", server="owlbear-memory")
    assert decide(WRITE, mcp, offered) is None
    assert decide(WRITE, mcp) == "mcp requests are not allowed in this step"
    assert decide(READ, Request("custom-tool", tool="submit_result")) is None
    assert decide(READ, Request("custom-tool", tool="other")) == "tool other is not allowed"
    assert decide(WRITE, Request("url")) is None  # the planner's web_fetch (TD-82)


@pytest.mark.parametrize(
    "text",
    [
        "git commit -F - <<'EOF'\nfix: refuse git push --force and git commit --no-verify\nEOF",
        "cat <<'EOF'\n$(git commit --no-verify -m x)\nEOF",
        "cat <<-EOF\n\tgit push -f\n\tEOF",
        "echo $((1<<2))",
        "x=$(cat <<'A'\nhi\nA\n); echo \"$x\"",
        "cat <<A <<'B'\none\nA\ngit push -f\nB",
    ],
)
def test_a_here_document_to_a_program_other_than_a_shell_is_data(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


@pytest.mark.parametrize(
    "text",
    [
        "cat <<EOF\n$(git commit --no-verify -m x)\nEOF",
        "cat <<EOF\n`git push -f`\nEOF",
        "echo $(( $(git push -f) + 1 ))",
        "echo $(( `git push -f` + 1 ))",
        "bash <<'EOF'\ngit push -f\nEOF",
        "bash <<< 'git push -f'",
    ],
)
def test_substitutions_and_a_shells_here_document_are_still_judged(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_the_lexer_attaches_here_documents_and_here_strings_to_their_command() -> None:
    first, second = parse("bash 3<<'A' <<-B\nfd3 $x\nA\n\tstdin $x\nB\ncat <<< \"$y\"")

    assert first.words == ["bash"]
    assert [(i.fd, i.kind, str(i.word), i.word.expanded) for i in first.inputs] == [
        (3, "here", "fd3 $x\n", False),
        (0, "here", "stdin $x\n", True),
    ]
    assert first.stdin().word == "stdin $x\n"
    assert (second.stdin().kind, second.stdin().word, second.stdin().word.expanded) == ("string", "$y", True)


def test_the_lexer_marks_expansions_tildes_and_where_input_comes_from() -> None:
    run_time, literal, echo, cat, sh, group, closer, fed, tee = parse(
        "$PY -V; '$PY' ~/a '~/b'; echo a | (cat; sh) && { x; } < f; tee >(sh)"
    )

    assert [(w.expanded, w.tilde) for w in run_time.words] == [(True, False), (False, False)]
    assert [(w.expanded, w.tilde) for w in literal.words] == [(False, False), (False, True), (False, False)]
    assert (echo.opaque_stdin, echo.top_level) == (False, True)
    assert (cat.opaque_stdin, sh.opaque_stdin, cat.top_level) == (True, True, False)
    assert (group.words, group.opaque_stdin, closer.words) == (["{", "x"], True, ["}"])  # the group's input feeds it
    assert (fed.words, fed.opaque_stdin, tee.opaque_stdin) == (["sh"], True, False)


BAD = "git commit --no-verify -m x\n"


@pytest.fixture
def scripts(tmp_path: Path) -> Path:
    """A worktree whose good.sh is harmless and whose bad.sh skips the hooks, also in sub/ and outside it."""
    root = tmp_path / "root"
    for folder, good, bad in ((root, "good.sh", "bad.sh"), (root / "sub", "x.sh", "bad.sh")):
        folder.mkdir(parents=True)
        (folder / good).write_text("echo hi\n")
        (folder / bad).write_text(BAD)
    (root / "x.sh").write_text("echo root\n")
    (root / "sub" / "x.sh").write_text(BAD)
    (root / "scripts").mkdir()
    (root / "scripts" / "check.sh").write_text("echo checked\n")
    return root


def at(root: Path, *, write: bool = True) -> Policy:
    return Policy(root, write=write)


@pytest.mark.parametrize(
    "text",
    [
        "bash scripts/check.sh --force",
        "bash good.sh",
        "sh -e good.sh",
        "bash -s < good.sh",
        "sh < good.sh",
        "source ./good.sh",
        ". ./good.sh",
        "BASH_ENV=./good.sh bash -c true",
        "bash --rcfile ./good.sh -ic true",
        "bash <<'EOF'\necho hi\nEOF",
        "bash <<< 'echo hi'",
        "source /dev/stdin <<< 'echo hi'",
        ". /dev/stdin <<'EOF'\necho hi\nEOF",
        "echo hi | sh -c 'echo hi'",
        "true || sh -c 'echo hi'",
        "'$PY' -V",
        'echo "$HOME"',
        'git commit -m "$MSG"',
        "sh -c 'echo $X'",
        "bash <<< 'echo $X'",
        "bash good.sh > log.txt",
        "bash good.sh && rm log.txt",
    ],
)
def test_a_readable_script_a_shell_runs_is_judged_and_a_harmless_one_runs(scripts: Path, text: str) -> None:
    assert decide(at(scripts), shell(text)) is None


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("bash bad.sh", "bad.sh"),
        ("sh -e bad.sh", "bad.sh"),
        ("bash -s < bad.sh", "bad.sh"),
        ("sh < bad.sh", "bad.sh"),
        ("source ./bad.sh", "./bad.sh"),
        (". ./bad.sh", "./bad.sh"),
        ("BASH_ENV=./bad.sh bash -c true", "./bad.sh"),
        ("bash --rcfile ./bad.sh -ic true", "./bad.sh"),
        ("timeout 5 bash bad.sh", "bad.sh"),
        ("cd sub && bash ../bad.sh", None),
    ],
)
def test_a_bypass_in_a_script_file_is_refused(scripts: Path, text: str, name: str | None) -> None:
    reason = decide(at(scripts), shell(text))

    if name is None:  # a relative cd leaves the folder unknown
        assert reason == f"`{text}` runs `../bad.sh` from a folder the guard can't follow; use an absolute path"
    else:
        assert reason == f"`{name}` uses --no-verify, {BYPASS}"


@pytest.mark.parametrize(
    "text",
    [
        "bash <<'EOF'\ngit commit --no-verify -m x\nEOF",
        "sh <<EOF\ngit commit --no-verify -m x\nEOF",
        "bash -s <<-EOF\n\tgit commit --no-verify -m x\n\tEOF",
        "bash <<< 'git commit --no-verify -m x'",
        "source /dev/stdin <<< 'git commit --no-verify -m x'",
        "bash <<'A' 3<<'B'\ngit commit --no-verify -m x\nA\necho hi\nB",
        "bash <<'A' <<'B'\necho hi\nA\ngit commit --no-verify -m x\nB",
    ],
)
def test_a_bypass_in_a_shells_here_document_or_here_string_is_refused(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(f"uses --no-verify, {BYPASS}")


def test_only_a_shells_last_standard_input_is_its_script() -> None:
    assert decide(WRITE, shell("bash <<'A' 3<<'B'\necho hi\nA\ngit commit --no-verify -m x\nB")) is None
    assert decide(WRITE, shell("bash <<'A' <<'B'\ngit commit --no-verify -m x\nA\necho hi\nB")) is None


PIPED = "pipes input into a shell, which the guard can't read; pass the commands with -c or as a script file"


@pytest.mark.parametrize(
    "text",
    [
        "echo 'git commit --no-verify -m x' | sh",
        "echo x | bash -s",
        "echo x |& sh",
        "echo x | bash -c 'sh'",
        "echo x | { true; sh; }",
        "echo x | (true; sh)",
        "echo x | while read l; do sh; done",
        "tee >(sh)",
        "cat f | source /dev/stdin",
        "printf x | eval 'sh'",
        "eval 'exec < f'; sh",
        "exec < f; bash",
        "ls | xargs sh",
        "bash 0<&3",
    ],
)
def test_a_shell_reading_input_the_guard_cant_see_is_refused(text: str) -> None:
    reason = decide(WRITE, shell(text))

    assert reason is not None
    assert reason.endswith(PIPED), reason
    assert decide(READ, shell(text)) is not None


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        ("$PY -V", "$PY"),
        ('"$PY" -V', "$PY"),
        ("$(echo git) push -f", "$"),
        ("`echo git` status", "$"),
        ("env $X", "$X"),
        ("echo a | xargs $CMD", "$CMD"),
        ("echo a | xargs -I{} {}", "{}"),
        ("PY=/usr/bin/python3; $PY -V", "$PY"),
    ],
)
def test_a_command_name_built_at_run_time_is_refused(text: str, shown: str) -> None:
    assert decide(WRITE, shell(text)) == (
        f"`{text}` builds a command at run time (`{shown}`); write the program and its script out"
    )


@pytest.mark.parametrize(
    "text",
    [
        'sh -c "$CMD"',
        'sh -c "git commit $X"',
        'bash -c "$(cat f) -x"',
        'eval "$CMD"',
        "eval git commit $X",
        'bash <<< "$CMD"',
        "bash <<EOF\necho $X\nEOF",
        "echo a | xargs -I{} sh -c '{}'",
    ],
)
def test_a_script_built_at_run_time_is_refused(text: str) -> None:
    reason = decide(WRITE, shell(text))
    assert reason is not None
    assert "hands a shell a script built at run time" in reason


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("bash missing.sh", "No such file or directory"),
        ("bash sub", "it is not a regular file"),
        ("bash latin1.sh", "it is not UTF-8 text"),
        ("bash fifo", "it is not a regular file"),
    ],
)
def test_a_script_that_cant_be_read_is_refused(scripts: Path, text: str, why: str) -> None:
    (scripts / "latin1.sh").write_bytes(b"echo \xe9\n")
    os.mkfifo(scripts / "fifo")
    file = text.split()[1]

    assert decide(at(scripts), shell(text)) == f"`{text}` runs `{file}`, which can't be read: {why}"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ('bash "$F"', "runs `$F`, a path built at run time; write the path out"),
        ("source setup.sh", "sources `setup.sh` through PATH; write `./setup.sh`"),
    ],
)
def test_a_script_path_the_guard_cant_resolve_is_refused(scripts: Path, text: str, reason: str) -> None:
    assert decide(at(scripts), shell(text)) == f"`{text}` {reason}"


def test_a_read_only_step_judges_a_scripts_writes(scripts: Path) -> None:
    (scripts / "wipe.sh").write_text("rm x\n")

    assert decide(at(scripts, write=False), shell("bash good.sh")) is None
    assert decide(at(scripts, write=False), shell("bash wipe.sh")) == (
        "`wipe.sh` uses filesystem mutation 'rm', which writes in a read-only step"
    )


def shebang(path: Path, first: str, body: str = "echo hi\n") -> Path:
    path.write_text(f"{first}\n{body}" if first else body)
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("first", ["#!/bin/bash", "#!/usr/bin/env bash", "#!/usr/bin/env -S bash -e", ""])
def test_a_shell_script_run_by_path_is_read(scripts: Path, first: str) -> None:
    shebang(scripts / "tool", first, BAD)
    shebang(scripts / "fine", first)

    assert decide(at(scripts), shell("./tool")).endswith(BYPASS)
    assert decide(at(scripts), shell("./fine")) is None


def test_a_program_by_path_that_isnt_a_shell_script_runs_unread(scripts: Path) -> None:
    shebang(scripts / "tool.py", "#!/usr/bin/env python3", "import subprocess\n")
    (scripts / "binary").write_bytes(b"\x7fELF\0\0git commit --no-verify")
    long_text = "#" + "é" * 3000 + "\n" + BAD  # a character cut at byte 4096 is still text

    (scripts / "long").write_text(long_text)

    assert decide(at(scripts), shell("./tool.py")) is None
    assert decide(at(scripts), shell("./binary")) is None
    assert decide(at(scripts), shell("./long")).endswith(BYPASS)
    assert decide(at(scripts), shell("./missing")) == (
        "`./missing` runs `./missing`, which can't be read: No such file or directory"
    )


def test_a_launcher_run_by_path_is_read_too(scripts: Path) -> None:
    shebang(scripts / "env", "#!/bin/sh", BAD)

    assert decide(at(scripts), shell("./env echo hi")).endswith(BYPASS)
    assert decide(at(scripts), shell("/usr/bin/env echo hi")) is None


def test_scripts_outside_the_worktree_are_read_too(scripts: Path) -> None:
    elsewhere = scripts.parent / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "good.sh").write_text("echo hi\n")
    shebang(elsewhere / "bad.sh", "#!/bin/sh", BAD)

    assert decide(at(scripts), shell(f"bash {elsewhere}/good.sh")) is None
    assert decide(at(scripts), shell(f"{elsewhere}/bad.sh")).endswith(BYPASS)


def test_nesting_counts_each_script_once_up_to_the_limit(scripts: Path) -> None:
    shebang(scripts / "leaf", "#!/bin/sh")
    (scripts / "mid.sh").write_text("./leaf\n")

    assert decide(at(scripts), shell("sh -c 'bash mid.sh'")) is None  # -c, mid.sh, leaf: three levels
    assert decide(at(scripts), shell("sh -c \"sh -c 'bash mid.sh'\"")).endswith("nests scripts more than 3 deep")


@pytest.mark.parametrize(
    "text",
    [
        "cd sub && bash x.sh",
        "CDPATH=/elsewhere; cd sub; bash x.sh",
        "cd -; bash x.sh",
        "(cd sub); bash x.sh",
        'cd "$D" && bash x.sh',
        "eval 'cd sub'; bash ./x.sh",
        "env -C sub bash x.sh",
        "find sub -name x.sh -execdir bash ./x.sh \\;",
        "for d in sub; do cd /tmp; done; bash x.sh",
    ],
)
def test_a_relative_script_after_a_folder_change_the_guard_cant_follow_is_refused(scripts: Path, text: str) -> None:
    assert decide(at(scripts), shell(text)).endswith("from a folder the guard can't follow; use an absolute path")


def test_a_cd_to_an_absolute_path_is_followed(scripts: Path) -> None:
    assert decide(at(scripts), shell(f"cd {scripts}/sub && bash x.sh")).endswith(BYPASS)
    assert decide(at(scripts), shell(f"cd {scripts}/sub && bash ../good.sh")) is None
    assert decide(at(scripts), shell(f"cd {scripts}/sub/.. && bash x.sh")).endswith("use an absolute path")
    assert decide(at(scripts), shell(f"cd sub && bash {scripts}/good.sh")) is None


def test_a_quoted_tilde_is_a_folder_named_tilde(scripts: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = scripts.parent / "home"
    home.mkdir()
    (home / "x.sh").write_text("echo hi\n")
    (scripts / "~").mkdir()
    (scripts / "~" / "x.sh").write_text(BAD)
    monkeypatch.setenv("HOME", str(home))

    assert decide(at(scripts), shell("bash ~/x.sh")) is None
    assert decide(at(scripts), shell("bash '~/x.sh'")).endswith(BYPASS)


@pytest.mark.parametrize(
    "text",
    [
        "cat > good.sh <<'EOF'\ngit commit --no-verify -m x\nEOF\nbash good.sh",
        "cp bad.sh good.sh && bash good.sh",
        "git checkout x && ./good.sh",
        "bash -c 'cp bad.sh good.sh'; bash ./good.sh",
        "source ./writer.sh; bash ./good.sh",
        "BASH_ENV=./writer.sh bash -c 'bash ./good.sh'",
        "cp a b; bash -c 'bash good.sh'",
        "cp tool.py ./tool && ./tool",
        "mkdir -p out && ./bin/x",
        "cp bad.sh ./env && ./env echo hi",
    ],
)
def test_a_script_or_program_run_after_a_write_in_the_same_command_is_refused(scripts: Path, text: str) -> None:
    (scripts / "writer.sh").write_text("cp bad.sh good.sh\n")

    assert decide(at(scripts), shell(text)).endswith("write it in one command and run it in the next")


def test_a_startup_file_that_writes_nothing_leaves_the_script_readable(scripts: Path) -> None:
    (scripts / "quiet.sh").write_text("echo quiet\n")

    assert decide(at(scripts), shell("BASH_ENV=./quiet.sh bash -c 'bash ./good.sh'")) is None


@pytest.mark.parametrize(
    "text",
    [
        "BASH_ENV=./bad.sh; bash -c true",
        "export BASH_ENV=./bad.sh; bash -c true",
    ],
)
def test_a_startup_file_set_earlier_in_the_command_is_read(scripts: Path, text: str) -> None:
    assert decide(at(scripts), shell(text)) == f"`./bad.sh` uses --no-verify, {BYPASS}"


def test_a_startup_file_set_where_the_guard_cant_follow_it_is_refused(scripts: Path) -> None:
    assert decide(at(scripts), shell("(BASH_ENV=./x); bash -c true")).endswith(
        "starts a shell whose startup file was set where the guard can't follow it"
    )


@pytest.mark.parametrize(
    "text",
    [
        "export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x; git status",
        "export GIT_CONFIG_PARAMETERS=\"'commit.gpgsign=false'\"; git status",
    ],
)
def test_git_settings_exported_before_git_stay_refused(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_a_harmless_exported_git_setting_runs() -> None:
    assert decide(WRITE, shell("export GIT_CONFIG_PARAMETERS=\"'commit.gpgsign=true'\"; git status")) is None


@pytest.mark.parametrize(
    "text",
    [
        "env -S 'git commit --no-verify -m x'",
        'env -S"git push -f"',
        "env --split-string='git push -f'",
        "env -iS 'git push -f'",
        "env -S 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git status'",
        "timeout 5 env -S 'X=1 git push -f'",
    ],
)
def test_a_bypass_through_env_split_string_is_refused(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_env_split_string_runs_its_harmless_command_and_reads_its_startup_file(scripts: Path) -> None:
    assert decide(WRITE, shell("env -S 'echo hi'")) is None
    assert decide(WRITE, shell("env -u X -S 'echo hi'")) is None
    assert (
        decide(at(scripts), shell("env -S 'BASH_ENV=./bad.sh bash -c true'"))
        == f"`./bad.sh` uses --no-verify, {BYPASS}"
    )
    shebang(scripts / "tool", "#!/usr/bin/env -S BASH_ENV=./bad.sh bash")
    assert decide(at(scripts), shell("./tool")) == f"`./bad.sh` uses --no-verify, {BYPASS}"


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("a\\_b", ["a", "b"]),
        ('"a\\_b"', ["a b"]),
        ("a\\c b", ["a"]),
        ("a # b", ["a"]),
        ("'a b' \"c d\"", ["a b", "c d"]),
        ("a\\tb", ["a\tb"]),
    ],
)
def test_env_split_string_splits_as_env_does(text: str, words: list[str]) -> None:
    assert split_string(text) == words


def test_env_split_string_marks_variables_and_refuses_what_env_wouldnt_read() -> None:
    assert [w.expanded for w in split_string("${HOME}/bin/x y")] == [True, False]
    for text in ("a\\q", "'open", "$HOME", "'a\\b'"):
        with pytest.raises(UnreadableError):
            split_string(text)
    assert decide(WRITE, shell("env -S 'a\\q'")) == "`env -S 'a\\q'` uses env -S with text the guard can't read"
    assert decide(WRITE, shell("env -S '${CMD} x'")).endswith(
        "builds a command at run time (`${CMD}`); write the program and its script out"
    )
