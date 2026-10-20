import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it, vi } from "vitest";
import CockpitShell from "./CockpitShell";

function requirePresent<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) {
    throw new Error("Expected value to be present");
  }
  return value;
}

vi.mock("./components/ThemeToggle", () => ({
  default: () => <button type="button">Theme</button>,
}));

vi.mock("./routes", () => {
  const routeConfig = [
    {
      path: "/memory",
      label: "Memory",
      icon: "memory",
      component: () => <main>Memory workspace</main>,
    },
    {
      path: "/ideas",
      label: "Ideas",
      icon: "ideas",
      component: () => <main>Ideas workspace</main>,
    },
  ];
  return {
    routeConfig,
    routeForPath: (pathname: string) => routeConfig.find((route) => pathname === route.path),
  };
});

it("navigates between the target product areas", async () => {
  render(
    <MemoryRouter initialEntries={["/memory"]}>
      <CockpitShell />
    </MemoryRouter>,
  );

  expect(screen.getByText("Memory workspace")).toBeInTheDocument();
  const desktopNavigation = screen.getByTestId("desktop-product-navigation");
  expect(desktopNavigation.querySelector('a[title="Memory"]')).toHaveAttribute("aria-current", "page");

  fireEvent.click(requirePresent(desktopNavigation.querySelector('a[title="Ideas"]')));

  expect(await screen.findByText("Ideas workspace")).toBeInTheDocument();
  expect(desktopNavigation.querySelector('a[title="Ideas"]')).toHaveAttribute("aria-current", "page");
});

it("opens labeled product navigation from the compact mobile header", () => {
  render(
    <MemoryRouter initialEntries={["/memory"]}>
      <CockpitShell />
    </MemoryRouter>,
  );

  fireEvent.click(screen.getByText("Open navigation"));

  const flyout = document.querySelector("p-flyout") as HTMLElement & {
    open: boolean;
  };
  expect(flyout.open).toBe(true);
  expect(flyout.querySelector("p-link-pure")).toHaveTextContent("Memory");
});

it("renders Not Found for an unmatched path", () => {
  render(
    <MemoryRouter initialEntries={["/unknown"]}>
      <CockpitShell />
    </MemoryRouter>,
  );

  expect(screen.getByTestId("not-found-view")).toBeInTheDocument();
});

it("does not render a generic command footer", () => {
  render(
    <MemoryRouter initialEntries={["/memory"]}>
      <CockpitShell />
    </MemoryRouter>,
  );

  expect(screen.queryByTestId("command-reference")).not.toBeInTheDocument();
});
