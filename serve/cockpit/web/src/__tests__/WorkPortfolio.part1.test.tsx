import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { PortfolioOperatingView, WorkItemPortfolioResponse } from "../api/workItems";
import { PortfolioHeaderSummary } from "../components/PortfolioOperatingSummary";
import {
  card,
  changeStatus,
  detail,
  fixtureState,
  group,
  inputValue,
  installWorkPortfolioHarness,
  namedPdsHost,
  portfolio,
  publicationCardForChecks,
  publicationForChecks,
  readiness,
  renderPage,
  requirePresent,
  runningBuilderClaim,
  selectValue,
  withUnadmittedDesign,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("summarizes all current Change phases and nonzero operating states", () => {
  const outcome = {
    change_id: "delivery-change",
    item_key: "outcome:OUT-001",
    scope: "outcome" as const,
  };
  const publication = {
    change_id: "publication-change",
    item_key: "publication",
    scope: "publication" as const,
  };
  const operating: PortfolioOperatingView = {
    unfinished_change_count: 3,
    completed_change_count: 8,
    statuses: [
      changeStatus("draft-change", {
        admission: "unadmitted",
        stage: "design",
        actionable_runtime: false,
      }),
      changeStatus("delivery-change"),
      changeStatus("design-reentry", { stage: "design" }),
      changeStatus("unavailable-change", {
        actionable_runtime: false,
        diagnostic_code: "runtime_unavailable",
        diagnostic_detail: "Runtime composition is unavailable.",
      }),
    ],
    draft_design_change_ids: ["legacy-draft", "legacy-draft-2"],
    design_required_change_ids: ["legacy-reentry", "legacy-reentry-2", "legacy-reentry-3"],
    claimed: [outcome],
    queued_for_orchestration: [publication],
    interventions: [outcome],
    dependency_waits: [publication],
    guidance: [],
  };
  const totals: WorkItemPortfolioResponse["totals"] = {
    total: 3,
    complete: 0,
    needs: { you: 1, dependency: 1, none: 1 },
    activity: { idle: 1, ready: 1, working: 1 },
  };
  const onNeedsFilter = vi.fn();

  render(
    <PortfolioHeaderSummary
      operating={operating}
      totals={totals}
      runPromptCount={2}
      needsFilter="you"
      onNeedsFilter={onNeedsFilter}
    />,
  );

  expect(screen.getByRole("region", { name: "Portfolio inventory" })).toHaveTextContent("4Changes2Design·2Delivery");
  expect(screen.getByRole("region", { name: "Attention" })).toHaveTextContent("1Needs you1Blocked2Run prompt");
  expect(screen.getByTestId("portfolio-activity-run-prompt")).not.toHaveClass("text-error");
  expect(screen.getByRole("region", { name: "Activity" })).toHaveTextContent("1Running1Ready");

  const needsYou = screen.getByRole("button", {
    name: "Filter to 1 work item: Needs you",
  });
  expect(needsYou).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(needsYou);
  expect(onNeedsFilter).toHaveBeenCalledWith("");
});

it("classifies Design and Delivery entries from explicit lifecycle statuses", async () => {
  const planningGroup = group({
    change_id: "planning-change",
    title: "Admitted planning",
    items: [
      card({
        change_id: "planning-change",
        title: "Planning without a task plan",
        progress: {
          kind: "plan",
          label: "Task plan not published",
          done: null,
          total: null,
        },
      }),
    ],
  });
  const reentryGroup = group({
    change_id: "design-reentry",
    title: "Admitted Design re-entry",
    items: [
      card({
        change_id: "design-reentry",
        title: "Returned to Design",
        stage: "design",
        progress: {
          kind: "design-return",
          label: "Returned to Design",
          done: null,
          total: null,
        },
      }),
    ],
  });
  const basePortfolio = portfolio([planningGroup, reentryGroup]);
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [
        changeStatus("design-draft", {
          admission: "unadmitted",
          stage: "design",
          actionable_runtime: false,
        }),
        changeStatus("planning-change"),
        changeStatus("design-reentry", { stage: "design" }),
        changeStatus("unavailable-change", {
          actionable_runtime: false,
          diagnostic_code: "runtime_unavailable",
          diagnostic_detail: "Persisted admission is valid, but runtime composition is unavailable.",
        }),
      ],
      draft_design_change_ids: ["planning-change", "design-reentry", "unavailable-change"],
      design_required_change_ids: [],
    },
  };

  renderPage();

  const designWork = await screen.findByTestId("design-work-section");
  expect(designWork).toHaveTextContent("Design Draft");
  expect(designWork).not.toHaveTextContent("Admitted planning");
  expect(designWork).not.toHaveTextContent("Admitted Design re-entry");
  expect(designWork).not.toHaveTextContent("unavailable-change");

  const table = screen.getByTestId("work-portfolio-table");
  expect(table).toHaveTextContent("Admitted planning");
  expect(table).toHaveTextContent("Task plan not published");
  expect(table).toHaveTextContent("Admitted Design re-entry");

  const unavailable = screen.getByTestId("delivery-issues-section");
  expect(unavailable).toHaveTextContent("unavailable-change");
  expect(unavailable).toHaveTextContent("Runtime unavailable");
  expect(unavailable).toHaveTextContent("Persisted admission is valid, but runtime composition is unavailable.");
  expect(unavailable).not.toHaveTextContent("Not admitted to Delivery");

  const summary = await screen.findByLabelText("Delivery portfolio status");
  expect(summary).toHaveTextContent("4Changes");
  expect(summary).toHaveTextContent("2Design");
  expect(summary).toHaveTextContent("2Delivery");
});

