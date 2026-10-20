import { type ComponentType, type LazyExoticComponent, lazy } from "react";

const IdeasPage = lazy(() => import("./pages/IdeasPage"));
const MemoryTab = lazy(() => import("./pages/MemoryTab"));

type WorkspaceComponent = ComponentType<Record<string, never>>;

export interface RouteConfigEntry {
  path: string;
  label: string;
  icon: string;
  kind?: "board" | "workspace";
  component: WorkspaceComponent | LazyExoticComponent<WorkspaceComponent>;
}

export const routeConfig: RouteConfigEntry[] = [
  {
    path: "/memory",
    label: "Memory",
    icon: "memory",
    component: MemoryTab,
  },
  {
    path: "/ideas",
    label: "Ideas",
    icon: "ideas",
    component: IdeasPage,
  },
];

export function routeForPath(pathname: string): RouteConfigEntry | undefined {
  return routeConfig.find((route) => pathname === route.path);
}

/** Superseded paths kept reachable so existing links and bookmarks still resolve. */
export const legacyRouteRedirects: Array<{ from: string; to: string }> = [
  { from: "/", to: "/memory" },
  { from: "/memories", to: "/memory" },
];
