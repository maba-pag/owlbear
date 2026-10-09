import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it } from "vitest";
import type { DeliveryEvidenceProjection, DeliveryRequest } from "../api/workItems";
import {
  card,
  detail,
  fixtureState,
  group,
  installWorkPortfolioHarness,
  portfolio,
  readiness,
  renderPage,
  requirePresent,
  situation,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

const RESUME = "9fa8699bf509ae6bce2ef483cbe2968242586272";
const HEADLINE = `Action needed: Sync with dev so ${RESUME} is included.`;
const PROMPT = "/continue-change change-alpha reread get_change and pass its readiness basis unchanged.";

const evidence: DeliveryEvidenceProjection = {
  change_id: "change-alpha",
  contract_digest: "4".repeat(64),
  frontier_digest: "5".repeat(64),
  finalization_id: null,
  finalization_rules: "none",
  criteria: [
    {
      acceptance_id: "AC-005",
      acceptance_version: "new".padEnd(64, "0"),
      outcome_id: "OUT-001",
      statement: "Statement for AC-005.",
      identity_source: "legacy-position",
      status: "uncovered",
      decided_by: null,
      evidence: [],
      evidence_truncated: 0,
    },
  ],
  unattributed: [],
  unattributed_truncated: 0,
  counts: { covered: 0, waived: 0, missing: 0, uncovered: 1, unknown: 0 },
};

const requests: DeliveryRequest[] = [
  {
    request_id: "REQ-PILOT",
    kind: "decision",
    outcome_id: "OUT-001",
    summary: "Run the managed-Mac pilot",
    options: [{ option_id: "passed", label: "passed" }],
    resolution: { selected_option_id: "passed", response_text: null },
    applies_to: {
      kind: "confirm-check",
      acceptance: [{ acceptance_id: "AC-005", acceptance_version: "old".padEnd(64, "0") }],
      procedure: "Run the pilot.",
    },
  },
  {
    request_id: "REQ-SYNC-1",
    kind: "action",
    outcome_id: "OUT-001",
    summary: "Sync with dev (first ask)",
    options: [],
    resolution: { selected_option_id: null, response_text: "done" },
  },
  {
    request_id: "REQ-SYNC-2",
    kind: "action",
    outcome_id: "OUT-001",
    summary: `Sync with dev from ${RESUME}`,
    options: [],
    resolution: null,
  },
];

function incidentDetail() {
  const progress = situation("needs-attention", { headline: HEADLINE, waiting_on: "you" });
  return detail({
    card: card({ needs: "you", action: { kind: "answer-request", label: "Answer request", command: null } }),
    change_progress: progress,
    readiness: readiness({
      status: "ready",
      operation: "answer-request",
      executable: true,
      next_actor: "you",
      reason_code: "request-action",
      prompt: PROMPT,
      progress,
    }),
    block: {
      block_id: "BLOCK-SYNC",
      reason: `Branch ${RESUME} lacks the required commit.`,
      unblock_condition: "Delivery synchronizes this Change with dev.",
      expected_evidence: [],
      locators: [],
      request_id: "REQ-SYNC-2",
      resolution_note: null,
      resolution_locators: [],
      resume_commit: RESUME,
    },
    requests,
    evidence,
  });
}

it("puts the open request first instead of an agent prompt that would only report it again", async () => {
  fixtureState.currentDetail = incidentDetail();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const readinessView = within(inspector).getByTestId("delivery-readiness");
  expect(within(readinessView).queryByTestId("readiness-prompt")).not.toBeInTheDocument();
  expect(within(readinessView).queryByRole("button", { name: /continuation prompt/i })).not.toBeInTheDocument();
  expect(within(readinessView).getByTestId("readiness-answer-request")).toHaveTextContent("Go to the request");
  expect(within(readinessView).getByTestId("readiness-progress")).toHaveTextContent("Needs you");

  const open = within(inspector).getByTestId("request-REQ-SYNC-2");
  expect(open.id).toBe("open-request");
  expect(within(open).getByText("Submit answer")).toBeInTheDocument();
  expect(within(open).getByTestId("request-submit-hint")).toHaveTextContent("Enter a response to submit.");
  const block = requirePresent(inspector.querySelector('section[aria-labelledby="work-block-heading"]'));
  expect(open.compareDocumentPosition(block) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  fireEvent.click(within(readinessView).getByText("Go to the request"));
  expect(document.activeElement).toBe(open);
});

it("collapses answered requests and says when their evidence no longer counts", async () => {
  fixtureState.currentDetail = incidentDetail();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const answered = await screen.findByTestId("answered-requests");
  expect(answered.tagName).toBe("DETAILS");
  expect(answered).not.toHaveAttribute("open");
  expect(answered).toHaveTextContent("Answered requests (2)");
  expect(within(answered).getByTestId("request-REQ-PILOT")).toBeInTheDocument();
  expect(within(answered).getByTestId("request-REQ-SYNC-1")).toHaveTextContent("done");
  expect(within(answered).getByTestId("request-uncounted-AC-005")).toHaveTextContent(
    "Criterion changed since this answer",
  );
  expect(within(answered).queryByTestId("request-REQ-SYNC-2")).not.toBeInTheDocument();
});

it("states the headline once and shortens full commits while keeping them in the title", async () => {
  fixtureState.currentDetail = incidentDetail();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const change = within(inspector).getByTestId("change-progress");
  expect(change).toHaveTextContent("Needs you");
  expect(change).not.toHaveTextContent("Action needed");
  const headline = within(inspector).getByTestId("readiness-headline");
  expect(headline).not.toHaveTextContent(RESUME);
  expect(within(headline).getByTitle(RESUME)).toHaveTextContent(RESUME.slice(0, 12));
  const block = requirePresent(inspector.querySelector('section[aria-labelledby="work-block-heading"]'));
  expect(block).toHaveTextContent(RESUME.slice(0, 12));
  expect(block).not.toHaveTextContent(RESUME);
});

it("keeps the agent prompt when Delivery's operation is not answering a request", async () => {
  const progress = situation("ready-for-next-step", { waiting_on: "you" });
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "ready",
      operation: "start-orchestration",
      executable: true,
      next_actor: "agent",
      reason_code: "ready",
      prompt: PROMPT,
      progress,
    }),
    requests: [requests[2]],
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-prompt")).toHaveTextContent(PROMPT);
  expect(within(inspector).queryByTestId("readiness-answer-request")).not.toBeInTheDocument();
});

it("links the portfolio Answer request action to the open request and focuses it", async () => {
  const answer = card({ needs: "you", action: { kind: "answer-request", label: "Answer request", command: null } });
  fixtureState.currentPortfolio = portfolio([group({ items: [answer] })]);
  fixtureState.currentDetail = incidentDetail();
  renderPage("/delivery");

  const table = await screen.findByTestId("work-portfolio-table");
  const host = requirePresent(within(table).getAllByText("Answer request")[0].closest("p-link-pure")) as HTMLElement & {
    href?: string;
  };
  expect(host.getAttribute("href") ?? host.href).toBe("/delivery/change-alpha/outcome%3AOUT-001#open-request");
  fireEvent.click(host);

  const open = await screen.findByTestId("request-REQ-SYNC-2");
  await waitFor(() => expect(document.activeElement).toBe(open));
});
