"use strict";
// The confirmation a consequential button opens (owner 2026-10-15): what happens now, what Delivery then does by
// itself, what the owner can do afterwards, and the way forward if he declines; true only when he confirms. A *tick*
// is a statement he must tick before confirming (TD-255).
function ask({ title, now, items = [], then, after, instead, yes, no = "Cancel", tick = "" }) {
  const parts = [["Now", now, items], ["Then, by itself", then], ["Afterwards", after], ["If you don't", instead]]
    .filter(([, said]) => said);
  const back = document.activeElement;
  const make = (tag, said, attrs = {}) => {
    const node = document.createElement(tag);
    if (said) node.textContent = said;
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  return new Promise((resolve) => {
    const box = make("p-modal", undefined, { class: "ask" });
    let answered = false;
    const end = (answer) => {
      if (answered) return;
      answered = true;
      box.open = false;
      setTimeout(() => box.remove(), 1000);
      back?.focus?.();
      resolve(answer);
    };
    const heading = make("p-heading", undefined, { size: "lg", slot: "header" });
    heading.append(make("h2", title));
    const body = make("div", undefined, { class: "parts" });
    for (const [label, said, listed] of parts) {
      const part = make("div");
      part.append(make("p-text", label, { weight: "semibold" }), make("p-text", said));
      if (listed?.length) {
        const list = make("ul");
        list.append(...listed.map((item) => make("li", item)));
        part.append(list);
      }
      body.append(part);
    }
    const foot = make("div", undefined, { class: "row", slot: "footer" });
    let ticked = () => true;
    const choice = (label, answer, variant) => {
      const node = make("p-button", label, { type: "button", variant });
      node.addEventListener("click", () => { if (!answer || ticked()) end(answer); });
      return node;
    };
    const decline = choice(no, false, "secondary"), confirm = choice(yes, true, "primary");
    if (tick) {
      const check = make("p-checkbox", undefined, { label: tick });
      ticked = () => check.checked === true;
      const set = () => { confirm.disabled = !ticked(); };
      check.addEventListener("change", set);
      set();
      body.append(check);
    }
    foot.append(confirm, decline);
    box.append(heading, body, foot);
    document.body.append(box);
    box.addEventListener("dismiss", () => end(false));
    box.open = true;
  });
}
