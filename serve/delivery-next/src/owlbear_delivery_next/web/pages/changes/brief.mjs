import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here, machineState } from "/assets/ui.mjs";
import { DIALOG, state, send, starts, draft } from "./state.mjs";
import { button, field, hd, text, list, panel, info, refusal, row, toggle } from "./widgets.mjs";
import { merging } from "./forms.mjs";
import { reviseBrief } from "./shaping.mjs";
import { detailsOn } from "./details.mjs";
import { versionList } from "./versions.mjs";
import { currentPages } from "./visual.mjs";

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

const ORIGINS = { decided: "you decided", approved: "you took the shaper's recommendation" };

// Who made the decision, then whether it stays in force for later Changes once approved (C-14, TD-426).
function said(x) {
  const how = [ORIGINS[x.origin], x.scope === "project" && "lasting: applies to later Changes too"].filter(Boolean);
  return [x.question, how.length ? `${x.answer} (${how.join("; ")})` : x.answer];
}

// The agreement the owner approves (TD-122, TD-179 rule 2): his decisions with their origins and what he specified
// among the technical details, the shaper's own choices that the approval accepts, and what is out; each folded
// under its count, the outcome above them.
function agreement(d, approved = false) {
  const decisions = d.brief.decisions || [], out = d.brief.non_goals || [], parts = [];
  const mine = decisions.filter((x) => x.origin in ORIGINS).map(said);
  const specified = [
    ...d.criteria.filter((k) => yours(d, k.id)).map((k) => ["Acceptance criterion", k.text]),
    ...d.brief.visual.filter((s) => yours(d, `screen:${s.name}`)).map((s) => ["Screen the visual check takes",
      screenSaid(s)]),
    ...d.checks.filter((c) => yours(d, `check:${c.id}`)).map((c) => ["Check you do yourself", checkSaid(c)]),
  ];
  const fold = (name, n, ...inside) => html`<section>${toggle(`${d.key}:${name}`, `${name} (${n})`, inside)}
    </section>`;
  if (mine.length || specified.length) {
    parts.push(fold("Your decisions", mine.length + specified.length, mine.length ? saidList(mine) : nothing,
      specified.length ? [hd(5, "You specified", "xs"), saidList(specified)] : nothing));
  }
  const proposed = decisions.filter((x) => !(x.origin in ORIGINS)).map(said);
  if (proposed.length) {
    const accepts = approved ? "Your approval accepted these choices." : "Approving accepts these choices.";
    parts.push(fold("Shaper's choices", proposed.length, text(accepts), saidList(proposed)));
  }
  if (!decisions.length && !specified.length) parts.push(text("No separate decisions recorded."));
  if (out.length) parts.push(fold("Out of scope", out.length, list(out)));
  return parts;
}

function checkSaid(c) {
  return `${c.steps.join("; ")}${c.expect ? `. Expected: ${c.expect}` : ""}`;
}

const SCOPES = [["global", "Global"], ["project", "This project"], ["change", "This Change"],
  [null, "Not in the current decisions"]];

// One picked decision, linked to its entry on its project's Decisions page; one no longer in force says what it is now.
function pickedItem(project, x) {
  if (!x.scope) return x.title;
  const was = x.state === "in_force" ? "" : ` (${x.state})`;
  return html`<a href=${here({ project, decision: x.id }, "/decisions")}>${x.title}</a>${was}`;
}

