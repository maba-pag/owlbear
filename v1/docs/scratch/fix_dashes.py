"""Fix en-dash/em-dash ruff errors and remove duplicate class in test file."""

import pathlib

p = pathlib.Path("tests/test_retrospective_hook.py")
t = p.read_text(encoding="utf-8")

# Show lines with special dashes
lines = t.splitlines()
for i, line in enumerate(lines, 1):
    if "\u2013" in line or "\u2014" in line:
        print(f"{i}: {line[:100]!r}")

# Fix en-dash (U+2013) -> hyphen-minus in the docstring and comment
t2 = t.replace(
    "(d) The ``create_task`` fallback path mirrors (a)\u2013(c) without a supervisor.",
    "(d) The ``create_task`` fallback path mirrors (a)-(c) without a supervisor.",
)
# Fix em-dash + en-dash in comment  "— create_task fallback mirrors (a)–(c)"
t2 = t2.replace(
    "# AC (d) \u2014 create_task fallback mirrors (a)\u2013(c)",
    "# AC (d) -- create_task fallback mirrors (a)-(c)",
)

# Remove the duplicate class block: everything from the marker line onwards
marker = "\n# ---------------------------------------------------------------------------\n# #989 \u2014 Non-blocking eligibility handoff\n# ---------------------------------------------------------------------------\n"
idx = t2.find(marker)
if idx != -1:
    t2 = t2[:idx]
    print(f"\nRemoved duplicate class block starting at byte {idx}")
else:
    print("\nDuplicate marker not found!")

# Check remaining dashes
lines2 = t2.splitlines()
for i, line in enumerate(lines2, 1):
    if "\u2013" in line or "\u2014" in line:
        print(f"REMAINING {i}: {line[:100]!r}")

p.write_text(t2, encoding="utf-8")
print("Done.")
