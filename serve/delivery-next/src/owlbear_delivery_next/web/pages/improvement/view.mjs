import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { state } from "./state.mjs";
import { casesSection } from "./cases.mjs";
import { looksSection } from "./looks.mjs";
import { proposalsSection } from "./proposals.mjs";
import { retroSection } from "./retro.mjs";
import { spotterSection } from "./spotter.mjs";
import { quiet, unread } from "./widgets.mjs";

// The page: the last action's outcome first, then the proposals waiting for the owner, the Spotter, its looks, Retro
// and the Spotter cases. A part that cannot be read says why; the others still show.

function notice() {
  if (!state.notice) return nothing;
  const { state: kind, text } = state.notice;
  return html`<p-inline-notification id="notice" state=${kind} dismiss-button="false"
    heading=${kind === "error" ? "That was not done" : "Done"} description=${text}></p-inline-notification>`;
}

export function view() {
  const d = state.data;
  if (!d) return html`${notice()}${state.error ? unread("The Improvement page", state.error)
    : quiet("Reading\u2026")}${looksSection()}`;
  return html`${notice()}${state.error ? unread("The newest state", state.error) : nothing}
    ${proposalsSection(d.proposals)}${spotterSection(d.spotter)}${looksSection()}${retroSection(d.retro)}
    ${casesSection(d.cases)}`;
}
