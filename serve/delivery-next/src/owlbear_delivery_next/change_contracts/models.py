"""Delivery-next state records for one Change (D3 §3.1 to §3.3)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts.amendment_records import Amendment
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.decision_records import (
    BriefDecision,
    Decision,
    DecisionBaseline,
    Pick,
    Published,
)
from owlbear_delivery_next.change_contracts.merge_records import Episode, Pullback, QueueClaim
from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.change_contracts.spend import Spend
from owlbear_delivery_next.change_contracts.tool_use import ToolUse
from owlbear_delivery_next.change_contracts.visual_records import OwnerCriterion, VisualResult, VisualRound

FORMAT = 7
DETAIL = 60000  # one review batch: up to 20 new and 20 owner-decided findings of about 1,300 characters

type Actor = Literal["you", "admin", "delivery", "github"]
type Channel = Literal["status-view", "chat"]
type Role = Literal[
    "planner", "builder", "reviewer", "challenger", "design-judge", "preparer", "shaper", "updater", "test-reviewer",
    "test-curator", "picker", "curator",
]  # fmt: skip
type Effort = Literal["low", "medium", "high", "xhigh", "max"]
type Context = Literal["default", "long"]  # the model's default context tier, or its long-context tier
type Move = Literal["done", "pause", "abandon", "retry", "accept", "repair", "reconsider", "another", "rebuild"]
type AnswerKind = Literal["event", "clarification", "brief_change"]  # its relayer's class of a worker's answer


class StepKind(StrEnum):
    """The eleven step kinds; TESTS is a test review's parallel reviewers (TD-373)."""

    SHAPE = "shape"
    PLAN = "plan"
    TESTS = "tests"
    BUILD = "build"
    REVIEW = "review"
    INTEGRATE = "integrate"
    PUBLISH = "publish"
    FOLLOW = "follow"
    CHECK = "check"
    MERGE = "merge"
    CLEANUP = "cleanup"


class Exit(StrEnum):
    """The five exits, plus pending on a named external condition."""

    DONE = "done"
    RETRY = "retry"
    ASK = "ask"
    BACK = "back"
    STOP = "stop"
    PENDING = "pending"


class ErrorKind(StrEnum):
    """The fifteen error kinds; every cause key starts with one."""

    AUTH = "auth"
    POLICY = "policy"
    TOOLING = "tooling"
    NETWORK = "network"
    CAPACITY = "capacity"
    PROJECT_ENV = "project-env"
    CHECKS = "checks"
    COMMIT_POLICY = "commit-policy"
    RESULT = "result"
    LIVENESS = "liveness"
    SCOPE = "scope"
    CONFLICT = "conflict"
    REVIEW = "review"
    GATE = "gate"
    STATE = "state"


class Waiting(StrEnum):
    """Pending conditions; none consumes budget."""

    CHAT = "chat"
    CI = "ci"
    CHECK_START = "check-start"
    REVIEWER = "reviewer"
    OWNER_ACTION = "owner-action"
    PERSON_CHECK = "person-check"
    GITHUB = "github"
    NETWORK = "network"


class Record(BaseModel):
    """Strict base: unknown fields are a format error, not silently dropped."""

    model_config = ConfigDict(extra="forbid")


class Criterion(Record):
    """One acceptance criterion; its version is a review and check input."""

    id: str
    text: str
    version: int = 1


VISUAL = "visual"  # the reserved check-step task id of the engine's visual check


class VisualStep(Record):
    """One owner-authored action before a state's screenshot (TD-49), on a prepared test copy only (TD-96)."""

    do: Literal["click", "type"]
    target: str  # the control's accessible name: a button or link to click, a field's label to type into
    text: str = ""  # what to type


class VisualState(Record):
    """One page state the visual check renders: a path under the preview root, steps, and what it must show."""

    name: str
    path: str
    expect: str
    steps: list[VisualStep] = Field(default_factory=list)
    version: int = 1


