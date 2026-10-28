import { defined, guard } from "/assets/ui.mjs";
import { state, show } from "./state.mjs";
import { reload, readModels } from "./layers.mjs";
import { readMachine, readAcross } from "./machine.mjs";
import { unsaved } from "./sections.mjs";

guard(unsaved);
document.addEventListener("owlbear-machine", async () => {
  if (!state.machine) return;
  await readMachine();
  show();
});

await defined(["p-select", "p-input-text", "p-checkbox", "p-button", "p-table"]);
show();
await reload();
show();
await readAcross();
show();
await readModels();
