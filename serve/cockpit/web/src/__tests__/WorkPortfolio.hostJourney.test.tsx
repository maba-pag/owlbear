import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import {
  CONTINUATION_PROMPT,
  card,
  changeStatus,
  continuationCard,
  detail,
  fixtureState,
  group,
  installWorkPortfolioHarness,
  portfolio,
  readiness,
  renderPage,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

function mockClipboard() {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  return writeText;
}

it("says a completed outcome of an open Change is complete, not that the Change ended", async () => {
  const done = card({
    stage: "completed",
    activity: { state: "idle", worker_role: null, started_at: null, task_id: null },
    readiness: readiness({ status: "complete", reason_code: "outcome-complete", progress: "completed" }),
  });
  fixtureState.currentPortfolio = portfolio([group({ items: [done] })]);
  fixtureState.currentDetail = detail({ card: done, readiness: done.readiness });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("This outcome is complete.");
  expect(inspector).not.toHaveTextContent("This Change reached a terminal state.");
});

it("calls a paused Change paused, never deferred", async () => {
  const paused = card({ readiness: readiness({ status: "waiting", reason_code: "change-paused" }) });
  const data = portfolio([group({ lifecycle: "deferred", items: [paused] })]);
  fixtureState.currentPortfolio = {
    ...data,
    operating: { ...data.operating, statuses: [changeStatus("change-alpha", { stage: "deferred" })] },
  };
  renderPage();

  const table = await screen.findByTestId("work-portfolio-table");
  expect(table).toHaveTextContent(/paused/i);
  expect(document.body).not.toHaveTextContent(/deferred/i);
});

it("copies a blocked repair prompt with one click", async () => {
  const writeText = mockClipboard();
  const prompt = "/repair-delivery Diagnose Change change-alpha read-only; preserve existing custody and journals.";
  const blocked = card({
    readiness: readiness({ status: "blocked", reason_code: "retry-exhausted", prompt, progress: "needs-decision" }),
  });
  fixtureState.currentPortfolio = portfolio([group({ items: [blocked] })]);
  fixtureState.currentDetail = detail({ card: blocked, readiness: blocked.readiness });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByRole("button", { name: "Copy prompt" }));

  await waitFor(() => expect(writeText).toHaveBeenCalledWith(prompt));
});

it("puts the Change's continuation prompt before Change requirements on a sibling outcome", async () => {
  const writeText = mockClipboard();
  const waiting = card({
    item_key: "outcome:OUT-002",
    work_item_id: "OUT-002",
    title: "User controls",
    readiness: readiness({ status: "waiting", reason_code: "task-incomplete" }),
  });
  fixtureState.currentPortfolio = portfolio([group({ items: [continuationCard(), waiting] })]);
  fixtureState.currentDetail = detail({
    card: waiting,
    readiness: waiting.readiness,
    revision_prompt: "/design change-alpha Change requirements:",
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-002");

  const inspector = await screen.findByTestId("work-item-detail");
  const continuation = within(inspector).getByRole("button", { name: "Copy continuation prompt" });
  const requirements = within(inspector).getByRole("button", { name: "Change requirements" });
  expect(continuation.compareDocumentPosition(requirements) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  fireEvent.click(continuation);
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(CONTINUATION_PROMPT));
});

it("copies the attention command for a Delivery health diagnostic", async () => {
  const writeText = mockClipboard();
  fixtureState.currentPortfolio = portfolio([], {
    status: "attention",
    diagnostics: [
      {
        source: "remote-state",
        code: "remote-state-reconciliation-required",
        detail: "remote Change branch differs from Delivery-state snapshot: quarantined-change",
        change_id: "quarantined-change",
        path: null,
        retry_safe: false,
        reason: "remote-change-head-mismatch",
        resolution: "authority-gap",
        expected_head: null,
        observed_head: null,
        observed_local_head: null,
        head_relation: null,
      },
    ],
  });
  renderPage();

  const health = await screen.findByTestId("delivery-issues-section");
  fireEvent.click(within(health).getByRole("button", { name: "Copy prompt" }));

  await waitFor(() => expect(writeText).toHaveBeenCalledWith("/resolve-delivery-attention quarantined-change"));
});
