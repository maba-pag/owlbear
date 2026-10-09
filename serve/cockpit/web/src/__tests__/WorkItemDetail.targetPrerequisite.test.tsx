import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it } from "vitest";
import {
  card,
  detail,
  fixtureState,
  installWorkPortfolioHarness,
  readiness,
  renderPage,
  situation,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

const REQUIRED = "d4ce5ffa8affc70de2a191612944f6734bdfba1a";
const PROMPT = "/continue-change change-alpha reread get_change and pass its readiness basis unchanged.";

function targetSyncDetail() {
  const progress = situation("ready-for-next-step", {
    headline: "Run the prompt in Copilot Chat to merge the latest target into this Change.",
    waiting_on: "you",
    target_sync: "required",
  });
  return detail({
    card: card({
      needs: "none",
      action: { kind: "sync-target", label: "Synchronize target", command: null },
      activity: { state: "ready", worker_role: null, started_at: null, task_id: null },
    }),
    readiness: readiness({
      status: "ready",
      operation: "sync-target",
      executable: true,
      next_actor: "agent",
      reason_code: "ready",
      prompt: PROMPT,
      progress,
    }),
    block: {
      block_id: "BLOCK-TARGET",
      reason: "The task needs a target commit.",
      unblock_condition: "The Change contains the required commit.",
      expected_evidence: ["A target-sync receipt."],
      locators: [`target-commit:${REQUIRED}`],
      request_id: null,
      resolution_note: null,
      resolution_locators: [],
      resume_commit: "9".repeat(40),
    },
  });
}

it("offers the engine target merge on an Outcome whose Builder needs a target commit", async () => {
  fixtureState.currentDetail = targetSyncDetail();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const note = within(inspector).getByTestId("block-target-sync");
  expect(note).toHaveTextContent("Delivery clears this itself");
  expect(within(note).getByTitle(REQUIRED)).toHaveTextContent(REQUIRED.slice(0, 12));
  const control = within(inspector).getByTestId("outcome-target-sync");
  expect(within(inspector).getByTestId("readiness-prompt")).toHaveTextContent(PROMPT);

  fireEvent.click(within(control).getByText("Merge target into Change"));

  await waitFor(() =>
    expect(
      fixtureState.requests.filter(({ url, method }) => method === "POST" && url.endsWith("/target/sync")),
    ).toHaveLength(1),
  );
});

it("offers no Outcome target merge when Delivery's operation is something else", async () => {
  fixtureState.currentDetail = detail();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByTestId("outcome-target-sync")).not.toBeInTheDocument();
  expect(within(inspector).queryByTestId("block-target-sync")).not.toBeInTheDocument();
});
