"use strict";
// The confirmation a consequential button opens (owner 2026-10-15): what happens now, what Delivery then does by
// itself, what the owner can do afterwards, and the way forward if he declines; true only when he confirms. A *tick*
// is a statement he must tick before confirming (TD-255). A *reason* is the label of the text he must give before
// confirming; the dialog then answers with that text, which starts as *value* and holds *limit* characters at most.
// A *destructive* confirm is never the primary: declining is (D-01M63C7BJZZ7RQV9XS4XVR0DNE); the confirm stays
// first, so focus does not start on declining.
function ask({ title, now, items = [], then, after, instead, yes, no = "Cancel", tick = "", reason = "", value = "",
  limit = 4000, destructive = false }) {
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
    const checks = [];
    let answer = () => true;
    const choice = (label, yes, variant) => {
      const node = make("p-button", label, { type: "button", variant });
      node.addEventListener("click", () => { if (!yes) end(false); else if (checks.every((c) => c())) end(answer()); });
      return node;
    };
    const decline = choice(no, false, destructive ? "primary" : "secondary"),
      confirm = choice(yes, true, destructive ? "secondary" : "primary");
    const set = () => { confirm.disabled = !checks.every((c) => c()); };
    if (reason) {
      const rows = value ? "8" : "3";
      const why = make("p-textarea", undefined, { label: reason, "max-length": String(limit), rows });
      why.value = value;
      checks.push(() => (why.value ?? "").trim() !== "");
      answer = () => why.value.trim();
      why.addEventListener("input", set);
      body.append(why);
    }
    if (tick) {
      const check = make("p-checkbox", undefined, { label: tick });
      checks.push(() => check.checked === true);
      check.addEventListener("change", set);
      body.append(check);
    }
    set();
    foot.append(confirm, decline);
    box.append(heading, body, foot);
    document.body.append(box);
    box.addEventListener("dismiss", () => end(false));
    box.open = true;
  });
}
