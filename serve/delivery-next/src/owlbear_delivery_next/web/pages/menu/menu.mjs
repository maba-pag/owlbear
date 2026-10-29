// The menu (D-01M63C8375KV9WA6NH8K2MB8PN): the top row's burger opens PDS's drilldown with every page. The work
// pages have their own level and on phones are only here; ui.mjs's guard covers its links
// (D-01M63C8DA1D95Z7M9ZYWVYYNF7).

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { defined, here } from "/assets/ui.mjs";

// The levels and the links beside them, in the menu's order.
export const LEVELS = [
  { id: "work", label: "Work", links: [["/", "Changes"], ["/backlog", "Backlog"], ["/memory", "Memory"],
    ["/decisions", "Decisions"], ["/metrics", "Metrics"]] },
];
export const LINKS = [["/projects", "Projects"], ["/config", "Settings"], ["/maintenance", "Maintenance"]];

const menu = { open: false, level: undefined };
const root = document.getElementById("menu");

function link([path, label]) {
  const current = path === location.pathname;
  return html`<p-drilldown-link ?active=${current}><a href=${here({}, path)}
    aria-current=${current ? "page" : nothing}>${label}</a></p-drilldown-link>`;
}

const item = (id) => root.querySelector(`p-drilldown-item[identifier="${id}"]`);

// PDS shows a level on its own schedule and its dialog focuses the dismiss button, so focus waits until the target
// shows, for at most a second.
async function focus(find) {
  for (let frame = 0; frame < 60; frame++) {
    await new Promise(requestAnimationFrame);
    const target = find();
    if (!target?.checkVisibility({ visibilityProperty: true })) continue;
    target.focus();
    if (target.matches(":focus")) return;
  }
}

// The menu opens at the level that holds this page, so its siblings are one step away, with focus on this page's link.
function open() {
  menu.open = true;
  menu.level = LEVELS.find((l) => l.links.some(([path]) => path === location.pathname))?.id;
  show();
  focus(() => root.querySelector("p-drilldown a[aria-current]") ?? root.querySelector("p-drilldown a[href]"));
}

function close() {
  menu.open = false;
  show();
}

// A level opens with focus on its first link; going back puts it on the button that opened the level.
function moved(e) {
  const left = menu.level;
  menu.level = e.detail.activeIdentifier;
  show();
  focus(() => menu.level ? item(menu.level)?.querySelector("a[href]")
    : item(left)?.shadowRoot?.querySelector("p-button-pure.button"));
}

// A link the guard held (ui.mjs) leaves the page as it is; the menu closes so its reason shows under the top row.
function clicked(e) {
  if (e.defaultPrevented && e.target.closest?.("a[href]")) close();
}

function show() {
  render(html`
    <p-button-pure type="button" icon="menu-lines" hide-label="true" aria="{'aria-haspopup': 'dialog'}"
      @click=${open}>Menu</p-button-pure>
    <p-drilldown .open=${menu.open} .activeIdentifier=${menu.level} .aria=${{ "aria-label": "OwlBear pages" }}
      @update=${moved} @dismiss=${close} @click=${clicked}>
      ${LEVELS.map((l) => html`<p-drilldown-item identifier=${l.id} label=${l.label}>${l.links.map(link)}
        </p-drilldown-item>`)}
      ${LINKS.map(link)}
    </p-drilldown>`, root);
}

if (root) {
  await defined(["p-button-pure", "p-drilldown", "p-drilldown-item", "p-drilldown-link"]);
  show();
}
