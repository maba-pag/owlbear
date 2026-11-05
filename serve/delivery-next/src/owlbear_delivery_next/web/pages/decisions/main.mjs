import { defined } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { show, state } from "./state.mjs";

await defined(["p-select", "p-button", "p-input-text", "p-textarea", "p-tag"]);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !state.form && !state.pending) refresh();
});
document.addEventListener("owlbear-polled", show);  // the machine host's start lines about decisions, once polled
refresh();
