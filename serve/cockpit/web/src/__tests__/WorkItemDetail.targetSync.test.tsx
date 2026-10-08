import { screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import {
  detail,
  fixtureState,
  installWorkPortfolioHarness,
  publicationCardForChecks,
  publicationForChecks,
  readiness,
  renderPage,
  situation,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

const CONFLICT_PROMPT =
  "/resolve-target-conflict change-alpha Target synchronization stopped on a merge conflict that the Change " +
  "worktree preserves. Resolve it there and record it with Delivery, or abort it. Do not edit Delivery state " +
  "or start another synchronization.";
const CONFLICT_HEADLINE =
  "Merging the latest target stopped on a conflict in web/src/pages/WorkPortfolioPage.tsx; resolve it with " +
  "/resolve-target-conflict.";
const GUIDANCE =
  "Target synchronization stopped on a preserved merge conflict. Resolve or abort it with " +
  "/resolve-target-conflict change-alpha; that exit releases this engine action.";

// Shaped like Delivery's detail response for a retained engine target-sync conflict.
function conflictDetail() {
  const progress = situation("ready-for-next-step", { headline: CONFLICT_HEADLINE, target_sync: "unavailable" });
  const blocked = readiness({
    status: "blocked",
    operation: "resolve-attention",
    reason_code: "engine-action-failed",
    next_actor: "you",
    prompt: CONFLICT_PROMPT,
    progress,
  });
  const publicationCard = publicationCardForChecks({
    publication_phase: "ready-for-finalization",
    next_actor: "you",
    needs_headline: GUIDANCE,
    next_step: GUIDANCE,
    progress: { kind: "publication", label: "Target sync conflict", done: null, total: null },
    readiness: blocked,
  });
  return detail({
    card: publicationCard,
    readiness: blocked,
    change_progress: { ...progress, target_sync: null },
    publication: {
      ...publicationForChecks("ready-for-finalization"),
      ready_for_finalization: false,
      readiness_diagnostics: ["engine-action-failed"],
      attention: {
        disposition_id: "6".repeat(64),
        kind: "publication-attention",
        change_id: "change-alpha",
        entered_from: "building",
        recorded_at: "2026-10-08T21:33:52Z",
        diagnostics: [
          "target-sync-operation:continue-op",
          "target synchronization merge conflict",
          "conflict-path:web/src/pages/WorkPortfolioPage.tsx",
        ],
      },
      target_sync_conflict: {
        conflict_id: "2".repeat(64),
        operation_id: "continue-op",
        target_head: "a".repeat(40),
        change_head_before: "1".repeat(40),
        conflict_paths: ["web/src/pages/WorkPortfolioPage.tsx"],
      },
    },
  });
}

it("presents a preserved target conflict as one next step with labelled alternatives", async () => {
  fixtureState.currentDetail = conflictDetail();
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-headline")).toHaveTextContent(CONFLICT_HEADLINE);
  expect(within(inspector).getAllByRole("button", { name: /^Copy/ })).toHaveLength(1);
  expect(within(inspector).getByTestId("readiness-prompt")).toHaveTextContent("/resolve-target-conflict change-alpha");
  expect(within(inspector).getByTestId("target-sync-conflict-paths")).toHaveTextContent(
    "web/src/pages/WorkPortfolioPage.tsx",
  );
  expect(within(inspector).getByTestId("target-sync-conflict-abort")).toHaveAccessibleDescription(
    "Rolls the Change back to its reviewed head; the latest target stays unmerged.",
  );
  expect(within(inspector).getByTestId("target-sync-conflict-resolve")).toHaveAccessibleDescription(
    /Only after you resolved and staged every conflicting file/,
  );

  expect(inspector).not.toHaveTextContent("A Delivery step failed");
  expect(inspector).not.toHaveTextContent("that exit releases this engine action");
  expect(inspector).not.toHaveTextContent("Finalization unavailable");
  expect(inspector).not.toHaveTextContent("run the continuation prompt again");
  expect(inspector).not.toHaveTextContent("Publication evidence needs reconciliation");
  expect(inspector).not.toHaveTextContent("while Delivery or an agent holds it");
  expect(within(inspector).queryByTestId("publication-readiness-status")).toBeNull();
  expect(within(inspector).queryByTestId("finalization-readiness")).toBeNull();
  expect(within(inspector).queryByTestId("target-sync")).toBeNull();
});

it("after an abort shows the repeat-merge warning without conflict controls", async () => {
  const aborted = situation("ready-for-next-step", {
    headline:
      "You aborted merging this target; running the prompt merges it again and keeps any conflict for you to resolve.",
    target_sync: "required",
  });
  const ready = readiness({
    status: "ready",
    operation: "sync-target",
    executable: true,
    reason_code: "ready",
    prompt: "/continue-change change-alpha reread get_change",
    progress: aborted,
  });
  fixtureState.currentDetail = detail({
    card: publicationCardForChecks({ publication_phase: "ready-for-finalization", readiness: ready }),
    readiness: ready,
    change_progress: { ...aborted, target_sync: null },
    publication: publicationForChecks("ready-for-finalization"),
  });
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-headline")).toHaveTextContent("You aborted merging this target");
  expect(within(inspector).queryByTestId("target-sync-conflict-abort")).toBeNull();
  expect(within(inspector).queryByText("Target sync conflict")).toBeNull();
});
