---
id: 527
title: Restrict os.startfile to safe file types in CLI channel
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:34.010185+01:00
updated: 2026-03-07T00:20:50.3173203+01:00
started: 2026-03-07T00:16:20.5668189+01:00
tags:
    - audit
    - security
    - scope:cli
class: standard
---

SEC-16: send_file() calls os.startfile(path) on Windows. If LLM controls path, could open executables or macro documents.
AC: only safe file types opened automatically.

Research complete: allowlist approach (.90 confidence). Add SAFE_EXTENSIONS frozenset to cli.py, check path.suffix.lower() before os.startfile, log warning for blocked types. See docs/research/startfile-allowlist.md

Research checklist:
1. Theoretical validity: N/A - straightforward allow-list of file suffixes
2. Prior art: OWASP allowlist guidance, Python os.startfile docs, Bandit S606 rule
3. Technical feasibility: N/A - trivial frozenset + suffix check (~10 LOC)