class Brief(Record):
    """The user's brief: the current draft, the approved version, and each approved version's content."""

    version: int = 0
    approved_version: int | None = None
    approved_at: datetime | None = None
    challenged: int | None = None  # the version its challenge loop ended on: approvable (TD-249, TD-208)
    requested: int | None = None  # the version the shaper asked to be challenged (TD-249)
    title: str = ""
    outcome: str = ""
    scope: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    decisions: list[BriefDecision] = Field(default_factory=list)
    picked: Pick | None = None  # the existing decisions this version's work follows (TD-459)
    criteria: list[Criterion] = Field(default_factory=list)
    ui: bool = False
    visual: list[VisualState] = Field(default_factory=list)
    specified: list[str] = Field(default_factory=list)  # criteria, states and checks the owner stated (TD-179)
    approved: list[Brief] = Field(default_factory=list)


class Intent(Record):
    """The user's words and the flags read at every step boundary."""

    words: str = ""
    paused_at: datetime | None = None
    pause_reason: str = ""
    abandoned_at: datetime | None = None
    hold: bool = False


class Inputs(Record):
    """What a review or person-only check depended on; valid while unchanged (P5)."""

    criteria: dict[str, int] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)
    procedure: int = 0
    environment: list[str] = Field(default_factory=list)


class PersonCheck(Record):
    """One person-only check declared in the brief."""

    id: str
    criteria: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expect: str = ""
    visual: bool = False  # the person judges how the UI looks
    paths: list[str] = Field(default_factory=list)
    procedure: int = 1
    environment: list[str] = Field(default_factory=list)
    answer: Answer | None = None


class Option(Record):
    """One answer option; ``next`` names the step it leads to, or ``done``, ``pause``, ``abandon`` or ``retry``."""

    id: str
    label: str
    next: StepKind | Move | None = None


class Answer(Record):
    """How and when a question or person-only check was answered; a check also records pass and inputs."""

    option: str | None = None
    text: str = ""
    channel: Channel = "status-view"
    at: datetime
    passed: bool | None = None
    inputs: Inputs | None = None
    tasks: list[str] = Field(default_factory=list)  # the plan tasks a final retry rebuilds (TD-217)
    kind: AnswerKind | None = None  # TD-461: set on a worker question's answer only
    statement: str = ""  # a clarification's confirmed intent: a Change decision once checked within the brief


class Question(Record):
    """A durable question; its answer is delivered to a session, and its cause clears once the effect is observed."""

    id: str = ""
    step: StepKind
    kind: Literal["decision", "action"] = "decision"
    text: str
    options: list[Option] = Field(default_factory=list)
    cause: str | None = None
    repair: list[Task] = Field(default_factory=list)  # a review round gate's pending repair, built only on its Fix
    answer: Answer | None = None
    delivered_at: datetime | None = None
    effect_observed_at: datetime | None = None


class ItemRef(Record):
    """The pull-request conversation item a task answers, at the version of its human comments it was opened for."""

    id: str
    kind: Literal["comment", "review", "thread"]
    version: str
    task: str  # the conversation task; its review repairs carry the same reference
    url: str = ""
    bot: bool = False  # written by a GitHub App account

    @property
    def notice(self) -> bool:
        """A bot's comment or review: the only item a builder may leave without a reply (TD-30)."""
        return self.bot and self.kind != "thread"


class Response(Record):
    """How the Builder handled a conversation task; ``commit`` is the worktree HEAD of its accepted result."""

    how: Literal["fixed", "answered", "no-action"]
    text: str = Field(max_length=3000)
    commit: str | None = None


class Handling(Record):
    """One conversation item handled at ``version``, recorded once its reply was observed."""

    item: str
    kind: Literal["comment", "review", "thread"]
    url: str = ""
    version: str
    how: Literal["fixed", "answered", "no-action"]
    text: str = ""
    commit: str | None = None
    task: str
    reply_id: str | None = None
    resolved: bool = False
    reposts: int = 0
    at: datetime


class Dispute(Record):
    """A review finding the builder rejected (TD-124/176): the fresh reviewer's recheck and, if upheld, the owner's."""

    key: str  # the finding's key in its repair task, e.g. F2
    finding: str
    reason: str  # the builder's
    upheld: bool | None = None
    recheck: str = ""  # the reviewer's reason
    owner: Literal["", "fix", "drop", "reconsider"] = ""
    note: str = Field(default="", max_length=2000)  # the owner's note with the decision (TD-193)
    reconsidered: Literal["", "withdrawn", "clarified", "unsure"] = ""  # a fresh reviewer, after the note
    clarified: str = ""  # the finding as that reviewer restated it


