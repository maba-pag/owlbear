import { defined } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { show, state } from "./state.mjs";

await defined(["p-select", "p-button", "p-input-text", "p-textarea", "p-tag"]);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !state.form && !state.pending) refresh();
});
let undecided = "[]";  // the machine host's start lines about decisions, shown in the error notice once polled
document.addEventListener("owlbear-polled", ({ detail }) => {
  const now = JSON.stringify(detail?.undecided ?? []);
  if (now !== undecided) {
    undecided = now;
    show();
  }
});
refresh();
