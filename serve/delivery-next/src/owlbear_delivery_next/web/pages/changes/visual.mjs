import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { api, token } from "/assets/ui.mjs";
import { DIALOG, REVERT, show, parts, draft, notify, send, starts } from "./state.mjs";
import { disclosure, button, field, tick, hd, text, list, row, panel } from "./widgets.mjs";
import { merging, finale, mergeSetting, droppedLine, withdrawing } from "./forms.mjs";

const JUDGE = { design: "Design judge", correctness: "Correctness judge" };
const SEVERITY = { P0: ["Blocks the task", "error"], P1: ["Serious", "error"], P2: ["Annoying", "warning"],
  P3: ["Polish", "secondary"] };

function widthsOf(items) {
  return [...new Set(items.map((f) => f.width).filter(Boolean))].sort((a, b) => a - b);
}

function where(at, widths) {
  return widths.length ? `${at} at ${widths.join(", ")} px` : at;
}

// One problem per entry: the same judge, state, rule, severity and origin at other widths; two at one width stay two.
function problems(r) {
  const groups = new Map();
  for (const v of r.verdicts) {
    for (const f of v.findings) {
      const base = JSON.stringify([v.lens, f.state, f.rule, f.severity, f.introduced]);
      let n = 0;
      while (groups.get(`${base}#${n}`)?.items.some((seen) => seen.width === f.width)) n += 1;
      const key = `${base}#${n}`;
      if (!groups.has(key)) groups.set(key, { key, lens: v.lens, first: f, items: [] });
      groups.get(key).items.push(f);
    }
  }
  return [...groups.values()];
}

function problemRow(p, mine) {
  const [label, variant] = SEVERITY[p.first.severity] ?? [];
  const on = mine.picked.includes(p.key);
  const flip = (checked) => {
    mine.picked = checked ? [...new Set([...mine.picked, p.key])] : mine.picked.filter((k) => k !== p.key);
    show();
  };
  const said = [JUDGE[p.lens], where(p.first.state, widthsOf(p.items)), p.first.rule].filter(Boolean)
    .join(" \u00b7 ");
  return html`<div class="finding">${tick(p.first.text, on, flip)}
    ${row(label ? html`<p-tag variant=${variant} compact="true">${label}</p-tag>` : nothing,
      text(said, { size: "xs", color: "contrast-medium" }))}
    ${new Set(p.items.map((f) => f.text)).size > 1 ? disclosure("What the judge wrote at each width",
      list(p.items.map((f) => `${f.width ? `${f.width} px: ` : ""}${f.text}`))) : nothing}</div>`;
}

function verdictLine(v) {
  const said = v.verdict ?? "no verified verdict";
  const first = v.unanchored && v.unanchored !== v.verdict
    ? `, ${v.unanchored} before it saw the detector's findings` : "";
  return html`<div>${text(`${JUDGE[v.lens]}: ${said}${first}`, { weight: "semibold" })}
    ${v.reason ? text(v.reason) : nothing}</div>`;
}

// The design judge's blind preferences, mapped back to before and after.
function comparison(r) {
  const sides = new Map();
  for (const v of r.verdicts) {
    for (const [pair, side] of Object.entries(v.preferences || {})) {
      const cut = pair.lastIndexOf("-"), at = pair.slice(0, cut);
      if (!sides.has(side)) sides.set(side, new Map());
      if (!sides.get(side).has(at)) sides.get(side).set(at, []);
      sides.get(side).get(at).push(Number(pair.slice(cut + 1)));
    }
  }
  const said = [...sides].flatMap(([side, states]) => [...states].map(([at, widths]) =>
    `${side === "equal" ? "no difference" : `${side} better`} for ${where(at, widths.sort((a, b) => a - b))}`));
  return said.length ? `Without knowing which was which, the design judge found ${said.join("; ")}.` : "";
}

function detectorLines(r) {
  const seen = new Map();
  for (const s of r.detector) {
    for (const f of s.findings) {
      const key = `${f.rule} (${f.freshness})|${s.state}`;
      if (!seen.has(key)) seen.set(key, []);
      if (s.width) seen.get(key).push(s.width);
    }
  }
  return [...seen].map(([key, widths]) => {
    const [rule, at] = key.split("|");
    return `${rule} on ${where(at, [...new Set(widths)].sort((a, b) => a - b))}`;
  });
}

