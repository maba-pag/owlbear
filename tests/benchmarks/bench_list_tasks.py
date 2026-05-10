"""Benchmark: list_tasks() latency at 700 and 1500 tasks.

Run with:
    uv run pytest tests/benchmarks/bench_list_tasks.py -v -s -n 0

Note: pass ``-n 0`` to disable xdist so that the latency table is printed
to the terminal.  Without it, tests still pass but worker stdout is not
forwarded to the main terminal.

Measurement methodology (per scenario):
  1. Cold: first call, no page-cache warmup.
  2. Warmup: N_WARMUP=3 calls to prime the OS page cache.
  3. Timed: N_ITERS=100 wall-clock measurements (perf_counter_ns).
  4. Report: cold_ms, p50_ms, p99_ms.

Board generation:
  - Fully deterministic (SEED=42).
  - All required Task model fields populated with valid values.
  - Tags: 2-5 per task drawn from a 20-item pool.
  - Status: distributed across all 7 configured statuses (round-robin by ID).
  - Priority: distributed across all 5 priorities (round-robin by ID).
  - Body: 20-100 lorem lines per task.
  - ~10% of tasks have blocked=true.

Scenarios: unfiltered, status/tag/priority/blocked filters.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCALES = [700, 1500]
N_WARMUP = 3
N_ITERS = 100
SEED = 42

STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]
PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]
TAG_POOL = [
    "engine",
    "cockpit",
    "mcp",
    "phase-0",
    "phase-1",
    "api",
    "perf",
    "security",
    "docs",
    "refactor",
    "bugfix",
    "frontend",
    "backend",
    "ux",
    "infra",
    "ci",
    "tooling",
    "dx",
    "type-test",
    "type-bench",
]
_LOREM = [
    "Implement the core feature per the brief.",
    "Add unit tests for the new module.",
    "Validate all edge cases and document findings.",
    "Run the full test suite and update coverage.",
    "Review the architecture decision for correctness.",
    "Integrate with the existing API surface.",
    "Refactor legacy code to match current conventions.",
    "Update documentation to reflect the new interface.",
    "Add observability hooks for production monitoring.",
    "Profile memory usage under sustained load.",
    "Investigate flaky test in CI and fix root cause.",
    "Benchmark the optimised path and record results.",
    "Verify the data migration script on staging.",
    "Stub out the external API calls for local testing.",
    "Deploy the change to the dev environment.",
    "Coordinate with the team on the spec changes.",
    "Check for security vulnerabilities in the input path.",
    "Write the design doc for the proposed change.",
    "Prototype the new algorithm in a scratch module.",
    "Clean up TODO comments from the last sprint.",
]
_VERBS = ["Implement", "Add", "Fix", "Update", "Refactor", "Document"]
_NOUNS = ["feature", "test", "module", "endpoint", "handler", "schema"]

_CONFIG_YAML = """\
next_id: 1
"""


# ---------------------------------------------------------------------------
# Board generation helpers
# ---------------------------------------------------------------------------


def _make_board(base_dir: Path, n_tasks: int, seed: int = SEED) -> Path:
    """Create a temp kanban board with *n_tasks* synthetic tasks.

    Fully deterministic given the same *seed*.  Returns the kanban_dir Path.
    """
    rng = random.Random(seed)  # noqa: S311
    kanban_dir = base_dir / f"board_{n_tasks}"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(
        _CONFIG_YAML.format(next_id=n_tasks + 1),
        encoding="utf-8",
    )
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    for task_id in range(1, n_tasks + 1):
        _write_task(tasks_dir, task_id, rng)
    return kanban_dir


def _write_task(tasks_dir: Path, task_id: int, rng: random.Random) -> None:
    """Write one synthetic task file to *tasks_dir*."""
    status = STATUSES[task_id % len(STATUSES)]
    priority = PRIORITIES[task_id % len(PRIORITIES)]
    n_tags = rng.randint(2, 5)
    tags = rng.sample(TAG_POOL, n_tags)
    blocked = "true" if rng.random() < 0.1 else "false"
    n_lines = rng.randint(20, 100)
    body = "\n".join(rng.choice(_LOREM) for _ in range(n_lines))
    title = f"{rng.choice(_VERBS)} {rng.choice(_NOUNS)} {task_id}"
    tag_yaml = "\n".join(f"- {t}" for t in tags)

    content = (
        "---\n"
        f"id: {task_id}\n"
        f'title: "{title}"\n'
        f"status: {status}\n"
        f"priority: {priority}\n"
        f"created: 2026-04-17T19:56:44.165954+00:00\n"
        f"updated: 2026-04-17T20:02:28.358032+00:00\n"
        f"tags:\n{tag_yaml}\n"
        f"parent:\n"
        f"depends_on: []\n"
        f"blocked: {blocked}\n"
        f"block_reason:\n"
        f"claimed_by:\n"
        f"claimed_at:\n"
        "---\n"
        f"{body}\n"
    )
    (tasks_dir / f"{task_id}-task-{task_id}.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------


def _percentile(sorted_ms: list[float], p: float) -> float:
    """Linear-interpolation percentile of a sorted sample."""
    n = len(sorted_ms)
    if n == 0:
        return 0.0
    k = (n - 1) * p / 100.0
    lo = int(k)
    hi = lo + 1
    if hi >= n:
        return sorted_ms[-1]
    return sorted_ms[lo] + (k - lo) * (sorted_ms[hi] - sorted_ms[lo])


def _measure(engine: KanbanEngine, kwargs: dict) -> tuple[float, float, float]:
    """Return (cold_ms, p50_ms, p99_ms) for *engine.list_tasks(**kwargs)*."""
    # Cold: first call with no prior page-cache warmup
    t0 = time.perf_counter_ns()
    engine.list_tasks(**kwargs)
    cold_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    # Warmup: populate OS page cache
    for _ in range(N_WARMUP):
        engine.list_tasks(**kwargs)

    # Timed iterations
    raw_ns: list[int] = []
    for _ in range(N_ITERS):
        t0 = time.perf_counter_ns()
        engine.list_tasks(**kwargs)
        raw_ns.append(time.perf_counter_ns() - t0)

    sorted_ms = sorted(ns / 1_000_000.0 for ns in raw_ns)
    return cold_ms, _percentile(sorted_ms, 50), _percentile(sorted_ms, 99)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bench_boards(tmp_path_factory: pytest.TempPathFactory) -> dict[int, Path]:
    """Build boards at each scale once per module run."""
    base = tmp_path_factory.mktemp("bench_boards", numbered=False)
    return {n: _make_board(base, n) for n in SCALES}


# ---------------------------------------------------------------------------
# Parametrised benchmark tests
# ---------------------------------------------------------------------------

_SCENARIOS: list[tuple[str, dict]] = [
    ("unfiltered", {}),
    ("status=todo", {"status": "todo"}),
    ("tag=engine", {"tag": "engine"}),
    ("priority=critical", {"priority": "critical"}),
    ("blocked=True", {"blocked": True}),
]
_SCENARIO_IDS = [s[0] for s in _SCENARIOS]


@pytest.mark.benchmark
@pytest.mark.parametrize("n_tasks", SCALES)
@pytest.mark.parametrize(("scenario", "kwargs"), _SCENARIOS, ids=_SCENARIO_IDS)
def test_list_tasks_latency(
    bench_boards: dict[int, Path],
    n_tasks: int,
    scenario: str,
    kwargs: dict,
    capsys: pytest.CaptureFixture,
) -> None:
    """Measure list_tasks() p50/p99 latency and print results.

    No functional failure threshold — this benchmark documents baseline
    performance for comparison after optimisation tasks #940 and #941.
    """
    kanban_dir = bench_boards[n_tasks]
    engine = KanbanEngine(kanban_dir, activity_log=False)
    cold_ms, p50_ms, p99_ms = _measure(engine, kwargs)

    with capsys.disabled():
        print(  # noqa: T201
            f"\n  [{n_tasks:>4} tasks | {scenario:<20}]"
            f"  cold={cold_ms:>7.1f}ms"
            f"  p50={p50_ms:>7.1f}ms"
            f"  p99={p99_ms:>7.1f}ms"
        )

    # Sanity assertions — not functional failure thresholds
    assert cold_ms >= 0, "cold_ms must be non-negative"
    assert p50_ms >= 0, "p50_ms must be non-negative"
    assert p99_ms >= p50_ms, "p99 must be >= p50"


# ---------------------------------------------------------------------------
# Warm-cache latency benchmark (AC #942)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_warm_cache_p99_under_50ms_at_1500_tasks(
    bench_boards: dict[int, Path],
    capsys: pytest.CaptureFixture,
) -> None:
    """Warm-read p99 must be <50ms at 1500 tasks after mtime cache is implemented.

    AC #942 target: warm read p99 <50ms at 1500 tasks.
    Baseline (no cache): p99 ~453ms.

    This test FAILS in RED phase — cache not yet implemented so p99 ~450ms.
    """
    kanban_dir = bench_boards[1500]
    engine = KanbanEngine(kanban_dir, activity_log=False)

    # Warm the cache with one unmetered call
    engine.list_tasks()

    # Measure warm reads (no file changes between calls)
    raw_ns: list[int] = []
    for _ in range(N_ITERS):
        t0 = time.perf_counter_ns()
        engine.list_tasks()
        raw_ns.append(time.perf_counter_ns() - t0)

    sorted_ms = sorted(ns / 1_000_000.0 for ns in raw_ns)
    p50_ms = _percentile(sorted_ms, 50)
    p99_ms = _percentile(sorted_ms, 99)

    with capsys.disabled():
        print(  # noqa: T201
            f"\n  [1500 tasks | warm_cache            ]"
            f"  p50={p50_ms:>7.1f}ms"
            f"  p99={p99_ms:>7.1f}ms"
            f"  (target: p99 <50ms)"
        )

    assert p99_ms < 50, (
        f"Warm-read p99 must be <50ms at 1500 tasks, got {p99_ms:.1f}ms. Cache not implemented or not effective."
    )
