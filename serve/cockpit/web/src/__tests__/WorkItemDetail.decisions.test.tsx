import { fireEvent, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { detail, fixtureState, installWorkPortfolioHarness, renderPage } from "./workPortfolioHarness";

installWorkPortfolioHarness();

const DECISIONS = [
  {
    decision_id: "DEC-001",
    origin: "approved" as const,
    basis: "package approval",
    statement: "Use one portfolio page.",
    supersedes: [],
  },
  {
    decision_id: "DEC-002",
    origin: "decided" as const,
    basis: 'askQuestions 2026-10-08 "Which page layout?"',
    statement: "Use two portfolio pages.",
    supersedes: ["DEC-001"],
  },
  {
    decision_id: "DEC-003",
    origin: "autonomous" as const,
    basis: "decide yourself",
    statement: "Sort by stage.",
    supersedes: [],
  },
];

it("names each decision's origin, marks superseded ones and filters to the user's own", async () => {
  fixtureState.currentDetail = detail({ decisions: DECISIONS });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const list = within(inspector).getByRole("list", { name: "Decisions (3)" });
  const first = within(list).getByTestId("work-decision-DEC-001");
  expect(first).toHaveTextContent("Approved by you");
  expect(first).toHaveTextContent("Superseded");
  expect(within(list).getByTestId("work-decision-DEC-002")).toHaveTextContent("Decided by you");
  expect(within(list).getByTestId("work-decision-DEC-002")).toHaveTextContent("replaces DEC-001");
  expect(within(list).getByTestId("work-decision-DEC-003")).toHaveTextContent("Made by an agent");

  const filter = within(inspector).getByText("Show only your decisions");
  fireEvent.click(filter);

  expect(within(list).queryByTestId("work-decision-DEC-001")).not.toBeInTheDocument();
  expect(within(list).getByTestId("work-decision-DEC-002")).toBeInTheDocument();
  expect(within(list).queryByTestId("work-decision-DEC-003")).not.toBeInTheDocument();
  expect(within(inspector).getByText("Show all decisions")).toBeInTheDocument();
});

it("shows no decision section for a contract without recorded decisions", async () => {
  fixtureState.currentDetail = detail({ decisions: [] });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByText(/^Decisions \(/)).not.toBeInTheDocument();
});

it("marks an answered request that a later decision replaced as superseded", async () => {
  const answered = (request_id: string, summary: string, option: string) => ({
    request_id,
    kind: "decision" as const,
    outcome_id: "OUT-001",
    summary,
    options: [{ option_id: "a", label: option }],
    resolution: { selected_option_id: "a", response_text: null },
  });
  fixtureState.currentDetail = detail({
    requests: [answered("REQ-001", "Which page layout?", "One page"), answered("REQ-002", "Sort order?", "By stage")],
    superseded_request_ids: ["REQ-001"],
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const replaced = within(inspector).getByText("One page").closest("p");
  expect(replaced).toHaveTextContent("Superseded");
  expect(replaced).toHaveTextContent("replaced by a later decision");
  expect(within(inspector).getByText("By stage").closest("p")).not.toHaveTextContent("Superseded");
});