it("shows bounded Delivery health diagnostics for quarantined state", async () => {
  const basePortfolio = portfolio([], {
    status: "attention",
    diagnostics: [
      {
        source: "local-runtime",
        code: "contract-identity-invalid",
        detail: "Persisted Change contract identity is invalid",
        change_id: "quarantined-change",
        path: ".owlbear/delivery/runtime/changes/quarantined-change",
        retry_safe: false,
        reason: "runtime-unavailable",
        resolution: "authority-gap",
        expected_head: null,
        observed_head: null,
        observed_local_head: null,
        head_relation: null,
      },
    ],
  });
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [
        changeStatus("quarantined-change", {
          actionable_runtime: false,
          diagnostic_code: "runtime_unavailable",
          diagnostic_detail: "Persisted Change contract identity is invalid",
        }),
      ],
    },
  };

  renderPage();

  const health = await screen.findByTestId("delivery-issues-section");
  expect(health).toHaveTextContent("Delivery issues");
  expect(health).toHaveTextContent("Quarantined state is hidden from dispatch.");
  expect(health).toHaveTextContent("quarantined-change");
  expect(health).toHaveTextContent("local-runtime / contract-identity-invalid");
  expect(health).toHaveTextContent("Persisted Change contract identity is invalid");
  expect(screen.queryByTestId("work-portfolio-table")).not.toBeInTheDocument();
});

it("shows actionable head evidence for a quarantined Change status", async () => {
  const expectedHead = "a".repeat(40);
  const remoteHead = "b".repeat(40);
  const localHead = "c".repeat(40);
  const basePortfolio = portfolio([], {
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
        expected_head: expectedHead,
        observed_head: remoteHead,
        observed_local_head: localHead,
        head_relation: "ancestor",
      },
    ],
  });
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [
        changeStatus("quarantined-change", {
          actionable_runtime: false,
          diagnostic_code: "runtime_unavailable",
          diagnostic_detail: "Remote Change branch differs from Delivery-state snapshot.",
        }),
      ],
    },
  };

  renderPage();

  const health = await screen.findByTestId("delivery-issues-section");
  expect(health).toHaveTextContent("No safe automatic repair is available.");
  expect(health).toHaveTextContent("/resolve-delivery-attention quarantined-change");
  expect(health).toHaveTextContent(expectedHead);
  expect(health).toHaveTextContent(remoteHead);
  expect(health).toHaveTextContent(localHead);
  expect(health).toHaveTextContent("ancestor");
});

it("tells the operator to upgrade when a newer controller wrote a remote snapshot", async () => {
  const basePortfolio = portfolio([], {
    status: "attention",
    diagnostics: [
      {
        source: "remote-state",
        code: "remote-state-version-unsupported",
        detail: "Remote Delivery snapshot schema_version 3 is newer than this controller supports (2).",
        change_id: "newer-change",
        path: ".owlbear/delivery/state/newer-change/snapshot.json",
        retry_safe: false,
        reason: "remote-state-version-unsupported",
        resolution: "authority-gap",
        expected_head: null,
        observed_head: null,
        observed_local_head: null,
        head_relation: null,
      },
    ],
  });
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [
        changeStatus("newer-change", {
          actionable_runtime: false,
          diagnostic_code: "remote-state-version-unsupported",
          diagnostic_detail: "Remote Delivery snapshot was written by a newer controller.",
        }),
      ],
    },
  };

  renderPage();

  const health = await screen.findByTestId("delivery-issues-section");
  expect(health).toHaveTextContent("remote-state / remote-state-version-unsupported");
  expect(health).toHaveTextContent("A newer Delivery controller wrote this Change's remote state.");
  expect(health).toHaveTextContent("Upgrade this controller before resuming the Change");
  expect(health).not.toHaveTextContent("/resolve-delivery-attention newer-change");
});