// The decisions in force this version's work follows, as Delivery's picker chose them (TD-459). Without the details
// one line counts them; with them they fold under their count, grouped by where each applies, each linked.
function picked(d, on) {
  const p = d.brief.picked, title = "Decisions this work follows", n = p?.decisions.length;
  if (!p || (!on && p.status !== "ok")) return nothing;
  if (!on) return text(`This version follows ${n} decision${n === 1 ? "" : "s"}.`);
  if (p.status === "owed") return part(title, text("Delivery is picking them from the decisions in force."));
  if (p.status === "failed") {
    return part(title, text(`The pick failed: ${p.reason}. Pick the decisions again under Open items.`));
  }
  if (!n) return part(title, text("None of the decisions in force governs it."));
  const items = d.brief.picked_items, why = d.brief.picked_unavailable;
  const groups = items ? SCOPES.map(([scope, name]) => {
    const held = items.filter((x) => x.scope === scope);
    if (!held.length) return nothing;
    return [hd(5, `${name} (${held.length})`, "xs"), list(held.map((x) => pickedItem(d.project, x)))];
  }) : [text(`They can't be grouped or linked: ${why}.`), list(p.decisions)];
  return html`<section>${toggle(`${d.key}:picked`, `${title} (${n})`, groups)}</section>`;
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

const KINDS = { safety: "Safety or irreversible", blocked: "Blocks work", uncertain: "Uncertain",
  improvement: "Improvement" };

// Read-backs waiting that apply to this Change (TD-427): at most three, optional; the rest wait on the Decisions page.
function readBacks(d) {
  const r = d.brief.read_backs;
  if (!r?.items.length) return nothing;
  const rows = r.items.map((i) => [`${KINDS[i.kind] ?? i.kind}: ${i.title}`, `${i.statement} — ${i.why}`]);
  return html`<section class="read-backs">${hd(4, "Decisions waiting to be read back", "sm")}
    ${text("Optional: approving does not wait on them, and each rule stays in force as recorded until you answer.")}
    ${saidList(rows)}<p-text size="sm"><a href=${here({}, "/decisions")}>Answer them on the Decisions page</a>${
      r.more ? ` (${r.more} more wait there)` : ""}</p-text></section>`;
}

// A new shaping chat on the saved brief, offered only while the brief may take a revision.
export function reviseButton(d) {
  if (d.brief.unrevisable !== "") return nothing;
  return button("Revise the brief in a new chat", () => reviseBrief(d),
    { variant: "secondary", icon: "edit", aria: DIALOG, busy: state.creating, ...starts(d) });
}

// Approving the current version, from its line in the version list; off, with the reason above, until it may be.
function approveButton(d) {
  const version = d.brief.version, key = `${d.key}:approve:${version}`;
  const start = async () => {
    if (await ask(d.brief.challenge_waits ? challengeFirst(d) : approving(d))) {
      send("/approve-brief", { version, unreviewed: Boolean(d.brief.unreviewed) }, d, key);
    }
  };
  return button(`Approve v${version}`, start,
    { icon: "check", aria: DIALOG, disabled: Boolean(d.brief.approve_off), ...starts(d) });
}

// When Delivery starts a waiting version's challenge, in the owner's time; a pause of Delivery holds it until Resume.
function startsWhen(d) {
  const at = d.brief.starts_at  // HH:MM in the owner's time, as the status line says it
    ? `at ${new Date(d.brief.starts_at).toLocaleTimeString("en-GB", { timeStyle: "short" })}`
    : "after the wait set in Settings";
  return machineState()?.paused ? `${at}, after you resume` : at;
}

// #986: a version saved after its loop ended waits for the challenge Delivery starts; Approve starts it now.
function waitLine(d) {
  const v = d.brief.version;
  if (d.paused) return `Brief v${v}'s challenge starts by itself after you resume this Change; resume it to approve`;
  return `Brief v${v}'s challenge starts by itself ${startsWhen(d)}; Approve starts it now and approves it if it is `
    + "clean";
}

// Approve on such a version: its challenge first, then the approval today's dialog describes, if nothing was found.
function challengeFirst(d) {
  const v = d.brief.version, base = approving(d);
  return { ...base, title: `Approve brief v${v} once its challenge is clean?`, yes: "Challenge and approve",
    now: `A challenger reads brief v${v} at once, even while paused, using AI credits. Nothing is approved yet.`,
    then: `If it finds nothing: ${base.now} That happens without another step from you, even while paused. `
      + `${base.then} If it finds something, the shaper revises the brief in the shaping chat and v${v} stays `
      + "unapproved.",
    instead: `The challenge starts by itself ${startsWhen(d)}; you approve after it.` };
}

// One more challenge of the current version, whose revision after its last challenge no challenger read (#966).
function challengeButton(d) {
  const version = d.brief.version, key = `${d.key}:approve:${version}`;
  const start = async () => {
    if (await ask({
      title: `Challenge brief v${version} once more?`, yes: "Challenge it", no: "Keep it waiting",
      now: `A challenger reads brief v${version}, including the revision no challenger reviewed. It starts at once, `
        + "even while paused, and uses AI credits.",
      then: `If it finds nothing, you approve v${version} without ticking that revision. If it finds something, the `
        + "shaper revises the brief for it in the shaping chat.",
      after: `The challenge only reads brief v${version}, which stays as it is. Once it runs, a pause doesn't stop it `
        + "and the credits it uses stay spent.",
      instead: `Brief v${version} waits; you can approve it as it is, ticking that no challenger reviewed its `
        + "revision.",
    })) {
      send("/challenge-brief", { version }, d, key);
    }
  };
  return button(`Challenge v${version}`, start, { variant: "secondary", aria: DIALOG, ...starts(d) });
}

function chatReceipt(d) {
  const c = d.brief.chat;
  return c ? html`<div class="shaping-chat-state">${text(c.text, { weight: "semibold" })}
    ${c.detail ? text(c.detail) : nothing}</div>` : nothing;
}

export function approval(d) {
  const version = d.brief.version, key = `${d.key}:approve:${version}`, on = detailsOn();
  // TD-249: off until its loop ended on this version; the wait line says the rest while its challenge waits
  const why = d.brief.challenge_waits && !d.brief.capture?.running ? "" : d.brief.approve_off;
  const act = (v) => [v.actions.includes("approve") ? approveButton(d) : nothing,
    v.actions.includes("challenge") ? challengeButton(d) : nothing];
  return panel(`Brief v${version}${d.brief.title ? `: ${d.brief.title}` : ""}`, key,
    html`<div class="brief">${d.brief.outcome ? text(d.brief.outcome, { size: "md" }) : nothing}${agreement(d)}
      ${picked(d, on)}${technical(d)}${currentPages(d.key, d.brief.capture, d.brief.visual)}${on ? readBacks(d)
        : nothing}</div>`,
    text("Nothing is built until you approve. You approve the whole brief, including the collapsed technical "
      + "details; your own choices stay yours to change. Approval authorises work within this brief, not new "
      + `product commitments. To change the brief before approving, ${d.brief.unrevisable === ""
        ? "revise it in a new chat or in the shaping chat" : "return to the shaping chat"}.`),
    d.brief.challenge_waits ? text(`${waitLine(d)}.`, { weight: "semibold" }) : nothing,
    why ? text(`Not yet: ${why}.`, { weight: "semibold" }) : nothing,
    d.brief.approve_refused ? refusal(d.brief.approve_refused) : nothing,
    chatReceipt(d),
    versionList(d.brief.versions, "Versions", act),
    d.brief.revising.length ? nothing : row(reviseButton(d)));  // while the shaper revises, Open items offers it
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
  const on = detailsOn();
  return info(`Brief v${v}${at ? `, approved ${at}` : ""}`, html`<div class="brief">
    ${d.brief.outcome ? text(d.brief.outcome) : nothing}${chatReceipt(d)}
    ${agreement(d, true)}${picked(d, on)}${technical(d)}
    ${on ? part("Changes since you approved", added.length ? saidList(added)
      : text("None besides the amendments below.")) : nothing}
    ${on ? amendmentsPart(d) : nothing}${versionList(d.brief.versions, "Versions")}</div>
    ${d.brief.unrevisable === "" ? row(reviseButton(d)) : nothing}`);
}

// TD-185: the reference and current versions, and every amendment: old -> new, reason, level, challenger and verdict,
// how it ended; an applied one takes his objection while he may object, else says why not.
const SOURCES = { worker: "a worker", answer: "your answer", allow: "your Allow it", revert: "your revert" };
const LEVELS = { autonomous: "applied by Delivery alone", approved: "approved by you", decided: "decided by you" };
const STATES = {
  recorded: "recorded before amendments existed; never applied", proposed: "in progress", applied: "applied",
  declined: "declined", refused: "refused: an outcome or non-goal change needs reshaping",
  moved: "moved: this Change merged first",
};

const OBJECTIONS = { revert: "reverted", keep: "kept", reshape: "reshaped" };

function amendmentsPart(d) {
  const m = d.amendments;
  if (!m) return nothing;
  const earlier = m.versions.filter((v) => v !== m.version).map((v) => `v${v}`);
  return part("Amendments", text(`Current version v${m.version}; reference version v${m.reference}, from which `
    + `the challenger judges how far the amendments since have weakened it${earlier.length
      ? `. Earlier versions, kept unchanged: ${earlier.join(", ")}` : ""}.`),
  m.list.length ? m.list.map((a) => amendment(a, d)) : text("None."));
}

function actionText(x) {
  return x.do === "type" ? `type "${x.text}" into "${x.target}"` : `click "${x.target}"`;
}

function itemRow(i) {
  const name = `${i.field}${i.key ? ` ${i.key}` : ""}`;
  if (i.remove) return [name, `removed: ${i.old}`];
  const look = i.visual == null ? "" : i.visual ? "judged by look" : "not judged by look";
  const shape = [i.path && `path ${i.path}`, i.actions && `actions: ${i.actions.map(actionText).join("; ") || "none"}`,
    i.steps?.length && `steps: ${i.steps.join("; ")}`, i.covers?.length && `covers ${i.covers.join(", ")}`, look,
    i.question && `question: ${i.question}`]
    .filter(Boolean).map((p) => ` (${p})`).join("");
  return [name, i.old ? `${i.old} → ${i.new}${shape}` : `added: ${i.new}${shape}`];
}

function amendment(a, d) {
  const verdict = a.verdict || (a.state === "recorded" ? "not judged" : "unsure");
  const judged = `${verdict}${a.unreviewed && a.verdict ? " (on an earlier wording)" : ""}`;
  const rows = [...a.items.map(itemRow), ["Reason", `${a.reason || "none given"} (from ${SOURCES[a.source]})`],
    ["Challenger", `${a.challenger ? `session ${a.challenger}: ` : ""}${judged}${a.judged ? `: ${a.judged}` : ""}`],
    ["State", `${STATES[a.state]}${a.version ? `, made v${a.version}` : ""}${a.level ? `, ${LEVELS[a.level]}` : ""}`]];
  if (a.unreviewed) rows.push(["Note", "its final wording was revised after the last challenge round"]);
  if (a.declined) rows.push(["Your reason", a.declined]);
  if (a.refused) rows.push(["Why refused", a.refused]);
  if (a.moved_to) rows.push(["Moved to", `Change ${a.moved_to}`]);
  if (a.objection) rows.push(["Your objection", OBJECTIONS[a.objection]]);
  return html`<div class="amendment">${hd(5, `${a.id}, proposed at the ${a.step} step`, "xs")}${saidList(rows)}
    ${a.state === "applied" ? objecting(a, d) : nothing}</div>`;
}

function objecting(a, d) {
  const key = `${d.key}:object:${a.id}`, why = a.object;
  if (why) return text(`Object: not now, ${why}.`, { size: "xs" });
  const go = async () => {
    if (!(await ask({
      title: `Object to amendment ${a.id}?`, yes: "Object", no: "Keep it as it is",
      now: "Work that depends on it pauses once the running step ends.",
      then: "Delivery shows you what was built and judged on it, and asks you to revert it as a new brief version, "
        + "keep it, or reshape the brief.",
      after: "Earlier brief versions stay unchanged; merged or published work can't be undone.",
      instead: "The amendment stays applied and the work goes on.",
    }))) return;
    send(`/amendments/${encodeURIComponent(a.id)}/objection`, { text: draft(key, () => ({})).text ?? "" }, d, key);
  };
  return html`${field(key, "text", "Why you object (optional)", "1")}
    ${row(button("Object", go, { variant: "secondary", aria: DIALOG, ...starts(d) }))}`;
}
