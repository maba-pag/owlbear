// A stacked bar chart's spec for chart.mjs: a row per bar, its parts stacked in their colours with a thin gap, the
// total at the bar's end, one tooltip with every part and the total, a legend that hides and shows parts (All,
// Invert), and on demand relative lengths: parts as shares of full-length bars, while tooltips keep raw values.
import { html } from "/assets/lit-html/3.3.3/lit-html.js";

const esc = (text) => globalThis.echarts.format.encodeHTML(String(text));

/** The switch between raw and relative lengths, for a stacked chart's controls. */
export const lengthSwitch = (on, set) => html`<p-switch compact="true" .checked=${on}
  @update=${(e) => set(e.detail.checked)}>Relative lengths</p-switch>`;

/**
 * The spec of a stacked chart: `labels` (one per bar, in order), `parts` (`{ id, name, values }`, a raw value per
 * bar, bottom of the stack first), `totals` (per bar), `colours(theme)` (one per part), `format` (a raw value as
 * text), `horizontal`, `relative`, `average` (an average line of the totals, raw lengths only) and `tick` (an axis
 * label from a bar's label, optional).
 */
export function stacked({ labels, parts, totals, colours, format, horizontal, relative, average, tick }) {
  const tip = (colour) => (ps) => {
    const r = ps[0].dataIndex;
    const lines = parts.map((p, j) => (p.values[r] ? `<span style="color:${colour[j]}">■</span> ${esc(p.name)}: ${
      format(p.values[r])}<br>` : "")).join("");
    return `<strong>${esc(labels[r])}</strong><br>${lines}Total: ${format(totals[r])}`;
  };
  function build(t, mark) {
    const marked = { borderColor: t.text, borderWidth: 3 };  // the clicked bar, outlined until the filters change
    const colour = colours(t), shown = (v, r) => (relative ? (totals[r] ? (v / totals[r]) * 100 : 0) : v);
    const category = { type: "category", data: labels, inverse: horizontal, axisTick: { show: false },
      axisLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, hideOverlap: true, width: horizontal ? 128 : undefined, overflow: "truncate",
        formatter: tick } };  // fmt: skip
    const value = { type: "value", max: relative ? 100 : null, splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, hideOverlap: true, formatter: relative ? "{value}%" : (v) => format(v) } };
    const series = parts.map((p, j) => ({
      id: p.id, name: p.name, type: "bar", stack: "all", barMaxWidth: 28, z: 2,
      data: p.values.map((v, r) => (r === mark ? { value: shown(v, r), itemStyle: marked } : shown(v, r))),
      itemStyle: { color: colour[j], borderColor: t.canvas, borderWidth: 1 },
      emphasis: { focus: "series", itemStyle: { borderColor: t.text, borderWidth: 2 } },
      blur: { itemStyle: { opacity: 0.3 } },
    }));  // fmt: skip
    const mean = totals.reduce((s, v) => s + v, 0) / totals.length;
    series.push({
      // A transparent full-length bar laid over the stack carries the total label at the bar's end.
      id: "total", name: "Total", type: "bar", barGap: "-100%", barMaxWidth: 28, z: 1, silent: true,
      data: totals.map((v) => (relative ? (v ? 100 : 0) : v)),
      itemStyle: { color: "transparent" }, emphasis: { disabled: true },
      label: { show: true, position: horizontal ? "right" : "top", color: t.text,
        formatter: (p) => format(totals[p.dataIndex]) },
      markLine: average && !relative ? { silent: true, symbol: "none", data: [{ yAxis: mean }],
        lineStyle: { color: t.text, type: "dashed" },
        label: { color: t.text, position: "insideEndTop", formatter: `Average ${format(mean)}` } } : { data: [] },
    });  // fmt: skip
    return {
      grid: { left: 8, right: horizontal ? 56 : 16, top: 48, bottom: 8, containLabel: true },
      legend: { type: "scroll", top: 0, left: 0, right: 0, data: parts.map((p) => p.name), textStyle: { color: t.text },
        inactiveColor: t.grid, pageIconColor: t.text, pageIconInactiveColor: t.grid, pageTextStyle: { color: t.text },
        selector: [{ type: "all", title: "All" }, { type: "inverse", title: "Invert" }],
        selectorLabel: { color: t.text, borderColor: t.grid } },
      tooltip: { trigger: "axis", confine: true, axisPointer: { type: "shadow" }, backgroundColor: t.surface,
        borderColor: t.grid, textStyle: { color: t.text }, formatter: tip(colour) },
      xAxis: horizontal ? value : category,
      yAxis: horizontal ? category : value,
      series,
    };  // fmt: skip
  }
  return {
    rows: labels.length, horizontal, build,
    height: horizontal ? 96 + labels.length * 32 : 340,
    items: (row, inst) => {
      const option = inst.getOption();
      const hidden = option?.legend?.[0]?.selected ?? {};
      // replaceMerge keeps the indices of kept series, so a part's index is looked up by its id
      const ids = (option?.series ?? []).map((s) => s?.id);
      return parts.flatMap((p) => (p.values[row] > 0 && hidden[p.name] !== false
        ? [{ seriesIndex: ids.indexOf(p.id), dataIndex: row }] : []));
    },
    row: (params) => (params.componentType === "series" && params.seriesId !== "total" ? params.dataIndex : null),
  };  // fmt: skip
}
