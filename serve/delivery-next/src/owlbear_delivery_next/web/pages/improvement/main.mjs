import { defined } from "/assets/ui.mjs";
import { refresh, show, state } from "./state.mjs";

show();
await defined(["p-button", "p-heading", "p-inline-notification", "p-link-pure", "p-modal", "p-select", "p-tag",
  "p-text", "p-textarea"]);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
// Work that ends in the background shows on the top bar's poll; a slow host gets one such read at a time.
let polled = null;
document.addEventListener("owlbear-polled", () => {
  if (!state.busy && !polled) polled = refresh().finally(() => { polled = null; });
});
refresh();
