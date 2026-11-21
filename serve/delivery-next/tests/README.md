# Delivery engine tests

## Preview servers for visual checks

The `owlbear` script starts the machine host on a free port of its own choosing against the owner's home, so it is
never a visual check's launch. Use a preview script instead; each takes the port and serves fixture data only.

| Page | Directory | Command | Ready URL |
| --- | --- | --- | --- |
| Metrics | `serve/delivery-next` | `uv run python tests/metrics_preview.py {port}` | `http://127.0.0.1:{port}/` |
| Backlog | `serve/delivery-next` | `uv run python tests/backlog_preview.py {port}` | `http://127.0.0.1:{port}/backlog` |

`metrics_preview.py` replaces `HOME` with a fresh temporary folder, drops `OWLBEAR_DATA` and `COPILOT_HOME`, and
seeds its own fixture there, so it reads neither the owner's data nor a prepared copy's `HOME`. Its pages seed the
token themselves: a state path such as `/metrics?period=all&by=agent` opens without `#token=`.
`test_metrics_preview.py` guards that boundary.

`backlog_preview.py` isolates itself the same way and makes no `gh` or GitHub call: its backlog issues live in
memory, its shared data checkout and registered clone are local folders in that `HOME`. `/backlog?reviews=open` unfolds
the Suppression reviews section, a state only the preview offers. `test_backlog_preview.py` guards that boundary.
