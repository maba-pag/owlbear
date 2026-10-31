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
    assert (echo.opaque_stdin, echo.top_level) == (False, False)  # a pipeline part runs in a subshell
    assert (cat.opaque_stdin, sh.opaque_stdin, cat.top_level) == (True, True, False)
    assert (group.words, group.opaque_stdin, closer.words) == (["{", "x"], True, ["}"])  # the group's input feeds it
    assert (fed.words, fed.opaque_stdin, tee.opaque_stdin) == (["sh"], True, False)


BAD = "git commit --no-verify -m x\n"


@pytest.fixture
def scripts(tmp_path: Path) -> Path:
    """A worktree whose good.sh and x.sh are harmless and whose bad.sh and sub/x.sh skip the hooks."""
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "good.sh").write_text("echo hi\n")
    (root / "bad.sh").write_text(BAD)
    (root / "x.sh").write_text("echo root\n")
    (root / "sub" / "x.sh").write_text(BAD)
    (root / "scripts").mkdir()
    (root / "scripts" / "check.sh").write_text("echo checked\n")
    return root


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
    assert decide(Policy(scripts), shell(text)) is None


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
    reason = decide(Policy(scripts), shell(text))

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

    assert decide(Policy(scripts), shell(text)) == f"`{text}` runs `{file}`, which can't be read: {why}"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ('bash "$F"', "runs `$F`, a path built at run time; write the path out"),
        ("source setup.sh", "sources `setup.sh` through PATH; write `./setup.sh`"),
    ],
)
def test_a_script_path_the_guard_cant_resolve_is_refused(scripts: Path, text: str, reason: str) -> None:
    assert decide(Policy(scripts), shell(text)) == f"`{text}` {reason}"


def test_a_read_only_step_judges_a_scripts_writes(scripts: Path) -> None:
    (scripts / "wipe.sh").write_text("rm x\n")

    assert decide(Policy(scripts, write=False), shell("bash good.sh")) is None
    assert decide(Policy(scripts, write=False), shell("bash wipe.sh")) == (
        "`wipe.sh` uses filesystem mutation 'rm', which writes in a read-only step"
    )


def shebang(path: Path, first: str, body: str = "echo hi\n") -> None:
    path.write_text(f"{first}\n{body}" if first else body)
    path.chmod(0o755)


@pytest.mark.parametrize("first", ["#!/bin/bash", "#!/usr/bin/env bash", "#!/usr/bin/env -S bash -e", ""])
def test_a_shell_script_run_by_path_is_read(scripts: Path, first: str) -> None:
    shebang(scripts / "tool", first, BAD)
    shebang(scripts / "fine", first)

    assert decide(Policy(scripts), shell("./tool")).endswith(BYPASS)
    assert decide(Policy(scripts), shell("./fine")) is None


def test_a_program_by_path_that_isnt_a_shell_script_runs_unread(scripts: Path) -> None:
    shebang(scripts / "tool.py", "#!/usr/bin/env python3", "import subprocess\n")
    (scripts / "binary").write_bytes(b"\x7fELF\0\0git commit --no-verify")
    long_text = "#" + "é" * 3000 + "\n" + BAD  # a character cut at byte 4096 is still text

    (scripts / "long").write_text(long_text)

    assert decide(Policy(scripts), shell("./tool.py")) is None
    assert decide(Policy(scripts), shell("./binary")) is None
    assert decide(Policy(scripts), shell("./long")).endswith(BYPASS)
    assert decide(Policy(scripts), shell("./missing")) == (
        "`./missing` runs `./missing`, which can't be read: No such file or directory"
    )


def test_a_launcher_run_by_path_is_read_too(scripts: Path) -> None:
    shebang(scripts / "env", "#!/bin/sh", BAD)

    assert decide(Policy(scripts), shell("./env echo hi")).endswith(BYPASS)
    assert decide(Policy(scripts), shell("/usr/bin/env echo hi")) is None