// A design rule the brief or one of the owner's criteria rules out: never ticked, never sent to the builder. One with
// a state or a brief criterion is taken by changing the brief; one with an owner's criterion by withdrawing it.
function conflictRow(k, q, r, d, key) {
  const said = r.departs?.[k.id] ?? "", owner = k.departs.startsWith("owner-");
  const take = async () => {
    const ok = await ask({
      title: `Change the brief to take conflict ${k.id}?`, yes: "Change the brief", no: "Keep reviewing",
      now: `The shaper drafts a brief amendment so that ${k.departs} allows what ${k.rule} asks: ${k.text}`,
      then: "A challenger judges the amendment; once it applies, the visual check runs again on the new brief. This "
        + "uses AI credits.",
      after: "The round's other conflicts are not part of it.",
      instead: "The round stays open; Pass keeps the brief as it is.",
    });
    if (ok) {
      const round = { round: r.number, head: r.head, pack: r.pack };
      send("/answers", { question: q.id, option: "amend", text: k.id, ...round, findings: [] }, d, key);
    }
  };
  const action = owner
    ? html`${text("Withdrawing it leaves this round to your Pass or Fail; later rounds no longer check it.",
      { size: "xs" })}${button(`Withdraw ${k.departs}`, withdrawing(k.departs, said, d),
      { variant: "secondary", aria: DIALOG })}`
    : button("Change the brief to take this", take, { variant: "secondary", aria: DIALOG, ...starts(d) });
  return html`<div class="finding">${text(`${where(k.state, k.width ? [k.width] : [])} · ${k.rule}: ${k.text}`)}
    ${text(`Departs from ${k.departs}${said ? `: “${said}”` : ""}`, { size: "xs", color: "contrast-medium" })}
    ${action}</div>`;
}

// The owner's decision on one visual round (TD-79): the screenshots, both verdicts, the problems he sends back,
// a comment, Pass or Fail; a conflict with the brief is his to settle, never the builder's.
export function decisionForm(q, r, pictures, d) {
  const all = problems(r), key = `${d.key}:visual:${r.number}:${r.head}`;
  const proposed = r.proposed || [];
  const mine = draft(key, () => ({ picked: all.filter((p) => p.items.some((f) => proposed.includes(f.id)))
    .map((p) => p.key) }));
  const made = all.filter((p) => p.first.introduced !== false), old = all.filter((p) => p.first.introduced === false);
  const preferred = comparison(r), evidence = detectorLines(r);
  const conflicts = r.verdicts.flatMap((v) => v.conflicts ?? []);
  const decide = async (option) => {
    const comment = (mine.text ?? "").trim(), chosen = made.filter((p) => mine.picked.includes(p.key));
    const findings = chosen.flatMap((p) => p.items.map((f) => f.id));
    if (option === "fail" && !findings.length && !comment) {
      return notify("To fail the round, tick a problem or write a comment.");
    }
    const instructions = chosen.flatMap((p) => (new Set(p.items.map((f) => f.text)).size > 1
      ? p.items.map((f) => `${where(f.state, widthsOf([f]))}: ${f.text}`) : [p.first.text]));
    const checks = d.checks.filter((c) => c.passed !== true).length;  // the open person checks come after the round
    const ok = await ask(option === "fail" ? {
      title: "Send these problems back to the builder?", yes: "Send back", no: "Keep reviewing",
      now: "The builder gets a fix task with:",
      items: [...instructions, ...(comment ? [`Your comment: ${comment}`] : [])],
      then: "After the fix, the reviewer checks it and both judges look again; this uses AI credits. If they do not "
        + "both pass it, Delivery may ask you again.",
      after: comment ? "Your comment stays a criterion every later round checks until you withdraw it." : "",
      instead: "The round stays open; pass it, or tick other problems.",
    } : {
      title: checks || mergeSetting(d) !== "auto" ? `Pass visual round ${r.number}?`
        : `Pass visual round ${r.number}, the last step before merging?`,
      yes: checks || mergeSetting(d) !== "auto" ? "Pass" : "Pass and merge", no: "Keep reviewing",
      now: "No problem of this round goes to the builder." + (comment ? " Your comment is kept as a note only." : ""),
      then: checks ? `Your check${checks > 1 ? "s" : ""} come${checks > 1 ? "" : "s"} next. ${merging(d)}.`
        : mergeSetting(d) === "auto" ? finale(d) : `${merging(d)}.`,
      after: checks || mergeSetting(d) !== "auto"
        ? "Until the merge, comments on the pull request come back to Delivery as work." : REVERT,
      instead: "The round stays open for your decision.",
    });
    if (ok) {
      const round = { round: r.number, head: r.head, pack: r.pack };
      send("/answers", { question: q.id, option, text: comment, ...round, findings }, d, key);
    }
  };
  return panel(`Decide visual round ${r.number} of ${r.head.slice(0, 7)}`, key, droppedLine(q), pictures,
    hd(4, "Verdicts", "sm"), r.verdicts.map(verdictLine),
    conflicts.length ? html`${hd(4, "Conflicts with the brief", "sm")}${text("The design judge found rules that the "
      + "brief or your criteria rule out. They are never sent to the builder: Pass keeps the brief.")}${conflicts
      .map((k) => conflictRow(k, q, r, d, key))}` : nothing,
    made.length ? html`${hd(4, "Problems this Change introduced", "sm")}${text("Blocking, serious and annoying "
      + "problems and any missed criterion of yours are ticked for you; a Fail sends the ticked ones to the "
      + "builder.")}${made.map((p) => problemRow(p, mine))}` : nothing,
    old.length ? disclosure(`Already there before the Change: ${old.length} (never sent to the build)`,
      list(old.map((p) => `${where(p.first.state, widthsOf(p.items))}: ${p.first.text}`))) : nothing,
    preferred ? text(preferred, { size: "xs" }) : nothing,
    evidence.length ? disclosure("What the design detector found (evidence for the judges)", list(evidence))
      : nothing,
    field(key, "text", "Comment: on Fail it becomes a criterion every later round checks until you withdraw it; on "
      + "Pass it is only a note"),
    row(button("Pass", () => decide("pass"), { icon: "check", aria: DIALOG, ...starts(d) }),
      button("Fail", () => decide("fail"), { variant: "secondary", icon: "close", aria: DIALOG, ...starts(d) })));
}

