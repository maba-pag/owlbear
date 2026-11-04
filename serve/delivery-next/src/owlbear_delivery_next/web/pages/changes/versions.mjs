import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { hd, text } from "./widgets.mjs";

// The five colours a version takes, each always said in words beside it; "not recorded" has no colour, only a ring.
const LEGEND = [["running", "challenge running"], ["waits", "waits for you"], ["findings", "findings"],
  ["clean", "clean"], ["unreviewed", "not challenged"]];

const dot = (state) => html`<span class=${`dot ${state}`} aria-hidden="true"></span>`;

// A brief's or plan's versions, oldest first: each version's state, the challenges that read it, and, from *act*,
// the buttons of the current one; then the rounds counted before versions were recorded, and the legend.
export function versionList(listed, title, act = () => nothing) {
  if (!listed?.versions.length) return nothing;
  const items = listed.versions.map((v) => {
    const said = [v.word, v.approved && "approved", v.current && "current"].filter(Boolean).join(", ");
    return html`<li><span class="version">${dot(v.state)}<span><strong>v${v.n}</strong> ${said}</span>${act(v)}</span>
      ${v.challenges.length ? html`<ul>${v.challenges.map((x) => html`<li>${x.label}</li>`)}</ul>` : nothing}</li>`;
  });
  return html`<section class="versions">${hd(4, title, "sm")}<ul class="version-list">${items}</ul>
    ${listed.legacy ? text(`${listed.legacy}.`, { size: "xs", color: "contrast-medium" }) : nothing}
    <ul class="legend" aria-label="Colours">${LEGEND.map(([state, word]) => html`<li>${dot(state)}${word}</li>`)}</ul>
  </section>`;
}
