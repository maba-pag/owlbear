# Restrict Token File Permissions

> **Owning task:** #468 — Restrict token file permissions
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`save_token()` in `src/owlbear/auth/copilot.py` writes `copilot_token.json` via `Path.write_text()` with default permissions. On multi-user systems, other users can read the Copilot session token. SEC-03 from the security audit rates this HIGH (OWASP A02:2021 Cryptographic Failures).

**Question:** What is the correct cross-platform approach to write token files with restricted permissions in Python?

## 2. Sources Studied

| Source | URL | Relevance | What we learned |
|--------|-----|-----------|-----------------|
| Ansible VaultEditor.write_data() | [ansible/vault/**init**.py](https://github.com/ansible/ansible/blob/devel/lib/ansible/parsing/vault/__init__.py) | 1.0 | Gold standard: `os.umask(0o077)` → `os.open(path, O_CREAT\|O_EXCL\|O_RDWR\|O_TRUNC, 0o600)` → `os.write()` → `os.close()`. Atomic creation, no TOCTOU race. |
| Python `os.open()` docs | [docs.python.org/3/library/os.html#os.open](https://docs.python.org/3/library/os.html#os.open) | 0.9 | `os.open(path, flags, mode)` creates file with permissions atomically. On Windows, mode is largely ignored (only read-only bit matters). `os.chmod` on Windows only affects read-only flag. |
| Python `os.mkdir` 3.13 Windows ACL | [docs.python.org/3/library/os.html#os.mkdir](https://docs.python.org/3/library/os.html#os.mkdir) | 0.7 | Since Python 3.13, `os.mkdir(path, 0o700)` on Windows restricts ACL to current user + admins. Not available on 3.12. |
| HuggingFace Hub `_login.py` | [huggingface_hub/_login.py](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/_login.py) | 0.5 | Counter-example: uses bare `path.write_text(token)` — same vulnerability as OwlBear. Shows this is a common oversight. |

## 3. Analysis

### Implementation Options

| Criterion | A: `os.open()` atomic (.90) | B: `write_text` + `chmod` (.60) | C: OS keyring (.40) |
|-----------|----------------------------|--------------------------------|---------------------|
| TOCTOU safety | Atomic — no race window | Race between write and chmod | N/A (OS-managed) |
| Unix support | Full (0o600 enforced) | Works but brief exposure window | Needs `secretstorage`/`keyring` |
| Windows support | Mode ignored; relies on parent dir ACL | `chmod` only sets read-only flag | Needs `pywin32` or `keyring` |
| Dependencies | stdlib only | stdlib only | Adds `keyring` dependency |
| Complexity | Low (~10 LOC) | Low (~5 LOC) | High (~50 LOC + new dep) |
| KISS/YAGNI | Aligned | Acceptable | Over-engineered for current need |
| Prior art | Ansible (battle-tested) | Common but flawed | Docker credential helpers |

### Windows Considerations

`os.chmod()` on Windows only controls the read-only flag — it cannot restrict per-user ACLs. Two options:

| Approach | Pros | Cons |
|----------|------|------|
| Accept parent dir ACL inheritance | Zero code; `~/.owlbear/` under user profile already restricted | Not explicitly locked down if parent has permissive ACL |
| `icacls` subprocess call | Full ACL control, no extra deps | Subprocess overhead, error handling, not Pythonic |

On standard Windows setups, `C:\Users\<username>\` has ACLs restricting access to the user + SYSTEM + Administrators. Files in `~/.owlbear/` inherit these ACLs. This is sufficient for most threat models. Explicit `icacls` hardening is a defense-in-depth enhancement.

### Testing Strategy

| Platform | Verification method |
|----------|-------------------|
| Unix | `stat.S_IMODE(os.stat(path).st_mode) == 0o600` |
| Windows | `os.stat().st_mode` doesn't reflect ACLs; use `pytest.mark.skipif(sys.platform == 'win32')` for permission bits test, or parse `icacls` output if ACL hardening is implemented |

Parent directory permissions should also be tested: `stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700` on Unix.

## 4. Recommendation (.90 confidence)

**Option A: Atomic write via `os.open()` + parent directory hardening.**

Implementation pattern (from Ansible prior art):

```python
def save_token(token_data: dict[str, Any], path: Path | None = None) -> None:
    path = path or _DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(token_data).encode())
    finally:
        os.close(fd)
```

**Rationale:** Atomic creation prevents TOCTOU race. Parent dir `0o700` prevents directory listing by other users. On Windows, mode is ignored but parent dir ACL inheritance provides adequate protection. Stdlib only, no new deps, ~10 LOC delta — KISS aligned.

**Risk:** On Windows, if the parent directory has permissive inherited ACLs (non-standard setup), the file would also be permissive. Mitigation: add `icacls` hardening as a separate follow-up task (P3, nice-to-have) for defense-in-depth.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement save_token() restricted permissions (Unix)" --priority needed --status backlog --tags "security,auth,phase-4" --body "Atomic file write via os.open() with mode 0o600. Harden parent dir to 0o700 on Unix. Pattern: os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600). Test: stat.S_IMODE(os.stat(path).st_mode) == 0o600. See docs/restrict-token-permissions-research.md. Depends on #468."

kanban\kanban-md.exe create "Windows ACL hardening for token file (defense-in-depth)" --priority nice-to-have --status ideation --tags "security,auth,windows" --body "Optional defense-in-depth: call icacls to restrict token file ACL to current user on Windows. Low priority — default home dir ACLs already restrict access on standard setups. See docs/restrict-token-permissions-research.md."
```

**Note:** Task #468 itself should be updated to `backlog` status and edited with the research findings. The implementation task above can be merged into #468 if preferred.
