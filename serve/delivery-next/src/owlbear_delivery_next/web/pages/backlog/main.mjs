import { defined } from "/assets/ui.mjs";
import { state } from "./state.mjs";
import { refresh } from "./view.mjs";

await defined(["p-select", "p-button", "p-checkbox", "p-input-text", "p-textarea"]);
document.addEventListener("visibilitychange", () => { if (!document.hidden && !state.creating) refresh(); });
refresh();
