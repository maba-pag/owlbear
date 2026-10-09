import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { detail, fixtureState, installWorkPortfolioHarness, renderPage } from "./workPortfolioHarness";

installWorkPortfolioHarness();

const REVISION_PROMPT = "/design change-alpha Change requirements:";

it("copies the engine revision prompt and says to run it in Copilot Chat", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  fixtureState.currentDetail = detail({ revision_prompt: REVISION_PROMPT });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const copy = within(inspector).getByRole("button", { name: "Change requirements" });
  expect(copy).toHaveAccessibleDescription(
    "Copies a /design prompt. Add the requirement change and run it in Copilot Chat. Copying does not start an agent.",
  );
  const toast = document.querySelector("p-toast") as HTMLElement & { addMessage: (message: unknown) => void };
  const addMessage = vi.spyOn(toast, "addMessage");

  fireEvent.click(copy);

  await waitFor(() => expect(writeText).toHaveBeenCalledWith(REVISION_PROMPT));
  expect(addMessage).toHaveBeenCalledWith({ text: "Copied change requirements", state: "success" });
  expect(fixtureState.requests.filter((request) => request.method !== "GET")).toEqual([]);
});

it("offers no Change requirements control when Delivery authors no revision prompt", async () => {
  fixtureState.currentDetail = detail({ revision_prompt: null });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("change-pause-change-alpha")).toBeInTheDocument();
  expect(within(inspector).queryByRole("button", { name: "Change requirements" })).not.toBeInTheDocument();
});
