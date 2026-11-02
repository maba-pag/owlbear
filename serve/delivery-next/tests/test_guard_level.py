"""The guard level ladder (#864): which class of finding each level refuses, warns about or lets through."""

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import git_reading, permissions, shell_walk
from owlbear_delivery_next.change_contracts.permissions import BYPASS, Policy, Request, Verdict, judge
from owlbear_delivery_next.local_system import shell_parse

ROOT = Path("/w")
READ, WRITE = Policy(ROOT, write=False), Policy(ROOT)
LEVELS = ("strict", "standard", "lenient", "off")
CLASSES = {  # one each class finds first
    "core": "git commit --no-verify -m x",
    "variant": "HUSKY=0 git commit -m x",
    "doubtful": "git commit $FLAGS -m x",
}
OUTCOMES = {  # per level: what core, variant and doubtful findings get
    "strict": ("refuse", "refuse", "warn"),
    "standard": ("refuse", "warn", "warn"),
    "lenient": ("warn", "warn", "warn"),
    "off": ("allow", "allow", "allow"),
}


def shell(text: str) -> Request:
    return Request("shell", (text,), text=text)


def outcome(verdict: Verdict | None) -> str:
    return "allow" if verdict is None else "refuse" if verdict.refuse else "warn"


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("found", list(CLASSES))
def test_each_level_refuses_warns_or_allows_each_class(found: str, level: str) -> None:
    expected = OUTCOMES[level][["core", "variant", "doubtful"].index(found)]
    assert outcome(judge(WRITE, shell(CLASSES[found]), level=level)) == expected


@pytest.mark.parametrize("level", ["lenient", "off"])
@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("git commit --no-verify -m x", True),
        ("git commit --no-verify -m x; touch x", True),
        ("touch x; git commit --no-verify -m x", True),
        ("bash -c 'git -c core.hooksPath=/dev/null status'; bash -c 'touch x'", True),
        ("echo '", False),
        ("HUSKY=0 git commit -m x", True),
    ],
)
def test_a_read_only_steps_writes_are_refused_at_every_level(text: str, *, named: bool, level: str) -> None:
    verdict = judge(READ, shell(text), level=level)
    assert verdict is not None
    assert verdict.refuse
    assert ("read-only step" in verdict.reason or "cannot be parsed" in verdict.reason) is True
    assert permissions.bypass(verdict.reason) is named  # a bypass it names isn't counted as a wrong tool


@pytest.mark.parametrize(
    "text",
    ["echo '", "$PROGRAM hello", "printf hello | bash", 'bash -c "$X"', "touch x; ./x.sh", "bash missing/x.sh"],
)
def test_what_a_write_step_cant_read_is_a_core_finding(tmp_path: Path, text: str) -> None:
    (tmp_path / "x.sh").write_text("echo hi\n")
    policy = Policy(tmp_path)
    assert [outcome(judge(policy, shell(text), level=level)) for level in LEVELS] == [
        "refuse",
        "refuse",
        "warn",
        "allow",
    ]


