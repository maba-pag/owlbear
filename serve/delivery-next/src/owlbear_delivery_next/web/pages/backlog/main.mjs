import { defined } from "/assets/ui.mjs";
import { show, state } from "./state.mjs";
import { refresh } from "./view.mjs";

await defined(["p-select", "p-button", "p-button-pure", "p-checkbox", "p-input-text", "p-textarea"]);
document.addEventListener("visibilitychange", () => { if (!document.hidden && !state.creating) refresh(); });
// #808: a project's block set or lifted elsewhere shows at the machine's next poll, with no GitHub read.
document.addEventListener("owlbear-polled", () => { if (state.loaded) show(); });
refresh();
