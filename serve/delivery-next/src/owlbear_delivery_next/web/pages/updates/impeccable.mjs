// Updates ▸ Impeccable, the same in every project and under All projects: the frame,
// where the pack stands (installed here, released with an OwlBear version, published by an update, the candidate an
// update validates), and the one Impeccable update of this machine, answerable from wherever the page is opened.
import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { defined, machineState } from "/assets/ui.mjs";
import { readChecks, update } from "./checks.mjs";
import { frame, framed, sentence, when } from "./frame.mjs";
import { button, follow, own, readPack, replay } from "./pack.mjs";
import { historyUnread, oldWaiting, runPart, startPart } from "./run.mjs";

function installed(i) {  // a missing pack is the running version's; one installing or failed names its version
  const whose = i.version ? `Impeccable of OwlBear ${i.version}` : "An Impeccable pack";
  return i.state === "missing" ? "This version's pack is not installed"
    : `${whose} ${i.state === "installing" ? "is being installed" : "failed to install"}`;
}

function released(bar) {
  const r = bar?.pack?.release;
  if (!bar) return "";
  if (r?.state === "newer") {
    return `OwlBear ${r.version} carries the newer pack ${r.pack}; this version pins ${r.running_pack}.`;
  }
  if (["none", "same"].includes(r?.state)) return "No released OwlBear version carries a newer pack.";
  return `Not known yet${r?.detail ? `: ${r.detail}` : ""}.`;  // never looked, unreadable, or another channel's look
}

function published(run) {
  const p = run?.published;
  const last = own.unread.runs && run ? "Last read: " : "";
  if (!p?.commit && historyUnread()) return "Not known: the machine's last update could not be read.";
  if (!p?.commit) return run ? `${last}Nothing yet from the last update.` : "Nothing yet.";
  const pr = p.url ? `pull request #${p.number}` : `commit ${p.commit.slice(0, 12)} on ${p.branch}`;
  return `${last}${sentence(pr)}${p.merged ? `, merged into main as ${p.merged.slice(0, 12)}`
    : p.url ? ", not merged yet" : ""}; a machine takes it with the OwlBear version that carries it.`;
}

function candidate(run) {
  if (!run || !["running", "waiting"].includes(run.state)) return historyUnread()
    ? "Not known: run history could not be read completely." : "None: no update runs now.";
  const made = (run.stages ?? []).find((s) => s.name === "candidate" && s.detail)?.detail;
  const last = own.unread.runs ? "Last read: " : "";
  return `${last}${made ?? "Being prepared"}; it is not active anywhere until it is `
    + "published and released.";
}

function fact(term, said, id) {
  return said ? html`<div><dt>${term}</dt><dd id=${id}>${said}</dd></div>` : nothing;
}

function stands() {
  const pin = own.pinned, bar = machineState(), install = bar?.pack?.install, run = own.runs?.run;
  const plain = (t) => String(t).replaceAll(String.fromCharCode(96), "");  // the status is CLI text with code marks
  return html`<div class="part">
    <p-heading size="md"><h3 id="pack-stands-title">Where the pack stands</h3></p-heading>
    ${own.unread.pinned ? html`<p-inline-notification id="pack-read-error" state="error" dismiss-button="false">
      Could not read Impeccable: ${own.unread.pinned}.</p-inline-notification>` : nothing}
    <dl class="facts" aria-labelledby="pack-stands-title">
      ${pin || install ? html`<div><dt>Installed</dt>
        ${pin ? html`<dd id="pack-active">Pinned: ${pin.pack} from upstream ${pin.upstream}, identity ${
          pin.identity}. ${plain(pin.status)}.</dd>` : nothing}
        ${install ? html`<dd id="pack-install-state">${installed(install)} on this machine${install.detail
          ? `: ${install.detail}` : ""}.</dd>` : nothing}</div>` : nothing}
      ${fact("Install record", bar?.pack?.unkept ? `${sentence(bar.pack.unkept)}.` : "", "pack-unkept")}
      ${fact("Released", released(bar), "pack-release")}
      ${own.runs ? fact("Published", published(run), "pack-published") : nothing}
      ${own.runs ? fact("Candidate", candidate(run), "pack-candidate") : nothing}
    </dl>
    <p-text id="pack-notice" size="xs" color="contrast-medium">${pin ? `Upstream: ${pin.notice.said}${pin.notice
      .checked_at ? `, checked ${when(pin.notice.checked_at)}` : ", not checked yet"}.` : ""}</p-text>
  </div>`;
}

function view() {
  const r = own.runs;
  return html`${frame("impeccable", { running: "Pinned upstream" })}
    ${machineState() ? html`<section id="pack" class="panel" aria-labelledby="pack-title">
      <p-heading size="lg"><h2 id="pack-title">The pack</h2></p-heading>
      ${stands()}
      ${startPart()}
      ${r ? html`<div class="part">${runPart(r.run)}${oldWaiting(r)}</div>` : own.unread.runs ? nothing
        : html`<p-text size="sm">Reading the last Impeccable update…</p-text>`}
      <div class="part row">
        ${button("Replay OwlBear's decided rounds", replay, { id: "pack-replay", busy: own.busy === "replay",
      disabled: !r || historyUnread() || Boolean(r.holder || own.busy || own.awaiting)
        || ["running", "waiting"].includes(r.run?.state) })}
        <p-text role="status">${own.replayed ?? ""}</p-text>
      </div>
    </section>` : nothing}`;
}

function show() {
  render(view(), document.getElementById("page"));
}

// A search that found a newer upstream release also refreshed what the pack part says of upstream.
let looked = update("impeccable")?.checked_at;
function checked() {
  const at = update("impeccable")?.checked_at;
  if (at !== looked) [looked] = [at, readPack()];
  show();
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification", "p-textarea", "p-radio-group"]);
follow(show);
framed(checked);
document.addEventListener("visibilitychange", () => { if (!document.hidden) readPack(); });
show();
readPack();
readChecks();
