import { html } from "/assets/lit-html/3.3.3/lit-html.js";
import { show } from "./state.mjs";

// One switch for every Change page of every project, kept in localStorage: "on" adds the record (the review rounds,
// the picked decisions, read-backs, amendments, the watcher, recent activity, tool calls, the Spotter and Retro) to
// what each Change page always shows. The key predates the switch's move from the menu, so a setting made there
// carries.
const DETAILS = "owlbear-improvement-detail";

export const detailsOn = () => localStorage.getItem(DETAILS) === "on";
addEventListener("storage", () => show());

export function detailsSwitch() {
  const on = detailsOn();
  const set = (e) => {
    if (e.detail?.checked === undefined || e.detail.checked === on) return;
    localStorage.setItem(DETAILS, e.detail.checked ? "on" : "off");
    show();
  };
  return html`<p-switch id="details-switch" compact="true" .checked=${on} @change=${set} @update=${set}>Show
    details</p-switch>`;
}
