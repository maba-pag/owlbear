"""The PDS auditor's one Delivery tool (#777): the audit skill's JSON report and its Markdown, which Delivery writes."""

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
    markdown: str = tools.bounded(
        REPORT, "The Markdown report rendered from that same JSON, as the skill's report template lays it out", "# ..."
    )


SUBMIT = tools.Spec(
    "submit_result", "Submit both reports once, instead of writing them as files.", AuditResult, "result"
)


def check(args: AuditResult, root: Path) -> list[str]:
    """The report's errors while the auditor can still fix them: not JSON, or refused by the copy at *root*'s schema."""
    try:
        report = json.loads(args.report)
    except ValueError as exc:
        return [f"report: not JSON ({exc})"[:300]]
    schema = json.loads((root / PACKAGE / SCHEMA).read_text(encoding="utf-8"))
    found = sorted(jsonschema.Draft202012Validator(schema).iter_errors(report), key=lambda e: list(e.absolute_path))
    return [f"report: {'/'.join(map(str, e.absolute_path)) or 'the report'}: {e.message}"[:300] for e in found[:5]]
