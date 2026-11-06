import { isKnown, nameOf } from "./names.mjs";

const QUESTION = ["This step needs settings no layer sets: ", ". Fill them in on the Settings page."];
const UNSET = ["settings unset: ", "; fill them in on the Settings page"];
const RESUMED = "; its accepted edits ";

function names(keys, legacy = false) {
  return keys.map((key) => legacy && !isKnown(key) ? `${key} (no current Settings row)` : nameOf(key)).join(", ");
}

function between(text, [start, end]) {
  return text.startsWith(start) && text.endsWith(end) && text.length > start.length + end.length
    ? text.slice(start.length, -end.length).split(", ") : null;
}

export function questionText(q) {
  if (!/^state:[^:]+:settings-unset$/.test(q.cause ?? "")) return q.text;
  const keys = between(q.text, QUESTION);
  return keys ? `${QUESTION[0]}${names(keys, true)}${QUESTION[1]}` : q.text;
}

export function statusLine(row) {
  const q = row.question;
  if (!q || !row.line.endsWith(` \u00b7 waiting for you: ${q.text}`)) return row.line;
  return row.line.slice(0, -q.text.length) + questionText(q);
}

export function curationReason(reason) {
  const at = reason.indexOf(RESUMED), own = at < 0 ? reason : reason.slice(0, at);
  const suffix = at < 0 ? "" : reason.slice(at);
  const keys = between(own, UNSET);
  if (keys) return `${UNSET[0]}${names(keys, true)}${UNSET[1]}${suffix}`;
  if (own === "agents.curator.subagents is unset") return `${names(["agents.curator.subagents"])} is unset${suffix}`;
  return reason;
}
