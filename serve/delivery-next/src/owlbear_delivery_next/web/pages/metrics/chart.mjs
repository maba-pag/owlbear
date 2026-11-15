// One ECharts instance per `#<name>-chart`, kept across renders: a new spec updates it with setOption, so ECharts
// animates the change. The chart is one Tab stop; arrow keys move between its rows and their parts, each focus showing
// its tooltip and emphasis, and Enter acts like a click. A clicked row stays marked, by its id, until the spec's key
// changes.
import { dark, theme } from "./palette.mjs";

const charts = new Map();  // name: { el, inst, spec, mark (a row id), at, said, observer }
const still = matchMedia("(prefers-reduced-motion: reduce)");

/**
 * Draws the chart `#<name>-chart` from *spec*, or removes it when the element or the spec is gone. A spec has:
 * `key` (the filters it shows: a new key clears the mark), `label` (the chart's name), `rows` (how many), `horizontal`
 * (rows on the vertical axis), `ids` (a stable id per row, which keeps a mark on its row when rows reorder), `facts`
 * (the data the option's formatters read, optional), `height` (CSS pixels), `build(theme, mark)` (the option, *mark*
 * the marked row's index or null), `items(row, inst)` (the row's
 * reachable `{ seriesIndex, dataIndex }` in order), `row(params)` (the row a clicked item belongs to, or null) and
 * `act(row)` (what a click or Enter does, after marking it).
 */
export function draw(name, spec) {
  const el = document.getElementById(`${name}-chart`);
  let c = charts.get(name);
  if (c && (c.el !== el || !spec)) c = drop(name);
  if (!el || !spec) return;
  c ??= create(name, el);
  if (c.spec?.key !== spec.key) {
    c.mark = null;
    c.at = [0, 0];
  }
  c.spec = spec;
  paint(c);
}

function drop(name) {
  const c = charts.get(name);
  c.observer.disconnect();
  c.listening.abort();
  c.inst.dispose();
  c.el.removeAttribute("tabindex");
  c.el.style.height = "";  // a container the page keeps takes no room without its chart
  charts.delete(name);
  return null;
}

function create(name, el) {
  const inst = globalThis.echarts.init(el);
  // a container the page keeps after a drop must not keep this chart's handlers
  const c = { el, inst, spec: null, mark: null, at: [0, 0], said: "", listening: new AbortController() };
  const { signal } = c.listening;
  el.tabIndex = 0;
  el.setAttribute("role", "group");
  el.addEventListener("keydown", (e) => key(c, e), { signal });
  el.addEventListener("focus", () => { if (el.matches(":focus-visible")) focus(c); }, { signal });
  el.addEventListener("blur", () => {
    inst.dispatchAction({ type: "downplay" });
    inst.dispatchAction({ type: "hideTip" });
  }, { signal });
  inst.on("click", (params) => {
    const row = c.spec.row(params);
    if (row != null) act(c, row);
  });
  c.observer = new ResizeObserver(() => inst.resize());
  c.observer.observe(el);
  charts.set(name, c);
  return c;
}

// Sets the spec's option, unless it, its facts and the scheme are what the chart shows already: JSON leaves out the
// formatters, so the facts they read stand in for them.
function paint(c) {
  const at = c.spec.ids.indexOf(c.mark), mark = at < 0 ? null : at;
  const option = { animation: !still.matches, backgroundColor: "transparent", ...c.spec.build(theme(), mark) };
  const said = JSON.stringify([dark.matches, c.spec.height, c.spec.facts ?? null, option]);
  if (said === c.said) return;
  c.said = said;
  c.el.setAttribute("aria-label", c.spec.label);
  if (c.el.style.height !== `${c.spec.height}px`) {
    c.el.style.height = `${c.spec.height}px`;
    c.inst.resize();
  }
  // a tooltip left showing would read series the new option removes
  c.inst.dispatchAction({ type: "hideTip" });
  c.inst.dispatchAction({ type: "updateAxisPointer", currTrigger: "leave" });
  c.inst.setOption(option, { replaceMerge: ["series"] });
  if (document.activeElement === c.el) focus(c);
}

function act(c, row) {
  c.mark = c.spec.ids[row];
  c.at[0] = row;
  paint(c);
  c.spec.act?.(row);
}

// Shows the focused item: its emphasis (the others dimmed, it outlined) and its row's tooltip.
function focus(c) {
  const rows = c.spec.rows;
  c.at[0] = Math.min(c.at[0], rows - 1);
  const items = c.spec.items(c.at[0], c.inst);
  c.at[1] = Math.max(0, Math.min(c.at[1], items.length - 1));
  const item = items[c.at[1]];
  c.inst.dispatchAction({ type: "downplay" });
  if (!item) return c.inst.dispatchAction({ type: "hideTip" });
  c.inst.dispatchAction({ type: "highlight", ...item });
  c.inst.dispatchAction({ type: "showTip", ...item });
}

const ALONG = { ArrowUp: -1, ArrowDown: 1 }, ACROSS = { ArrowLeft: -1, ArrowRight: 1 };
// The legend by keyboard, for charts whose spec has `legend`: Space hides the focused part, A shows all, I inverts.
const LEGEND = { a: "legendAllSelect", i: "legendInverseSelect" };

function key(c, e) {
  if (e.key === "Enter") {
    e.preventDefault();
    act(c, c.at[0]);
    return;
  }
  if (c.spec.legend && (e.key === " " || LEGEND[e.key.toLowerCase()]) && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    if (e.key === " ") {
      const item = c.spec.items(c.at[0], c.inst)[c.at[1]];
      const name = item && c.inst.getOption().series[item.seriesIndex]?.name;
      if (name != null) c.inst.dispatchAction({ type: "legendUnSelect", name });
    } else {
      c.inst.dispatchAction({ type: LEGEND[e.key.toLowerCase()] });
    }
    focus(c);
    return;
  }
  const [rowKeys, itemKeys] = c.spec.horizontal ? [ALONG, ACROSS] : [ACROSS, { ArrowUp: 1, ArrowDown: -1 }];
  if (rowKeys[e.key]) {  // the next row in that direction with a part to show
    for (let r = c.at[0] + rowKeys[e.key]; r >= 0 && r < c.spec.rows; r += rowKeys[e.key]) {
      if (c.spec.items(r, c.inst).length) {
        c.at[0] = r;
        break;
      }
    }
  } else if (itemKeys[e.key]) {
    c.at[1] += itemKeys[e.key];
  } else {
    return;
  }
  e.preventDefault();
  focus(c);
}

// An OS scheme switch redraws every chart in the new colours, without a reload.
dark.addEventListener("change", () => { for (const c of charts.values()) paint(c); });
