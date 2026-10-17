from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.permissions import Policy, Request, decide, view

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
        "bash scripts/check.sh --force",
        "timeout 5 npm run build -- --force",
        "echo git push -f",
        "xargs grep -- git push -f",
        "bash -c ' '",
        "eval '# a comment'",
        "git config user.name x",
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
