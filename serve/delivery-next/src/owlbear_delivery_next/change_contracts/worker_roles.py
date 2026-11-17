"""Role policy shared by runtime tool grants and worker admission."""

LOOKERS = frozenset({"planner", "builder", "reviewer", "preparer", "test-curator", "repairer"})  # a step's worker
JUDGES = frozenset(
    (
        "challenger",
        "design-judge",
        "test-reviewer",
        "picker",
        "curator",
        "auditor",
        "project-auditor",
        "audit-verifier",
        "quality-judge",
    )
)