// Screenshots load with the token once each; a loaded one renders from its object URL.
const shots = new Map();

function shot(change, kind, name, at) {
  const key = `${change}/${kind}/${name}/${at}`, [of, slug] = parts(change);
  if (!shots.has(key)) {
    const entry = { url: null, failed: false };
    shots.set(key, entry);
    const init = { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(5000) };
    entry.loading = fetch(api(`/changes/${slug}/${kind}/${encodeURIComponent(name)}`, of), init)
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(r.statusText))))
      .then((b) => { entry.url = URL.createObjectURL(b); }, () => { entry.failed = true; })
      .then(() => show());
  }
  return shots.get(key);
}

// Each side of a screenshot: the enlarged view's caption, and how its text alternative places it.
const SIDES = { before: ["Before", "before the Change"], after: ["After", "with the Change"],
  shaped: ["Current page", "as the target shows it now"], reference: ["Design reference", "as shaped"] };

// One screenshot in a gallery: a button that enlarges it, in the order before then after at each width.
function zoomable(entry, gallery) {
  const index = gallery.push(entry) - 1, side = SIDES[entry.side][1];
  entry.alt = `${entry.state} at ${entry.width}px ${side}, at ${entry.commit}`;
  const s = shot(entry.slug, entry.kind, entry.name, entry.at);
  return html`<button type="button" class="zoom" aria-haspopup="dialog" @click=${() => lightbox(gallery, index)}>
    <img alt=${`Enlarge: ${entry.alt}${s.failed ? " (not available)" : ""}`} loading="lazy"
      src=${s.url ?? nothing}></button>`;
}

