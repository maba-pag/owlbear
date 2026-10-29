"""TD-76/TD-77: Impeccable's pins and install, the detector's three scans, and the UI builder's design skill."""

import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.commands import dispatch
from owlbear_delivery_next.impeccable import detector, pack_files
from owlbear_delivery_next.local_system import local_home, preload
from owlbear_delivery_next.runtimes import sdk_adapter

ENGINE_JSON = [
    {"antipattern": "side-tab", "category": "slop", "severity": "warning", "name": "Side-tab", "file": "a.html",
     "line": 3, "snippet": "border-left: 4px"},
    {"antipattern": "em-dash-overuse", "category": "slop", "severity": "advisory", "name": "Em-dash", "file": "a.html",
     "line": 0, "snippet": ""},
]  # fmt: skip


def fake_engine(tmp_path: Path, code: int, out: str, sleep: float = 0) -> pack_files.Installed:
    script = tmp_path / "impeccable"
    script.write_text(f"#!/bin/sh\nenv > {tmp_path / 'env.txt'}\necho $* > {tmp_path / 'args.txt'}\n"
                      f"sleep {sleep}\ncat <<'EOF'\n{out}\nEOF\nexit {code}\n")  # fmt: skip
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    return pack_files.Installed(engine=script, engine_sha256=digest, bundle="window.x = 1")


def pinned(monkeypatch, engine: bytes, bundle: bytes) -> None:
    pins = pack_files.manifest()
    pins["engine"][pack_files.platform_name()] = hashlib.sha256(engine).hexdigest()
    pins["bundle"]["sha256"] = hashlib.sha256(bundle).hexdigest()
    monkeypatch.setattr(pack_files, "manifest", lambda: json.loads(json.dumps(pins)))


def test_the_pack_pins_every_platform_its_skills_and_the_licence_text() -> None:
    pins = pack_files.manifest()
    assert set(pins["engine"]) == {"darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64"}
    assert all(len(d) == 64 and int(d, 16) >= 0 for d in [*pins["engine"].values(), pins["bundle"]["sha256"]])
    assert preload.missing("builder", ui=True) == []
    assert all(preload._named(name) for name in pins["skills"])  # noqa: SLF001
    licence = preload.directory() / "IMPECCABLE-LICENSE"
    assert hashlib.sha256(licence.read_bytes()).hexdigest() == pins["licence"]["IMPECCABLE-LICENSE"]
    assert pins["upstream"]["commit"] in (preload.directory() / "NOTICE.md").read_text()


def test_the_pack_identity_covers_its_skills(monkeypatch, tmp_path) -> None:
    before = pack_files.identity()
    assert before.startswith(pack_files.manifest()["pack"] + "+")
    for name in pack_files.manifest()["skills"]:  # a candidate's own skill folder, as the package holds it
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(preload.text(name))
    assert pack_files.identity(skills=tmp_path) == before
    (tmp_path / name / "SKILL.md").write_text(preload.text(name) + "edited by the updater")
    assert pack_files.identity(skills=tmp_path) != before
    text = preload.text
    monkeypatch.setattr(preload, "text", lambda name, folder=None: text(name, folder) + "changed")
    assert pack_files.identity() != before


def test_install_keeps_only_files_that_match_their_digests(monkeypatch) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return b"engine" if "releases" in url else b"bundle"

    found = pack_files.install(fetch)
    assert (found.engine.read_bytes(), found.bundle) == (b"engine", "bundle")
    assert os.access(found.engine, os.X_OK)
    assert pack_files.folder().is_relative_to(local_home.root())
    assert pack_files.folder().stat().st_mode & 0o077 == 0
    pack_files.install(fetch)
    assert len(fetched) == 2  # nothing is downloaded again
    (pack_files.folder() / pack_files.BUNDLE).write_bytes(b"tampered")
    assert pack_files.installed() is None
    assert "not installed" in pack_files.status()
    found.engine.write_bytes(b"swapped after verification")
    with pytest.raises(pack_files.PackError, match="no longer matches"):
        found.verified_engine()


def test_an_older_runtime_installs_impeccable_through_the_hidden_design_pack_command(monkeypatch) -> None:
    """D-01M63CB9WFXBV3TDXGG295QCST: a version from before the rename installs the new one's pack by its old name."""
    pinned(monkeypatch, b"engine", b"bundle")
    monkeypatch.setattr(pack_files, "fetch", lambda url: b"engine" if "releases" in url else b"bundle")
    assert pack_files.installed() is None

    assert dispatch.main(["design-pack", "--install"]) == 0  # what the older runtime's versions.pack runs

    assert pack_files.installed() is not None


def test_the_pack_is_kept_only_in_a_private_folder(monkeypatch, tmp_path) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(pack_files, "folder", lambda _pins=None, **_how: shared / "pack")
    shared.chmod(0o777)
    with pytest.raises(pack_files.PackError, match="private folder"):
        pack_files.install(lambda url: b"engine" if "releases" in url else b"bundle")
    shared.chmod(0o755)
    assert pack_files.install(lambda url: b"engine" if "releases" in url else b"bundle").bundle == "bundle"
    assert [p.name for p in (shared / "pack").iterdir() if p.name.startswith(".")] == []