class Task(Record):
    """One plan task; fix tasks are appended without a new plan version."""

    id: str
    title: str
    scope: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    origin: Literal["plan", "review", "ci", "pr-feedback", "person-check", "integration"] = "plan"
    detail: str = Field(default="", max_length=DETAIL)  # a review batch's findings, CI log tail, thread, instruction
    done: bool = False
    fixes: str | None = None  # the task whose review findings this fix task resolves
    base: str | None = None  # HEAD when the task's build first started; its changes are measured from here
    spans: list[str] = Field(default_factory=list)  # each build session's `start..end`: its own commits (TD-210)
    item: ItemRef | None = None  # the conversation item a pr-feedback task answers
    response: Response | None = None  # the Builder's handling of that item
    built_by: str = ""  # the session whose build Delivery accepted last (TD-123)
    resume: str = ""  # a review repair's producing session, given its one repair chance; "" starts fresh
    earlier: str = Field(default="", max_length=2000)  # that session's accepted work, for a fresh fallback (TD-175)
    disputes: list[Dispute] = Field(default_factory=list)  # findings of this repair task its builder rejected
    settled: list[str] = Field(default_factory=list)  # finding keys the owner decided to fix: never rejected
    notes: dict[str, str] = Field(default_factory=dict)  # the owner's whole note per settled finding key (TD-193)


class Plan(Record):
    """Ordered tasks of one plan version."""

    version: int = 1
    tasks: list[Task] = Field(default_factory=list)


class Review(Record):
    """One review verdict and its recorded inputs; ``task`` is None for the final review."""

    task: str | None = None
    commit: str
    inputs: Inputs
    verdict: Literal["pass", "fix"]
    round: int = 1
    tree: str | None = None  # the reviewed tree; ``inputs.paths`` hold the engine-computed covered blobs
    findings: list[str] = Field(default_factory=list)  # every accepted finding, complete


class Step(Record):
    """The one current step; ``mode`` is ``final`` for review, the caller for integrate, ``abandon``."""

    kind: StepKind
    task: str | None = None
    mode: str | None = None
    attempt: int = 1
    started_at: datetime | None = None
    session: str | None = None
    resumed: str = ""  # the planner session that had its repair chance after a plan challenge (TD-123)
    repair: str = ""  # the planner session whose repair chance is in flight until its plan is accepted


class Outcome(Record):
    """Exactly one exit or pending condition per step attempt."""

    exit: Exit
    cause: str | None = None
    reason: str = ""
    who: Actor = "delivery"
    waiting: Waiting | None = None
    wake_at: datetime | None = None
    question: str | None = None
    denial: str | None = None
    challenged: bool = False  # the plan challenge's findings sent the plan back (TD-188)
    at: datetime


class Score(Record):
    """How far one work failure got: failing checks or findings, satisfied criteria, finding identities."""

    failing: int = 0
    satisfied: int = 0
    findings: list[str] = Field(default_factory=list)


class Budget(Record):
    """Count of one cause and the premise it was counted under; environment causes keep an episode instead."""

    count: int = 0
    premise: str = ""
    task: str | None = None
    at: datetime | None = None
    signature: str = ""  # the last failure's stable signature
    counts: dict[str, int] = Field(default_factory=dict)  # work failures per normalised signature
    progress: Score | None = None  # the best score of the current streak
    alternative: bool = False  # the one different approach was tried for this cause
    since: datetime | None = None  # start of an environment episode
    attempts: int = 0  # attempts in that episode; never budget


class Budgets(Record):
    """Per-cause retries, review rounds per subject and re-plans per Change."""

    causes: dict[str, Budget] = Field(default_factory=dict)
    rounds: dict[str, int] = Field(default_factory=dict)
    loops: dict[str, int] = Field(default_factory=dict)  # every round ever, never reset: the progress display (TD-97)
    replans: int = 0


class MergeConsent(Record):
    """Consent to merge one exact head; void when the PR head differs."""

    head: str
    at: datetime
    channel: Channel = "status-view"
    delta: str = ""


class Stop(Record):
    """One action, its actor and the condition that resumes the step."""

    kind: ErrorKind
    reason: str
    action: str
    actor: Actor = "you"
    resume: str
    at: datetime


