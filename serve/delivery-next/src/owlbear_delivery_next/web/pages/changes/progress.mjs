import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { toggle, disclosure, hd, text, list, meta } from "./widgets.mjs";

function count(n) {
  return n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`;
}

// The total, then a line per model; input includes cache reads and writes, so "in" is the uncached rest.
export function spendLines(spend) {
  const lines = Object.entries(spend.models).map(([model, u]) => {
    const fresh = Math.max(0, u.input - u.cache_read - u.cache_write);
    const split = u.tokens && u.input + u.output === u.tokens  // sessions recorded before the split leave it partial
      ? ` (${count(fresh)} in \u00b7 ${count(u.output)} out \u00b7 ${count(u.cache_read)} cache read \u00b7 `
        + `${count(u.cache_write)} cache write)`
      : "";
    const credits = u.credits_unread ? (u.credits ? `${u.credits.toFixed(2)}+ credits` : "credits unknown")
      : `${u.credits.toFixed(2)} credits`;
    return text(`${model}: ${credits}, ${count(u.tokens)} tokens${split}`, { size: "xs", color: "contrast-medium" });
  });
  return toggle("spend", `Spent ${spentText(spend.credits, (spend.unread || []).length)}`, lines);
}

// Credits a session did not report make the total a lower bound, never a false zero (TD-94).
export function spentText(credits, unknown) {
  if (!unknown) return `${credits.toFixed(2)} credits`;
  const sessions = `unknown for ${unknown} session${unknown === 1 ? "" : "s"}`;
  return credits ? `${credits.toFixed(2)}+ credits (${sessions})` : `credits ${sessions}`;
}

function ago(iso) {
  const seconds = Math.round((Date.now() - Date.parse(iso)) / 1000);
  if (Number.isNaN(seconds)) return "";
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60), hours = Math.round(minutes / 60);
  return minutes < 60 ? `${minutes} min ago` : hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} d ago`;
}

const BOOKKEEPING = new Set(["pids", "inventory", "skill", "tasks", "preserved"]);
const SAID = {
  step: (e) => `${e.kind} step ${e.exit}${e.reason ? `: ${e.reason}` : ""}`,
  tool: (e) => e.summary || `Called ${e.tool}${e.accepted === false ? " (rejected)" : ""}`,
  session: (e) => (e.resumed ? "Session resumed" : `Session started${e.role ? ` (${e.role})` : ""}`),
  denied: (e) => `Denied: ${e.reason || e.kind}`,
  publish: (e) => `Published PR #${e.pr}`,
  labels: (e) => `Labelled PR #${e.pr}: ${e.labels.join(", ")}`,
  "labels-failed": (e) => `Could not label PR #${e.pr} with ${e.labels.join(", ")}: ${e.reason}`,
  ci: (e) => (e.failed?.length ? `CI failed: ${e.failed.join(", ")}`
    : `CI passed${e.passed?.length ? `: ${e.passed.join(", ")}` : ""}`),
  "merge-offer": (e) => `Merge offered for ${String(e.head || "").slice(0, 7)}`,
  "merge-request": (e) => e.message || `Merge requested (${e.status})`,
  merged: (e) => `Merged PR #${e.pr}`,
  pullback: (e) => `Pull-back ${e.state}${e.reason ? `: ${e.reason}` : ""}`,
  "ro-install": (e) => `${e.command} in ${e.package}${e.ok ? "" : " failed"}`,
  "fix-drafted": (e) => `Drafted fix Change ${e.fix}`,
  brief: (e) => `Brief v${e.version} saved`,
};

// Newest first, in words; process and inventory bookkeeping stays in the activity file.
export function activityLog(events) {
  const kept = events.filter((e) => e.event && !BOOKKEEPING.has(e.event)).slice(-12).reverse();
  if (!kept.length) return text("Nothing yet.", { size: "xs", color: "contrast-medium" });
  return html`<ol class="log">${kept.map((e) => html`<li>${e.at ? html`<time datetime=${e.at}
    title=${new Date(e.at).toLocaleString()}>${ago(e.at)}</time>` : html`<span></span>`}
    <span>${(SAID[e.event] ?? ((x) => x.event))(e)}</span></li>`)}</ol>`;
}

export function planList(d) {
  const working = ["build", "review", "integrate"].includes(d.step) && !d.line.startsWith("Done");
  const now = working ? d.plan.find((t) => !t.done) : null;
  return html`<ol class="plan">${d.plan.map((t) => {
    const [label, variant] = t.done ? ["done", "success"] : t === now ? ["now", "info"] : ["to do", "secondary"];
    return html`<li><p-tag variant=${variant} compact="true">${label}</p-tag><span>${t.title}${t.origin
      && t.origin !== "plan" ? html` ${meta(`from ${t.origin}`)}` : nothing}</span>${taskRounds(t.id, d)}</li>`;
  })}</ol>`;
}

// TD-217: a round's marker is its most urgent finding's kind, in words with a count; the loop's latest round is bold.
const KIND = { open: ["error", "exclamation", "open"], unverified: ["warning", "warning", "unverified"],
  settled: ["secondary", "check", "settled"] };