it("presents Change-grouped Outcomes by work, progress, and status", async () => {
  renderPage();

  const table = await screen.findByTestId("work-portfolio-table");
  expect(table).toHaveTextContent("Portfolio redesign");
  expect(table).toHaveTextContent("Work");
  expect(table).toHaveTextContent("State");
  expect(table).toHaveTextContent("Claimed");
  expect(table).not.toHaveTextContent("Working");
  expect(table).toHaveTextContent("Builder");
  expect(table).toHaveTextContent("Decision required");
  expect(table).toHaveTextContent("Answer request");
  expect(table).toHaveTextContent("Outcome: OUT-001");
  expect(within(table).getAllByText("OUT-001", { selector: "code" }).length).toBeGreaterThan(0);
  expect(within(table).getAllByText("Portfolio redesign")).toHaveLength(1);
  expect(await screen.findByLabelText("Delivery portfolio status")).toHaveTextContent("1Running");
  const guidance = screen.getByLabelText("Delivery guidance");
  expect(guidance).toHaveTextContent("Review 1 item that needs you");
  expect(guidance).toHaveTextContent("1 Work Item holds active custody; each Change shows its progress.");
  expect(guidance).not.toHaveTextContent("already working");
  expect(within(guidance).queryByTestId("portfolio-commands")).not.toBeInTheDocument();
  expect(table.compareDocumentPosition(guidance) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByText("Reviewed", { exact: true })).not.toBeInTheDocument();
});

it("copies empty-portfolio session commands with the shared compact control", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  fixtureState.currentPortfolio = portfolio([]);
  renderPage();

  const guidance = await screen.findByLabelText("Delivery guidance");
  const ideateCommand = within(guidance).getByRole("button", {
    name: "Copy command /ideate",
  });
  fireEvent.click(ideateCommand);

  await waitFor(() => expect(writeText).toHaveBeenCalledWith("/ideate"));
});

it("shows unadmitted Design work on the board and opens its verified sources", async () => {
  const basePortfolio = withUnadmittedDesign(portfolio());
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      guidance: [{ kind: "resume-design", change_ids: ["design-draft"], work_count: 1 }],
    },
  };
  renderPage("/delivery/design-draft/design");

  const designWork = await screen.findByTestId("design-work-section");
  expect(designWork).toHaveTextContent("Design Draft");
  expect(designWork).toHaveTextContent("Not admitted to Delivery");
  expect(designWork).not.toHaveTextContent("/design design-draft");
  expect(
    within(designWork).queryByRole("button", {
      name: "Copy command /design design-draft",
    }),
  ).not.toBeInTheDocument();
  expect(
    within(designWork)
      .getAllByRole("term")
      .map((term) => term.textContent),
  ).toEqual(["Work", "State"]);
  expect(within(designWork).getAllByRole("definition")).toHaveLength(2);
  const status = screen.getByLabelText("Delivery portfolio status");
  expect(status).toHaveTextContent("2Changes");
  expect(status).toHaveTextContent("1Design");
  expect(status).toHaveTextContent("1Delivery");

  const detailView = await screen.findByTestId("design-work-detail");
  expect(detailView).toHaveTextContent("Shape a coherent operator workflow.");
  const flyout = document.querySelector("p-flyout") as HTMLElement & {
    aria?: { "aria-label"?: string };
  };
  expect(flyout.aria?.["aria-label"]).toBe("Design detail");
  expect(detailView).toHaveTextContent("Continue with/design design-draft");
  expect(
    within(detailView).getByRole("button", {
      name: "Copy command /design design-draft",
    }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByText("Design", { selector: "summary" }));
  expect(detailView).toHaveTextContent("Keep authority explicit.");
  expect(fixtureState.requests.some(({ url }) => url === "/api/design-work/design-draft")).toBe(true);
  const guidance = screen.getByLabelText("Delivery guidance");
  expect(guidance).toHaveTextContent("Continue Design for: design-draft");
  expect(within(guidance).queryByTestId("portfolio-commands")).not.toBeInTheDocument();
});

it("uses Design-specific unavailable detail copy and retry action", async () => {
  const basePortfolio = withUnadmittedDesign(portfolio());
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
    },
  };
  fixtureState.designFailure = true;
  renderPage("/delivery/design-draft/design");

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("This Design work is unavailable.");
  expect(alert).toHaveTextContent("Retry Design");
  expect(alert).not.toHaveTextContent("This Work Item is unavailable.");

  fixtureState.designFailure = false;
  fireEvent.click(within(alert).getByText("Retry Design", { exact: true }));
  expect(await screen.findByTestId("design-work-detail")).toBeInTheDocument();
});

it("refreshes open Design detail after an authored package revision", async () => {
  vi.useFakeTimers();
  try {
    fixtureState.currentPortfolio = withUnadmittedDesign(portfolio());
    renderPage("/delivery/design-draft/design");

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    const detailView = screen.getByTestId("design-work-detail");
    expect(detailView).toHaveTextContent("Keep authority explicit.");

    fixtureState.currentDesignWork = {
      ...fixtureState.currentDesignWork,
      package_id: "e".repeat(64),
      design_markdown: "# Architecture\n\nUse the revised authority.",
    };
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    expect(detailView).toHaveTextContent("Use the revised authority.");
  } finally {
    vi.useRealTimers();
  }
});

