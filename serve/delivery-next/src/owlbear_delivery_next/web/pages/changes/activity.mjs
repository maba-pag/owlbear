import { html } from "/assets/lit-html/3.3.3/lit-html.js";
import { text } from "./widgets.mjs";

export function split(line) {  // the stage, then what is happening in it
  const at = line.indexOf(" \u00b7 ");
  return at < 0 ? ["", line] : [line.slice(0, at), line.slice(at + 3)];
}

// A card and the activity log name a file by its name; the current activity in the detail keeps the whole path. A
// tool's one target may hold spaces; elsewhere a path ends at one, and a relative one counts only with an extension,
// so counters, "CI/CD" and URLs stay as they are.
const LAST = String.raw`([^\s,/\u00b7]+)`;
export const short = (said) => said
  .replace(new RegExp(String.raw`(?<=(?:^|\u00b7 )(?!ran )[\w-]+ )~?\/(?:[^\s,/\u00b7][^,/\u00b7]*?\/)+${LAST}`, "g"),
    "$1")
  .replace(new RegExp(String.raw`(?<![^\s(])~?\/(?:[^\s,/\u00b7]+\/)+${LAST}`, "g"), "$1")
  .replace(/(?<![^\s(])(?![\d./]+(?=[\s,)\u00b7]|$))(?:[\w.-]+\/)+([\w-]*\.[\w.-]+)(?=[\s,)\u00b7]|$)/g, "$1");

function ago(iso) {
  const seconds = Math.round((Date.now() - Date.parse(iso)) / 1000);
  if (Number.isNaN(seconds)) return "";
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60), hours = Math.round(minutes / 60);
  return minutes < 60 ? `${minutes} min ago` : hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} d ago`;
}

const BOOKKEEPING = new Set(["pids", "inventory", "skill", "tasks", "preserved"]);
const CLASSES = { event: "an event", clarification: "a clarification", brief_change: "a brief change" };  // TD-461
const STEPS = {
  shape: "Shaping", plan: "Planning", tests: "Test review", build: "Building", review: "Review",
  integrate: "Update with the target", publish: "Publishing", follow: "Following the pull request",
  check: "Check preparation", merge: "Merge", cleanup: "Clean-up", "visual-review": "Visual review",
  "design-review": "Design review", "plan-challenge": "Plan challenge", "brief-challenge": "Brief challenge",
  "amendment-challenge": "Amendment challenge", "dispute-reconsider": "Reconsideration",
};
const EXITS = { done: "finished", retry: "will try again", ask: "asks you", back: "went back", stop: "stopped",
  pending: "waiting" };
const pr = (e) => (e.pr ? ` PR #${e.pr}` : "");
const why = (said) => (said ? `: ${said}` : "");
const sha = (s) => String(s || "").slice(0, 7);
const words = (name) => {
  const said = String(name).replaceAll(/[-_]/g, " ");
  return said.charAt(0).toUpperCase() + said.slice(1);
};
const METHOD = { queue: "merge queue" };

// A lint event records the linters that ran and the ones skipped; "passed" alone is true when none ran.
function linted(e) {
  const ran = (e.ran || []).map((r) => r.tool), skipped = (e.skipped || []).join("; ");
  if (!ran.length) return `Lint not run${why(skipped)}`;
  return `Lint ${e.passed ? "passed" : "found problems"} (${ran.join(", ")})${skipped ? `; skipped: ${skipped}` : ""}`;
}

