import { defined, guard } from "/assets/ui.mjs";
import { state, page, show } from "./state.mjs";
import { reload, readModels } from "./layers.mjs";
import { readMachine, readAcross } from "./machine.mjs";
import { unsaved, route } from "./sections.mjs";

guard(unsaved);
document.addEventListener("owlbear-machine", async () => {
  if (!state.machine && !state.machineUnread) return;  // not read yet, or this host has no machine
  await readMachine();
  show();
});
addEventListener("hashchange", () => route());

await defined(["p-select", "p-input-text", "p-checkbox", "p-button", "p-table"]);
route(true);
await reload();
show();
await readAcross();
show();
page.target = null;  // an address naming nothing shown by now names nothing here
await readModels();
