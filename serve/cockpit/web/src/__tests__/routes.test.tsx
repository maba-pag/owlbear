/** Durable route-contract tests for Cockpit routing. */

import { describe, expect, it } from "vitest";
import { legacyRouteRedirects, routeConfig, routeForPath } from "../routes";

// Mined from #1639 and #1644: route configuration, redirects, lazy loading, and path matching.

describe("RoutesConfigContracts", () => {
  it("exposes exactly the preserved utility routes", () => {
    const paths = routeConfig.map((entry) => entry.path);
    expect(paths).toEqual(["/memory", "/ideas"]);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it("redirects superseded paths to the aligned route", () => {
    expect(legacyRouteRedirects).toEqual([
      { from: "/", to: "/memory" },
      { from: "/memories", to: "/memory" },
    ]);
    const paths = routeConfig.map((entry) => entry.path);
    for (const redirect of legacyRouteRedirects) {
      expect(paths).toContain(redirect.to);
      expect(paths).not.toContain(redirect.from);
    }
  });

  it("loads the Memory route lazily", () => {
    const memoryEntry = routeConfig.find((entry) => entry.path === "/memory");
    expect(memoryEntry?.component).toBeDefined();
    expect((memoryEntry?.component as { $$typeof?: symbol })?.$$typeof).toBe(Symbol.for("react.lazy"));
  });

  it("matches only exact route paths", () => {
    expect(routeForPath("/memory")?.path).toBe("/memory");
    expect(routeForPath("/ideas")?.path).toBe("/ideas");
    expect(routeForPath("/memory/extra")).toBeUndefined();
    expect(routeForPath("/delivery")).toBeUndefined();
    expect(routeForPath("/unknown")).toBeUndefined();
  });
});