def test_off_reads_no_shell_command_in_a_write_step(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(shell_parse, "parse", fail)
    monkeypatch.setattr(git_reading, "bypass", fail)
    monkeypatch.setattr(shell_walk.Walk, "commands", fail)
    assert judge(WRITE, shell("git commit --no-verify -m x"), level="off") is None


@pytest.mark.parametrize("level", ["strict", "off"])
@pytest.mark.parametrize(
    ("policy", "req", "memory", "refused"),
    [
        (READ, Request("write", paths=("a.ts",)), False, "writes are not allowed in this step"),
        (READ, Request("read", paths=("/etc/hosts",)), False, None),
        (Policy(ROOT, confined=True), shell("ls"), False, "this step runs no shell commands"),
        (Policy(ROOT, confined=True), Request("write", paths=("../x",)), False, "../x is outside this step's folder"),
        (Policy(ROOT, confined=True), Request("write", paths=("x",)), False, None),
        (WRITE, Request("mcp", tool="other-x", server="other"), False, "mcp requests are not allowed in this step"),
        (WRITE, Request("mcp", tool="owlbear-x", server="owlbear"), False, None),
        (WRITE, Request("memory", tool="store_memory"), False, "Copilot Memory is off for Delivery's sessions"),
        (WRITE, Request("memory", tool="store_memory"), True, None),
        (WRITE, Request("custom-tool", tool="nope"), False, "tool nope is not allowed"),
        (WRITE, Request("url"), False, None),
    ],
)
def test_the_rules_outside_the_ladder_hold_at_every_level(
    policy: Policy, req: Request, *, memory: bool, refused: str | None, level: str
) -> None:
    offered = frozenset({"owlbear/x", "store_memory"})
    verdict = judge(policy, req, offered, memory=memory, level=level)
    if refused is None:
        assert verdict is None
    else:
        assert verdict is not None
        assert verdict.refuse
        assert verdict.reason.startswith(refused)


def test_decide_returns_only_refusals() -> None:
    text = "git commit --no-verify -m x"
    assert permissions.decide(WRITE, shell(text)) == f"`{text}` uses --no-verify, {BYPASS}"
    assert permissions.decide(WRITE, shell(text), level="lenient") is None


ROUTES = {  # #864's routes: each case's command and the class it is found in, or None when allowed
    8: [  # a program named by a glob or brace is picked from file names at run time
        ("/usr/bin/gi? commit --no-verify -m x", "core"),
        ("g?t commit --no-verify -m x", "core"),
        ("gi[t] commit -m x", "core"),
        ("{git,commit} --no-verify", "core"),
        ('case "$x" in a*) git commit --no-verify;; esac', "core"),  # an arm's commands are still read
        ("'g?t' status", None),
        (r"g\?t status", None),
        ("case $x in a*) echo;; esac", None),
        ("case $x in\n (a*|b?) echo;;\n *) ls;;\nesac", None),
        ("curl 'https://x/?a=1'", None),
        ("curl https://x/?a=1", None),
        ("echo *.py", None),
        ("[ -f x ]", None),
        ("[[ x ]]", None),
        ("{ echo; }", None),
        ('files=(*.py); echo "${files[@]}"', None),
        ("echo $? $*", None),
    ],
    13: [  # a mirror push force-updates and deletes every remote ref
        ("git push --mirror", "core"),
        ("git -c remote.origin.mirror=yes push", "core"),
        ("git config remote.origin.mirror true && git push", "core"),
        ("git config remote.origin.mirror true", "core"),  # its push may come in the next command
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true git push", "core"),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true bash -c 'git push'", "core"),
        ("git -c remote.origin.mirror=true rebase -x 'git push' main", "core"),
        ("git -c remote.origin.mirror=true -c alias.p='!git push' p", "core"),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.o.mirror GIT_CONFIG_VALUE_0=1 git rebase -x 'git push' m", "core"),
        ("export GIT_CONFIG_PARAMETERS=\"'remote.origin.mirror'='true'\"; git push", "core"),
        ("git remote add --mirror=push o u", "core"),
        ("git remote add --mirror o u", "core"),
        ("git remote -v add --mirror=push o u", "core"),  # remote's own -v comes before add
        ("MIRROR=true git --config-env=remote.origin.mirror=MIRROR push", "core"),
        ("MIRROR=false git --config-env=remote.origin.mirror=MIRROR push", None),
        ("git -c remote.origin.mirror=yes fetch", None),
        ("git remote add --mirror=fetch o u", None),
        ("git clone --mirror u d", None),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true git status", None),
        ("env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true git fetch", None),
        # an export outlives its command, so its push may come later
        ("export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true", "core"),
        *((f"git -c remote.origin.mirror{v} push", "core") for v in ("=true", "=YES", "=on", "=1", "=-3", "")),
        *((f"git -c remote.origin.mirror={v} push", None) for v in ("false", "no", "off", "0", "")),
    ],
    3: [  # a git alias the command defines runs its body
        ("git -c alias.ci='commit --no-verify' ci", "variant"),
        ("git -c alias.ci='!git commit --no-verify' ci", "variant"),
        ("CI='commit -n' git --config-env=alias.ci=CI ci", "variant"),
        ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.ci GIT_CONFIG_VALUE_0='push --force' git ci", "variant"),
        ("git config alias.c 'commit --no-verify' && git c -m x", "variant"),
        ("GIT_CONFIG_PARAMETERS=\"'alias.c'='commit -n'\" git c -m x", "variant"),
        ("git -c alias.st=status st", None),
        ("git -c alias.lg='!git log --oneline' lg", None),
        ("HUSKY=0 git -c alias.c='!git commit -m x' c", "variant"),  # the run that calls it passes HUSKY on
        ("HUSKY=0 git -c alias.c='commit -m x' c", "variant"),
        ("export HUSKY=0; env -u HUSKY git -c alias.c='!git commit -m x' c", None),
        ("HUSKY=0 git config alias.c '!git commit -m x'", None),  # it runs later, with the shell's variables
        ("git c -m x", None),  # an alias already in config: a documented limit
        ("git --config-env=alias.ci=UNKNOWN ci", None),
    ],
    5: [  # commands git runs
        ("git rebase -x 'git commit --amend --no-verify' main", "variant"),
        ("git rebase --exec 'git commit --amend --no-verify' main", "variant"),
        ("git rebase --exec='git push --force' main", "variant"),
        ("git rebase -ix 'git commit -n' main", "variant"),
        ("git rebase -x /usr/bin/true main", "variant"),  # a file it runs may be one the rebase just wrote
        ("git rebase -x 'make test' main", None),
        ("git submodule foreach '/bin/echo hi'", None),
        ("git submodule foreach './fix'", "variant"),  # from each submodule's folder, which the guard can't follow
        ("git submodule foreach 'git push --force'", "variant"),
        ("git submodule --quiet foreach --recursive 'git push --force'", "variant"),
        ("git submodule foreach bash -c 'git commit --no-verify -m x'", "variant"),  # sh -c '<first> "$@"' <the rest>
        ("git submodule foreach git status --short", None),
        ("BASH_ENV=/w/start.sh git rebase -x 'bash -c \"git status\"' main", "variant"),  # its bash reads it
        ("export BASH_ENV=/w/start.sh; env -u BASH_ENV git submodule foreach 'bash -c \"git status\"'", None),
        ("git submodule foreach bash -c -- 'git commit --no-verify -m x'", "variant"),  # its -- is bash's
        ("git submodule foreach git commit -q -n -m x", "variant"),
        ('FLAG=-n; git submodule foreach git commit "$FLAG" -m x', "doubtful"),  # git hands it -n
        ("git submodule foreach -- 'git push --force'", None),  # git refuses foreach --, running nothing
        ("git bisect run 'git commit -n'", None),  # a documented limit
    ],
    10: [  # hook tools' switches
        ("HUSKY=0 git commit -m x", "variant"),
        ("env LEFTHOOK=false git push", "variant"),
        ("export SKIP=lint; git commit -m x", "variant"),
        ("LEFTHOOK_EXCLUDE=x git commit -m x", "variant"),
        ("export HUSKY=0; bash -c 'git commit -m x'", "variant"),
        ("HUSKY=0 eval 'git commit -m x'", "variant"),
        ("HUSKY=0 eval 'git status'; git commit -m x", None),  # only for that text
        ("export HUSKY=0; HUSKY=1 eval 'unset HUSKY'; git commit -m x", "variant"),  # bash restores HUSKY=0
        ("HUSKY=1 eval 'export HUSKY=0'; git commit -m x", None),
        ("HUSKY=1 eval 'unset HUSKY'; git commit -m x", None),  # nothing to restore
        ("export HUSKY=0; (export HUSKY=1); git commit -m x", "variant"),
        ("export HUSKY=0; if false; then export HUSKY=1; fi; git commit -m x", "variant"),
        ('export HUSKY="$OFF"; (export HUSKY=1); git commit -m x', "doubtful"),
        ("export HUSKY=1; if x; then export HUSKY=0; fi; git commit -m x", "variant"),
        ("HUSKY=0 git submodule foreach 'git commit -m x'", "variant"),
        ("export HUSKY=0; env -u HUSKY git submodule foreach 'git commit -m x'", None),
        ('HUSKY=0 git commit "$FLAGS" -m x', "variant"),
        ("HUSKY=0 git commit --no-verify -m x", "core"),  # the core reason comes first
        ("HUSKY=2 git commit -m x", None),
        ("LEFTHOOK=1 git commit -m x", None),
        ("SKIP= git commit -m x", None),
        ("export HUSKY=0; unset HUSKY; git commit -m x", None),
        ("export HUSKY=0; env -u HUSKY git commit -m x", None),
        ("SKIP=lint pre-commit run", None),
        ("HUSKY=0 git status", None),
    ],
    1: [  # commands in an interpreter's inline code
        ("""python3 -c 'import subprocess; subprocess.run(["git", "commit", "--no-verify", "-m", "x"])'""", "doubtful"),
        ("""node -e "require('child_process').execSync('git push --force')\"""", "doubtful"),
        ("perl -e 'system(\"git push --force\")'", "doubtful"),
        ("perl -e '1;' -e 'system(\"git push --force\")'", "doubtful"),  # perl runs every -e
        ("python3 -Bc 'import os; os.system(\"git push -f\")'", "doubtful"),
        ("python3 -Bc'import os; os.system(\"git push -f\")'", "doubtful"),
        ("python3 -W ignore -c 'import os; os.system(\"git push -f\")'", "doubtful"),
        ('node -r path -e \'require("child_process").execSync("git push -f")\'', "doubtful"),
        ("perl -we'system(\"git push --force\")'", "doubtful"),
        ("python3 -- - <<'EOF'\nimport os\nos.system('git push -f')\nEOF", "doubtful"),
        ("python3 <<'EOF'\nimport os\nos.system('git commit -n -m x')\nEOF", "doubtful"),
        ("python3 <<< 'import os; os.system(\"git commit -n\")'", "doubtful"),
        ("python3 -c 'print(\"git commit --no-verify\")'", "doubtful"),  # printing it reads the same
        ("python3 -c 'print(1)'", None),
        ("python3 script.py --no-verify", None),  # a script file: a documented limit
        ("python3 -m pytest -k 'git commit --no-verify'", None),
    ],
    4: [  # git words built at run time
        ("git commit $FLAG -m x", "doubtful"),
        ('git commit -"$FLAG" -m x', "doubtful"),  # not -F with a value
        ('git commit -m"$MSG"', None),
        ("git $SUB", "doubtful"),
        ('git commit "$@"', "doubtful"),
        ('git commit "${args[@]}"', "doubtful"),
        ("git commit -m $MSG", "doubtful"),  # split, so it may be several words
        ('git push origin "$REFSPEC"', "doubtful"),
        ('git -c "$K"=x commit -m x', "doubtful"),
        ('git -c commit.gpgsign="$V" commit -m x', "doubtful"),
        ('GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0="$V" git commit -m x', "doubtful"),
        ('git config commit.gpgsign "$V"', "doubtful"),
        ('MIRROR="$V" git --config-env=remote.origin.mirror=MIRROR push', "doubtful"),
        ('VALUE=false git --config-env="$K"=VALUE commit -m x', "doubtful"),
        ('git --config-env=remote.origin.mirror="$VARNAME" push', "doubtful"),
        ('git -c remote.origin.mirror="$M" fetch', None),
        ('git -c core.hooksPath="$P" commit -m x', "core"),  # the key alone skips hooks
        ('HUSKY="$OFF" git commit -m x', "doubtful"),
        ('export HUSKY="$OFF"; unset HUSKY; git commit -m x', None),
        ('git commit -m "$MSG"', None),
        ('git commit --message="$MSG"', None),
        ('git commit --gpg-sign="$KEYID" -m x', None),  # any long option's attached value stays one word
        ('git add -- "$F"', None),
        ('git config user.name "$N"', None),
        ('git -c "$K" status', None),
        ('git log "$REV"', None),
    ],
}
SEEN = {"refuse": "refused", "warn": "warned", "allow": "allowed"}


@pytest.mark.parametrize("level", ["strict", "standard"])
@pytest.mark.parametrize(
    ("text", "found"),
    [pytest.param(t, f, id=f"route{r}-{t}") for r, cases in ROUTES.items() for t, f in cases],
)
def test_each_routes_cases_through_the_guard_and_a_steps_session(
    through_step, text: str, found: str | None, level: str
):
    expected = "allow" if found is None else OUTCOMES[level][["core", "variant", "doubtful"].index(found)]
    assert outcome(judge(WRITE, shell(text), level=level)) == expected
    got = through_step(text, level)
    assert got.outcome == SEEN[expected]
    assert [e["event"] for e in got.events] == {"refuse": ["denied"], "warn": ["warned"], "allow": []}[expected]
