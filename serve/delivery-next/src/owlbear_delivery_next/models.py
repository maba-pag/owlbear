"""Delivery-next state records for one Change (D3 §3.1 to §3.3)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FORMAT = 1
PROFILE_FORMAT = 1

type Actor = Literal["you", "admin", "delivery", "github"]
type Channel = Literal["status-view", "chat"]


class StepKind(StrEnum):
    """The ten step kinds."""

    SHAPE = "shape"
    PLAN = "plan"
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
    MERGE_QUEUE = "merge-queue"
    NETWORK = "network"


class Record(BaseModel):
    """Strict base: unknown fields are a format error, not silently dropped."""

    model_config = ConfigDict(extra="forbid")


class Criterion(Record):
    """One acceptance criterion; its version is a review and check input."""

    id: str
    text: str
    version: int = 1


class Brief(Record):
    """The user's brief: the current draft, the approved version, and each approved version's content."""

    version: int = 0
    approved_version: int | None = None
    approved_at: datetime | None = None
    outcome: str = ""
    scope: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
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
    paths: list[str] = Field(default_factory=list)
    procedure: int = 1
    environment: list[str] = Field(default_factory=list)
    answer: Answer | None = None


class Decision(Record):
    """One recorded decision with its provenance."""

    text: str
    origin: Literal["decided", "approved", "autonomous"]
    at: datetime


class Option(Record):
    """One answer option; ``next`` names the step it leads to, or ``done``, ``pause`` or ``abandon``."""

    id: str
    label: str
    next: StepKind | Literal["done", "pause", "abandon"] | None = None


class Answer(Record):
    """How and when a question or person-only check was answered; a check also records pass and inputs."""

    option: str | None = None
    text: str = ""
    channel: Channel = "status-view"
    at: datetime
    passed: bool | None = None
    inputs: Inputs | None = None


class Question(Record):
    """A durable question; its answer is delivered to a session, and its cause clears once the effect is observed."""

    id: str = ""
    step: StepKind
    kind: Literal["decision", "action"] = "decision"
    text: str
    options: list[Option] = Field(default_factory=list)
    cause: str | None = None
    answer: Answer | None = None
    delivered_at: datetime | None = None
    effect_observed_at: datetime | None = None


class Task(Record):
    """One plan task; fix tasks are appended without a new plan version."""

    id: str
    title: str
    scope: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    origin: Literal["plan", "review", "ci", "pr-feedback", "person-check", "integration"] = "plan"
    done: bool = False


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


class Step(Record):
    """The one current step; ``mode`` is ``final`` for review, the caller for integrate, ``abandon``."""

    kind: StepKind
    task: str | None = None
    mode: str | None = None
    attempt: int = 1
    started_at: datetime | None = None
    session: str | None = None


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
    at: datetime


class Budget(Record):
    """Count of one cause and the premise it was counted under."""

    count: int = 0
    premise: str = ""
    task: str | None = None
    at: datetime | None = None


class Budgets(Record):
    """Per-cause retries, review rounds per subject and re-plans per Change."""

    causes: dict[str, Budget] = Field(default_factory=dict)
    rounds: dict[str, int] = Field(default_factory=dict)
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


class Names(Record):
    """Names only; heads always come from git."""

    branch: str = ""
    target: str = ""
    worktree: str = ""
    preserved: list[str] = Field(default_factory=list)


class Change(Record):
    """The whole durable record of one Change."""

    format: int = FORMAT
    slug: str
    profile_version: int = 0
    intent: Intent = Field(default_factory=Intent)
    brief: Brief = Field(default_factory=Brief)
    checks: list[PersonCheck] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    plan: Plan | None = None
    reviews: list[Review] = Field(default_factory=list)
    step: Step = Field(default_factory=lambda: Step(kind=StepKind.SHAPE))
    outcome: Outcome | None = None
    budgets: Budgets = Field(default_factory=Budgets)
    consent: MergeConsent | None = None
    stop: Stop | None = None
    names: Names = Field(default_factory=Names)
    finished_at: datetime | None = None
    inbox_acked: list[str] = Field(default_factory=list)


class ProfileEntry(Record):
    """One detected project fact with its evidence (DR1); an HTTP 403 on rules is unknown."""

    state: Literal["known", "unknown", "unsupported"]
    value: str = ""
    evidence: str = ""


class Profile(Record):
    """The confirmed project profile; a new version is a premise change."""

    format: int = PROFILE_FORMAT
    version: int = 0
    confirmed_at: datetime | None = None
    entries: dict[str, ProfileEntry] = Field(default_factory=dict)
    models: dict[StepKind, str] = Field(default_factory=dict)


class _Item(Record):
    at: datetime
    channel: Channel = "status-view"


class BriefApproval(_Item):
    """Approve one brief version."""

    kind: Literal["brief-approval"] = "brief-approval"
    version: int


class AnswerItem(_Item):
    """Answer one open question."""

    kind: Literal["answer"] = "answer"
    question: str
    option: str | None = None
    text: str = ""


class CheckResult(_Item):
    """Pass or fail of one person-only check, with the inputs shown to the user."""

    kind: Literal["check-result"] = "check-result"
    check: str
    passed: bool
    note: str = ""
    inputs: Inputs


class Recovery(_Item):
    """The user performed the current stop's action."""

    kind: Literal["recovery"] = "recovery"
    action: str


class ConsentItem(_Item):
    """Consent to merge one exact head."""

    kind: Literal["merge-consent"] = "merge-consent"
    head: str
    delta: str = ""


class IntentItem(_Item):
    """Pause, resume, abandon, or change the intent."""

    kind: Literal["intent"] = "intent"
    intent: Literal["pause", "resume", "abandon", "change"]
    text: str = ""


type InboxItem = Annotated[
    BriefApproval | AnswerItem | CheckResult | Recovery | ConsentItem | IntentItem, Field(discriminator="kind")
]
