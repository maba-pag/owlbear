import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { api, token } from "/assets/ui.mjs";
import { DIALOG, REVERT, show, parts, draft, notify, send } from "./state.mjs";
import { disclosure, button, field, tick, hd, text, list, row, panel } from "./widgets.mjs";
import { merging, finale, mergeSetting } from "./forms.mjs";

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

// The owner's decision on one visual round (TD-79): the screenshots, both verdicts, the problems he sends back,
// a comment, Pass or Fail.
export function decisionForm(q, r, pictures, d) {
  const all = problems(r), key = `${d.key}:visual:${r.number}:${r.head}`;
  const proposed = r.proposed || [];
  const mine = draft(key, () => ({ picked: all.filter((p) => p.items.some((f) => proposed.includes(f.id)))
    .map((p) => p.key) }));
  const made = all.filter((p) => p.first.introduced !== false), old = all.filter((p) => p.first.introduced === false);
  const preferred = comparison(r), evidence = detectorLines(r);
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
  return panel(`Decide visual round ${r.number} of ${r.head.slice(0, 7)}`, key, pictures,
    hd(4, "Verdicts", "sm"), r.verdicts.map(verdictLine),
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
    row(button("Pass", () => decide("pass"), { icon: "check", aria: DIALOG }),
      button("Fail", () => decide("fail"), { variant: "secondary", icon: "close", aria: DIALOG })));
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

// One screenshot in a gallery: a button that enlarges it, in the order before then after at each width.
function zoomable(entry, gallery) {
  const index = gallery.push(entry) - 1, side = entry.side === "before" ? "before the Change" : "with the Change";
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
      html`<p class="caption" aria-live="polite"><strong>${e.side === "before" ? "Before" : "After"}</strong> at
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

// The screenshots of a visual check and what was found: its lines, and the gallery with its count.
export function visualSection(slug, v, b, existing, deciding) {
  const open = deciding || v.doubts.length;
  const [said, variant] = v.passed ? ["Passed", "success"] : open ? ["Undecided", "warning"] : ["Failed", "error"];
  const gallery = [], pairs = v.files.map((name) => {
    const [, at, width] = name.match(/^(.*)-(\d+)\.png$/);
    const kept = b && b.files.includes(name);
    const comparable = kept && b.states[at] === v.states[at];  // a revised state's old shot is no baseline
    const one = (kind, s, when, head) => zoomable(
      { slug, kind, name, at: when, side: s, state: at, width, commit: head.slice(0, 7) }, gallery);
    const before = comparable ? one("before", "before", b.at, b.head)
      : html`<span class="missing">${kept ? "Not comparable: the state changed since" : "Not available"}</span>`;
    return html`<figure class="pair"><figcaption>${at} \u00b7 ${width} px</figcaption>${side("Before", before)}
      ${side("After", one("visual", "after", v.at, v.head))}</figure>`;
  });
  const lines = html`${row(text(`Visual check of ${v.head.slice(0, 7)}`, { weight: "semibold" }),
    html`<p-tag variant=${variant} compact="true">${said}</p-tag>`)}
    ${v.findings.length ? list(v.findings) : nothing}
    ${v.doubts.length ? html`${text("The judges could not decide:", { size: "xs" })}${list(v.doubts)}` : nothing}
    ${existing.length ? text(`Errors already there before the Change: ${existing.join("; ")}`, { size: "xs" })
      : nothing}
    ${b && b.findings.length ? text(`Before: ${b.findings.join("; ")}`, { size: "xs", color: "contrast-medium" })
      : nothing}`;
  return { lines, shots: html`<div class="gallery"><div class="shots">${pairs}</div></div>`, count: gallery.length };
}

export function beforeSection(slug, b) {
  const gallery = [], cells = b.files.map((name) => {
    const [, at, width] = name.match(/^(.*)-(\d+)\.png$/);
    return side(`${at} \u00b7 ${width} px`, zoomable({ slug, kind: "before", name, at: b.at, side: "before",
      state: at, width, commit: (b.head || "").slice(0, 7) }, gallery));
  });
  const seen = b.errors.map((e) => `${e.state} at ${e.width}px, ${e.kind} error: ${e.text}`);
  const lines = html`${text(`Before the Change${b.head ? `, at ${b.head.slice(0, 7)}` : ""}`, { weight: "semibold" })}
    ${b.findings.length ? text(`Not available: ${b.findings.join("; ")}`, { color: "contrast-medium" }) : nothing}
    ${b.errors.length ? text(`Errors before the Change: ${seen.join("; ")}`, { size: "xs" }) : nothing}`;
  return { lines, shots: html`<div class="shots">${cells}</div>`, count: gallery.length };
}
