"""Generate a standalone HTML knowledge graph viewer from the SQLite database.

Usage:
    uv run python .owlbear/scripts/knowledge_graph_viewer.py [--db PATH] [--out PATH]

Reads entities and edges from the knowledge SQLite database and produces a
self-contained HTML file using vis.js for interactive network visualization.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def _load_graph(db_path: str) -> tuple[list[dict], list[dict]]:
    """Read entities and edges from the knowledge database."""
    conn = sqlite3.connect(db_path)
    try:
        entities = conn.execute(
            "SELECT id, name, entity_type, description, importance, document_id FROM entities"
        ).fetchall()
        edges = conn.execute("SELECT id, source_id, target_id, relation, weight FROM edges").fetchall()
    finally:
        conn.close()

    # Build entity ID set for edge filtering
    entity_ids = {row[0] for row in entities}

    nodes = []
    for row in entities:
        eid, name, etype, description, importance, doc_id = row
        nodes.append(
            {
                "id": eid,
                "label": name,
                "title": f"{name}\n{etype or ''}\n{description or ''}",
                "group": etype or "unknown",
                "value": max(float(importance or 0.5), 0.2),
                "doc_id": doc_id or "",
            }
        )

    links = []
    for row in edges:
        _edge_id, source, target, relation, weight = row
        # Only include edges where both endpoints exist
        if source in entity_ids and target in entity_ids:
            links.append(
                {
                    "from": source,
                    "to": target,
                    "label": relation or "",
                    "title": f"{relation} (weight: {weight or 0})",
                    "value": max(float(weight or 0.5), 0.1),
                }
            )

    return nodes, links


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OwlBear Knowledge Graph</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0d1117; color: #e6edf3; }
  #controls {
    position: fixed; top: 0; left: 0; right: 0; z-index: 10;
    padding: 12px 16px; background: #161b22; border-bottom: 1px solid #30363d;
    display: flex; gap: 12px; align-items: center;
  }
  #controls input {
    padding: 6px 12px; background: #0d1117; border: 1px solid #30363d;
    border-radius: 6px; color: #e6edf3; font-size: 14px; width: 300px;
  }
  #controls .stats { margin-left: auto; font-size: 13px; color: #8b949e; }
  #graph { width: 100vw; height: 100vh; padding-top: 52px; }
  #detail {
    position: fixed; bottom: 16px; right: 16px; width: 360px;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 16px; font-size: 13px; display: none; z-index: 10;
    max-height: 50vh; overflow-y: auto;
  }
  #detail h3 { font-size: 15px; margin-bottom: 8px; color: #58a6ff; }
  #detail .field { margin-bottom: 4px; }
  #detail .label { color: #8b949e; }
</style>
</head>
<body>
<div id="controls">
  <input type="text" id="search" placeholder="Filter nodes..." autocomplete="off">
  <div class="stats" id="stats"></div>
</div>
<div id="graph"></div>
<div id="detail"></div>
<script>
const rawNodes = __NODES__;
const rawEdges = __EDGES__;

const COLORS = {
  concept: "#58a6ff", system: "#f78166", process: "#3fb950",
  person: "#d2a8ff", role: "#79c0ff", team: "#ffa657",
  tool: "#ff7b72", policy: "#a5d6ff", standard: "#7ee787",
  unknown: "#8b949e"
};

const nodes = new vis.DataSet(rawNodes.map(n => ({
  ...n,
  color: { background: COLORS[n.group] || COLORS.unknown, border: "#30363d",
           highlight: { background: "#e6edf3", border: "#58a6ff" } },
  font: { color: "#e6edf3", size: 12 + (n.value || 0.5) * 8 },
  shape: "dot",
  size: 8 + (n.value || 0.5) * 20,
})));

const edges = new vis.DataSet(rawEdges.map(e => ({
  ...e,
  color: { color: "#30363d", highlight: "#58a6ff", opacity: 0.6 },
  font: { color: "#8b949e", size: 10, strokeWidth: 0 },
  arrows: "to",
  smooth: { type: "continuous" },
  width: 1 + (e.value || 0.5) * 2,
})));

document.getElementById("stats").textContent =
  rawNodes.length + " entities, " + rawEdges.length + " edges";

const container = document.getElementById("graph");
const network = new vis.Network(container, { nodes, edges }, {
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: { gravitationalConstant: -80, springLength: 120, damping: 0.4 },
    stabilization: { iterations: 150 },
  },
  interaction: { hover: true, tooltipDelay: 200 },
});

// Search filter
const searchInput = document.getElementById("search");
searchInput.addEventListener("input", () => {
  const q = searchInput.value.toLowerCase();
  if (!q) {
    nodes.forEach(n => nodes.update({ id: n.id, hidden: false }));
    edges.forEach(e => edges.update({ id: e.id, hidden: false }));
    return;
  }
  const matchIds = new Set();
  nodes.forEach(n => {
    const match = n.label.toLowerCase().includes(q) ||
                  (n.group || "").toLowerCase().includes(q);
    if (match) matchIds.add(n.id);
    nodes.update({ id: n.id, hidden: !match });
  });
  edges.forEach(e => {
    const vis = matchIds.has(e.from) && matchIds.has(e.to);
    edges.update({ id: e.id, hidden: !vis });
  });
});

// Detail panel
const detail = document.getElementById("detail");
network.on("selectNode", params => {
  const nodeId = params.nodes[0];
  const node = rawNodes.find(n => n.id === nodeId);
  if (!node) return;
  const connected = rawEdges.filter(e => e.from === nodeId || e.to === nodeId);
  let html = "<h3>" + node.label + "</h3>";
  html += '<div class="field"><span class="label">Type:</span> ' + (node.group || "—") + "</div>";
  html += '<div class="field"><span class="label">Importance:</span> ' + (node.value || 0).toFixed(2) + "</div>";
  if (node.title) html += '<div class="field"><span class="label">Description:</span> '
    + node.title.split("\\n").pop() + "</div>";
  if (connected.length) {
  if (connected.length) {
    html += '<div class="field" style="margin-top:8px">'
      + '<span class="label">Connections (' + connected.length + '):</span></div>';
    connected.slice(0, 20).forEach(e => {
      const peer = e.from === nodeId ? rawNodes.find(n => n.id === e.to) : rawNodes.find(n => n.id === e.from);
      const dir = e.from === nodeId ? "→" : "←";
      html += '<div class="field">  ' + dir + " " + (e.label || "—") + " " + (peer ? peer.label : "?") + "</div>";
    });
  }
  detail.innerHTML = html;
  detail.style.display = "block";
});
network.on("deselectNode", () => { detail.style.display = "none"; });
</script>
</body>
</html>
"""


def generate(db_path: str, out_path: str) -> None:
    """Generate the HTML viewer file."""
    nodes, links = _load_graph(db_path)
    html = _HTML_TEMPLATE.replace("__NODES__", json.dumps(nodes)).replace("__EDGES__", json.dumps(links))
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Generated graph viewer: {out_path}")
    print(f"  {len(nodes)} entities, {len(links)} edges")


def main() -> None:
    """Generate an HTML knowledge-graph viewer from the configured SQLite database."""
    parser = argparse.ArgumentParser(description="Generate knowledge graph viewer")
    parser.add_argument("--db", default=".owlbear/knowledge/local.db", help="Path to knowledge SQLite database")
    parser.add_argument("--out", default=".owlbear/scratch/knowledge-graph.html", help="Output HTML file path")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    generate(args.db, args.out)


if __name__ == "__main__":
    main()
