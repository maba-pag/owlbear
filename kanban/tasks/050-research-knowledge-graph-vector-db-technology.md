---
id: 50
title: Research knowledge graph + vector DB technology
status: done
priority: high
created: 2026-02-26T18:52:39.2041727+01:00
updated: 2026-02-27T03:32:27.2772391+01:00
started: 2026-02-26T19:43:05.0899992+01:00
completed: 2026-02-27T03:32:27.2772391+01:00
tags:
    - research
    - memory
    - phase-2
class: standard
---

Research the knowledge graph and vector database technology for OwlBear's structured memory.\n\n## Research sources\n\n- **tool.graphicator** (C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator): Prior implementation by the user. Uses SQLite + sqlite-vec for graph storage and vector embeddings. Has schema.py (documents, entities, edges, metadata tables), graph.py (CRUD operations), vectors.py (embedding storage + similarity search with rowid_map bridge), models.py (Pydantic domain models: DocumentRecord, EntityRecord, EdgeRecord). Not yet tested or complete, but substantial prior art.\n- 2+ external GitHub repos implementing knowledge graphs with vector search\n\n## Research checklist\n\n1. Theoretical validity — Is SQLite + sqlite-vec the right approach for an always-on laptop-resident system? Alternatives to evaluate.\n2. Prior art — tool.graphicator + 2+ external repos\n3. Technical feasibility — sqlite-vec compatibility with Python 3.12, performance characteristics\n4. Architecture fit — How does this integrate with owlbear.memory? Alongside or replacing JSONL sessions?\n5. Implementation approach — What can we reuse from tool.graphicator? What needs adaptation?