// The enlarged screenshots: arrow keys or buttons step through them, Escape or the modal's dismiss button ends. Built
// apart from the page's render, so a poll never touches it.
function lightbox(gallery, start) {
  const modal = document.createElement("p-modal");
  modal.className = "lightbox";
  modal.setAttribute("fullscreen", "true");
  modal.setAttribute("aria", "{ 'aria-label': 'Screenshots' }");
  let at = start, size = "";
  const draw = () => {
    const e = gallery[at], s = shot(e.slug, e.kind, e.name, e.at);
    render(html`${row(
      button("Previous", () => go(-1), { icon: "arrow-left", variant: "secondary", keys: "ArrowLeft",
        title: "Previous screenshot (left arrow)" }),
      html`<p class="caption" aria-live="polite"><strong>${SIDES[e.side][0]}</strong> at
        ${e.commit} \u00b7 ${e.state} \u00b7 ${e.width} px wide \u00b7 ${at + 1} of ${gallery.length}${s.failed
        ? " \u00b7 not available" : ""}${size}</p>`,
      button("Next", () => go(1), { icon: "arrow-right", variant: "secondary", keys: "ArrowRight",
        title: "Next screenshot (right arrow)" }),
    )}<div class="frame"><img alt=${e.alt} src=${s.url ?? nothing} @load=${(ev) => {
      size = ` \u00b7 ${ev.target.naturalWidth} \u00d7 ${ev.target.naturalHeight} px`;
      draw();
    }}></div>`, modal);
    if (!s.url && !s.failed) s.loading.then(() => { if (gallery[at] === e) draw(); });
  };
  const go = (step) => {
    at = (at + step + gallery.length) % gallery.length;
    size = "";
    draw();
  };
  modal.addEventListener("keydown", (k) => {
    if (k.key !== "ArrowLeft" && k.key !== "ArrowRight") return;
    k.preventDefault();
    go(k.key === "ArrowLeft" ? -1 : 1);
  });
  modal.addEventListener("dismiss", () => {
    modal.open = false;
    setTimeout(() => modal.remove(), 1000);
  });
  document.body.append(modal);
  draw();
  modal.open = true;
}

function side(label, child) {
  return html`<div class="side"><span>${label}</span>${child}</div>`;
}

function refusedScan(s) {
  const reason = s.reason || "no reason given";
  return s.kind === "source" ? `changed sources: ${reason}` : `${s.state} at ${s.width}px: ${reason}`;
}

// The scans the design detector could not make, each with its whole reason; they never fail a round.
function refusedLine(items) {
  return items.length ? text(`The design detector could not scan: ${items.join("; ")}`, { size: "xs" }) : nothing;
}

function refused(scans, prefix = "") {
  return (scans ?? []).filter((s) => !s.scanned).map((s) => `${prefix}${refusedScan(s)}`);
}

// The design reference's picture of a state at a width, first in the gallery (D-01M6Q4B6VV4Z05WFQ1BD4X95HJ): the
// target's page as shaping captured it, which the expectations were written against; none where it has no such state.
function referenced(slug, r, name, at, width, gallery) {
  if (!r || !r.files.includes(name)) return null;
  const commit = (r.head || "").slice(0, 7), when = new Date(r.at).toLocaleDateString("en-GB", { dateStyle: "medium" });
  return side(`Design reference (shaping, ${commit}, ${when})`, zoomable({ slug, kind: "reference", name, at: r.at,
    side: "reference", state: at, width, commit }, gallery));
}

// The screenshots of a visual check and what was found: its lines, and the gallery with its count.
export function visualSection(slug, v, b, existing, deciding, r = null) {
  const open = deciding || v.doubts.length;
  const [said, variant] = v.passed ? ["Passed", "success"] : open ? ["Undecided", "warning"] : ["Failed", "error"];
  const gallery = [], pairs = v.files.map((name) => {
    const [, at, width] = name.match(/^(.*)-(\d+)\.png$/);
    const kept = b && b.files.includes(name);
    const comparable = kept && b.states[at] === v.states[at];  // a revised state's old shot is no baseline
    const one = (kind, s, when, head) => zoomable(
      { slug, kind, name, at: when, side: s, state: at, width, commit: head.slice(0, 7) }, gallery);
    const shaped = referenced(slug, r, name, at, width, gallery);
    const before = comparable ? one("before", "before", b.at, b.head)
      : html`<span class="missing">${kept ? "Not comparable: the state changed since" : "Not available"}</span>`;
    return html`<figure class=${shaped ? "pair three" : "pair"}><figcaption>${at} \u00b7 ${width} px</figcaption>${
      shaped ?? nothing}${side("Before", before)}${side("After", one("visual", "after", v.at, v.head))}</figure>`;
  });
  const lines = html`${row(text(`Visual check of ${v.head.slice(0, 7)}`, { weight: "semibold" }),
    html`<p-tag variant=${variant} compact="true">${said}</p-tag>`)}
    ${v.findings.length ? list(v.findings) : nothing}
    ${v.doubts.length ? html`${text("The judges could not decide:", { size: "xs" })}${list(v.doubts)}` : nothing}
    ${existing.length ? text(`Errors already there before the Change: ${existing.join("; ")}`, { size: "xs" })
      : nothing}
    ${b && b.findings.length ? text(`Before: ${b.findings.join("; ")}`, { size: "xs", color: "contrast-medium" })
      : nothing}
    ${refusedLine([...refused(v.design), ...refused(b?.design, "before, ")])}`;
  return { lines, shots: html`<div class="gallery"><div class="shots">${pairs}</div></div>`, count: gallery.length };
}

