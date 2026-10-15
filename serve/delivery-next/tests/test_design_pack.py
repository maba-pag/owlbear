"""TD-76/TD-77: the design pack's pins and install, the detector's three scans, and the UI builder's design skill."""

import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import design_pack, detector, preload, sdk_adapter
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.models import StepKind

ENGINE_JSON = [
    {"antipattern": "side-tab", "category": "slop", "severity": "warning", "name": "Side-tab", "file": "a.html",
     "line": 3, "snippet": "border-left: 4px"},
    {"antipattern": "em-dash-overuse", "category": "slop", "severity": "advisory", "name": "Em-dash", "file": "a.html",
     "line": 0, "snippet": ""},
]  # fmt: skip


def fake_engine(tmp_path: Path, code: int, out: str, sleep: float = 0) -> design_pack.Installed:
    script = tmp_path / "impeccable"
    script.write_text(f"#!/bin/sh\nenv > {tmp_path / 'env.txt'}\necho $* > {tmp_path / 'args.txt'}\n"
                      f"sleep {sleep}\ncat <<'EOF'\n{out}\nEOF\nexit {code}\n")  # fmt: skip
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    return design_pack.Installed(engine=script, engine_sha256=digest, bundle="window.x = 1")


def pinned(monkeypatch, engine: bytes, bundle: bytes) -> None:
    pins = design_pack.manifest()
    pins["engine"][design_pack.platform_name()] = hashlib.sha256(engine).hexdigest()
    pins["bundle"]["sha256"] = hashlib.sha256(bundle).hexdigest()
    monkeypatch.setattr(design_pack, "manifest", lambda: json.loads(json.dumps(pins)))


def test_the_pack_pins_every_platform_its_skills_and_the_licence_text() -> None:
    pins = design_pack.manifest()
    assert set(pins["engine"]) == {"darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64"}
    assert all(len(d) == 64 and int(d, 16) >= 0 for d in [*pins["engine"].values(), pins["bundle"]["sha256"]])
    assert preload.missing("builder", ui=True) == []
    assert all(preload._named(name) for name in pins["skills"])  # noqa: SLF001
    licence = preload.directory() / "IMPECCABLE-LICENSE"
    assert hashlib.sha256(licence.read_bytes()).hexdigest() == pins["licence"]["IMPECCABLE-LICENSE"]
    assert pins["upstream"]["commit"] in (preload.directory() / "NOTICE.md").read_text()


def test_the_pack_identity_covers_its_skills(monkeypatch) -> None:
    before = design_pack.identity()
    assert before.startswith(design_pack.manifest()["pack"] + "+")
    text = preload.text
    monkeypatch.setattr(preload, "text", lambda name: text(name) + "changed")
    assert design_pack.identity() != before


def test_install_keeps_only_files_that_match_their_digests(monkeypatch) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return b"engine" if "releases" in url else b"bundle"

    found = design_pack.install(fetch)
    assert (found.engine.read_bytes(), found.bundle) == (b"engine", "bundle")
    assert os.access(found.engine, os.X_OK)
    assert design_pack.folder().is_relative_to(Path(os.environ["OWLBEAR_HOME"]))
    assert design_pack.folder().stat().st_mode & 0o077 == 0
    design_pack.install(fetch)
    assert len(fetched) == 2  # nothing is downloaded again
    (design_pack.folder() / design_pack.BUNDLE).write_bytes(b"tampered")
    assert design_pack.installed() is None
    assert "not installed" in design_pack.status()
    found.engine.write_bytes(b"swapped after verification")
    with pytest.raises(design_pack.PackError, match="no longer matches"):
        found.verified_engine()


def test_the_pack_is_kept_only_in_a_private_folder(monkeypatch, tmp_path) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(design_pack, "folder", lambda _pins=None: shared / "pack")
    shared.chmod(0o777)
    with pytest.raises(design_pack.PackError, match="private folder"):
        design_pack.install(lambda url: b"engine" if "releases" in url else b"bundle")
    shared.chmod(0o755)
    assert design_pack.install(lambda url: b"engine" if "releases" in url else b"bundle").bundle == "bundle"
    assert [p.name for p in (shared / "pack").iterdir() if p.name.startswith(".")] == []


def test_a_download_that_does_not_match_is_refused_and_not_kept(monkeypatch) -> None:
    pinned(monkeypatch, b"engine", b"bundle")
    with pytest.raises(design_pack.PackError, match="does not match"):
        design_pack.install(lambda _url: b"something else")
    assert not (design_pack.folder() / design_pack.ENGINE).exists()

    def offline(_url: str) -> bytes:
        msg = "offline"
        raise OSError(msg)

    with pytest.raises(design_pack.PackError, match="cannot download"):
        design_pack.install(offline)


def test_an_unsupported_machine_is_named(monkeypatch) -> None:
    monkeypatch.setattr(design_pack.platform, "system", lambda: "Plan9")
    with pytest.raises(design_pack.PackError, match="no engine for Plan9"):
        design_pack.platform_name()
    assert "no engine for Plan9" in design_pack.status()


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
    pack = design_pack.Installed(tmp_path / "e", "0" * 64, "window.detector = 1")
    found = detector.scan_page(page, pack)
    assert [(f.rule, f.where) for f in found] == [("gradient-text", "h1")]
    assert calls[0] == "window.__IMPECCABLE_CONFIG__ = {autoScan: false}"
    assert calls[1] == "script window.detector = 1"  # the verified text itself, never a path

    def refuse(_js: str) -> None:
        msg = "detector core unavailable: wasm-unsafe-eval"
        raise RuntimeError(msg)

    with pytest.raises(detector.DetectorError, match="refused the design detector"):
        detector.scan_page(SimpleNamespace(evaluate=refuse, add_script_tag=print), pack)


def test_a_ui_change_gives_its_builder_the_design_skill_in_both_runtimes() -> None:
    assert preload.required("builder", ui=True) == (*preload.REQUIRED["builder"], "owlbear-ui-design")
    assert preload.required("reviewer", ui=True) == preload.REQUIRED["reviewer"]
    assert "owlbear-ui-design" in sdk_adapter.agent(StepKind.BUILD, ui=True)["skills"]
    assert "owlbear-ui-design" not in sdk_adapter.agent(StepKind.BUILD)["skills"]
    placed = [rel for rel, _render in wf.skills("builder", ui=True)]
    assert wf.skill_path("owlbear-ui-design") in placed
    assert "owlbear-ui-design]" in wf.agent("builder", Path("/i.json"), ui=True)(None)
