import { defined } from "/assets/ui.mjs";
import { show } from "./state.mjs";
import { refresh } from "./view.mjs";
import { arrive } from "./compaction.mjs";

show();
await defined(["p-select", "p-checkbox", "p-button", "p-button-pure", "p-input-text", "p-table"]);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
await refresh();
arrive();
