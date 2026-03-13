# Restrict os.startfile to Safe File Types

> **Owning task:** #527 — Restrict os.startfile to safe file types in CLI channel
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

SEC-16 from the security audit: `CLIChannel.send_file()` calls `os.startfile(path)` on Windows without checking the file extension. If an LLM-controlled agent passes an arbitrary path, `os.startfile` invokes the Windows shell handler — which could execute `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.msi`, or macro-enabled Office formats (`.docm`, `.xlsm`).

**Question:** What file extensions should be allowlisted, and how should blocked types be handled?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python `os.startfile` docs | <https://docs.python.org/3/library/os.html#os.startfile> | Confirms `startfile` calls `ShellExecute()` — equivalent to double-clicking in Explorer | .90 |
| 2 | OWASP Unrestricted File Upload | <https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload> | Allowlist over denylist for file type validation; never trust extensions alone but allowlist is minimum bar | .85 |
| 3 | Bandit S606 rule (os.startfile) | <https://bandit.readthedocs.io/en/latest/plugins/b606_start_process_with_a_shell.html> | Flags os.startfile as shell-equivalent risk; already suppressed with `# noqa: S606` in our code | .80 |
| 4 | Windows dangerous file types list | <https://support.microsoft.com/en-us/windows/unsafe-file-types-in-outlook> | Microsoft's own list of executable/dangerous extensions blocked by Outlook | .85 |

## 3. Analysis

### Call chain

`ScreenshotService.deliver()` → `CLIChannel.send_file()` → `os.startfile(path)`. Currently the only caller is `ScreenshotService`, which always passes `.png` screenshot paths. However, `send_file` is a public method — any future toolset could call it.

### Approach comparison

| Criterion | Allowlist (check suffix) | Denylist (block bad suffixes) | User confirmation |
|-----------|--------------------------|-------------------------------|-------------------|
| Security | High (.90) — only known-safe types open | Medium (.60) — easy to miss exotic types | High (.95) — human in loop |
| KISS | High — simple frozenset check | Medium — longer list, maintenance burden | Low — async confirmation flow |
| UX impact | None for current use (screenshots are .png) | None | Blocks auto-open, requires interaction |
| OWASP guidance | Recommended | Discouraged (bypass-prone) | Acceptable |
| Implementation effort | ~10 LOC | ~15 LOC | ~30 LOC + channel protocol change |

### Recommended safe extensions

Based on current OwlBear use cases (screenshots, text output) and common safe-to-open types:

| Category | Extensions | Rationale |
|----------|------------|-----------|
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.bmp` | View-only in image viewers |
| Text | `.txt`, `.md`, `.json`, `.csv`, `.log`, `.xml`, `.yaml`, `.yml`, `.toml` | View-only in text editors |
| Documents | `.html`, `.pdf` | Common output formats; viewers don't execute code |

**Excluded:** `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.vbe`, `.js`, `.wsh`, `.wsf`, `.msi`, `.scr`, `.com`, `.pif`, `.reg`, `.docm`, `.xlsm`, `.pptm` and all other executable/macro types.

### Handling blocked types

When the extension is not in the allowlist:

1. Still print the file path to output (user can manually open if desired)
2. Log a warning: `"Blocked os.startfile for unsafe extension: {suffix}"`
3. Do NOT raise an exception — the file was already delivered to the output stream

## 4. Recommendation (.90 confidence)

**Allowlist approach.** Add a module-level `frozenset` of safe suffixes. Check `Path.suffix.lower()` before calling `os.startfile`. Log a warning for blocked types. This is the simplest fix that satisfies AC and aligns with OWASP allowlist guidance.

Risk: a future legitimate file type isn't in the allowlist — mitigated by the fallback (path is always printed to output, user can open manually). Extending the allowlist is a one-line change.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement os.startfile allowlist in CLIChannel.send_file" --priority needed --tags "security,scope:cli,phase-9" --body "Add SAFE_EXTENSIONS frozenset to cli.py. Check path.suffix.lower() before os.startfile. Log warning for blocked types. Tests: safe ext opens, unsafe ext blocked+warned, case-insensitive check. See docs/startfile-allowlist-research.md"
```
