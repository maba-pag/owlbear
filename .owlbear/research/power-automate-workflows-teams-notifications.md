# Power Automate Workflows for Teams Notifications

> **Owning task:** #592 — Evaluate Power Automate Workflows availability for Teams notifications
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Decision #514 deferred the notification feature because Slack is unavailable and
Teams integration was blocked by corp policy (O365 Connectors approach). Since then,
Microsoft deprecated O365 Connectors (retirement deadline: April 30, 2026) and
introduced Power Automate Workflows with "When a Teams webhook request is received"
as the official replacement. **Can this new mechanism deliver orchestrator
notifications to a Teams channel?**

## 2. Sources Studied

| ID | Source | Rel. | What |
|----|--------|:----:|------|
| S1 | MS connector deprecation blog (devblogs.microsoft.com) | 1.0 | O365 Connectors retire Apr 30 2026; Workflows is the migration path |
| S2 | Teams webhook connector reference (learn.microsoft.com) | 1.0 | `TeamsIncomingWebhookTrigger` — HTTP POST, Adaptive Card JSON, auth options |
| S3 | Create incoming webhooks with Workflows (support.microsoft.com) | .95 | Step-by-step: template or scratch setup, URL copy, auth types |
| S4 | `docs/research/notifier-protocol-344-duplicate-assessment.md` §3.3 | 1.0 | Prior comparison table: Slack vs Teams vs Generic webhook |
| S5 | `docs/decisions/resolved/514-slack-notification-approach.md` | 1.0 | Deferral decision: no Slack, Teams not possible under old approach |
| S6 | Teams Incoming Webhook docs (learn.microsoft.com) | .85 | Legacy approach docs — now points to Workflows as replacement |

## 3. Analysis

### 3.1 Technical Feasibility

Power Automate Workflows webhook trigger is an HTTP POST endpoint that accepts
Adaptive Card JSON. The calling pattern is identical to the Slack webhook
approach — `urllib.request.urlopen` with a JSON payload. [S2, S3]

**Payload format** (Adaptive Card, required):
```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "contentUrl": null,
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard", "version": "1.2",
      "body": [{"type": "TextBlock", "text": "Dispatched #42 to builder"}]
    }
  }]
}
```

As of Feb 2026, MessageCard format is also supported during the migration period,
but Adaptive Card is the forward-looking standard. [S1]

### 3.2 Comparison Table

| Criterion | Slack Webhook (.85) | Teams Workflows (.75) | Generic Webhook (.55) |
|-----------|:-------------------:|:---------------------:|:---------------------:|
| New deps | 0 (stdlib) | 0 (stdlib) | 0 (stdlib) |
| Config vars | 1 (URL) | 1 (URL) | 2+ (URL + template) |
| Payload format | `{"text": "msg"}` | Adaptive Card JSON (~15 lines) | User-defined |
| Setup complexity | Slack app webhook | Teams Workflows app + trigger | Target-dependent |
| Corp availability | **Blocked** [S5] | **Unknown — needs user test** | N/A |
| Deprecation risk | None | None (IS the replacement) [S1] | None |
| LOC estimate | ~35 | ~50 (heavier JSON) | ~60 |
| Auth options | URL-only | Anyone / Tenant / Specific users [S2] | Varies |
| Rate limits | Slack-imposed | ~1000 concurrent, 4500 invokes/5min [S2] | Varies |
| Private channels | Yes | Under development (Feb 2026) [S1] | Varies |
| KISS alignment | Highest | High | Medium |

### 3.3 Corp Availability Requirements

The Workflows webhook requires all of the following to be enabled in the corp
tenant [S2, S3]:

1. **Power Automate licensing** — Standard connector (included in most M365 E3/E5 plans)
2. **Workflows app** set to "allow" in Teams admin center
3. **User permission** to create flows (Power Automate maker role)
4. **Webhook template availability** — may be restricted by org policy [S3]

**These cannot be verified programmatically.** User must test manually:

1. Open Teams → More options (···) on a channel → Workflows
2. Search for "Post to a channel when a webhook request is received" template
3. If template appears → create it, copy the URL
4. Test: `Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/json' -Body $json`

### 3.4 Notifier Protocol Compatibility

The existing `Notifier` protocol design from `slack-notification-v2.md` remains
transport-agnostic. A `TeamsWorkflowNotifier` would implement the same 3-method
interface (`on_dispatch`, `on_completion`, `on_decision_request`). The only
difference is the JSON payload structure (Adaptive Card vs plain text). [S4]

### 3.5 Risk: Workflow Ownership

Workflows are tied to a specific user account, not to a team or channel. If the
owner leaves, the workflow becomes orphaned. Mitigation: assign co-owners. [S1]

## 4. Recommendation (.75 confidence)

**Proceed with user verification of corp availability, then reopen #514 if
available.**

The tech is sound and KISS-aligned (stdlib only, ~50 LOC, single config var).
Confidence is .75 (not higher) because the critical unknown — corp tenant
enablement — can only be resolved by manual user testing.

If available: create T3 DR to reopen decision #514 with Teams Workflows as
Option D. If unavailable: close the feature as blocked by corp policy until
Slack or another channel becomes available.

Challenge: FALLBACK — `challenger` agent not available for Teams availability
research (requires user-side verification, not code analysis).

## 5. Follow-up Tasks

1. **User verification: test Workflows webhook in corp Teams** — manual test
   following §3.3 procedure. If pass → trigger DR to reopen #514. If fail →
   close #592 chain.

## 6. Verification Outcome (Task #597, 2026-04-06)

User completed manual verification. Power Automate Workflows template ("Post to a
channel when a webhook request is received") **is available** in the corp tenant,
but the webhook trigger is **disabled by corporate policy**.

**Error returned:**
```
{"error":{"code":"WorkflowTriggerIsNotEnabled","message":"Could not execute workflow
'...' trigger 'manual' with state 'Suspended': trigger is not enabled."}}
```

**AC outcome:** "If unavailable" path confirmed. No T3 DR to reopen #514 needed.
Feature remains blocked by corp policy. Table 3.2 cell "Corp availability: Unknown"
should be read as **Blocked (trigger disabled by policy)**.

**#514 status:** Decision (Defer/do nothing) remains correct — no webhook mechanism
available.

**#661** tracks the structural pipeline gap surfaced during this task (no mechanism
for user-action-required tasks in the pipeline).
