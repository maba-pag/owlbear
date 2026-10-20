import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call } from "/assets/ui.mjs";
import { WRITE, RESULTS, TAGS, ENDINGS, FOUND, state, show, notify } from "./state.mjs";
import { button } from "./cells.mjs";

let polling = null;

function when(iso) {
  return iso ? new Date(iso).toLocaleString() : "";
}

function packLine(u) {
  if (state.packProblem) return state.packProblem;
  if (!u) return "";
  const at = u.stages.findIndex((s) => s.name === u.stage);
  let line = ENDINGS[u.state] ?? u.state;
  if (u.state === "running") {
    line = at < 0 ? "Starting the update…" : `Running stage ${at + 1} of ${u.stages.length}: ${u.stages[at].label}…`;
  } else if (u.started_at) {
    line += ` Started ${when(u.started_at)}` + (u.ended_at ? `, ended ${when(u.ended_at)}.` : ".");
  }
  return line;
}

function updated(u) {
  state.update = u;
  state.packProblem = "";
  show();
  if (u.state === "running") poll();
}

function findings(found) {
  return found.map((f) => {
    const why = [f.reason && `Updater: ${f.reason}`, f.judgement && `Challenger: ${f.judgement}`,
      f.note && `Your note: ${f.note}`, f.clarified && `Reconsidered: ${f.clarified}`].filter(Boolean).join(" ");
    return html`<li>${f.id} (round ${f.raised}), ${FOUND[f.state] ?? f.state}: ${f.text}${why ? ` ${why}` : ""}</li>`;
  });
}

// A waiting run's question: one per finding the challenger upheld against the updater (TD-193), the end without a
// pass (TD-256), or a change the owner decides (TD-177, TD-194), with its diff. A note being typed lives in state, so
// it survives every reload of the update's state.
function packQuestion(q) {
  let field = nothing;
  if (q.kind === "dispute") {
    const label = "Your note (guides the updater; needed to ask the challenger again)";
    const note = state.packNotes.get(q.id) ?? "", keep = (e) => state.packNotes.set(q.id, e.target.value ?? "");
    field = html`<p-textarea label=${label} rows="2" max-length="2000" .value=${live(note)} @input=${keep}
      @change=${keep}></p-textarea>`;
  }
  return html`<div class="pack-question"><p-text>${q.text}</p-text>
    ${q.diff ? html`<pre class="pack-diff" aria-label="The change">${q.diff}</pre>` : nothing}
    ${field}
    <div class="row">${q.options.map((o) => button(o.label, () => answerUpdate(q, o, state.packNotes.get(q.id) ?? ""),
      { variant: "secondary" }))}</div></div>`;
}

async function answerUpdate(q, o, note) {
  const left = ["rejected", "standing", "owner-drop"], loop = state.update?.loop;
  const standing = (loop?.findings ?? []).filter((f) => left.includes(f.state));
  const items = [...(loop?.unreviewed ?? []).map((r) => `Repair ${r}: no challenger reviewed it.`),
    ...standing.map((f) => `${f.id} not changed for (${FOUND[f.state]}): ${f.text}`)];
  if (o.id === "activate" && !(await ask({
    title: "Activate the pack without a passing challenge?", yes: "Activate", no: "Keep it waiting",
    now: "Delivery activates the candidate as it is now: it commits design_pack.json, skills/NOTICE.md and the "
      + "files the updater changed, opens a pull request to main and merges it once CI passes. It activates "
      + (items.length ? "with these left as they are:" : "with no repair left unreviewed and no finding left open."),
    items,
    then: "The commit message records that the rounds ended without a pass and which findings were not changed for.",
    after: "Later visual rounds use the new pack; run another update when upstream moves on.",
    instead: "The update keeps waiting; you can still discard it.",
  }))) return;
  try {
    const answered = await call("/design-pack/update/answer",
      { body: { question: q.id, option: o.id, note }, timeout: WRITE });
    state.packNotes.delete(q.id);
    updated(answered);
  } catch (e) {
    notify(e.message);
    await readPack();
  }
}

async function discardUpdate() {
  try {
    updated(await call("/design-pack/update/discard", { method: "POST", timeout: WRITE }));
  } catch (e) {
    notify(e.message);
    await readPack();
  }
}

export async function readPack() {
  try {
    state.pack = await call("/design-pack");
    updated(state.pack.update);
  } catch (e) {
    state.packProblem = `Could not read the design pack: ${e.message}`;
    show();
  }
}

function poll() {
  clearTimeout(polling);
  polling = setTimeout(async () => {
    try {
      updated(await call("/design-pack/update"));
    } catch (e) {
      state.packProblem = `Could not read the update: ${e.message}`;
      show();
      poll();
    }
  }, 2000);
}