function marker(m) {
  const [variant, icon, word] = KIND[m.kind], said = `R${m.round} \u00b7 ${m.count} ${word}`;
  return html`<p-tag variant=${variant} icon=${icon} compact="true">${m.last ? html`<strong>${said}</strong>`
    : said}</p-tag>`;
}

export function marks(label, rounds) {
  return html`<span class="marks">${meta(label)}${rounds.map(marker)}</span>`;
}

// Per loop and round its summary, then each finding with what became of it and why; a toggle, never hover-only.
// A loop may name its worker and its judge: the planner and the challenger for the plan (TD-190).
export function findingDetails(summary, loops) {
  const said = (f, [worker, judge]) => [`${f.id} (${f.state}): ${f.text}`, f.reason && `${worker}: ${f.reason}`,
    f.judgement && `${judge}: ${f.judgement}`, f.note && `Your note: ${f.note}`].filter(Boolean).join(" \u00b7 ");
  return disclosure(summary, loops.flatMap(([label, rounds, who = WORKERS.task]) => rounds.map((m) => html`
    ${text(`${label}, ${m.said.charAt(0).toLowerCase()}${m.said.slice(1)}`, { size: "xs", weight: "semibold" })}
    ${list(m.findings.map((f) => said(f, who)))}`)));
}
export const WORKERS = { task: ["Builder", "Reviewer"], plan: ["Planner", "Challenger"],
  brief: ["Shaper", "Challenger"] };
const LOOPS = (loop) => ({ final: "final review", plan: "plan challenge", brief: "brief challenge" })[loop]
  ?? `task ${loop}`;

// A plan task's markers, task review and final review apart, with their finding details; nothing without rounds.
// *where* keeps each toggle's summary unique on the page: an open toggle is kept by its summary.
export function taskRounds(id, d, where = "") {
  const r = d.rounds?.tasks[id];
  if (!r || !(r.task.length || r.final.length)) return nothing;
  const shown = [["Task review", r.task], ["Final review", r.final]].filter(([, rounds]) => rounds.length);
  return html`${shown.map(([label, rounds]) => marks(label, rounds))}${findingDetails(
    `Finding details of ${id}${where}`, shown)}`;
}

// The plan challenge's and the final review's own rounds, the work no round reviewed, and the rejections that stand.
export function roundsInfo(r, d) {
  const parts = [];
  if (r.brief?.length && d.brief.approved) {  // before approval the approval view shows them
    parts.push(marks("Brief challenge", r.brief),
      findingDetails("Finding details of the brief challenge", [["Brief challenge", r.brief, WORKERS.brief]]));
  }
  if (r.plan?.length) {
    parts.push(marks("Plan challenge", r.plan),
      findingDetails("Finding details of the plan challenge", [["Plan challenge", r.plan, WORKERS.plan]]));
  }
  if (r.final.length) {
    const attempt = r.attempt > 1 ? ` (attempt ${r.attempt})` : "";
    parts.push(marks(`Final review${attempt}`, r.final),
      findingDetails("Finding details of the final review", [["Final review", r.final]]));
  }
  if (r.unreviewed.length) {
    parts.push(text("Repairs no round reviewed", { size: "sm", weight: "semibold" }),
      list(r.unreviewed.map((u) => `${u.id}: ${u.title} (${LOOPS(u.loop)})`)));
  }
  if (r.standing.length) {
    parts.push(text("Rejections that stand", { size: "sm", weight: "semibold" }), list(r.standing.map((f) => {
      const [worker, judge] = WORKERS[f.loop] ?? WORKERS.task;
      return [`${f.id} (${LOOPS(f.loop)}, ${f.state}): ${f.text}`, f.reason && `${worker}: ${f.reason}`,
        f.judgement && `${judge}: ${f.judgement}`].filter(Boolean).join(" \u00b7 ");
    })));
  }
  if (!parts.length) return nothing;
  return html`<section class="info rounds">${hd(3, "Review rounds", "md")}${parts}</section>`;
}

const STEP = { done: ["done", "success"], current: ["now", "info"], upcoming: ["to do", "secondary"],
  skipped: ["not needed", "secondary"] };

// The stages in order; the state is a word, never colour alone, and a loop badge says its rounds.
export function stepper(p) {
  const at = [p.task ? `Task ${p.task} of ${p.tasks}` : "", p.sub || ""].filter(Boolean).join(" \u00b7 ");
  return html`<ol class="stepper">${p.stages.map((s) => {
    const [label, variant] = STEP[s.state];
    return html`<li class=${s.state} aria-current=${s.state === "current" ? "step" : nothing}><span>
      <span>${s.label}</span><p-tag variant=${variant} compact="true">${label}</p-tag>
      ${s.state === "current" && at ? meta(at) : nothing}
      ${s.rounds > 1 ? html`<span class="loops"><span aria-hidden="true">\u00d7${s.rounds}</span><span
        class="sr">${s.rounds} rounds</span></span>` : nothing}</span></li>`;
  })}</ol>`;
}
