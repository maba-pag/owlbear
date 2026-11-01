// Settings' groups (D-01M63C8QQMANY46N8GMNNKH1V9): one view each, with its own address; the menu's Settings level
// lists them too. No imports: every page's menu reads this list.

export const GROUPS = [["overview", "Overview"], ["agents", "Agents"], ["runs", "Runs"], ["checks", "Checks and merge"],
  ["project", "Project"], ["this-machine", "This machine"]];

// Each group's sections and rows by the names their ids start with: a heading's (agents-title), a table's, a row's
// (set-spotter-switch) or a control's (global-machine-channel). An old address names one of them.
const PARTS = {
  overview: ["scope", "unset", "across", "reads"],
  agents: ["agents", "models", "shaper", "subagents", "spotter", "user-config", "load_user"],
  runs: ["rounds", "limits", "at-once", "sessions", "curation", "curator_threshold"],
  checks: ["general", "widths", "design_failures", "agreement", "impeccable", "merge", "prefs", "pr"],
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

// The row that sets an unset key, as the server and This machine name it (agents.builder.model, machine.channel).
export function rowOf(key) {
  const [head, role, field] = key.split(".");
  if (head === "final_review") return "set-rounds-final_review";
  if (head !== "agents") return `set-${key.replaceAll(".", "-")}`;
  const table = ["model", "effort", "context"].includes(field) ? "agents" : field === "minutes" ? "limits"
    : field === "subagents" ? "subagents" : "rounds";
  return `set-${table}-${role}`;
}

// The group an unsaved draft belongs to, by its key as the page keeps it ("builder.model", "spot.looks").
export function draftGroup(key) {
  const [head, field] = key.split(".");
  if (head === "machine") return "this-machine";
  if (head === "spot" || head.startsWith("load_user_") || ["model", "effort", "context", "subagents"].includes(field)) {
    return "agents";
  }
  return ["widths", "design_failures", "prefs", "pr_labels", "pr_marker"].includes(head) ? "checks" : "runs";
}
