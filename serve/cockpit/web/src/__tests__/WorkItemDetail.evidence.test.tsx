import { fireEvent, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import type { DeliveryEvidenceItem, DeliveryEvidenceProjection } from "../api/workItems";
import { detail, fixtureState, installWorkPortfolioHarness, renderPage } from "./workPortfolioHarness";

installWorkPortfolioHarness();

function record(overrides: Partial<DeliveryEvidenceItem>): DeliveryEvidenceItem {
  return {
    observation_id: "1".repeat(64),
    observation_schema: 2,
    source: "task",
    task_or_finalization_id: "TASK-001",
    exact_commit: "2".repeat(40),
    observation_kind: "pytest",
    procedure: "uv run pytest tests/test_launch.py",
    verdict: "passed",
    owner: null,
    reason: null,
    provenance: "machine-observed",
    request_id: null,
    locator: null,
    summary: null,
    observed_at: "2026-10-04T12:00:00+00:00",
    ...overrides,
  };
}

function criterion(
  acceptanceId: string,
  status: DeliveryEvidenceProjection["criteria"][number]["status"],
  evidence: DeliveryEvidenceItem[] = [],
) {
  return {
    acceptance_id: acceptanceId,
    acceptance_version: "3".repeat(64),
    outcome_id: "OUT-001",
    statement: `Statement for ${acceptanceId}.`,
    identity_source: "authored" as const,
    status,
    decided_by: evidence[0]?.observation_id ?? null,
    evidence,
    evidence_truncated: 0,
  };
}

const evidence: DeliveryEvidenceProjection = {
  change_id: "change-alpha",
  contract_digest: "4".repeat(64),
  frontier_digest: "5".repeat(64),
  finalization_id: null,
  finalization_rules: "none",
  criteria: [
    criterion("AC-001", "covered", [record({ locator: "path:reports/launch.txt" })]),
    {
      ...criterion("AC-002", "missing", [
        record({
          observation_id: "6".repeat(64),
          verdict: "missing",
          owner: "assisted-check",
          reason: "Needs a browser.",
          procedure: "browser check",
        }),
      ]),
      evidence_truncated: 3,
    },
    criterion("AC-003", "waived", [
      record({ observation_id: "7".repeat(64), verdict: "waived", request_id: "waive-sign-off" }),
    ]),
    criterion("AC-004", "uncovered"),
  ],
  unattributed: [record({ observation_id: "8".repeat(64), observation_schema: 1, verdict: null, summary: "exit:0" })],
  unattributed_truncated: 0,
  counts: { covered: 1, waived: 1, missing: 1, uncovered: 1, unknown: 0 },
};

it("shows each criterion's evaluator status and its records, with locators as text", async () => {
  fixtureState.currentDetail = detail({ evidence });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const summary = await screen.findByTestId("evidence-summary");
  fireEvent.click(within(summary).getByText(/Acceptance evidence/));
  expect(summary).toHaveTextContent("Acceptance evidence (1 covered, 1 waived by you, 1 missing, 1 uncovered)");
  expect(summary).toHaveTextContent("Not finalized");
  expect(within(summary).getByTestId("evidence-AC-001")).toHaveTextContent("Covered");
  expect(within(summary).getByTestId("evidence-AC-002")).toHaveTextContent(
    "Missing · owner: assisted-check · Needs a browser.",
  );
  expect(within(summary).getByTestId("evidence-AC-002")).toHaveTextContent("3 earlier record(s) not shown");
  expect(within(summary).getByTestId("evidence-AC-003")).toHaveTextContent("Waived by you");
  expect(within(summary).getByTestId("evidence-AC-003")).toHaveTextContent("request waive-sign-off");
  expect(within(summary).getByTestId("evidence-AC-004")).toHaveTextContent("Uncovered");
  expect(summary).toHaveTextContent("Records without a current criterion (1)");
  expect(summary).toHaveTextContent("Legacy record · exit:0");
  const locator = within(summary).getByTestId("evidence-locator");
  expect(locator).toHaveTextContent("path:reports/launch.txt");
  expect(locator.closest("a")).toBeNull();
  expect(within(summary).queryAllByRole("link")).toEqual([]);
});

it("shows a scoped request's kind, criteria and procedure beside its answer controls", async () => {
  fixtureState.currentDetail = detail({
    evidence,
    requests: [
      {
        request_id: "waive-sign-off",
        kind: "decision",
        outcome_id: "OUT-001",
        summary: "Waive the manual sign-off",
        options: [
          { option_id: "waive", label: "waive" },
          { option_id: "keep-required", label: "keep-required" },
        ],
        resolution: null,
        applies_to: {
          kind: "waive",
          acceptance: [{ acceptance_id: "AC-003", acceptance_version: "3".repeat(64) }],
          procedure: "manual sign-off",
        },
      },
    ],
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const scope = await screen.findByTestId("request-scope-waive");
  expect(scope).toHaveTextContent("Applies toWaiver");
  expect(scope).toHaveTextContent("AC-003 Statement for AC-003.");
  expect(scope).toHaveTextContent("Proceduremanual sign-off");
  const article = scope.closest("article");
  expect(article).not.toBeNull();
  expect(within(article as HTMLElement).getByText("Submit answer")).toBeInTheDocument();
});
