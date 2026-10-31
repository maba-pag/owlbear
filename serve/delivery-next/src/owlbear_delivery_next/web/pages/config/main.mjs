import { defined, guard } from "/assets/ui.mjs";
import { state, page, show } from "./state.mjs";
import { readMachine } from "./machine.mjs";
import { unsaved, route } from "./sections.mjs";
import { refresh, readAgain, followPolled } from "./reads.mjs";

guard(unsaved);
document.addEventListener("owlbear-machine", async () => {
  if (!state.machine && !state.machineUnread) return;  // not read yet, or this host has no machine
  await readMachine();
  show();
});
addEventListener("hashchange", () => route());
document.addEventListener("owlbear-polled", followPolled);

await defined(["p-select", "p-input-text", "p-checkbox", "p-button", "p-table"]);
route(true);
await refresh().catch(() => undefined);  // what was read last: the read state shows even when a layer does not read
page.target = null;  // an address naming nothing shown by now names nothing here
await readAgain();  // and what is there now
