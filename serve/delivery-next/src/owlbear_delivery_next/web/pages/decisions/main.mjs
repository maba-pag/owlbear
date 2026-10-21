import { defined } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { state } from "./state.mjs";

await defined(["p-select", "p-button", "p-input-text", "p-textarea", "p-tag"]);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !state.form && !state.pending) refresh();
});
refresh();
