"""Render the pinned PDS audit's validated JSON as its prescribed human report."""

from __future__ import annotations

import hashlib
import html
import re
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import audit_tools

if TYPE_CHECKING:
    from pathlib import Path

TEMPLATE = audit_tools.SCHEMA.with_name("report-template.md")
SCHEMA_VERSION = "1.0.0"
TEMPLATE_HASH = "f121c6aa8196d5f0f616e79c9ec6d170889013ff96a516caa022a42e3fb9409a"
EFFORTS = ("trivial", "small", "medium", "large")
CONFIDENCES = ("high", "medium")


class UnsupportedFormatError(ValueError):
    """The release does not declare the report format this renderer implements."""


def template(tree: Path, schema: dict[str, Any]) -> str:
    """Read the known report template, or identify the unsupported release format."""
    properties = schema.get("properties")
    declared = properties.get("schemaVersion") if isinstance(properties, dict) else None
    version = declared.get("const") if isinstance(declared, dict) else None
    if version != SCHEMA_VERSION:
        msg = (
            f"unsupported PDS audit schema at {tree / audit_tools.SCHEMA}: "
            f"schemaVersion {version!r}, supported {SCHEMA_VERSION!r}"
        )
        raise UnsupportedFormatError(msg)
    path = tree / TEMPLATE
    raw = path.read_bytes()
    found = hashlib.sha256(raw).hexdigest()
    if found != TEMPLATE_HASH:
        msg = f"unsupported PDS audit template at {path}: SHA-256 {found}, supported {TEMPLATE_HASH}"
        raise UnsupportedFormatError(msg)
    return raw.decode("utf-8")


def _text(value: str) -> str:
    escaped = re.sub(r"([\\`*_\[\]|&<>~#])", r"\\\1", value)
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _code(value: str) -> str:
    if not value or "\n" in value or "\r" in value:
        escaped = html.escape(value, quote=False).replace("\r\n", "\n").replace("\r", "\n")
        return f"<code>{escaped.replace(chr(10), '<br>')}</code>"
    longest = max((len(m[0]) for m in re.finditer(r"`+", value)), default=0)
    fence = "`" * (longest + 1)
    padding = " " if value.strip(" ") and (value.startswith(("`", " ")) or value.endswith(("`", " "))) else ""
    return f"{fence}{padding}{value}{padding}{fence}"


def _block(value: str) -> list[str]:
    longest = max((len(m[0]) for m in re.finditer(r"`+", value)), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"    {fence}", *(f"    {line}" for line in value.split("\n")), f"    {fence}"]


def render(body: dict[str, Any], source: str) -> str:
    """Render every field the pinned template prescribes; canonical JSON remains unchanged."""
    audit, project, scope, coverage = (body[k] for k in ("audit", "project", "scope", "coverage"))
    findings, follow_ups = body["findings"], body["manualFollowUps"]
    packages = ", ".join(_code(f"{p['name']}@{p['version']}") for p in project["pdsPackages"])
    lines = [
        f"# Porsche Design System deprecation audit (js) \u2014 {_text(audit['runId'])}",
        "",
        f"- **PDS version audited:** {_code(audit['pdsVersion'])}",
        "- **Framework:** `js`",
        f"- **Project root:** {_code(project['root'])}",
        f"- **Packages:** {packages}",
        f"- **Generated at:** {_text(audit['generatedAt'])}",
        f"- **Result:** {_code(body['summary']['result'])}",
        "",
        "## Scope",
        "",
        "### Included",
        "",
        *(f"- {_code(p)}" for p in scope["includedPaths"]),
        "",
        "### Excluded",
        "",
        *(
            [f"- {_code(p['path'])} \u2014 {_text(p['reason'])}" for p in scope["excludedPaths"]]
            or ["Nothing was excluded."]
        ),
        "",
        "## Coverage",
        "",
        "### Skipped files",
        "",
        *(
            [f"- {_code(p['path'])} \u2014 {_text(p['reason'])}" for p in coverage["skippedFiles"]]
            or ["No eligible files were skipped."]
        ),
        "",
        "### Limitations",
        "",
        *([f"- {_text(p)}" for p in coverage["limitations"]] or ["No limitations to report."]),
        "",
        "## Summary",
        "",
        f"- **{len(findings)}** findings across **{sum(len(f['evidence']) for f in findings)}** locations",
        f"- **{len(follow_ups)}** manual follow-ups",
    ]
    if findings:
        lines += ["", "| Effort | Findings |", "| --- | --- |"]
        for effort in EFFORTS:
            if count := sum(f.get("observedEffort", f["baselineEffort"]) == effort for f in findings):
                lines.append(f"| {_code(effort)} | {count} |")
        lines += ["", "| Confidence | Findings |", "| --- | --- |"]
        for confidence in CONFIDENCES:
            if count := sum(f["confidence"] == confidence for f in findings):
                lines.append(f"| {_code(confidence)} | {count} |")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("No deprecated usage was found.")
    else:
        lines.append(
            "Ordered cheapest first \u2014 effective effort ascending, then confidence, then occurrence count "
            "descending, then rule id. This order is the recommended action plan."
        )
    for i, finding in enumerate(findings, 1):
        lines += _finding(finding, i)
    lines += _follow_ups(follow_ups)
    footer = source.split("## How to act on this report\n", 1)[1].split("\n````", 1)[0]
    footer = footer.replace("`<audit.pdsVersion>`", _code(audit["pdsVersion"]))
    lines += ["", "## How to act on this report", "", footer.strip("\n")]
    return "\n".join(lines) + "\n"


