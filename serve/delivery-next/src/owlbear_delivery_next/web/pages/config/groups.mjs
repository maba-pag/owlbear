// Settings' groups: one view each, with its own address; the menu's Settings level lists them too. No imports: every
// page's menu reads this list.

export const GROUPS = [["overview", "Overview"], ["agents", "Agents and runs"], ["guardrails", "Guardrails"],
  ["memory", "Memory"], ["checks", "Checks and merge"], ["project", "Project"], ["this-machine", "This machine"]];

// Each group's sections and rows by the names their ids start with: a heading's (agents-title), a table's, a row's
// (set-spotter-switch) or a control's (global-machine-channel). An old address names one of them; "runs" was a group.
const PARTS = {
  overview: ["scope", "unset", "across", "reads"],
  agents: ["agents", "models", "shaper", "subagents", "limits", "runs", "rounds", "at-once", "sessions"],
  guardrails: ["spotter", "user-config", "load_user", "guard"],
  memory: ["memory", "curation", "curator_threshold"],  // the curation section and its threshold moved here
  checks: ["general", "widths", "design_failures", "agreement", "impeccable", "merge", "prefs", "pr", "github_account"],
  project: ["folder", "rename"],
  "this-machine": ["machine", "global-machine"],
};

// The group an address opens: a group's own, or the group holding the section or row it names; else the overview.
export function groupOf(id) {
  if (GROUPS.some(([group]) => group === id)) return id;
  const name = id.replace(/^set-/, "");
  const part = (p) => name === p || name.startsWith(`${p}-`) || name.startsWith(`${p}_`);
  return Object.keys(PARTS).find((group) => PARTS[group].some(part)) ?? "overview";
}

// What an older address named that is no longer in the page, as what shows it now: the per-role subagents and session
// time rows became cells of the agent's row, and their sections and the Runs group went into Agents and runs.
export function renamed(id) {
  const row = id.match(/^set-(limits|subagents)-(.+)$/);
  if (row) return `set-agents-${row[2]}-${row[1] === "limits" ? "minutes" : "subagents"}`;
  return ["runs", "limits", "limits-title", "subagents", "subagents-title"].includes(id) ? "agents-title" : id;
}

// The row that sets an unset key, as the server and This machine name it (agents.builder.model, machine.channel).
export function rowOf(key) {
  const [head, role, field] = key.split(".");
  if (head === "final_review") return "set-rounds-final_review";
  if (head !== "agents") return `set-${key.replaceAll(".", "-")}`;
  if (["minutes", "subagents"].includes(field)) return `set-agents-${role}-${field}`;  // a cell of the agent's row
  return `set-${["model", "effort", "context"].includes(field) ? "agents" : "rounds"}-${role}`;
}

// The group an unsaved draft belongs to, by its key as the page keeps it ("builder.model", "spot.looks").
export function draftGroup(key) {
  const [head] = key.split(".");
  if (head === "machine") return "this-machine";
  if (head === "memory" || head === "curator_threshold") return "memory";
  if (head === "spot" || head.startsWith("load_user_") || head === "guard_level") return "guardrails";
  const checks = ["widths", "design_failures", "prefs", "pr_labels", "pr_marker", "github_account"];
  return checks.includes(head) ? "checks" : "agents";
}