def test_a_download_that_does_not_match_is_refused_and_not_kept(monkeypatch) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    with pytest.raises(pack_files.PackError, match="does not match"):
        pack_files.install(lambda _url: b"something else")
    assert not (pack_files.folder() / pack_files.ENGINE).exists()

    def offline(_url: str) -> bytes:
        msg = "offline"
        raise OSError(msg)

    with pytest.raises(pack_files.PackError, match="cannot download"):
        pack_files.install(offline)


def test_an_unsupported_machine_is_named(monkeypatch) -> None:
    monkeypatch.setattr(pack_files.platform, "system", lambda: "Plan9")
    with pytest.raises(pack_files.PackError, match="no engine for Plan9"):
        pack_files.platform_name()
    assert "no engine for Plan9" in pack_files.status()


def test_the_engine_answers_findings_quietly(tmp_path) -> None:
    pack = fake_engine(tmp_path, 2, json.dumps(ENGINE_JSON))
    found = detector.scan_url(pack, "http://127.0.0.1:5173/", 1920, "/bin/chromium", tmp_path)
    assert [(f.rule, f.advisory, f.where) for f in found] == [
        ("side-tab", False, "a.html:3"),
        ("em-dash-overuse", True, "a.html"),
    ]
    assert (tmp_path / "args.txt").read_text().split() == [
        "detect", "--json", "--no-config", "--viewport", "1920x800", "http://127.0.0.1:5173/"
    ]  # fmt: skip
    env = (tmp_path / "env.txt").read_text()
    assert all(f"{k}={v}" in env for k, v in detector.QUIET.items())
    assert "IMPECCABLE_BROWSER=/bin/chromium" in env
    assert detector.scan_source(fake_engine(tmp_path, 0, "[]"), [tmp_path / "a.html"], tmp_path) == []
    assert detector.scan_source(pack, [], tmp_path) == []


@pytest.mark.parametrize(
    ("code", "out", "why"),
    [
        (1, "[]", "failed \\(1\\)"),
        (2, "not json", "not JSON"),
        (0, "", "not JSON"),
        (0, "{}", "not a list"),
        (2, "[null]", "not a list"),
    ],
)
def test_a_scan_that_did_not_complete_is_never_clean(tmp_path, code, out, why) -> None:
    with pytest.raises(detector.DetectorError, match=why):
        detector.scan_source(fake_engine(tmp_path, code, out), [tmp_path / "a.html"], tmp_path)


def test_only_web_addresses_and_absolute_paths_reach_the_engine(tmp_path) -> None:
    pack = fake_engine(tmp_path, 0, "[]")
    with pytest.raises(detector.DetectorError, match="not a web address"):
        detector.scan_url(pack, "--no-advisory", 1280, "/bin/chromium", tmp_path)
    with pytest.raises(detector.DetectorError, match="absolute paths"):
        detector.scan_source(pack, [Path("-x.html")], tmp_path)
    assert not (tmp_path / "args.txt").exists()


def test_a_scan_that_hangs_ends(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(detector, "SECONDS", 0.2)
    with pytest.raises(detector.DetectorError, match="did not finish"):
        detector.scan_source(fake_engine(tmp_path, 0, "[]", sleep=5), [tmp_path / "a.html"], tmp_path)


def test_the_in_page_detector_runs_without_overlay_and_a_refusing_page_is_an_error(tmp_path) -> None:
    calls: list[str] = []
    groups = [{"selector": "h1", "findings": [{"type": "gradient-text", "category": "slop", "advisory": False}]}]
    page = SimpleNamespace(
        evaluate=lambda js, *arg: calls.append(js) or (groups if (js, arg) == (detector.PAGE, (60_000,)) else None),
        add_script_tag=lambda content: calls.append(f"script {content}"),
    )
    pack = pack_files.Installed(tmp_path / "e", "0" * 64, "window.detector = 1")
    found = detector.scan_page(page, pack)
    assert [(f.rule, f.where) for f in found] == [("gradient-text", "h1")]
    assert calls[0] == "window.__IMPECCABLE_CONFIG__ = {autoScan: false}"
    assert calls[1] == "script window.detector = 1"  # the verified text itself, never a path

    def refuse(_js: str) -> None:
        msg = "detector core unavailable: wasm-unsafe-eval"
        raise RuntimeError(msg)

    with pytest.raises(detector.DetectorError, match="refused the design detector"):
        detector.scan_page(SimpleNamespace(evaluate=refuse, add_script_tag=print), pack)


def test_a_ui_change_gives_its_builder_the_design_skill() -> None:
    assert preload.required("builder", ui=True) == (*preload.REQUIRED["builder"], "owlbear-interface-design")
    assert preload.required("reviewer", ui=True) == preload.REQUIRED["reviewer"]
    assert "owlbear-interface-design" in sdk_adapter.agent(StepKind.BUILD, ui=True)["skills"]
    assert "owlbear-interface-design" not in sdk_adapter.agent(StepKind.BUILD)["skills"]