def _finding(finding: dict[str, Any], position: int) -> list[str]:
    lines = [
        "",
        f"### {position}. {_text(finding['title'])}",
        "",
        f"- **Rule id:** {_code(finding['ruleId'])}",
        f"- **Kind:** {_code(finding['usageKind'])}",
        f"- **Confidence:** {_code(finding['confidence'])}",
    ]
    baseline = finding["baselineEffort"]
    if "observedEffort" in finding:
        lines += [
            f"- **Effort:** {_code(finding['observedEffort'])} (observed \u2014 baseline {_code(baseline)})",
            f"- **Effort rationale:** {_text(finding['effortRationale'])}",
        ]
    else:
        lines.append(f"- **Effort:** {_code(baseline)} (baseline)")
    if "deprecationMessage" in finding:
        lines.append(f"- **Deprecation message:** {_text(finding['deprecationMessage'])}")
    remediation = finding["remediation"]
    if "replacement" in remediation:
        replacement = remediation["replacement"]
        lines.append(f"- **Replacement:** {_code(replacement['from'])} \u2192 {_code(replacement['to'])}")
    lines += [
        f"- **Instruction:** {_text(remediation['instruction'])}",
        "- **Sources:**",
        *(
            f"  - {_code('pds-knowledge-js/' + s['reference'])} (PDS {_text(s['pdsVersion'])})"
            for s in finding["sources"]
        ),
        f"- **Locations ({len(finding['evidence'])}):**",
    ]
    for place in finding["evidence"]:
        detail = f"  - {_code(f'{place["path"]}:{place["line"]}')} \u2014 {_code(place['detection'])}"
        if "valueResolution" in place:
            detail += f", value {_code(place['valueResolution'])}"
        lines += [detail, *_block(place["snippet"])]
        if "anchor" in place:
            anchor = place["anchor"]
            lines += [
                f"    anchored by {_code(f'{anchor["path"]}:{anchor["line"]}')}",
                *_block(anchor["snippet"]),
            ]
    return lines


def _follow_ups(follow_ups: list[dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## Manual follow-ups",
        "",
        "Detected but not statically resolvable. These are for a human to review \u2014 do not fix them automatically.",
    ]
    if not follow_ups:
        lines += ["", "No manual follow-ups."]
    for i, item in enumerate(follow_ups, 1):
        lines += ["", f"### {i}. {_text(item['subject'])}", ""]
        if "ruleId" in item:
            lines.append(f"- **Rule id:** {_code(item['ruleId'])}")
        lines += [
            f"- **Reason:** {_text(item['reason'])}",
            f"- **Evidence ({len(item['evidence'])}):**",
        ]
        for place in item["evidence"]:
            lines += [
                f"  - {_code(f'{place["path"]}:{place["line"]}')}",
                *_block(place["snippet"]),
            ]
    return lines
