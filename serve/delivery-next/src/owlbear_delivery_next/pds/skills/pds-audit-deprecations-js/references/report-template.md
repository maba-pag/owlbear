# Markdown report template

The Markdown report is a rendering of the validated JSON, written to the structure below. It is the file a human opens and the file an agent is later asked to act on, so its shape is fixed rather than composed per run: the same sections, in the same order, every time.

## How to read this template

- Reproduce every section, in this order, with these headings verbatim. Add none, drop none.
- `<…>` is a placeholder naming the JSON path it renders, so every line of the report is traceable to the field it came from. One ending in `[]` is a repeated item: render one entry per array element.
- A line marked `— only when …` is rendered only in that case and omitted entirely otherwise. The marker itself is never written into the report.
- Empty-state sentences are given verbatim. Write the sentence rather than dropping the section, so an empty section never reads as a missing one.
- Compute every count from the arrays you validated. Never write one from memory: a number that disagrees with the list under it discredits the whole report.
- Nothing enters the report that is not in the JSON. Anything else worth saying — that `.pds/` is not git-ignored, for instance — belongs in your reply to the user, not in this file.

## Template

````markdown
# Porsche Design System deprecation audit (js) — <audit.runId>

- **PDS version audited:** `<audit.pdsVersion>`
- **Framework:** `js`
- **Project root:** `<project.root>`
- **Packages:** `<project.pdsPackages[].name>@<project.pdsPackages[].version>` — one per entry, comma-separated
- **Generated at:** <audit.generatedAt>
- **Result:** `<summary.result>`

## Scope

### Included

- `<scope.includedPaths[]>`

### Excluded

- `<scope.excludedPaths[].path>` — <scope.excludedPaths[].reason>

Nothing was excluded. — only when `scope.excludedPaths` is empty, replacing the list

## Coverage

### Skipped files

- `<coverage.skippedFiles[].path>` — <coverage.skippedFiles[].reason>

No eligible files were skipped. — only when `coverage.skippedFiles` is empty, replacing the list

### Limitations

- <coverage.limitations[]>

No limitations to report. — only when `coverage.limitations` is empty, replacing the list

## Summary

- **<number of findings>** findings across **<number of evidence locations across all findings>** locations
- **<number of manual follow-ups>** manual follow-ups

| Effort | Findings |
| --- | --- |
| `<effort>` | <number of findings with that effective effort> |

| Confidence | Findings |
| --- | --- |
| `<confidence>` | <number of findings with that confidence> |

## Findings

Ordered cheapest first — effective effort ascending, then confidence, then occurrence count descending, then rule id. This order is the recommended action plan.

### <position in `findings`>. <findings[].title>

- **Rule id:** `<findings[].ruleId>`
- **Kind:** `<findings[].usageKind>`
- **Confidence:** `<findings[].confidence>`
- **Effort:** `<findings[].baselineEffort>` (baseline)
- **Effort:** `<findings[].observedEffort>` (observed — baseline `<findings[].baselineEffort>`) — only when `observedEffort` is present, replacing the line above
- **Effort rationale:** <findings[].effortRationale> — only when `observedEffort` is present
- **Deprecation message:** <findings[].deprecationMessage> — only when present
- **Replacement:** `<findings[].remediation.replacement.from>` → `<findings[].remediation.replacement.to>` — only when present
- **Instruction:** <findings[].remediation.instruction>
- **Sources:**
  - `pds-knowledge-js/<findings[].sources[].reference>` (PDS <findings[].sources[].pdsVersion>)
- **Locations (<number of entries in `findings[].evidence`>):**
  - `<findings[].evidence[].path>:<findings[].evidence[].line>` — `<findings[].evidence[].detection>`, value `<findings[].evidence[].valueResolution>` — the value half only when `valueResolution` is present
    ```
    <findings[].evidence[].snippet>
    ```
    anchored by `<findings[].evidence[].anchor.path>:<findings[].evidence[].anchor.line>` — only when `anchor` is present, together with the block below
    ```
    <findings[].evidence[].anchor.snippet>
    ```

No deprecated usage was found. — only when `findings` is empty, replacing the ordering sentence, the entries and both Summary tables

## Manual follow-ups

Detected but not statically resolvable. These are for a human to review — do not fix them automatically.

### <position in `manualFollowUps`>. <manualFollowUps[].subject>

- **Rule id:** `<manualFollowUps[].ruleId>` — only when present
- **Reason:** <manualFollowUps[].reason>
- **Evidence (<number of entries in `manualFollowUps[].evidence`>):**
  - `<manualFollowUps[].evidence[].path>:<manualFollowUps[].evidence[].line>`
    ```
    <manualFollowUps[].evidence[].snippet>
    ```

No manual follow-ups. — only when `manualFollowUps` is empty, replacing the entries

## How to act on this report

This report describes Porsche Design System `<audit.pdsVersion>` and is only valid for that version. After upgrading the package, run the audit again rather than working from this file.

Findings are ordered cheapest first, so the list is the action plan: work down it. Applying one takes two lookups against `pds-knowledge-js`, and neither is optional. Re-check the rule id against the deprecation index: it is the only thing that establishes an API is still deprecated and what replaces it, and it describes the installed version rather than the one this report was written against. Then open the reference the finding lists under **Sources**, which documents how the replacement is actually written — **Instruction** and **Replacement** name the edit, not the current API.

Manual follow-ups are for a human to resolve and must not be fixed automatically. Their values could not be determined statically, so it is not established that they are deprecated at all.

Re-run this audit over the same scope afterwards. A clean re-run is the only reliable confirmation that a finding has been resolved.
````

## The values the template derives

Four things above are computed rather than copied, and each has exactly one right answer:

- **Effective effort** is `observedEffort` when present, else `baselineEffort`. It is what the findings order and the Summary effort table both use.
- **Breakdown rows** list only buckets that have findings, ordered `trivial`, `small`, `medium`, `large` and `high`, `medium` — the same direction as the findings themselves, so the cheapest and most certain work reads first.
- **Finding numbers** are the position in `findings`, so `### 1.` is the first thing to fix. Manual follow-ups are numbered the same way.
- **Source paths** are skill-qualified: `pds-knowledge-js` followed by the stored `reference`, which is relative to that skill's root. They point at the reference documenting the replacement, never at the deprecation index.
