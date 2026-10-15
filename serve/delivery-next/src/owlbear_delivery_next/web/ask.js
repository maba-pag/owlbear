"use strict";
// The confirmation a consequential button opens (owner 2026-10-15): what happens now, what Delivery then does by
// itself, what the owner can do afterwards, and the way forward if he declines; true only when he confirms.
function ask({ title, now, items = [], then, after, instead, yes, no = "Cancel" }) {
  const parts = [["Now", now, items], ["Then, by itself", then], ["Afterwards", after], ["If you don't", instead]]
    .filter(([, said]) => said);
  const designed = Boolean(customElements.get("p-modal")), back = document.activeElement;
  const make = (tag, said, attrs = {}) => {
    const node = document.createElement(tag);
    if (said) node.textContent = said;
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const titled = (level, said, size, attrs = {}) => {
    if (!designed) return make(`h${level}`, said, attrs);
    const node = make("p-heading", undefined, { size, ...attrs });
    node.append(make(`h${level}`, said));
    return node;
  };
  return new Promise((resolve) => {
    const box = make(designed ? "p-modal" : "dialog", undefined, { class: "ask" });
    let answered = false;
    const end = (answer) => {
      if (answered) return;
      answered = true;
      if (designed) box.open = false;
      else box.close();
      setTimeout(() => box.remove(), 1000);
      back?.focus?.();
      resolve(answer);
    };
    const body = make("div", undefined, { class: "parts" });
    for (const [label, said, listed] of parts) {
      const part = make("div");
      part.append(make(designed ? "p-text" : "h3", label, designed ? { weight: "semibold" } : {}),
        make(designed ? "p-text" : "p", said));
      if (listed?.length) {
        const list = make("ul");
        list.append(...listed.map((item) => make("li", item)));
        part.append(list);
      }
      body.append(part);
    }
    const foot = make("div", undefined, { class: "row", ...(designed ? { slot: "footer" } : {}) });
    const choice = (label, answer, variant) => {
      const node = make(designed ? "p-button" : "button", label, { type: "button", ...(designed ? { variant } : {}) });
      node.addEventListener("click", () => end(answer));
      return node;
    };
    foot.append(choice(yes, true, "primary"), choice(no, false, "secondary"));
    box.append(titled(2, title, "lg", designed ? { slot: "header" } : {}), body, foot);
    if (designed) box.addEventListener("dismiss", () => end(false));
    else box.addEventListener("cancel", (event) => { event.preventDefault(); end(false); });
    document.body.append(box);
    if (designed) box.open = true;
    else box.showModal();
  });
}