// Each recorded event in plain words; an event this page does not know reads as its name, with its reason if any.
const SAID = {
  step: (e) => `${STEPS[e.kind] ?? words(e.kind ?? "step")} ${EXITS[e.exit] ?? "ended"}${why(e.reason)}`,
  tool: (e) => e.summary || `Called ${e.tool}${e.accepted === false ? " (refused)" : ""}`,
  session: (e) => (e.resumed ? "Session resumed" : `Session started${e.role ? ` (${e.role})` : ""}`),
  started: () => "Session started",
  ended: (e) => `Session ended${e.ending ? ` (${e.ending})` : ""}`,
  denied: (e) => `Denied: ${e.reason || e.kind}`,
  publish: (e) => `Published PR #${e.pr}`,
  labels: (e) => `Labelled PR #${e.pr}: ${e.labels.join(", ")}`,
  "labels-failed": (e) => `Could not label PR #${e.pr} with ${e.labels.join(", ")}: ${e.reason}`,
  ci: (e) => (e.failed?.length ? `CI failed: ${e.failed.join(", ")}`
    : `CI passed${e.passed?.length ? `: ${e.passed.join(", ")}` : ""}`),
  "merge-offer": (e) => `Merge offered for commit ${sha(e.head)}`,
  "merge-request": (e) => (e.status === "merged" ? `Merged${pr(e)}`
    : `Merge of${pr(e)} ${e.status === "refused" ? "refused" : "not confirmed"}${why(e.message)}`),
  "merge-enqueue": (e) => `Merge queue for${pr(e)}: ${e.message || e.status}`,
  merged: (e) => `Merged${pr(e)}${e.sha ? ` as ${sha(e.sha)}` : ""}${e.method
    ? ` (${METHOD[e.method] ?? e.method})` : ""}`,
  "queue-adopted": (e) => `Found${pr(e)} already in the merge queue`,
  "queue-left": (e) => `${pr(e).trim()} left the merge queue${why(e.reason)}`,
  "queue-removed": (e) => `${pr(e).trim()} was taken out of the merge queue${why(e.reason)}`,
  pullback: (e) => (e.state === "updated" ? `Local target branch updated${why(e.reason)}`
    : `Local target branch ${e.state === "behind" ? "left behind" : "not updated"}${why(e.reason)}`),
  "branch-retired": (e) => `Branch ${e.branch} ${e.result || "retired"}`,
  "branch-kept": (e) => `Branch ${e.branch} kept: it moved after the merge`,
  "workspace-kept": (e) => `Workspace ${e.path} kept${why(e.reason)}`,
  "read-only-kept": (e) => `Read-only copy kept${why(e.why)}`,
  "target-checks-unfinished": (e) => `Checks on ${sha(e.sha)} unfinished: ${(e.missing || []).join(", ")}`,
  "ro-install": (e) => `${e.command} in ${e.package}${e.ok ? "" : " failed"}`,
  "fix-drafted": (e) => `Drafted fix Change ${e.fix}`,
  "fix-draft-failed": () => "Could not draft a fix Change",
  brief: (e) => `Brief v${e.version} saved`,
  answer: (e) => `Answered ${e.question} as ${CLASSES[e.class] ?? e.class}`,
  reply: () => "Replied on the pull request",
  reopen: (e) => `Could not reopen${pr(e)}${why(e.error)}`,
  undo: (e) => `${e.error ? "Could not undo" : "Undid"} ${e.task === "final" ? "the work rejected at final review"
    : `task ${e.task}`}, attempt ${e.attempt}${why(e.error)}`,
  wave: (e) => `Judges started${e.left ? `, ${e.left} left` : ""}`,
  snapshot: () => "Check environment saved",
  "prepared-end": (e) => (e.cleanup && e.cleanup !== "ok" ? `Check ${e.check} not fully cleaned up: ${e.cleanup}`
    : `Check ${e.check} cleaned up`),
  "prepared-stray": () => "Stray files from preparing discarded",
  lint: linted,
  "lint-skipped": (e) => `Lint ${e.tool} skipped${why(e.reason)}`,
  "lint-unresolved": () => "Lint problems left unresolved",
  "subagent-started": (e) => `Subagent ${e.agent || ""} started${e.allowed === false ? " (not allowed)" : ""}`,
  subagent: (e) => `Subagent ${e.name || e.agent || ""} ${e.outcome || "ended"}`,
  "force-stop": () => "Session stopped",
  reminder: () => "Agent reminded to finish",
  shelved: () => "Shelved",
  "profile-confirmed": (e) => `Profile ${e.key} confirmed`,
  "profile-not-saved": (e) => `Profile ${e.key} not saved${why(e.reason)}`,
  "effort-omitted": (e) => `Effort ${e.effort} not sent: ${e.model} takes none`,
  "usage-unread": (e) => `Usage not read${why(e.reason)}`,
  "request-failed": (e) => `Request ${e.operation} failed (${e.error})`,
};

const said = (e) => short((SAID[e.event] ?? ((x) => `${words(x.event)}${why(x.reason || x.notice || x.why)}`))(e))
  .replaceAll(/\s+/g, " ").trim();

// A merge is recorded three times (its request, the merge, the merge step); it reads once, as the merge.
function oneMerge(events) {
  const merged = new Set(events.filter((e) => e.event === "merged").map((e) => `${e.pr}`));
  return events.filter((e) => !(
    (e.event === "merge-request" && e.status === "merged" && merged.has(`${e.pr}`))
    || (e.event === "step" && e.kind === "merge" && e.exit === "done"
      && [...merged].some((n) => String(e.reason || "").startsWith(`merged PR #${n} `)))));
}

// Newest first, in words, the same line in a row once with its count; bookkeeping stays in the activity file.
export function activityLog(events) {
  const lines = [];
  for (const e of oneMerge(events.filter((x) => x.event && !BOOKKEEPING.has(x.event)))) {
    const last = lines.at(-1), line = said(e);
    if (last?.line === line) [last.times, last.at] = [last.times + 1, e.at || last.at];
    else lines.push({ line, at: e.at, first: e.at, times: 1 });
  }
  const kept = lines.slice(-12).reverse();
  if (!kept.length) return text("Nothing yet.", { size: "xs", color: "contrast-medium" });
  const exact = (iso) => new Date(iso).toLocaleString();
  return html`<ol class="log">${kept.map((l) => html`<li>${l.at ? html`<time datetime=${l.at}
    title=${l.times > 1 && l.first && l.first !== l.at ? `${exact(l.first)} to ${exact(l.at)}` : exact(l.at)}
    >${ago(l.at)}</time>` : html`<span></span>`}<span>${l.line}${l.times > 1 ? html` <span class="times"><span
    aria-hidden="true">\u00d7${l.times}</span><span class="sr">, ${l.times} times</span></span>` : ""}</span></li>`)}
    </ol>`;
}
