// Global settings changed elsewhere (#810): the machine's poll counts them; Settings lists them, Dismiss here clears
// every one counted, on every page.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, here, machineState, reread } from "/assets/ui.mjs";
import { show } from "./state.mjs";

const BATCH = 200;  // the dismiss route's most ids at once
const own = { busy: false, error: "" };

async function dismiss(ids) {
  own.busy = true;
  own.error = "";
  show();
  try {
    for (let i = 0; i < ids.length; i += BATCH) {
      await call("/settings-read/dismiss", { method: "POST", machine: true, body: { ids: ids.slice(i, i + BATCH) } });
    }
    await reread();
  } catch (e) {
    own.error = `Not dismissed: ${e.message}`;
  } finally {
    own.busy = false;
    show();
  }
}

export function elsewhereBanner() {
  const ids = machineState()?.reads?.notices ?? [];
  if (!ids.length) return own.error ? html`<p role="alert">${own.error}</p>` : nothing;
  const n = ids.length;
  return html`<p-inline-notification id="elsewhere" state="info" dismiss-button="false" action-label="Dismiss"
    action-icon="close" .actionLoading=${own.busy} @action=${() => dismiss(ids)}>
    ${n} Global setting${n === 1 ? "" : "s"} changed elsewhere.
    <a href=${here({}, "/config#reads-changed")}>Show in Settings</a>
    ${own.error ? html`<br><span role="alert">${own.error}</span>` : nothing}</p-inline-notification>`;
}
