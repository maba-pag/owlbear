import { PToast } from "@porsche-design-system/components-react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import CopyCommand from "../components/CopyCommand";

afterEach(() => {
  vi.restoreAllMocks();
});

function stubClipboard(writeText: (value: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
}

function renderCommand(command: string) {
  render(
    <>
      <CopyCommand command={command} />
      <PToast />
    </>,
  );
  const toast = document.querySelector("p-toast") as HTMLElement & {
    addMessage: (message: unknown) => void;
  };
  return vi.spyOn(toast, "addMessage");
}

it("copies the complete command and confirms success", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  stubClipboard(writeText);
  const addMessage = renderCommand("/design website-to-knowledge-vertical");

  fireEvent.click(
    screen.getByRole("button", {
      name: "Copy command /design website-to-knowledge-vertical",
    }),
  );

  await waitFor(() => expect(writeText).toHaveBeenCalledWith("/design website-to-knowledge-vertical"));
  expect(addMessage).toHaveBeenCalledWith({
    text: "Copied /design website-to-knowledge-vertical",
    state: "success",
  });
  expect(screen.getByRole("button")).toHaveAttribute("title", "Copied /design website-to-knowledge-vertical");
});

it("reports a clipboard failure without navigating", async () => {
  stubClipboard(vi.fn().mockRejectedValue(new Error("Clipboard denied")));
  const addMessage = renderCommand("/orchestrate");

  fireEvent.click(screen.getByRole("button", { name: "Copy command /orchestrate" }));

  await waitFor(() =>
    expect(addMessage).toHaveBeenCalledWith({
      text: "Could not copy /orchestrate",
      state: "error",
    }),
  );
  expect(screen.getByRole("button")).toHaveAttribute("title", "Could not copy /orchestrate");
});

it.each([
  [true, "Copied continuation prompt", "success"],
  [false, "Could not copy continuation prompt", "error"],
])("labelled copy keeps the exact prompt and names the copy (clipboard ok=%s)", async (ok, text, state) => {
  const prompt = "/continue-change change-a reread get_change and pass its readiness basis unchanged.";
  const writeText = ok ? vi.fn().mockResolvedValue(undefined) : vi.fn().mockRejectedValue(new Error("denied"));
  stubClipboard(writeText);
  render(
    <>
      <CopyCommand
        command={prompt}
        label="Copy continuation prompt"
        helper="Run it in Copilot Chat. Copying does not start an agent."
      />
      <PToast />
    </>,
  );
  const toast = document.querySelector("p-toast") as HTMLElement & { addMessage: (message: unknown) => void };
  const addMessage = vi.spyOn(toast, "addMessage");
  const button = screen.getByRole("button", { name: "Copy continuation prompt" });
  expect(button).toHaveAccessibleDescription("Run it in Copilot Chat. Copying does not start an agent.");
  expect(button).not.toHaveTextContent("/continue-change");

  fireEvent.click(button);

  await waitFor(() => expect(addMessage).toHaveBeenCalledWith({ text, state }));
  expect(writeText).toHaveBeenCalledWith(prompt);
});
