import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { DIALOG, state, send } from "./state.mjs";
import { button, hd, text, list, panel, info } from "./widgets.mjs";
import { merging } from "./forms.mjs";
import { marks, findingDetails, WORKERS } from "./progress.mjs";

function screen(s) {
  const steps = s.steps.map((x) => (x.do === "type" ? `type "${x.text}" into ${x.target}` : `click ${x.target}`));
  return `${s.name} (${s.path}${steps.length ? `, then ${steps.join(", ")}` : ""}): ${s.expect}`;
}

// Who stated a technical item (TD-179 rule 1): the owner himself, or the shaper, whose proposal the approval accepts.
// Keys: a criterion's id, `screen:<name>`, `check:<name>`.
function yours(d, key) {
  return (d.brief.specified || []).includes(key);
}

// Each entry: what was asked (or what kind of item it is) as a small label, then the answer.
function saidList(items) {
  return html`<ul class="said">${items.map(([label, answer]) => html`<li><span class="label">${label}</span>
    <span>${answer}</span></li>`)}</ul>`;
}

function part(title, ...children) {
  return html`<section>${hd(4, title, "sm")}${children}</section>`;
}

// The agreement the owner approves (TD-122, TD-179 rule 2): his decisions, what he specified among the technical
// details, the shaper's choices that the approval accepts, and what is out.
function agreement(d, approved = false) {
  const decisions = d.brief.decisions || [], out = d.brief.non_goals || [], parts = [];
  const mine = decisions.filter((x) => x.origin === "decided").map((x) => [x.question, x.answer]);
  const specified = [
    ...d.criteria.filter((k) => yours(d, k.id)).map((k) => ["Acceptance criterion", k.text]),
    ...d.brief.visual.filter((s) => yours(d, `screen:${s.name}`)).map((s) => ["Screen the visual check takes",
      screenSaid(s)]),
    ...d.checks.filter((c) => yours(d, `check:${c.id}`)).map((c) => ["Check you do yourself", checkSaid(c)]),
  ];
  if (mine.length || specified.length) parts.push(part("Your decisions", saidList([...mine, ...specified])));
  const proposed = decisions.filter((x) => x.origin !== "decided").map((x) => [x.question, x.answer]);
  if (proposed.length) {
    const accepts = approved ? "Your approval accepted these choices." : "Approving accepts these choices.";
    parts.push(part("Choices proposed by the shaper", text(accepts), saidList(proposed)));
  }
  if (!decisions.length && !specified.length) parts.push(text("No separate decisions recorded."));
  if (out.length) parts.push(part("Not in this Change", list(out)));
  return parts;
}

function checkSaid(c) {
  return `${c.steps.join("; ")}${c.expect ? `. Expected: ${c.expect}` : ""}`;
}

// A screen as the owner reads it: what it must show, then where and after which clicks.
function screenSaid(s) {
  const steps = s.steps.map((x) => (x.do === "type" ? `type "${x.text}" into ${x.target}` : `click ${x.target}`));
  return `${s.expect} (at ${s.path}${steps.length ? `, after: ${steps.join(", ")}` : ""})`;
}

function counted(n, one, many) {
  return n ? `${n} ${n === 1 ? one : many}` : "";
}

// What the technical details hold, in a line that stays visible while they are collapsed.
function detailCount(d) {
  return [counted(d.criteria.length, "criterion", "criteria"), counted(d.brief.visual.length, "screen", "screens"),
    counted(d.checks.length, "check for you", "checks for you")].filter(Boolean).join(" \u00b7 ");
}

// The technical details, collapsed (TD-122); an item the owner stated says so (TD-179 rule 1).
function technical(d) {
  const scope = d.brief.scope || [], mark = (key) => (yours(d, key) ? " (you specified)" : ""), inside = [];
  if (d.criteria.length) {
    inside.push(hd(5, "Acceptance criteria", "sm"), list(d.criteria.map((k) => `${k.id}: ${k.text}${mark(k.id)}`)));
  }
  if (d.brief.visual.length) {
    inside.push(hd(5, "Screens the visual check captures", "sm"),
      list(d.brief.visual.map((s) => `${screen(s)}${mark(`screen:${s.name}`)}`)));
  }
  if (d.checks.length) {
    inside.push(hd(5, "Checks you do yourself", "sm"),
      list(d.checks.map((c) => `${c.id}: ${checkSaid(c)}${mark(`check:${c.id}`)}`)));
  }
  if (d.brief.ui) {
    inside.push(text(d.brief.visual.length ? "This Change has a user interface: the visual check captures its screens."
      : "This Change has a user interface: you judge it in your own check."));
  }
  if (scope.length) inside.push(text(`Scope: ${scope.join(", ")}`));
  if (!inside.length) return nothing;
  const said = detailCount(d), summary = "Technical details";
  const toggled = (e) => (e.target.open ? state.opened.add(summary) : state.opened.delete(summary));
  return html`<details .open=${state.opened.has(summary)} @toggle=${toggled}><summary>${summary}${said
    ? html`<span class="count">${said}</span>` : nothing}</summary>${inside}</details>`;
}

