"""The PDS auditor's one Delivery tool: its JSON report, from which Delivery derives the human Markdown."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from owlbear_delivery_next.change_contracts import tools

SKILL = "pds-audit-deprecations-js"
PACKAGE = Path("node_modules", "@porsche-design-system", "components-js")  # the release, as the copy installs it
SCHEMA = Path("skills", SKILL, "references", "report.schema.json")  # in the release's tree
REPORT = 400_000  # characters: a report quoting every finding's evidence in a large project


class AuditResult(tools.Args):
    """``submit_result`` for one PDS deprecation audit."""

    report: str = tools.bounded(
        REPORT,
        "The JSON report, serialized: one object valid against the skill's references/report.schema.json",
        '{"schemaVersion": "1.0.0", "...": "..."}',
    )


SUBMIT = tools.Spec(
    "submit_result", "Submit the JSON report once; Delivery writes both reports.", AuditResult, "result"
)


def check(args: AuditResult, root: Path) -> list[str]:
    """The report's errors while the auditor can still fix them: not JSON, or refused by the copy at *root*'s schema."""
    try:
        report = json.loads(args.report)
    except ValueError as exc:
        return [f"report: not JSON ({exc})"]
    schema = json.loads((root / PACKAGE / SCHEMA).read_text(encoding="utf-8"))
    found = sorted(jsonschema.Draft202012Validator(schema).iter_errors(report), key=lambda e: list(e.absolute_path))
    return [f"report: {'/'.join(map(str, e.absolute_path)) or 'the report'}: {e.message}" for e in found[:5]]
