import { call, defined, guard } from "/assets/ui.mjs";
import { state, show } from "./state.mjs";
import { reload, readModels } from "./layers.mjs";
import { readPack } from "./pack.mjs";
import { readMachine, readAcross } from "./machine.mjs";
import { unsaved } from "./sections.mjs";

// TD-290: an update another project runs on this machine shows here once it starts and goes once it ends.
setInterval(async () => {
  if (!state.pack || document.hidden) return;
  const machine = await call("/design-pack/machine").then((r) => r.machine, () => state.pack.machine);
  if (machine !== state.pack.machine) {
    state.pack = { ...state.pack, machine };
    show();
  }
}, 5000);

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
await readPack();
await readModels();
