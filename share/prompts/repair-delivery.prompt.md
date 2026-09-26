---
description: "Run bounded read-only offline Delivery diagnosis"
mode: ask
---

Run the fixed `delivery-diagnose inspect` operation for the current project, optionally scoped to
one native Change ID, with `PYTHONDONTWRITEBYTECODE=1`. If the installed entry is unavailable,
invoke the source fallback exactly as `python -B serve/tools/src/owlbear_tools/delivery_diagnostics.py inspect`
(resolving the distributed source path when available); do not run `uv sync`, setup,
initialization, or lifecycle commands. If neither the installed entry nor an already-supported
Python source fallback is available, report the diagnostic as unavailable. Treat its output as
structural evidence only: it does not establish healthy
execution, user confirmation, provenance, worker termination, approval, or merge readiness.

Use no Delivery, MCP, Cockpit, runtime-parser, mutating, Git, network, provider, lock,
or filesystem-repair commands; “process commands” here means termination or control, not the
bounded Python inspector itself. Do not edit, delete, copy, unlock, recover, upgrade, or repair the
inspected files. Repair and upgrade writes require D07's supported route; do not promise an
automatic fix or ask the user to perform manual repair. Report bounded diagnostics, pending opaque
transactions, incomplete inspection, and the responsible owner without exposing raw record values,
paths, exception text, or log lines.
