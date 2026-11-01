"""The PDS auditor's one Delivery tool (#777): the audit skill's JSON report and its Markdown, which Delivery writes."""

from __future__ import annotations

from owlbear_delivery_next.change_contracts import tools

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
