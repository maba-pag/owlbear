"""Eval dataset: orchestrator routing test cases.

Provides ``RoutingCase`` dataclass and ``ROUTING_CASES`` constant for
evaluating orchestrator intent classification and agent delegation
accuracy.  Each case pairs a user prompt with the expected intent and
target agent.

The harness in ``tool_eval.py`` (#719) can import ``ROUTING_CASES``
directly for benchmark evaluation.

Tasks: #720
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["ROUTING_CASES", "RoutingCase"]


@dataclass(frozen=True)
class RoutingCase:
    """A single routing test case for orchestrator intent classification.

    Attributes:
        case_id: Unique identifier (e.g. ``"plan-01"``).
        prompt: User message to classify.
        expected_intent: Intent category from the orchestrator routing table.
        expected_agent: Target agent name (``"self"`` for status,
            ``"ask_user"`` for ambiguous/question intent).
        difficulty: ``"clear"`` when intent is unambiguous, ``"ambiguous"``
            when reasonable humans might disagree on the routing.
    """

    case_id: str
    prompt: str
    expected_intent: str
    expected_agent: str
    difficulty: Literal["clear", "ambiguous"]


# ---------------------------------------------------------------------------
# Dataset — organised by intent
# ---------------------------------------------------------------------------

ROUTING_CASES: list[RoutingCase] = [
    # ------------------------------------------------------------------
    # plan → kanban-planner
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="plan-01",
        prompt="I have an idea for a new feature",
        expected_intent="plan",
        expected_agent="kanban-planner",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="plan-02",
        prompt="Let's plan the next sprint",
        expected_intent="plan",
        expected_agent="kanban-planner",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="plan-03",
        prompt="Break this down into smaller tasks",
        expected_intent="plan",
        expected_agent="kanban-planner",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="plan-04",
        prompt="Design the authentication module",
        expected_intent="plan",
        expected_agent="kanban-planner",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # build → builder
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="build-01",
        prompt="Fix the bug in config.py",
        expected_intent="build",
        expected_agent="builder",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="build-02",
        prompt="Implement the retry logic for HTTP calls",
        expected_intent="build",
        expected_agent="builder",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="build-03",
        prompt="Add a test for the session store",
        expected_intent="build",
        expected_agent="builder",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="build-04",
        prompt="Refactor the delegation toolset to use the new error types",
        expected_intent="build",
        expected_agent="builder",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # research → researcher
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="research-01",
        prompt="Research how others do prompt caching with Claude",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="research-02",
        prompt="Investigate alternatives to Qdrant for vector storage",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="research-03",
        prompt="Compare PydanticAI with LangGraph for multi-agent orchestration",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="research-04",
        prompt="What's the best way to handle OAuth token refresh?",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # architect → architect
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="architect-01",
        prompt="Review the backlog and refine acceptance criteria",
        expected_intent="architect",
        expected_agent="architect",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="architect-02",
        prompt="Approve task 450 for development",
        expected_intent="architect",
        expected_agent="architect",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="architect-03",
        prompt="Do an architecture review of the browser module",
        expected_intent="architect",
        expected_agent="architect",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # review → reviewer
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="review-01",
        prompt="Review the changes in PR #5",
        expected_intent="review",
        expected_agent="reviewer",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="review-02",
        prompt="Check if the test coverage is above 90%",
        expected_intent="review",
        expected_agent="reviewer",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="review-03",
        prompt="Verify the builder's implementation of task 483",
        expected_intent="review",
        expected_agent="reviewer",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # docs → writer
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="docs-01",
        prompt="Update the docs for the new CLI commands",
        expected_intent="docs",
        expected_agent="writer",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="docs-02",
        prompt="Run the documentation gate on task 500",
        expected_intent="docs",
        expected_agent="writer",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="docs-03",
        prompt="Check that the README reflects the latest changes",
        expected_intent="docs",
        expected_agent="writer",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # close → auditor
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="close-01",
        prompt="Verify done tasks and archive confirmed ones",
        expected_intent="close",
        expected_agent="auditor",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="close-02",
        prompt="Commit and push the latest changes",
        expected_intent="close",
        expected_agent="auditor",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="close-03",
        prompt="Close task 480 — all AC verified",
        expected_intent="close",
        expected_agent="auditor",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # status → self (no delegation)
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="status-01",
        prompt="What's on the board right now?",
        expected_intent="status",
        expected_agent="self",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="status-02",
        prompt="Give me a standup summary",
        expected_intent="status",
        expected_agent="self",
        difficulty="clear",
    ),
    RoutingCase(
        case_id="status-03",
        prompt="How many tasks are in progress?",
        expected_intent="status",
        expected_agent="self",
        difficulty="clear",
    ),
    # ------------------------------------------------------------------
    # question / ambiguous → ask_user
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="question-01",
        prompt="Do something about the widget",
        expected_intent="question",
        expected_agent="ask_user",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="question-02",
        prompt="The login page doesn't feel right",
        expected_intent="question",
        expected_agent="ask_user",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="question-03",
        prompt="Can you help me with the config?",
        expected_intent="question",
        expected_agent="ask_user",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="question-04",
        prompt="What do you think about the current approach?",
        expected_intent="question",
        expected_agent="ask_user",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="question-05",
        prompt="Handle the deployment situation",
        expected_intent="question",
        expected_agent="ask_user",
        difficulty="ambiguous",
    ),
    # ------------------------------------------------------------------
    # Cross-intent ambiguous cases (could reasonably map to 2+ intents)
    # ------------------------------------------------------------------
    RoutingCase(
        case_id="ambig-01",
        prompt="Look at the search module and make it better",
        expected_intent="build",
        expected_agent="builder",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="ambig-02",
        prompt="Is there a better way to structure the hooks?",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="ambig-03",
        prompt="The tests are failing, can you take a look?",
        expected_intent="build",
        expected_agent="builder",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="ambig-04",
        prompt="We need to think about how browser isolation works",
        expected_intent="research",
        expected_agent="researcher",
        difficulty="ambiguous",
    ),
    RoutingCase(
        case_id="ambig-05",
        prompt="Check the architecture of the new knowledge module",
        expected_intent="architect",
        expected_agent="architect",
        difficulty="ambiguous",
    ),
]
