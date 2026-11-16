import { html, noChange, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { Directive, directive } from "/assets/lit-html/3.3.3/directive.js";
import { Slow } from "/assets/ui.mjs";

// What a click that sends to Delivery shows, for any page: the clicked control loads at once and its form (the
// element whose `data-form` is the form key the send names) locks and dims; on success the control shows a checkmark
// for at least HOLD before the page rereads and returns to normal after BACK; on a refusal or timeout the form unlocks
// with its input kept and the control says so until that form is clicked or edited again.
// A page renders its buttons with `control`, wraps their handlers in `press`, and brackets each request with
// `begin` and the returned send's `done` or `failed`.
const HOLD = 1000, BACK = 2000;
const SAID = { pending: "Sending", sent: "Sent", failed: "Failed", unsure: "Not confirmed" };
const MARK = { failed: "error", unsure: "warning", sent: "check" };
const sends = new Set();  // each: { control, scope, form, id, phase, released, holds }
let clicked = null;  // the control of the latest click: the next send is its own
let redraw = () => {};
let region = null;

// The page's render function, called whenever a send's look changes.
export function changed(show) {
  redraw = show;
}

function of(control) {
  return [...sends].find((s) => s.control === control);
}

const locks = (s) => s.phase === "pending" || s.phase === "sent";

// True while a send waits for its answer or holds its checkmark: the page rereads nothing until then, so its form
// stays in place however fast Delivery answers.
export function holding() {
  return [...sends].some((s) => s.holds && (s.phase === "pending" || (s.phase === "sent" && !s.released)));
}

function lock(s, on) {
  if (s.scope) {
    s.scope.inert = on;
    s.scope.classList.toggle("sending", on);
  }
  if (s.control) {
    s.control.inert = on;
    s.control.toggleAttribute("data-sending", on);
  }
}

function forget(s) {
  sends.delete(s);
  lock(s, false);
}

function announce(phase) {
  if (!region?.isConnected) {
    region = Object.assign(document.createElement("div"), { className: "said-aloud" });
    region.setAttribute("role", "status");
    region.setAttribute("aria-live", "polite");
    document.body.append(region);
  }
  region.textContent = SAID[phase];
}

function move(s, phase) {
  s.phase = phase;
  announce(phase);
  if (!sends.has(s)) return;  // its control shows another action now: it is not this send's to lock
  lock(s, locks(s));
  redraw();
}

// The owner clicked or edited the form of a refused send, or it went: its control goes back to normal.
function touched(e) {
  const path = e.composedPath();
  const back = [...sends].filter((s) => !locks(s) && (!s.control?.isConnected || path.includes(s.scope ?? s.control)));
  back.forEach(forget);
  if (back.length) redraw();
}

for (const kind of ["click", "input", "change"]) addEventListener(kind, touched, true);

// A click or action handler for a control that may send: a locked control ignores it.
export function press(handler) {
  return (e) => {
    const s = of(e.currentTarget);
    if (s && locks(s)) return undefined;
    clicked = e.currentTarget;
    return handler(e);
  };
}

// One send of the control clicked last, for form *form*; null when that control is already sending. It locks and
// redraws at once, so the click that sends is the one that disables. *on* is the control that shows it when the one
// clicked goes at once (a chooser's Continue); a send with *hold* false keeps no reread of the page waiting, for one
// whose control the reread leaves in place and whose answer may take long (a chat launch, a follow-up).
export function begin(form = "", { on = null, hold = true } = {}) {
  const control = on ?? clicked;
  clicked = null;
  const was = control && of(control);
  if (was && locks(was)) return null;
  if (was) forget(was);
  const scope = form && control?.closest?.(`[data-form="${CSS.escape(form)}"]`);
  const s = {
    control, scope: scope || null, form, id: control?.dataset.sends, phase: "pending", released: false, holds: hold,
  };
  if (control) control.style.minInlineSize = `${control.getBoundingClientRect().width}px`;
  sends.add(s);
  move(s, "pending");
  return {
    // Accepted: resolves once the checkmark has shown for HOLD; the control goes back to normal after BACK.
    done() {
      move(s, "sent");
      setTimeout(() => {
        if (sends.has(s)) {
          forget(s);
          redraw();
        }
      }, BACK);
      return new Promise((resolve) => {
        setTimeout(() => {
          s.released = true;
          resolve();
        }, HOLD);
      });
    },
    // Not done (*error*): a timeout is unsure, anything else failed. The form unlocks; focus returns to the control.
    failed(error) {
      move(s, error instanceof Slow ? "unsure" : "failed");
      if (s.control?.isConnected && [null, document.body].includes(document.activeElement)) s.control.focus();
    },
  };
}

// The phase shown on *el* (showing action *id*), if its send still holds: one whose element now shows another action,
// or whose form element now holds another form, is over, as is a refused or unsure one whose element is now disabled.
function shown(el, id, disabled) {
  el.dataset.sends = id;
  const s = of(el);
  if (s && (s.id !== id || (s.scope && s.scope.dataset.form !== s.form) || (disabled && !locks(s)))) forget(s);
  const now = sends.has(s) ? s : null;
  if (!now || !locks(now)) el.style.minInlineSize = "";
  return now?.phase;
}

// A p-button's label, icon, loading and disabled state, as its send shows them; *id* names its action (its label
// unless that changes), so a send ends once the element shows another action.
class Look extends Directive {
  render() {
    return noChange;
  }

  update(part, [id, label, { icon, busy = false, disabled = false } = {}]) {
    const el = part.element, phase = shown(el, id, disabled);
    // a p-button whose icon was set and then removed shows an arrow: "none" says no icon
    el.setAttribute("icon", phase === "sent" ? "none" : MARK[phase] ?? icon ?? "none");
    el.toggleAttribute("disabled", disabled);
    el.loading = busy || phase === "pending";
    render(phase === "sent" ? html`<p-icon class="sent-mark" name="check" color="inherit" aria-hidden="true"></p-icon
      ><span class="said-aloud">${SAID.sent}</span>` : phase in MARK ? SAID[phase] : label, el);
    return noChange;
  }
}
export const control = directive(Look);