it("shows stale Design detail state and retries the refresh in place", async () => {
  vi.useFakeTimers();
  try {
    renderPage("/delivery/design-draft/design");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    const detailView = screen.getByTestId("design-work-detail");
    fixtureState.designFailure = true;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Showing the last successful Design detail; live updates paused.");
    expect(alert).toHaveTextContent("Design source temporarily unavailable");
    expect(detailView).toBeInTheDocument();

    fixtureState.designFailure = false;
    fireEvent.click(within(alert).getByText("Retry Design", { exact: true }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(
      screen.queryByText("Showing the last successful Design detail; live updates paused."),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("design-work-detail")).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
}, 6_000);

it("closes removed Design detail after a portfolio refresh", async () => {
  const initialPortfolio = portfolio();
  fixtureState.currentPortfolio = withUnadmittedDesign(initialPortfolio);
  renderPage("/delivery/design-draft/design");
  await screen.findByTestId("design-work-detail");

  fixtureState.currentPortfolio = portfolio();
  fireEvent.click(screen.getByRole("button", { name: "Change history", exact: true }));
  await screen.findByTestId("completed-history-workspace");
  fireEvent.click(screen.getByRole("button", { name: "Current delivery", exact: true }));

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
      (element) => (element as HTMLElement & { open: boolean }).open,
    );
    expect(openFlyout).toBeUndefined();
  });
  await waitFor(() => expect(screen.getByRole("button", { name: "Current delivery", exact: true })).toHaveFocus());
});

it("filters grouped rows by Change and Needs without conflating Activity", async () => {
  const secondGroup = group({
    change_id: "change-beta",
    title: "Runtime hardening",
    snapshot_version: "b".repeat(64),
    outcome_total: 1,
    items: [
      card({
        change_id: "change-beta",
        needs: "dependency",
        needs_headline: "Waiting on OUT-009",
        next_actor: "dependency",
        next_step: "Waiting on OUT-009",
      }),
    ],
  });
  const basePortfolio = portfolio([group(), secondGroup]);
  fixtureState.currentPortfolio = {
    ...basePortfolio,
    operating: withUnadmittedDesign(basePortfolio).operating,
  };
  const { container } = renderPage();
  await screen.findByTestId("work-portfolio-table");

  const needsYou = screen.getByRole("button", {
    name: "Filter to 1 work item: Needs you",
  });
  fireEvent.click(needsYou);
  await waitFor(() => expect(needsYou).toHaveAttribute("aria-pressed", "true"));
  expect(screen.getByTestId("work-shown-count")).toHaveTextContent("2 of 4");
  fireEvent.click(needsYou);
  await waitFor(() => expect(needsYou).toHaveAttribute("aria-pressed", "false"));
  expect(screen.queryByTestId("work-shown-count")).not.toBeInTheDocument();

  const filterToggle = screen.getByTestId("work-filters-toggle");
  fireEvent.click(filterToggle);
  expect(filterToggle).toHaveAttribute("aria-expanded", "true");
  expect(filterToggle).toHaveAttribute("aria-controls", "work-filters-panel");
  expect(screen.getByTestId("work-filters-panel")).toHaveAttribute("id", "work-filters-panel");
  const selects = container.querySelectorAll("p-select");
  selectValue(selects[0], "change-alpha");
  selectValue(selects[1], "you");

  expect(screen.getByTestId("work-shown-count")).toHaveTextContent("1 of 4");
  expect(screen.getByTestId("work-portfolio-table")).toHaveTextContent("User controls");
  expect(screen.getByTestId("work-portfolio-table")).not.toHaveTextContent("Delivery foundation");
  expect(screen.getByTestId("work-portfolio-table")).not.toHaveTextContent("Runtime hardening");

  selectValue(selects[0], "");
  expect(await screen.findByTestId("design-work-section")).toHaveTextContent("Design Draft");
  expect(screen.getByTestId("work-shown-count")).toHaveTextContent("2 of 4");

  selectValue(selects[1], "dependency");
  await waitFor(() => expect(screen.queryByTestId("design-work-section")).not.toBeInTheDocument());
  expect(screen.getByTestId("work-shown-count")).toHaveTextContent("1 of 4");

  selectValue(selects[1], "you");
  selectValue(selects[0], "change-beta");
  expect(await screen.findByText("No matching delivery work")).toBeInTheDocument();
  expect(screen.queryByText("No current Delivery work.")).not.toBeInTheDocument();
});

