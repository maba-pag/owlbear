import { defined } from "/assets/ui.mjs";
import { refresh, show } from "./state.mjs";

show();
await defined(["p-button", "p-heading", "p-inline-notification", "p-link-pure", "p-modal", "p-select", "p-tag",
  "p-text", "p-textarea"]);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
refresh();