export function approval(d) {
  const version = d.brief.version, key = `${d.key}:approve:${version}`;
  const start = async () => {
    if (await ask(approving(d))) {
      send("/approve-brief", { version, unreviewed: Boolean(d.brief.unreviewed) }, d, key);
    }
  };
  const why = d.brief.unapprovable;  // TD-249: off until its challenge loop ended on this version
  return panel(`Brief v${version}${d.brief.title ? `: ${d.brief.title}` : ""}`, key,
    html`<div class="brief">${d.brief.outcome ? text(d.brief.outcome, { size: "md" }) : nothing}${agreement(d)}
      ${technical(d)}</div>`,
    d.rounds?.brief?.length ? html`${marks("Brief challenge", d.rounds.brief)}${findingDetails(
      "Finding details of the brief challenge", [["Brief challenge", d.rounds.brief, WORKERS.brief]])}` : nothing,
    text("Nothing is built until you approve. You approve the whole brief, including the collapsed technical "
      + "details; your own choices stay yours to change. Approval authorises work within this brief, not new "
      + "product commitments. To change the brief before approving, return to the shaping chat."),
    why ? text(`Not yet: ${why}.`, { weight: "semibold" }) : nothing,
    button(`Approve brief v${version}`, start, { icon: "check", aria: DIALOG, disabled: Boolean(why) }));
}

// What approving starts (TD-151): the brief, details included, becomes the baseline; then the challenge, planning,
// building and review, the visual round and the merge; the owner's own parts come afterwards.
function approving(d) {
  const v = d.brief.version, screens = d.brief.visual.length, checks = d.checks.length, you = [];
  const said = detailCount(d), then = ["Delivery plans the work, builds and reviews each task, and opens a pull "
    + "request."];
  if (screens) then.push(`It captures ${screens} screen${screens > 1 ? "s" : ""} for the visual check.`);
  then.push(`${merging(d)}. It takes on no new product commitment without you. AI credits are used `
    + `${d.paused ? "once you resume" : "from now on"}.`);
  if (screens) you.push("Judge the screens when Delivery asks.");
  if (checks) you.push(checks > 1 ? `Do your ${checks} checks once the pull request's checks pass.`
    : "Do your check once the pull request's checks pass.");
  return {
    title: `Approve brief v${v} and start the work?`, yes: d.paused ? "Approve; stay paused" : "Approve and start",
    no: "Keep it waiting",
    now: `Brief v${v}${said ? `, including its technical details (${said})` : ""}, becomes the approved version `
      + `every step follows${d.paused ? "; the Change stays paused until you resume" : ""}.`,
    then: then.join(" "),
    after: ["Answer questions here as they come up.", ...you, "Pause at any time; a pause takes effect after the "
      + "running step. Spent credits and finished work are not undone. To change the brief, revise it in the shaping "
      + "chat and approve the new version."].join(" "),
    instead: "Nothing is built. The brief waits here; revise it in the shaping chat or come back later.",
    ...(d.brief.unreviewed ? {  // TD-255: the revision after the challenge's last round, which no challenger judged
      tick: `I accept brief v${v} as revised after its last challenge round; no challenger reviewed that revision.`,
    } : {}),
  };
}

// The same agreement after approval (Sol, TD-179 rule 8): what was approved, and what changed since.
export function briefInfo(d) {
  const at = d.brief.approved_at ? new Date(d.brief.approved_at).toLocaleString() : "";
  const v = d.brief.approved || d.brief.version;
  const added = (d.owner_criteria || []).map((k) => [`You added in visual round ${k.round}`, k.text]);
  return info(`Brief v${v}${at ? `, approved ${at}` : ""}`, html`<div class="brief">
    ${d.brief.outcome ? text(d.brief.outcome) : nothing}${agreement(d, true)}${technical(d)}
    ${part("Changes since you approved", added.length ? saidList(added)
      : text("None. A change to an approved brief comes back to you as a new version to approve."))}
    ${(d.amendments || []).length ? proposedWording(d.amendments) : nothing}</div>`);
}

// TD-179: new wording a worker proposed for a generated criterion, with the challenger's verdict. Nothing is
// applied: adopting one means revising the brief in chat, which comes back as a version to approve.
function proposedWording(amendments) {
  const judged = { equivalent: "keeps the approved intent", weaker: "weaker", unsure: "unsure" };
  const rows = amendments.flatMap((a) => a.items.flatMap((i) => [
    [`${i.criterion} as you approved it`, i.old],
    [`Proposed by the ${a.step} step`, `${i.new} (${i.why})`],
    ["Challenger", [judged[a.verdict] || "not judged yet", a.judged].filter(Boolean).join(": ")],
  ]));
  return part("Proposed wording (not applied)", saidList(rows),
    text("To adopt one, revise the brief in chat; the new version comes back to you to approve."));
}