async function startUpdate() {
  const sure = await ask({
    title: "Update the design pack?", yes: "Update", no: "Keep the current pack",
    now: "Delivery takes the newest upstream pack, detector pins and design skills together; an updater session "
      + "brings the skills, golden pages and detector glue in line, then the golden pages, calibration replay and a "
      + "challenger check it. The challenger's findings go back to the updater. This uses AI credits.",
    then: "Only if every stage passes, it activates the pack: it commits design_pack.json, skills/NOTICE.md and "
      + "the files the updater changed, opens a pull request to main and merges it once CI passes. It asks you here "
      + "before changed golden evidence counts and before a glue change goes into the pull request, and when the "
      + "rounds end without a pass or the challenger upholds a finding the updater rejected.",
    after: "Later visual rounds use the new pack. If a stage fails, nothing changes and the stages below say why.",
    instead: "The current pack stays active.",
  });
  if (!sure) return;
  try {
    updated(await call("/design-pack/update", { method: "POST", timeout: 10000 }));
  } catch (e) {
    notify(e.message);
    await readPack();
  }
}

export function packSection() {
  const u = state.update, pack = state.pack;
  const plain = (t) => String(t).replaceAll(String.fromCharCode(96), "");  // the status is CLI text with code marks
  const active = pack ? `Active: ${pack.pack} from upstream ${pack.upstream}, identity ${pack.identity}. `
    + `${plain(pack.status)}.` : "";
  const questions = u?.state === "waiting" ? u.questions : [], found = u?.loop?.findings ?? [];
  const p = u?.published, busy = u?.state === "running" || u?.state === "waiting";
  const elsewhere = !busy && Boolean(pack?.machine);  // TD-290: one update runs at a time on this machine
  return html`<section id="pack" class="panel" aria-labelledby="pack-title">
    <p-heading size="lg"><h2 id="pack-title">Design pack</h2></p-heading>
    <p-text id="pack-active">${active}</p-text>
    <p-text id="pack-notice" size="xs" color="contrast-medium">${pack ? `Last notice: ${pack.notice}.` : ""}</p-text>
    <p-text>An update takes the newest upstream pack and validates it with model requests. Only if every stage
      passes, or if you accept it after its challenge rounds end without a pass, it commits it on its own branch,
      opens a pull request to main and merges it once CI passes.</p-text>
    ${elsewhere ? html`<p-text id="pack-machine" size="sm" role="status">A design pack update runs on this machine
      for ${pack.machine}; one runs at a time, so this one can start once it has ended.</p-text>` : nothing}
    <div class="row">
      ${button("Update design pack", startUpdate, { id: "pack-update", icon: "refresh", disabled: busy || elsewhere })}
      <p-text id="pack-state" size="sm" role="status" aria-live="polite">${packLine(u)}</p-text>
    </div>
    <ol id="pack-stages" aria-label="Update stages">${(u?.stages ?? []).map((s) => html`<li>
      <p-text size="sm">${s.label}: </p-text><p-tag variant=${TAGS[s.result]} compact="true">${RESULTS[s.result]
        ?? s.result}</p-tag>${s.detail ? html`<p-text size="xs" color="contrast-medium"> ${s.detail}</p-text>`
        : nothing}</li>`)}</ol>
    <p-text id="pack-reason" size="sm">${u && u.state !== "running" ? u.reason : ""}</p-text>
    <p-text id="pack-pushed" size="sm">${p?.commit ? html`Commit ${p.commit.slice(0, 12)} on ${p.branch}${p.url
      ? html`, <a href=${p.url} target="_blank" rel="noopener">pull request #${p.number}</a>` : nothing}${p.merged
      ? `, merged as ${p.merged.slice(0, 12)}` : p.url ? ", not merged yet" : ""}.` : ""}</p-text>
    <div id="pack-ask" ?hidden=${!questions.length}>
      <p-heading size="md"><h3 id="pack-ask-title">The update waits for you</h3></p-heading>
      <div id="pack-questions">${questions.map(packQuestion)}</div>
      ${button("Discard the update", discardUpdate, { id: "pack-discard", variant: "secondary", icon: "close" })}
    </div>
    <details id="pack-findings-box" ?hidden=${!found.length}>
      <summary>Findings of the challenge rounds</summary>
      <ul id="pack-findings">${findings(found)}</ul>
    </details>
    <details>
      <summary>Log of the last run</summary>
      <pre id="pack-log">${u?.log.length ? u.log.join("\n") : "No run yet."}</pre>
    </details>
  </section>`;
}
