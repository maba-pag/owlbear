"""The guard level ladder (#864): which class of finding each level refuses, warns about or lets through."""

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import git_reading, permissions, shell_walk
from owlbear_delivery_next.change_contracts.permissions import BYPASS, Policy, Request, Verdict, judge
from owlbear_delivery_next.local_system import shell_parse

ROOT = Path("/w")
READ, WRITE = Policy(ROOT, write=False), Policy(ROOT)
LEVELS = ("strict", "standard", "lenient", "off")
CLASSES = {"core": "git commit --no-verify -m x"}  # one command each class finds first
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
