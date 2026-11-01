"""#777: PDS's pin — the tarball checked before extraction, safe extraction, the link closure and the served files."""

import base64
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from owlbear_delivery_next.pds_runs import pin
from owlbear_delivery_next.project_host import pages

SKILL = "skills/pds-knowledge-js"
AUDIT = "skills/pds-audit-deprecations-js"
BASE = {
    "package.json": b'{"name": "@porsche-design-system/components-js"}',
    "LICENSE.md": b"licence",
    "OSS_NOTICE": b"notice",
    "CHANGELOG.md": b"# Changelog\n[link](/components/link/) [npm](https://npmjs.com) [top](#top)\n",
    f"{SKILL}/SKILL.md": b"Paths are from this folder. See `tokens/` and [deprecations](references/deprecations.md).\n",
    f"{SKILL}/references/deprecations.md": b"[button](references/components/button.md)\n",  # skill-root form
    f"{SKILL}/references/components/button.md": b"[back](../deprecations.md)\n",  # file-relative form
    f"{AUDIT}/SKILL.md": b"audit\n",
    "meta/index.mjs": b"meta",
    "tokens/index.mjs": b"tokens",
    "scss/index.scss": b"scss",
    "tailwindcss/index.css": b"tw",
    "esm/index.mjs": b"export const load = () => 1;",
    "stylesheets/index.css": b"html{margin:0}\n",
    "esm/unlinked.mjs": b"not vendored",
}


def tarball(entries: dict[str, bytes], extra: list[tarfile.TarInfo] | None = None) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, body in entries.items():
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
        for info in extra or []:
            tar.addfile(info)
    return out.getvalue()


def integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()


def unpacked(entries: dict[str, bytes]) -> pin.Release:
    data = tarball(entries)
    return pin.unpack("4.11.0", integrity(data), data)


def test_a_tampered_tarball_stops_before_anything_is_extracted(monkeypatch) -> None:
    data = tarball(BASE)
    monkeypatch.setattr(pin, "extract", lambda _: pytest.fail("extracted before the integrity check"))
    with pytest.raises(pin.PinError, match="does not match npm's integrity"):
        pin.unpack("4.11.0", integrity(data + b"x"), data)


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, "dotdot"])
def test_a_link_or_an_escaping_entry_refuses_the_tarball(kind) -> None:
    info = tarfile.TarInfo("package/../x" if kind == "dotdot" else "package/skills/pds-knowledge-js/x")
    if kind != "dotdot":
        info.type, info.linkname = kind, "/etc/passwd"
    data = tarball(BASE, [info])
    with pytest.raises(pin.PinError, match=r"unsafe path|not a regular file"):
        pin.unpack("4.11.0", integrity(data), data)


def test_the_closure_follows_both_link_forms_and_skips_documentation_links() -> None:
    release = unpacked(BASE)
    assert sorted(release.tree) == sorted(set(BASE) - {"esm/index.mjs", "stylesheets/index.css", "esm/unlinked.mjs"})
    assert all(release.tree[p] == BASE[p] for p in release.tree)  # npm's bytes, unmodified


def test_two_hops_reach_exactly_the_linked_files_outside_the_seeds() -> None:
    entries = BASE | {
        "CHANGELOG.md": b"[a](docs/a.md)\n",
        "docs/a.md": b"[b](../partials/b.md)\n",
        "partials/b.md": b"leaf\n",
        "docs/unlinked.md": b"[c](c.md)\n",
    }
    tree = unpacked(entries).tree
    assert {"docs/a.md", "partials/b.md", "tokens/index.mjs", f"{SKILL}/references/components/button.md"} <= set(tree)
    assert not {"docs/unlinked.md", "esm/unlinked.mjs"} & set(tree)


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({f"{SKILL}/references/deprecations.md": b"[x](references/missing.md)"}, "names no file"),
        ({"CHANGELOG.md": b"[x](../../etc/passwd)"}, "outside the package"),
        ({"tokens/index.mjs": None}, "has no tokens"),
        ({"esm/index.mjs": None}, "has no esm/index.mjs"),
    ],
)
def test_a_missing_seed_or_a_broken_link_refuses_the_release(change, said) -> None:
    entries = {k: v for k, v in (BASE | change).items() if v is not None}
    with pytest.raises(pin.PinError, match=said):
        unpacked(entries)


def test_served_files_are_npms_bytes_after_a_header_with_one_final_newline() -> None:
    served = unpacked(BASE).served
    header, _, body = served["load.mjs"].partition(b"\n")
    assert header.startswith(f"/* {pin.NAME} {'4.11.0'} esm/index.mjs;".encode())  # split: no PDS version in the repo
    assert body == BASE["esm/index.mjs"] + b"\n"
    assert served["index.css"].partition(b"\n")[2] == BASE["stylesheets/index.css"]  # already ended with one


def test_the_pin_names_every_file_and_an_update_deletes_what_only_the_old_one_had(tmp_path: Path) -> None:
    old = unpacked(BASE).pin()
    entries = BASE | {f"{SKILL}/references/components/button.md": b"no links\n"}
    entries.pop(f"{SKILL}/references/deprecations.md")
    entries[f"{SKILL}/SKILL.md"] = b"See [button](references/components/button.md).\n"
    new = unpacked(entries)
    out = new.files(old)
    assert out[f"{pin.PREFIX}{pin.TREE}/{SKILL}/references/deprecations.md"] is None
    folder = tmp_path / "package"
    folder.mkdir()
    (folder / pin.PIN).write_bytes(out[f"{pin.PREFIX}{pin.PIN}"])
    written = pin.read(folder)
    assert (written.version, written.integrity) == ("4.11.0", new.integrity)
    kept = {p.removeprefix(pin.PREFIX) for p, b in out.items() if b is not None and not p.endswith(pin.PIN)}
    assert set(written.files) == kept
    assert written.files[f"{pin.WEB}/load.mjs"] == hashlib.sha256(new.served["load.mjs"]).hexdigest()


def test_the_repositorys_pin_verifies_and_its_closure_is_closed() -> None:
    """The 4.10.1 pin was written from npm's real tarball by ``pin.release``; its files must still be that closure."""
    root, current = pin.package(), pin.read()
    assert pin.verify() == []
    vendored = {
        p.removeprefix(f"{pin.TREE}/"): (root / p).read_bytes() for p in current.files if p.startswith(f"{pin.TREE}/")
    }
    assert sorted(pin.closure(vendored)) == sorted(vendored)
    assert max(len(line) for line in (root / pin.PIN).read_text(encoding="utf-8").splitlines()) <= 120
    assert pages.pds_version() == current.version
    first = (root / pin.WEB / "load.mjs").read_text(encoding="utf-8").split(None, 3)[2]
    assert first == current.version  # the served header names the pinned release


def test_no_pinned_file_is_ignored_by_git() -> None:
    repo = Path(pin.package()).parents[3]
    names = "\n".join(f"{pin.PREFIX}{p}" for p in pin.read().files)
    found = subprocess.run(["git", "-C", str(repo), "check-ignore", "--stdin"], input=names, capture_output=True,  # noqa: S603, S607
                           text=True, check=False)  # fmt: skip
    assert found.stdout == ""