it("keeps routed detail open when filters hide its portfolio row", async () => {
  const secondGroup = group({
    change_id: "change-beta",
    title: "Runtime hardening",
    snapshot_version: "b".repeat(64),
    items: [
      card({
        change_id: "change-beta",
        title: "Blocked runtime task",
        needs: "dependency",
        needs_headline: "Waiting on OUT-009",
        next_actor: "dependency",
        next_step: "Waiting on OUT-009",
      }),
    ],
  });
  fixtureState.currentPortfolio = portfolio([group(), secondGroup]);
  const { container } = renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(screen.getByTestId("work-filters-toggle"));
  const selects = container.querySelectorAll("p-select");
  selectValue(selects[1], "dependency");

  await waitFor(() => expect(table).not.toHaveTextContent("Delivery foundation"));
  expect(inspector).toBeInTheDocument();
  expect(screen.getByTestId("work-filters-panel")).toBeInTheDocument();

  fireEvent.keyDown(inspector, { key: "Escape" });
  await waitFor(() => expect(screen.getByTestId("work-filters-toggle")).toHaveFocus());
});

it("restores focus to the clicked work item after closing its detail", async () => {
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  const itemLink = within(table).getAllByRole("link", {
    name: /Delivery foundation/,
  })[0];

  fireEvent.click(itemLink);
  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.keyDown(inspector, { key: "Escape" });

  await waitFor(() => expect(itemLink).toHaveFocus());
});