def test_scripts_outside_the_worktree_are_read_too(scripts: Path) -> None:
    elsewhere = scripts.parent / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "good.sh").write_text("echo hi\n")
    shebang(elsewhere / "bad.sh", "#!/bin/sh", BAD)

    assert decide(Policy(scripts), shell(f"bash {elsewhere}/good.sh")) is None
    assert decide(Policy(scripts), shell(f"{elsewhere}/bad.sh")).endswith(BYPASS)


def test_nesting_counts_each_script_once_up_to_the_limit(scripts: Path) -> None:
    shebang(scripts / "leaf", "#!/bin/sh")
    (scripts / "mid.sh").write_text("./leaf\n")

    assert decide(Policy(scripts), shell("sh -c 'bash mid.sh'")) is None  # -c, mid.sh, leaf: three levels
    assert decide(Policy(scripts), shell("sh -c \"sh -c 'bash mid.sh'\"")).endswith("nests scripts more than 3 deep")


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
    assert decide(Policy(scripts), shell(text)).endswith("from a folder the guard can't follow; use an absolute path")


def test_a_cd_to_an_absolute_path_is_followed(scripts: Path) -> None:
    assert decide(Policy(scripts), shell(f"cd {scripts}/sub && bash x.sh")).endswith(BYPASS)
    assert decide(Policy(scripts), shell(f"cd {scripts}/sub && bash ../good.sh")) is None
    assert decide(Policy(scripts), shell(f"cd {scripts}/sub/.. && bash x.sh")).endswith("use an absolute path")
    assert decide(Policy(scripts), shell(f"cd sub && bash {scripts}/good.sh")) is None