class Environment(Record):
    """A person-only check's environment: the Builder's launch recipe and the PIDs the host started from it."""

    check: str
    command: str
    directory: str
    ready_url: str
    pids: dict[int, float | None] = Field(default_factory=dict)
    pgid: int | None = None
    launched_at: datetime | None = None  # set before spawning; without ``pgid`` the launch is uncertain
    ready_at: datetime | None = None


class Recipe(Record):
    """The launch recipe one check last started from; reused while its directory's own files are unchanged."""

    check: str
    command: str
    directory: str
    ready_url: str
    inputs: str | None = None  # digest of the directory's own files at launch; unknown is never reused


class Names(Record):
    """Names only; heads always come from git."""

    branch: str = ""
    target: str = ""
    worktree: str = ""
    pr: int | None = None  # kept to find a merged or closed PR; its state is always read from GitHub
    labelled: int | None = None  # the PR the project's labels were added to, once (TD-308)
    preserved: list[str] = Field(default_factory=list)


class Overlap(Record):
    """Paths this Change's plan shares with another Change's scope: information, never a question (D7)."""

    other: str
    paths: list[str] = Field(default_factory=list)


class Change(Record):
    """The whole durable record of one Change."""

    format: int = FORMAT
    slug: str = Field(pattern=r"^[^.]+$")  # a dot could name another Change's read-only worktree
    handle: str = ""  # host-issued short handle for chat tools (T2), e.g. c3
    profile_version: int = 0
    intent: Intent = Field(default_factory=Intent)
    brief: Brief = Field(default_factory=Brief)
    checks: list[PersonCheck] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    plan: Plan | None = None
    overlaps: list[Overlap] = Field(default_factory=list)  # recorded with each plan kept: accepted or challenged
    reviews: list[Review] = Field(default_factory=list)
    step: Step = Field(default_factory=lambda: Step(kind=StepKind.SHAPE))
    outcome: Outcome | None = None
    budgets: Budgets = Field(default_factory=Budgets)
    consent: MergeConsent | None = None
    queue: QueueClaim | None = None  # TD-226: Delivery's open enqueue attempt
    queue_seen: str = ""  # the last merge-queue removal event Delivery handled
    missing: Episode | None = None
    lag: Episode | None = None  # GitHub's PR head behind a pushed branch head
    stop: Stop | None = None
    blocked: Stop | None = None  # host-owned: a process survives in the worktree, so no writer starts
    env: Environment | None = None
    recipe: Recipe | None = None
    visual: VisualResult | None = None
    before: VisualResult | None = None  # TD-24: the states at the merge-base, captured once; never gates
    visual_rounds: list[VisualRound] = Field(default_factory=list)  # TD-78: two judges per round
    owner_criteria: list[OwnerCriterion] = Field(default_factory=list)  # TD-79: checked by every later round
    waived: dict[str, str] = Field(default_factory=dict)  # TD-341: criteria the owner accepted unmet, by their text
    amendments: list[Amendment] = Field(default_factory=list)  # TD-179: proposed brief wording, challenged
    loops: dict[str, RoundLoop] = Field(default_factory=dict)  # TD-208: each subject's challenge loop
    names: Names = Field(default_factory=Names)
    spend: Spend = Field(default_factory=Spend)
    tool_use: ToolUse = Field(default_factory=ToolUse)  # C-28 T8: how agents' Delivery tool calls went
    finished_at: datetime | None = None
    pullback: Pullback | None = None
    pull_requested: datetime | None = None  # the owner asked to pull the target again
    inbox_acked: list[str] = Field(default_factory=list)
    handled: list[Handling] = Field(default_factory=list)  # pull-request conversation items, oldest first
    tests: TestReview | None = None  # a test review's shares and report (TD-373)
    decisions_baseline: DecisionBaseline | None = None  # pinned at brief approval (TD-419 slice 4)
    decisions_offered: DecisionBaseline | None = None  # the set the owner's open decisions question would pin
    decisions_unpinned_at: datetime | None = None  # approved while unreadable: the owner confirms the set to pin
    decisions_published: list[Published] = Field(default_factory=list)  # the brief's project ones (TD-453)