it("restores focus to the row trigger after opening the detail from a row action link", async () => {
  fixtureState.currentDetail = detail({
    card: card({
      item_key: "outcome:OUT-002",
      work_item_id: "OUT-002",
      title: "User controls",
      needs: "you",
      action: {
        kind: "answer-request",
        label: "Answer request",
        command: null,
      },
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  const itemLink = within(table).getAllByRole("link", {
    name: /User controls/,
  })[0];
  const actionLink = within(table).getAllByText("Answer request")[0].closest("p-link-pure") as HTMLElement;

  fireEvent.click(actionLink);
  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.keyDown(inspector, { key: "Escape" });

  await waitFor(() => expect(itemLink).toHaveFocus());
});

it("opens routed semantic detail with acceptance and bounded task evidence", async () => {
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const inspector = await screen.findByTestId("work-item-detail");
  expect(screen.getByLabelText("Delivery guidance")).toBeInTheDocument();
  expect(screen.getByTestId("work-portfolio-table")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Current delivery" })).not.toBeInTheDocument();
  expect(inspector).toHaveTextContent("Portfolio redesign / OUT-001");
  expect(within(inspector).getByText("OUT-001", { selector: "code" })).toBeInTheDocument();
  expect(inspector).toHaveTextContent("Make Delivery supervision coherent.");
  expect(inspector).toHaveTextContent("The current state is unambiguous.");
  expect(inspector).toHaveTextContent("Build the projection");
  expect(inspector).toHaveTextContent("A reviewed grouped snapshot.");
  expect(screen.getByText("Acceptance (1)").closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText("Delivery task evidence (1)").closest("details")).not.toHaveAttribute("open");
  expect(
    fixtureState.requests.some(({ url }) => url === "/api/changes/change-alpha/work-items/outcome%3AOUT-001"),
  ).toBe(true);
});

it("shows a refused retry as a blocked non-executable current exception", async () => {
  fixtureState.currentDetail = detail({
    active_claim: {
      attempt_id: "attempt-retry",
      claim_id: "claim-retry",
      owner_id: "planner-001",
      process_id: "process-retry",
      continuation: false,
      started_at: "2026-09-30T12:00:00Z",
      worker_role: "planner",
      task_id: null,
    },
    retry_diagnostic: {
      code: "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
      attempt_id: "attempt-retry",
      transition: {
        action: "retry",
        outcome_id: "OUT-001",
        claim_id: "claim-retry",
        abandoned_commit: null,
        attempt_id: null,
        failure_code: "planner-failed",
      },
    },
    readiness: readiness({
      status: "blocked",
      next_actor: "none",
      reason_code: "retry-transition-contained",
      prompt:
        "/repair-delivery Inspect only Change change-alpha using the bounded offline inspector. " +
        "Make no MCP calls; do not retry.",
    }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const readinessView = within(inspector).getByTestId("delivery-readiness");
  expect(within(readinessView).getByTestId("readiness-status")).toHaveTextContent("Blocked");
  expect(within(readinessView).getByText("Next: Nobody")).toBeInTheDocument();
  expect(within(readinessView).getByTestId("readiness-not-executable")).toBeInTheDocument();
  expect(within(readinessView).getByText("retry-transition-contained")).toBeInTheDocument();
  expect(within(readinessView).getByTestId("readiness-prompt")).toHaveTextContent("Make no MCP calls");
  expect(inspector).toHaveTextContent("Retry refused");
  expect(inspector).toHaveTextContent(
    "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED: planner-failed for attempt attempt-retry " +
      "and claim claim-retry remains active because host worker-exclusion evidence is missing.",
  );
});

it("answers a decision request and refetches its resolved state", async () => {
  fixtureState.currentDetail = detail({
    requests: [
      {
        request_id: "REQ-001",
        kind: "decision",
        outcome_id: "OUT-001",
        summary: "Choose the retained contract",
        options: [{ option_id: "keep", label: "Keep it" }],
        resolution: null,
      },
    ],
  });
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByText("Choose the retained contract");

  const submit = screen.getByText("Submit answer") as HTMLElement & {
    disabled: boolean;
  };
  const option = await waitFor(() => {
    const element = namedPdsHost(container, "p-select", "request-REQ-001-option");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  selectValue(option, "keep");
  await waitFor(() => expect(submit.disabled).toBe(false));
  fireEvent.click(submit);

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/requests/REQ-001/answer",
      method: "POST",
      body: {
        selected_option_id: "keep",
        response_text: null,
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );
  expect(await screen.findByText("Keep it")).toBeInTheDocument();
});

it("clears action feedback when switching to another work item", async () => {
  fixtureState.currentDetail = detail({
    requests: [
      {
        request_id: "REQ-001",
        kind: "decision",
        outcome_id: "OUT-001",
        summary: "Choose the retained contract",
        options: [{ option_id: "keep", label: "Keep it" }],
        resolution: null,
      },
    ],
  });
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByText("Choose the retained contract");

  const submit = screen.getByText("Submit answer") as HTMLElement & {
    disabled: boolean;
  };
  const option = await waitFor(() => {
    const element = namedPdsHost(container, "p-select", "request-REQ-001-option");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  selectValue(option, "keep");
  await waitFor(() => expect(submit.disabled).toBe(false));
  fireEvent.click(submit);
  expect(await screen.findByText("Request answered.")).toBeInTheDocument();

  fireEvent.click(screen.getAllByRole("link", { name: "User controls" })[0]);
  await waitFor(() => expect(screen.queryByText("Request answered.")).not.toBeInTheDocument());
});

it("shows a loading state instead of stale detail while switching work items", async () => {
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");
  fixtureState.pendingDetailItemKey = "outcome%3AOUT-002";

  try {
    fireEvent.click(screen.getAllByRole("link", { name: "User controls" })[0]);
    await screen.findByText("Loading Work Item details...");
  } finally {
    fixtureState.pendingDetailRelease?.();
    fixtureState.pendingDetailItemKey = null;
    fixtureState.pendingDetailRelease = null;
  }
});

it("clears earlier action feedback before previewing a backward move", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "planning" }),
    requests: [
      {
        request_id: "REQ-001",
        kind: "decision",
        outcome_id: "OUT-001",
        summary: "Choose the retained contract",
        options: [{ option_id: "keep", label: "Keep it" }],
        resolution: null,
      },
    ],
  });
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByText("Choose the retained contract");

  const submit = screen.getByText("Submit answer") as HTMLElement & {
    disabled: boolean;
  };
  const option = await waitFor(() => {
    const element = namedPdsHost(container, "p-select", "request-REQ-001-option");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  selectValue(option, "keep");
  await waitFor(() => expect(submit.disabled).toBe(false));
  fireEvent.click(submit);
  expect(await screen.findByText("Request answered.")).toBeInTheDocument();

  fireEvent.click(screen.getByText("Administrative actions"));
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-select", "backward-stage"),
      namedPdsHost(container, "p-input-text", "backward-reason"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  selectValue(stage, "design");
  inputValue(reason, "Authority changed");
  fireEvent.click(screen.getByText("Review backward move"));

  await screen.findByText("The following Outcomes will be reset:");
  expect(screen.queryByText("Request answered.")).not.toBeInTheDocument();
});

it("requires evidence before clearing a requestless block", async () => {
  fixtureState.currentDetail = detail({
    block: {
      block_id: "BLOCK-001",
      reason: "Proof is missing",
      unblock_condition: "Verify external evidence",
      expected_evidence: ["Evidence locator"],
      locators: ["request:REQ-001"],
      request_id: null,
      resolution_note: null,
      resolution_locators: [],
      resume_commit: null,
    },
  });
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  const clear = (await screen.findByText("Clear block")) as HTMLElement & {
    disabled: boolean;
  };
  expect(clear.disabled).toBe(true);

  const [note, locator] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-input-text", "block-note"),
      namedPdsHost(container, "p-input-text", "block-locator"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  inputValue(note, "Verified externally");
  inputValue(locator, "request:REQ-001");
  await waitFor(() => expect(clear.disabled).toBe(false));
  fireEvent.click(clear);

  await waitFor(() =>
    expect(
      fixtureState.requests.some(({ url, method }) => method === "POST" && url.includes("/blocks/BLOCK-001/clear")),
    ).toBe(true),
  );
  expect(await screen.findByText("Block cleared.")).toBeInTheDocument();
});

it("keeps block evidence available when clearing the block fails", async () => {
  fixtureState.currentDetail = detail({
    block: {
      block_id: "BLOCK-001",
      reason: "Proof is missing",
      unblock_condition: "Verify external evidence",
      expected_evidence: ["Evidence locator"],
      locators: ["request:REQ-001"],
      request_id: null,
      resolution_note: null,
      resolution_locators: [],
      resume_commit: null,
    },
  });
  fixtureState.mutationFailurePath = "/clear";
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  const clear = (await screen.findByText("Clear block")) as HTMLElement & {
    disabled: boolean;
  };
  const [note, locator] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-input-text", "block-note"),
      namedPdsHost(container, "p-input-text", "block-locator"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  inputValue(note, "Verified externally");
  inputValue(locator, "request:REQ-001");
  await waitFor(() => expect(clear.disabled).toBe(false));
  fireEvent.click(clear);

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("The Delivery operation was rejected while the confirmation was open.");
  expect((note as HTMLElement & { value: string }).value).toBe("Verified externally");
  expect((locator as HTMLElement & { value: string }).value).toBe("request:REQ-001");
  await waitFor(() => expect(clear.disabled).toBe(false));
});

it("releases a stuck worker after an explicit confirmation and keeps backward movement confirmable", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: runningBuilderClaim,
    readiness: readiness({ status: "running", reason_code: "active-custody" }),
  });
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByText("Release stuck worker");
  fireEvent.click(screen.getByText("Release stuck worker"));
  const dialog = screen.getByRole("alertdialog");
  expect(dialog).toHaveTextContent("Use this only for a worker whose chat was stopped or whose VS Code window closed.");
  expect(dialog).toHaveTextContent("counts toward this work's retry budget");
  expect(dialog).toHaveTextContent("The worktree, including uncommitted work, is preserved for the next attempt.");
  expect(dialog).toHaveTextContent(
    "changes nothing while any process still uses the worktree or if it changed in the last 30 seconds.",
  );
  expect(dialog.textContent ?? "").not.toMatch(/two minutes/i);
  expect(dialog.textContent ?? "").not.toMatch(/\bstops?\b|\bkill|\bterminal\b|\brun the\b|\bcommand\b/i);
  fireEvent.click(within(dialog).getByText("Confirm release"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/workers/release-stuck",
      method: "POST",
      body: { outcome_id: "OUT-001", attempt_id: "attempt-one", claim_id: "claim-one" },
    }),
  );
  expect(
    await screen.findByText("Stuck worker released. The attempt was recorded as failed; its work is preserved."),
  ).toBeInTheDocument();
  expect(fixtureState.requests.some(({ url }) => url.endsWith("/claims/recover"))).toBe(false);

  fireEvent.click(screen.getByText("Administrative actions"));
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-select", "backward-stage"),
      namedPdsHost(container, "p-input-text", "backward-reason"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  selectValue(stage, "planning");
  inputValue(reason, "Authority changed");
  fireEvent.click(screen.getByText("Review backward move"));
  const previewMessage = await screen.findByText("The following Outcomes will be reset:");
  const previewModal = requirePresent(previewMessage.closest("p-modal"));
  expect(within(previewModal).getByText("OUT-002")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Confirm backward move"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/outcomes/OUT-001/move-backward",
      method: "POST",
      body: {
        target: "planning",
        reason: "Authority changed",
        snapshot_version: "a".repeat(64),
      },
    }),
  );
  expect(await screen.findByText("Moved backward. Reset: OUT-002.")).toBeInTheDocument();
});

it.each([
  ["write", "the worker may still be active. Nothing was changed."],
  ["processes", "1 process (node) is still active in the worker's worktree"],
  ["unobservable", "could not be observed safely"],
] as const)("keeps the release confirmation open when a %s guard refuses the release", async (guard, message) => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: runningBuilderClaim,
    readiness: readiness({ status: "running", reason_code: "active-custody" }),
  });
  fixtureState.releaseStuckWorkerActive = guard;
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByText("Release stuck worker");
  fireEvent.click(screen.getByText("Release stuck worker"));
  fireEvent.click(screen.getByText("Confirm release"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/workers/release-stuck",
      method: "POST",
      body: { outcome_id: "OUT-001", attempt_id: "attempt-one", claim_id: "claim-one" },
    }),
  );
  const dialog = screen.getByRole("alertdialog");
  const feedback = await within(dialog).findByRole("status");
  expect(feedback).toHaveTextContent("ERR_DELIVERY_WORKER_ACTIVE");
  expect(feedback).toHaveTextContent(message);
  if (guard === "write") {
    const retryAfter = within(feedback).getByTestId("worker-active-retry-after");
    expect(retryAfter).toHaveTextContent("2026-10-02T12:00:30Z");
    expect(retryAfter).toHaveAttribute("datetime", "2026-10-02T12:00:30Z");
  } else {
    expect(within(feedback).queryByTestId("worker-active-retry-after")).not.toBeInTheDocument();
    expect(feedback).not.toHaveTextContent("Retry at or after");
  }
  expect(within(dialog).getByText("Release stuck worker")).toBeInTheDocument();
  expect(screen.getByTestId("work-item-detail")).toHaveTextContent("attempt-one");
});

it("explains a stall wait without an eligible time while processes still use the worktree", async () => {
  const prompt = "/continue-change change-alpha 1 process (node) is still active in its worktree.";
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: runningBuilderClaim,
    readiness: readiness({ status: "waiting", reason_code: "worker-stall-wait", next_eligible_at: null, prompt }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-prompt")).toHaveTextContent(prompt);
  expect(within(inspector).getByTestId("worker-stall-no-eligible-time")).toHaveTextContent(
    "processes still use this worker's worktree",
  );
  expect(inspector).not.toHaveTextContent("Next eligible at");
  expect(within(inspector).queryByText("Release stuck worker")).not.toBeInTheDocument();
});

it.each([
  ["another claim", { attempt_id: "attempt-two", claim_id: "claim-two" }, "running"],
  ["a stall wait", {}, "worker-stall-wait"],
] as const)("withdraws an open release confirmation when polling shows %s", async (_case, identity, next) => {
  vi.useFakeTimers();
  try {
    fixtureState.currentDetail = detail({
      card: card({ stage: "implementation" }),
      active_claim: runningBuilderClaim,
      readiness: readiness({ status: "running", reason_code: "active-custody" }),
    });
    renderPage("/delivery/change-alpha/outcome%3AOUT-001");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    fireEvent.click(screen.getByText("Release stuck worker"));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("attempt-one");

    fixtureState.currentDetail = detail({
      card: card({ stage: "implementation" }),
      active_claim: { ...runningBuilderClaim, ...identity },
      readiness:
        next === "running"
          ? readiness({ status: "running", reason_code: "active-custody" })
          : readiness({ status: "waiting", reason_code: "worker-stall-wait" }),
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(screen.queryByText("Confirm release")).not.toBeInTheDocument();
    expect(fixtureState.requests.some(({ url }) => url.endsWith("/workers/release-stuck"))).toBe(false);
  } finally {
    vi.useRealTimers();
  }
});

it.each(["running", "worker-stall-wait"] as const)(
  "releases a held Finalizer from the publication card only while it runs (%s)",
  async (state) => {
    fixtureState.currentDetail = detail({
      card: publicationCardForChecks(),
      publication: publicationForChecks("ready-for-finalization"),
      held_finalizer: {
        attempt_id: "finalizer-attempt",
        claim_id: "finalizer-claim",
        owner_id: "vscode-host",
        process_id: "chat-session",
        started_at: "2026-10-02T12:00:00Z",
      },
      readiness:
        state === "running"
          ? readiness({ status: "running", reason_code: "active-custody" })
          : readiness({ status: "waiting", reason_code: "worker-stall-wait" }),
    });
    renderPage("/delivery/change-alpha/publication");

    const inspector = await screen.findByTestId("work-item-detail");
    expect(inspector).toHaveTextContent("Active claim");
    expect(inspector).toHaveTextContent("Finalizer");
    if (state === "worker-stall-wait") {
      expect(within(inspector).queryByText("Release stuck worker")).not.toBeInTheDocument();
      return;
    }
    fireEvent.click(within(inspector).getByText("Release stuck worker"));
    fireEvent.click(within(screen.getByRole("alertdialog")).getByText("Confirm release"));
    await waitFor(() =>
      expect(fixtureState.requests).toContainEqual({
        url: "/api/changes/change-alpha/workers/release-stuck",
        method: "POST",
        body: { outcome_id: null, attempt_id: "finalizer-attempt", claim_id: "finalizer-claim" },
      }),
    );
  },
);

it("offers stuck-worker release only for running claims", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: runningBuilderClaim,
    readiness: readiness({ status: "blocked", next_actor: "none", reason_code: "retry-transition-contained" }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Active claim");
  expect(within(inspector).queryByText("Release stuck worker")).not.toBeInTheDocument();
});

it("clears a backward target that becomes invalid after a successful move", async () => {
  fixtureState.currentDetail = detail({ card: card({ stage: "implementation" }) });
  fixtureState.moveBackwardUpdatesDetailStage = "planning";
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");

  fireEvent.click(screen.getByText("Administrative actions"));
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-select", "backward-stage"),
      namedPdsHost(container, "p-input-text", "backward-reason"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  selectValue(stage, "planning");
  inputValue(reason, "Authority changed");
  fireEvent.click(screen.getByText("Review backward move"));
  await screen.findByText("The following Outcomes will be reset:");
  fireEvent.click(screen.getByText("Confirm backward move"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/outcomes/OUT-001/move-backward",
      method: "POST",
      body: {
        target: "planning",
        reason: "Authority changed",
        snapshot_version: "a".repeat(64),
      },
    }),
  );
  await waitFor(() => expect((stage as HTMLElement & { value: string }).value).toBe(""));
  expect(
    (
      screen.getByText("Review backward move") as HTMLElement & {
        disabled: boolean;
      }
    ).disabled,
  ).toBe(true);
});
