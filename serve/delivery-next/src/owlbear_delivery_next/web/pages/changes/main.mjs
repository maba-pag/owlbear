import { defined } from "/assets/ui.mjs";
import { state, page, show } from "./state.mjs";
import { wanted, choose, refresh } from "./list.mjs";

state.selected = wanted(new URLSearchParams(location.search).get("change"));
page.arrived = Boolean(state.selected);
await defined(["p-button", "p-select", "p-checkbox", "p-textarea", "p-radio-group"]);
show();
addEventListener("popstate", () => choose(new URLSearchParams(location.search).get("change"), false));
refresh();
setInterval(refresh, 3000);
