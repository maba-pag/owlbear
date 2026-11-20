// Global settings changed elsewhere (#810): the machine's poll counts them; Settings lists them, Dismiss here clears
// every one counted, on every page.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { begin } from "/assets/page/sending/feedback.mjs";
import { call, here, machineState, reread } from "/assets/ui.mjs";
import { show } from "./state.mjs";
import { button } from "./widgets.mjs";

const BATCH = 200;  // the dismiss route's most ids at once
const own = { error: "", ids: null };  // ids: those a Dismiss sends, shown until its checkmark is over

// One action, however many batches: its button shows the send (sending/feedback.mjs), the banner kept until then.
async function dismiss(ids) {
  const sending = begin("", { hold: false });
  if (!sending) return;
  own.error = "";
  own.ids = ids;
  show();
  try {
    for (let i = 0; i < ids.length; i += BATCH) {
      await call("/settings-read/dismiss", { method: "POST", machine: true, body: { ids: ids.slice(i, i + BATCH) } });
    }
    await sending.done();
    own.ids = null;
    await reread();
  } catch (e) {
    if (own.ids) sending.failed(e);
    own.error = `Not dismissed: ${e.message}`;
  } finally {
    own.ids = null;
    show();
  }
}

export function elsewhereBanner() {
  const ids = own.ids ?? machineState()?.reads?.notices ?? [];
  if (!ids.length) return own.error ? html`<p role="alert">${own.error}</p>` : nothing;
  return html`<p-inline-notification id="elsewhere" state="info" dismiss-button="false">
    ${ids.length} Global setting${ids.length === 1 ? "" : "s"} changed elsewhere.
    <a href=${here({}, "/config#reads-changed")}>Show in Settings</a>
    ${own.error ? html`<br><span role="alert">${own.error}</span>` : nothing}
    <div class="note-action">${button("Dismiss", () => dismiss(ids), { variant: "secondary", icon: "close",
      id: "dismiss-elsewhere" })}</div></p-inline-notification>`;
}
