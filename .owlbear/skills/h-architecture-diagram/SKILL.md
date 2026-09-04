---
name: h-architecture-diagram
description: "Handbook: Author and maintain static Archify architecture diagrams for OwlBear documentation"
user-invocable: true
---

# Static Architecture Diagrams

Use this skill for architecture maps published from `share/diagrams/`. The output is a static SVG
for Markdown; do not enable Archify viewer motion, guided views, or presentation behavior.

## Source And Coverage

Keep the Archify JSON source beside its generated SVG. The diagram manifest owns the source-to-
artifact relationship and its `describes` globs; keep those globs limited to the implementation
files the diagram explains.

Use stable component and connection IDs. Keep the first map to roughly 8–12 components, one clear
main structure, and only relationships that help explain it. The JSON source, repository
configuration, and server implementations remain authoritative over the picture.

## Authoring And Proof

Resolve the pinned development renderer with:

```shell
uv run python .owlbear/scripts/diagrams/sync.py --print-root
```

Validate and render a source with:

```shell
uv run python .owlbear/scripts/diagrams/render.py \
  --input share/diagrams/example.architecture.json \
  --output share/diagrams/example.svg \
  --offline
```

Use `quality_profile: "showcase"`. Repair the named Archify diagnostic rather than weakening a
layout gate or editing the generated SVG by hand. Regenerate the artifact after every source edit
or Archify lock bump, and verify that the documentation index and manifest remain current.
