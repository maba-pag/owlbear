# Delivery engine tests

## `owlbear demo` for visual checks

The `owlbear` script starts the machine host on a free port of its own choosing against the owner's home, so it is
never a visual check's launch. `owlbear demo` is: it serves every page on example data, on the port it is given.

| Directory | Command | Ready URL | Preparation option |
| --- | --- | --- | --- |
| `serve/delivery-next` | `uv run owlbear demo --port {port}` | `http://127.0.0.1:{port}/` | `demo-example-data` |

The demo replaces `HOME` with a fresh temporary folder, drops `OWLBEAR_DATA` and `COPILOT_HOME`, keeps Git and `gh`
off GitHub and seeds its own example data there; it removes that folder when it stops. It runs no scheduler and
refuses every request that would start work, with one plain sentence. Its pages seed the token themselves, so a state
path such as `/metrics?period=all&by=agent` opens without `#token=`, and `/backlog?reviews=open` unfolds the
Suppression reviews section. `test_demo.py` guards that boundary and the served Metrics and Backlog rows.

A visual check launches only on a declared test preparation. The owner declares `demo-example-data` in the project's
settings before the first follow-on Change is shaped:

```json
"preparations": [
  {
    "id": "demo-example-data",
    "kind": "data-only",
    "seed": "mkdir -p .owlbear/scratch/demo-home",
    "cleanup": "rm -rf .owlbear/scratch/demo-home",
    "isolation": {"HOME": ".owlbear/scratch/demo-home"}
  }
]
```

It copies no data: the demo seeds and removes its own temporary home, so `seed` only creates the empty, git-ignored
folder that `HOME` names and `cleanup` removes it. `HOME` keeps the launch off the owner's home: `uv run` and the
version lease run before the demo replaces `HOME` itself.

### Example Changes in `owlbear demo`

`machine_host/demo_changes.py` writes six Changes on every start of the demo, at the same addresses:

| Project | State | Address |
| --- | --- | --- |
| example-shop | being built | `/?change=e0a1b2c3d4e5f601/example-shop-cart-badge` |
| example-shop | waiting on a disputed brief finding | `/?change=e0a1b2c3d4e5f601/example-shop-gift-cards` |
| example-shop | waiting on a worker's question | `/?change=e0a1b2c3d4e5f601/example-shop-search-filters` |
| example-docs | stopped after a failed repair | `/?change=e0a1b2c3d4e5f602/example-docs-link-checker` |
| example-docs | paused | `/?change=e0a1b2c3d4e5f602/example-docs-dark-theme` |
| example-docs | done | `/?change=e0a1b2c3d4e5f602/example-docs-install-guide` |