def test_a_quoted_tilde_is_a_folder_named_tilde(scripts: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = scripts.parent / "home"
    home.mkdir()
    (home / "x.sh").write_text("echo hi\n")
    (scripts / "~").mkdir()
    (scripts / "~" / "x.sh").write_text(BAD)
    monkeypatch.setenv("HOME", str(home))

    assert decide(Policy(scripts), shell("bash ~/x.sh")) is None
    assert decide(Policy(scripts), shell("bash '~/x.sh'")).endswith(BYPASS)


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

    assert decide(Policy(scripts), shell(text)).endswith("write it in one command and run it in the next")


def test_a_startup_file_that_writes_nothing_leaves_the_script_readable(scripts: Path) -> None:
    (scripts / "quiet.sh").write_text("echo quiet\n")

    assert decide(Policy(scripts), shell("BASH_ENV=./quiet.sh bash -c 'bash ./good.sh'")) is None


@pytest.mark.parametrize(
    "text",
    [
        "BASH_ENV=./bad.sh; bash -c true",
        "export BASH_ENV=./bad.sh; bash -c true",
    ],
)
def test_a_startup_file_set_earlier_in_the_command_is_read(scripts: Path, text: str) -> None:
    assert decide(Policy(scripts), shell(text)) == f"`./bad.sh` uses --no-verify, {BYPASS}"


def test_a_startup_file_set_where_the_guard_cant_follow_it_is_refused(scripts: Path) -> None:
    assert decide(Policy(scripts), shell("(BASH_ENV=./x); bash -c true")).endswith(
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
        decide(Policy(scripts), shell("env -S 'BASH_ENV=./bad.sh bash -c true'"))
        == f"`./bad.sh` uses --no-verify, {BYPASS}"
    )
    shebang(scripts / "tool", "#!/usr/bin/env -S BASH_ENV=./bad.sh bash")
    assert decide(Policy(scripts), shell("./tool")) == f"`./bad.sh` uses --no-verify, {BYPASS}"


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


def test_an_escaped_character_in_a_double_quoted_delimiter_ends_the_document_where_the_shell_does() -> None:
    text = 'cat <<"\\$END"\nhello\n$END\ngit commit --no-verify -m x'

    assert decide(WRITE, shell(text)).endswith(BYPASS)
    assert decide(WRITE, shell('cat <<"\\$END"\nhello\n$END\necho after')) is None


def test_an_unquoted_here_documents_escapes_are_removed_before_the_shell_reads_it() -> None:
    assert "builds a command at run time (`$CMD`)" in decide(WRITE, shell("bash <<EOF\n\\$CMD\nEOF"))
    assert decide(WRITE, shell("bash <<EOF\necho \\$HOME\nEOF")) is None


@pytest.mark.parametrize(
    "text",
    [
        "cd {root}/sub || cd {root}; bash ./x.sh",
        "true && cd {root}/sub; bash ./x.sh",
        "cd {root}/sub | cat; bash ./x.sh",
        "cd {root}/sub & bash ./x.sh",
        "cd {root}/missing; bash ./x.sh",
    ],
)
def test_a_folder_change_that_may_not_happen_leaves_the_folder_unknown(scripts: Path, text: str) -> None:
    assert decide(Policy(scripts), shell(text.format(root=scripts))).endswith("use an absolute path")


def test_a_startup_variable_set_conditionally_is_not_followed(scripts: Path) -> None:
    text = "export BASH_ENV=./bad.sh\nfalse && export BASH_ENV=./good.sh\nbash -c true"

    assert decide(Policy(scripts), shell(text)).endswith("set where the guard can't follow it")


def test_a_script_run_by_path_keeps_the_variables_it_was_started_with(scripts: Path) -> None:
    shebang(scripts / "fine", "#!/bin/bash")

    assert decide(Policy(scripts), shell("BASH_ENV=./bad.sh ./fine")) == f"`./bad.sh` uses --no-verify, {BYPASS}"
    assert decide(Policy(scripts), shell("env BASH_ENV=./bad.sh ./fine")) == f"`./bad.sh` uses --no-verify, {BYPASS}"
    assert decide(Policy(scripts), shell("BASH_ENV=./good.sh ./fine")) is None


@pytest.mark.parametrize("prefix", ["command ", "builtin "])
def test_exec_behind_command_or_builtin_still_redirects_the_shells_input(prefix: str) -> None:
    assert decide(WRITE, shell(f"{prefix}exec <<< 'echo hi'\nsh")).endswith(PIPED)
    assert decide(WRITE, shell(f"{prefix}sh -c 'echo hi'")) is None


def test_a_command_env_split_string_hides_is_judged_for_writes(scripts: Path) -> None:
    assert (
        decide(READ, shell("env -S 'rm x'"))
        == "`env -S 'rm x'` uses filesystem mutation 'rm', which writes in a read-only step"
    )
    assert decide(READ, shell("env -S 'echo hi'")) is None
    assert decide(Policy(scripts), shell("env -S 'cp a b'; /usr/bin/env echo hi")).endswith("run it in the next")


@pytest.mark.parametrize("text", ["env -C sub sh -c 'bash x.sh'", "find sub -execdir sh -c 'bash x.sh' \\;"])
def test_a_shell_started_in_another_folder_reads_relative_scripts_nowhere(scripts: Path, text: str) -> None:
    assert decide(Policy(scripts), shell(text)).endswith("use an absolute path")
    assert decide(Policy(scripts), shell(text.replace("x.sh", f"{scripts}/good.sh"))) is None


def test_a_launcher_run_by_path_is_checked_with_nothing_for_it_to_run(scripts: Path) -> None:
    shebang(scripts / "find", "#!/bin/sh", BAD)

    assert decide(Policy(scripts), shell("./find . -name x")).endswith(BYPASS)
    assert decide(Policy(scripts), shell("cp a b; /usr/bin/env")).endswith("run it in the next")
    assert decide(Policy(scripts), shell("/usr/bin/find . -name x")) is None


@pytest.mark.parametrize("text", ["source -", ". -", "source - <<< 'echo hi'"])
def test_source_reads_a_file_named_dash_not_its_input(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith("through PATH; write `./-`")


@pytest.mark.parametrize("text", ["env -S \"'$CMD' hi\"", "env -S \"bash -c 'echo $CMD'\"", 'env --split-string="$X"'])
def test_an_env_split_string_the_outer_shell_filled_in_is_refused(text: str) -> None:
    assert decide(WRITE, shell(text)) == f"`{text}` uses env -S with text built at run time; write it out"


def test_a_function_body_is_not_the_shells_own_folder(scripts: Path) -> None:
    for text in (f"function f {{\ncd {scripts}/sub\n}}\nbash ./x.sh", f"f() {{\ncd {scripts}/sub\n}}\nbash ./x.sh"):
        assert decide(Policy(scripts), shell(text)).endswith("use an absolute path")
    assert decide(Policy(scripts), shell(f"function f {{\ncd {scripts}/sub\n}}\nbash {scripts}/good.sh")) is None


@pytest.mark.parametrize("first", ["#!/bin/sh\t-e", "#!/usr/bin/env\tbash", "#! /bin/sh"])
def test_a_shebang_separated_by_tabs_or_spaces_names_the_same_shell(scripts: Path, first: str) -> None:
    shebang(scripts / "tool", first, BAD)
    shebang(scripts / "fine", first)

    assert decide(Policy(scripts), shell("./tool")).endswith(BYPASS)
    assert decide(Policy(scripts), shell("./fine")) is None


@pytest.mark.parametrize("prefix", ["command -- ", "command -p ", "builtin -- "])
def test_exec_or_export_behind_command_options_still_changes_the_shell(scripts: Path, prefix: str) -> None:
    assert decide(WRITE, shell(f"{prefix}exec <<< 'echo hi'\nbash")).endswith(PIPED)
    assert decide(Policy(scripts), shell(f"{prefix}export BASH_ENV=./bad.sh\nbash -c true")) == (
        f"`./bad.sh` uses --no-verify, {BYPASS}"
    )


def test_a_shebangs_environment_is_judged_like_a_typed_one(scripts: Path) -> None:
    first = "#!/usr/bin/env -S GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x bash"
    shebang(scripts / "tool", first, "git commit -m x\n")

    assert decide(Policy(scripts), shell("./tool")) == (
        f"`./tool` uses environment setting core.hooksPath=/x, {BYPASS}"
    )


def test_a_script_run_by_path_in_another_folder_reads_relative_scripts_nowhere(scripts: Path) -> None:
    shebang(scripts / "tool", "#!/bin/sh", "bash ./x.sh\n")

    assert decide(Policy(scripts), shell(f"env -C sub {scripts}/tool")).endswith("use an absolute path")
    assert decide(Policy(scripts), shell(f"{scripts}/tool")) is None


def test_a_write_in_a_here_documents_substitution_comes_before_the_command_that_reads_it(scripts: Path) -> None:
    assert decide(Policy(scripts), shell("bash good.sh <<EOF\n$(cp bad.sh good.sh)\nEOF")).endswith(
        "run it in the next"
    )
    assert decide(Policy(scripts), shell("bash good.sh <<'EOF'\n$(cp bad.sh good.sh)\nEOF")) is None


def test_a_write_by_one_find_action_comes_before_the_next(scripts: Path) -> None:
    text = "find . -maxdepth 0 -exec cp bad.sh good.sh \\; -exec bash good.sh \\;"

    assert decide(Policy(scripts), shell(text)).endswith("run it in the next")
    assert decide(Policy(scripts), shell("find . -maxdepth 0 -exec bash good.sh \\;")) is None


@pytest.mark.parametrize(("text", "shown"), [("$'bash' bad.sh", "$bash"), ("bash $'bad.sh'", None)])
def test_ansi_c_quoting_is_not_decoded_but_refused(scripts: Path, text: str, shown: str | None) -> None:
    reason = decide(Policy(scripts), shell(text))

    if shown:
        assert reason == f"`{text}` builds a command at run time (`{shown}`); write the program and its script out"
    else:
        assert reason.endswith("a path built at run time; write the path out")


@pytest.mark.parametrize(
    "wrapper", ['"$WRAP/env" echo hi', '"${TOOL_DIR}/timeout" 5 echo hi', '"$WRAP/find" . -name x']
)
def test_a_wrapper_whose_name_is_built_at_run_time_is_refused(wrapper: str) -> None:
    assert "builds a command at run time" in decide(WRITE, shell(wrapper))
    assert decide(WRITE, shell("/usr/bin/env echo hi")) is None


@pytest.mark.parametrize(
    "text",
    [
        "if true; then export BASH_ENV=./bad.sh; fi; bash -c true",
        "if true; then BASH_ENV=./bad.sh; fi; bash -c true",
    ],
)
def test_a_startup_variable_set_after_a_control_word_is_not_followed(scripts: Path, text: str) -> None:
    assert decide(Policy(scripts), shell(text)).endswith("set where the guard can't follow it")


@pytest.mark.parametrize(
    "text",
    [
        "if true; then exec <<< 'echo hi'; fi; sh",
        "printf x | time -p sh",
        "f() { sh; }\nprintf x | f",
        "function f { sh; }\nprintf x | f",
    ],
)
def test_input_hidden_by_a_control_word_time_or_a_function_is_refused(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(PIPED)


def test_time_and_functions_keep_their_readable_counterparts() -> None:
    assert decide(WRITE, shell("time -p sh -c 'echo hi'")) is None
    assert decide(WRITE, shell("f() { sh -c 'echo hi'; }\nf")) is None
    assert decide(WRITE, shell("printf data | time -p $CMD")).endswith(
        "builds a command at run time (`$CMD`); write the program and its script out"
    )


@pytest.mark.parametrize("delimiter", ["\\\nEOF", "$'EOF'"])
def test_a_here_document_delimiter_the_guard_reads_differently_hides_nothing(delimiter: str) -> None:
    text = f"cat << {delimiter}\nhello\nEOF\ngit commit --no-verify -m x"

    reason = decide(WRITE, shell(text))
    assert reason is not None
    assert reason.endswith((BYPASS, "cannot be parsed"))
    assert decide(WRITE, shell("cat << \\\nEOF\nhello\nEOF\necho after")) is None


@pytest.mark.parametrize("prefix", ["command ", "builtin ", "if true; then "])
def test_git_settings_exported_behind_a_prefix_stay_refused(prefix: str) -> None:
    text = f"{prefix}export GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/x'\""
    text += "; fi; git status" if prefix.startswith("if") else "; git status"

    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_a_function_defined_with_the_keyword_is_judged_like_its_body() -> None:
    assert decide(WRITE, shell("function f { git push -f; }")).endswith(BYPASS)
    assert decide(WRITE, shell("function f { echo hi; }")) is None


def test_a_shebang_interpreter_built_at_run_time_is_refused(scripts: Path) -> None:
    shebang(scripts / "tool", "#!/usr/bin/env -S ${OB_INTERP}", "rm x\n")

    assert decide(Policy(scripts), shell("OB_INTERP=/bin/sh ./tool")) == (
        "`OB_INTERP=/bin/sh ./tool` runs `./tool`, whose interpreter is built at run time (`${OB_INTERP}`)"
    )


def test_a_subshells_output_redirection_is_a_write_before_what_follows(scripts: Path) -> None:
    text = "(printf '%s\\n' 'git commit --no-verify -m x') > good.sh; bash good.sh"

    assert decide(Policy(scripts), shell(text)).endswith("run it in the next")
    assert decide(Policy(scripts), shell("(echo hi) > /dev/null; bash good.sh")) is None


@pytest.mark.parametrize(
    "text",
    [
        "env -S 'nohup env sh' <<'EOF'\ngit commit --no-verify -m x\nEOF",
        "nohup timeout 3 sh <<'EOF'\ngit commit --no-verify -m x\nEOF",
    ],
)
def test_stacked_wrappers_still_reach_the_shell(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_wrappers_stacked_past_the_limit_are_refused_unread() -> None:
    text = "nohup " * 9 + "echo hi"

    assert decide(WRITE, shell(text)) == f"`{text}` runs wrapper programs more than 8 deep"


@pytest.mark.parametrize(
    "text",
    [
        "BASH_ENV=/missing env -u BASH_ENV bash -c true",
        "BASH_ENV=/missing env -i bash -c true",
        "export BASH_ENV=/missing; env --unset=BASH_ENV bash -c true",
    ],
)
def test_a_startup_file_env_removes_is_not_read(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


def test_a_startup_file_set_again_after_env_removes_one_is_read(scripts: Path) -> None:
    assert decide(Policy(scripts), shell("BASH_ENV=/missing env -u BASH_ENV BASH_ENV=./bad.sh bash -c true")) == (
        f"`./bad.sh` uses --no-verify, {BYPASS}"
    )


@pytest.mark.parametrize(
    "text",
    [
        "((1<<x))\ngit commit --no-verify -m wip\nx",
        "for ((i=0; i<<x; i++)); do :; done\ngit commit --no-verify -m wip\nx",
        "echo $[1<<x]\ngit commit --no-verify -m wip\nx",
        "echo ${a:-<<x}\ngit commit --no-verify -m wip\nx}",
        "((git push -f); true)",
    ],
)
def test_a_shift_in_arithmetic_or_a_parameter_is_no_here_document(text: str) -> None:
    for policy in (READ, WRITE):
        assert decide(policy, shell(text)).endswith(BYPASS)


@pytest.mark.parametrize("text", ["echo $((1<<2))", "for ((i=0;i<3;i++)); do echo $i; done", "echo ${HOME:-x}"])
def test_ordinary_arithmetic_and_parameters_run(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


def test_the_runtimes_segments_are_checked_for_a_bypass_too() -> None:
    misread = view(
        cli_shell("((1<<x))\ngit commit --no-verify -m x\nx", "((1<<x))", "git commit --no-verify -m x", "x")
    )

    assert misread.commands[1] == "git commit --no-verify -m x"
    assert decide(WRITE, misread).endswith(BYPASS)


STARTUP = (
    "reads startup files of its own; use bash or sh without -i or -l, or zsh -f, fish --no-config, bash --norc"
    " --noprofile"
)


@pytest.mark.parametrize(
    "text",
    ["zsh -c true", "ZDOTDIR=/tmp/x zsh -c true", "fish -c true", "bash -ic true", "bash -l -c true", "sh -l -c true"],
)
def test_a_shell_that_reads_startup_files_of_its_own_is_refused(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith(STARTUP)


@pytest.mark.parametrize(
    "text",
    [
        "zsh -f -c true",
        "fish --no-config -c true",
        "bash --norc -ic true",
        "bash --noprofile -l -c true",
        "bash -c true",
    ],
)
def test_a_shell_told_not_to_read_its_own_startup_files_runs(text: str) -> None:
    assert decide(WRITE, shell(text)) is None


def test_a_bypass_in_a_startup_reading_shells_script_is_still_a_bypass() -> None:
    assert decide(WRITE, shell("zsh -c 'git push -f'")) == f"`git push -f` uses -f, {BYPASS}"


@pytest.mark.parametrize(
    "text",
    ["HOME=/tmp/elsewhere; bash ~/good.sh", "export HOME=/tmp/elsewhere; . ~/good.sh", "unset HOME; bash ~/good.sh"],
)
def test_a_tilde_after_home_changed_is_refused(scripts: Path, text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(scripts))

    assert decide(Policy(scripts), shell(text)).endswith("a path built at run time; write the path out")
    assert decide(Policy(scripts), shell("bash ~/good.sh")) is None


@pytest.mark.parametrize("text", ["bash ~+/good.sh", "bash ~-/good.sh", "bash ~root/x.sh"])
def test_a_tilde_form_the_guard_doesnt_expand_is_refused(scripts: Path, text: str) -> None:
    assert decide(Policy(scripts), shell(text)).endswith("a path built at run time; write the path out")


@pytest.mark.parametrize(
    "text",
    ["bash /dev/fd/3 3<<'E'\ngit commit --no-verify -m wip\nE", "source /proc/self/fd/0", "bash /dev/tty"],
)
def test_a_device_or_process_file_is_not_read_by_the_guard(text: str) -> None:
    assert decide(WRITE, shell(text)).endswith("a device or process file the guard doesn't read")


def test_a_bypass_in_a_shells_script_is_named_before_a_missing_shell_file() -> None:
    text = "/nonexistent/zsh -c 'cd x && git push -f'"  # /bin/zsh on a machine without zsh

    assert decide(WRITE, shell(text)) == f"`cd x && git push -f` uses -f, {BYPASS}"


def test_a_declaration_naming_home_and_a_startup_file_records_both(scripts: Path) -> None:
    text = "export BASH_ENV=./good.sh; declare HOME=/tmp BASH_ENV=./bad.sh; bash -c true"

    assert decide(Policy(scripts), shell(text)).endswith("set where the guard can't follow it")


def test_a_shebang_interpreter_that_is_itself_a_script_is_refused(scripts: Path) -> None:
    shebang(scripts / "env", "#!/bin/sh", BAD)
    shebang(scripts / "tool", f"#!{scripts}/env bash")

    assert decide(Policy(scripts), shell("./tool")) == (
        f"`./tool` runs `./tool`, whose interpreter `{scripts}/env` is itself a script"
    )


def test_a_tilde_in_a_shell_started_with_another_home_is_refused(scripts: Path) -> None:
    for text in ("HOME=/other bash -c 'bash ~/good.sh'", "env -u HOME bash -c 'bash ~/good.sh'"):
        assert decide(Policy(scripts), shell(text)).endswith("a path built at run time; write the path out")


def test_a_link_to_a_process_file_is_not_followed(scripts: Path) -> None:
    (scripts / "here").symlink_to("/proc/self/cwd")

    assert decide(Policy(scripts), shell("bash here/x.sh")).endswith("a device or process file the guard doesn't read")


def test_a_locale_translated_word_is_built_at_run_time(scripts: Path) -> None:
    assert decide(Policy(scripts), shell('$"bash" bad.sh')).endswith("write the program and its script out")
    assert decide(WRITE, shell('echo "cost $"')) is None


def test_a_substitution_in_a_double_quoted_parameter_default_is_judged() -> None:
    text = "unset x; echo \"${x:-'$(git commit --no-verify -m x)'}\""

    assert decide(WRITE, shell(text)).endswith(BYPASS)


def test_arithmetic_inside_a_parameter_is_no_here_document() -> None:
    assert decide(WRITE, shell("echo ${a:-$((1<<x))}\ngit commit --no-verify -m x\nx")).endswith(BYPASS)


def test_a_here_document_delimiter_joined_by_a_continuation_ends_the_body(scripts: Path) -> None:
    (scripts / "joined.sh").write_text("cat <<EOF\nhi\nEO\\\nF\ngit commit --no-verify -m x\n")

    assert decide(Policy(scripts), shell("bash joined.sh")).endswith(BYPASS)
    assert decide(WRITE, shell("cat <<'EOF'\nEO\\\nF\nEOF")) is None  # a quoted body joins nothing