// A round's refused scans while no judged capture of its commit shows them, as when a judge failed.
export function roundRefused(r, v) {
  if (!r) return nothing;
  const shown = new Set(r.head === v?.head ? refused(v.design) : []);  // a judged capture shows its own scans
  const items = refused(r.detector).filter((line) => !shown.has(line));
  return items.length ? text(`The design detector could not scan round ${r.number} at ${r.head.slice(0, 7)}: ${
    items.join("; ")}`, { size: "xs" }) : nothing;
}

export function beforeSection(slug, b, r = null) {
  const gallery = [], cells = b.files.map((name) => {
    const [, at, width] = name.match(/^(.*)-(\d+)\.png$/);
    const shaped = referenced(slug, r, name, at, width, gallery);
    const before = side(`${at} \u00b7 ${width} px`, zoomable({ slug, kind: "before", name, at: b.at, side: "before",
      state: at, width, commit: (b.head || "").slice(0, 7) }, gallery));
    return shaped ? html`${shaped}${before}` : before;
  });
  const seen = b.errors.map((e) => `${e.state} at ${e.width}px, ${e.kind} error: ${e.text}`);
  const lines = html`${text(`Before the Change${b.head ? `, at ${b.head.slice(0, 7)}` : ""}`, { weight: "semibold" })}
    ${b.findings.length ? text(`Not available: ${b.findings.join("; ")}`, { color: "contrast-medium" }) : nothing}
    ${b.errors.length ? text(`Errors before the Change: ${seen.join("; ")}`, { size: "xs" }) : nothing}
    ${refusedLine(refused(b.design))}`;
  return { lines, shots: html`<div class="shots">${cells}</div>`, count: gallery.length };
}

// The draft's current pages as its shaping capture rendered them at the target (D-01M61V2GR0C6JV2R6KJ0WR4PNB): each
// state's pictures per width, or why it has none. The shaper and the owner write the expectations against them.
export function currentPages(slug, c, states) {
  if (!c) return nothing;
  if (c.running) return text("Capturing the current pages\u2026 Approval waits until they are captured.");
  const gallery = [], commit = (c.head || "").slice(0, 7), mine = (s, f) => f.startsWith(`${s.name} at `)
    || f.startsWith(`${s.name}:`);
  const figures = states.map((s) => {
    const why = c.findings.filter((f) => mine(s, f)), cells = c.widths.map((w) => [w, `${s.name}-${w}.png`])
      .filter(([, name]) => c.files.includes(name)).map(([w, name]) => side(`${w} px`, zoomable({ slug,
        kind: "shaped", name, at: c.at, side: "shaped", state: s.name, width: w, commit }, gallery)));
    return html`<figure class="pair"><figcaption>${s.name}</figcaption>${cells}${why.length || !cells.length
      ? html`<span class="missing">Not captured${why.length ? `: ${why.join("; ")}` : ""}</span>` : nothing}</figure>`;
  });
  const rest = c.findings.filter((f) => !states.some((s) => mine(s, f)));
  const when = new Date(c.at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
  return html`<section>${hd(4, "The current pages", "sm")}${text(commit ? `The target at ${commit}, captured ${when}`
    : `Not captured, ${when}`, { size: "xs", color: "contrast-medium" })}${rest.length
    ? text(`Not captured: ${rest.join("; ")}`) : nothing}<div class="shots">${figures}</div></section>`;
}
