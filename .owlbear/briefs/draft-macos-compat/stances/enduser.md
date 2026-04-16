# End User Stance — macOS Hook System

## Position

**Option A (Python hooks) delivers the best developer experience, but requires revising D2, O1, and O2. If the brief stays closed, Option B (Bash + PowerShell dual) is the acceptable fallback. Option C is last choice.**

## Usability Reasoning

### Why Option A

OwlBear is a Python system. MCP servers, kanban engine, setup, tests — all Python. Making hooks Python eliminates the language boundary that every other option introduces or preserves.

**Consumer DX (developer using OwlBear via setup/init.py):**

- **Setup**: init.py seeds `.py` hooks. One artifact type per platform, no dispatcher logic, no platform-conditional seeding.
- **Runtime**: Hooks fire automatically via `uv run python .owlbear/hooks/{name}.py`. Developers don't notice unless something fails.
- **Failure investigation**: When a hook silently blocks an action, the developer opens one Python file to understand why. No dispatcher → shell script trace-through. No "which platform's script am I looking at?"
- **Customization**: Adding an allowed directory to `deny-code-writes` means editing one Python file. In Option B, the developer must edit both `.ps1` and `.sh` (or create drift by editing only one).

**Maintainer DX (developer working on OwlBear itself):**

- 7 hook implementations, not 14. One change per behavioral update.
- One test suite per hook, not two platform-specific test paths.
- One debugging toolchain (Python debugger, Python tracebacks).
- Zero drift risk between platform variants — the single implementation IS the source of truth.

### Why not Option B (if A is off the table)

Option B is honest about what it is: two parallel implementations (`.ps1` + `.sh`) with a dispatcher that selects per platform. It works within the brief as written. It avoids Windows regression risk (`.ps1` files stay untouched).

The permanent cost: every hook change must be made twice, tested twice, and verified for behavioral parity. The O1 acceptance tests (parameterized `.ps1`/`.sh` pair testing) mitigate this — but tests catch divergence after the fact, not before. Drift is an ongoing maintenance tax, not a one-time cost.

### Why not Option C

Option C wraps Option B in a Python dispatcher. If Python is already running (the dispatcher), the delegation to platform-specific shell scripts is pure overhead. It combines Python's startup cost with shell's divergence cost and adds a third component to debug. It has a coherent design rationale (solves the single-command-string constraint), but Option A solves that constraint more cleanly — `uv run python .owlbear/hooks/{name}.py` is already a single cross-platform command string.

## Key Trade-offs

| Dimension | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Ongoing maintenance | 7 files, 1 language | 14 files + dispatcher, 2 languages | 14 files + dispatcher, 2 languages + Python glue |
| Migration scope | Substantial: hooks, agents, tests, brief revision | Substantial: hooks, agents, tests, dispatcher | Substantial: all of B + dispatcher code/tests |
| Windows regression risk | Real — mitigable via parity testing | Zero — .ps1 untouched | Zero — .ps1 untouched |
| Brief compatibility | Requires D2/O1/O2 revision | Fully compatible | Fully compatible |
| Startup overhead | ~50-100ms (imperceptible vs LLM latency) | ~5ms | ~50-100ms + shell startup |
| Drift risk | None | Present (mitigated by paired tests) | Present (mitigated by paired tests) |
| Consumer comprehension | Python (same as rest of system) | Shell (language boundary) | Dispatcher + shell (two boundaries) |

## Warnings

1. **Option A requires explicit brief revision.** D2 mandates "native POSIX shell (bash)." O1 specifies `.ps1`/`.sh` pairs. O2 requires seeded bash variants. Adopting Option A means rewriting these. This is a deliberate recommendation, not an oversight.

2. **Option A carries Windows regression risk.** The current `.ps1` hooks work on Windows. Replacing them with Python hooks means the Windows path changes too. Rigorous parity testing (same inputs → same outputs) before retiring `.ps1` files is essential.

3. **Startup overhead is real but likely imperceptible.** `uv run python` adds ~50-100ms vs ~5ms for bash. On PreToolUse hooks that fire every tool call, this accumulates — but agent tool cycles are dominated by LLM inference (seconds), making hook startup noise.

4. **"One-time migration" is understated for all options.** The migration touches 7 hook files, 19 agent `command:` fields, hook tests, setup/init.py seeding, setup documentation, and seed artifacts. This is true regardless of which option is chosen.

5. **Option B's drift risk is real but testable.** The O1 acceptance criteria require parameterized tests verifying `.ps1`/`.sh` behavioral parity. This catches drift after the fact. It does not prevent a developer from editing one variant and forgetting the other.

## Confidence

**0.82** — Option A is the right long-term DX choice. The brief conflict is real and requires user decision. If D2 is closed, Option B at ~0.65 confidence.
