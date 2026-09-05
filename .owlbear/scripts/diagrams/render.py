"""Validate an Archify architecture source and write a standalone SVG artifact."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sync import SyncError, ensure_archify  # noqa: E402

SVG_SELECTOR_RE = re.compile(
    r"(^|,)\s*(svg|:root|\[data-theme|\[data-preset|\.semantic-sigil|\.s-|\.c-|\.t-|\.a-|\.m-)"
)
COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
CLASS_ATTRIBUTE_RE = re.compile(r'\bclass="([^"]*)"')
CLASS_SELECTOR_RE = re.compile(r"(?<![A-Za-z0-9_-])\.([A-Za-z_][A-Za-z0-9_-]*)")
VIEWBOX_RE = re.compile(r'\bviewBox="0\s+0\s+(?P<width>[0-9]+(?:\.[0-9]+)?)\s+(?P<height>[0-9]+(?:\.[0-9]+)?)"')


class RenderError(RuntimeError):
    """Report a static Archify rendering failure."""


def _fail(message: str, cause: BaseException | None = None) -> None:
    """Raise one rendering error with an optional source exception."""
    if cause is None:
        raise RenderError(message)
    raise RenderError(message) from cause


def _extract_tag(content: str, tag: str) -> str:
    """Extract one complete HTML/XML element by tag name."""
    matches = list(re.finditer(rf"<{re.escape(tag)}\b", content))
    if len(matches) != 1:
        _fail(f"Expected one {tag} element, found {len(matches)}.")
    start = matches[0].start()
    opening_end = content.find(">", start)
    closing = content.find(f"</{tag}>", opening_end + 1)
    if opening_end < 0 or closing < 0:
        _fail(f"The {tag} element is incomplete.")
    return content[start : closing + len(tag) + 3]


def _consume_css_lexeme(
    css: str,
    index: int,
    quote: str | None,
    *,
    comment: bool,
) -> tuple[int, str | None, bool, bool]:
    """Consume one CSS string/comment lexeme, if one starts at *index*."""
    character = css[index]
    next_character = css[index + 1] if index + 1 < len(css) else ""
    next_index = index + 1
    next_quote = quote
    next_comment = comment
    consumed = False
    if comment:
        consumed = True
        if character == "*" and next_character == "/":
            next_index = index + 2
            next_quote = None
            next_comment = False
    elif quote is not None:
        consumed = True
        if character == "\\":
            next_index = index + 2
        elif character == quote:
            next_quote = None
    elif character == "/" and next_character == "*":
        next_index = index + 2
        next_comment = True
        consumed = True
    elif character in {"'", '"'}:
        next_quote = character
        consumed = True
    return next_index, next_quote, next_comment, consumed


def _top_level_css_rules(css: str) -> list[tuple[str, str]]:
    """Return top-level CSS rules without hoisting nested conditional rules."""
    rules: list[tuple[str, str]] = []
    depth = 0
    rule_start = 0
    rule_open = -1
    quote: str | None = None
    comment = False
    index = 0
    while index < len(css):
        next_index, quote, comment, consumed = _consume_css_lexeme(css, index, quote, comment=comment)
        if consumed:
            index = next_index
            continue
        character = css[index]
        if character == "{":
            if depth == 0:
                rule_open = index
            depth += 1
        elif character == "}":
            if depth == 0 or rule_open < 0:
                _fail("Archify stylesheet has an unmatched closing brace.")
            depth -= 1
            if depth == 0:
                header = css[rule_start:rule_open].strip()
                body = css[rule_open + 1 : index].strip()
                rules.append((header, body))
                rule_start = index + 1
                rule_open = -1
        index += 1
    if comment or quote is not None or depth != 0:
        _fail("Archify stylesheet has an unterminated comment, string, or rule.")
    return rules


def _extract_svg_css(css: str) -> str:
    """Keep only top-level CSS rules that can affect a standalone Archify SVG."""
    rules: list[str] = []
    for header, body in _top_level_css_rules(css):
        selector_header = COMMENT_RE.sub("", header).strip()
        if body and (re.match(r"^@font-face\b", selector_header) or SVG_SELECTOR_RE.search(selector_header)):
            rules.append(f"{header} {{{body}}}")
    return "\n".join(rules)


def _validate_svg_css_coverage(svg: str, css: str) -> None:
    """Reject SVG classes that have no retained stylesheet selector."""
    emitted_classes = {class_name for attribute in CLASS_ATTRIBUTE_RE.findall(svg) for class_name in attribute.split()}
    retained_selectors = set(CLASS_SELECTOR_RE.findall(css))
    missing = sorted(emitted_classes - retained_selectors)
    if missing:
        _fail(f"Archify SVG classes lack retained CSS selectors: {', '.join(missing)}.")


def _replace_attribute(opening: str, name: str, value: str) -> str:
    """Set one double-quoted root attribute."""
    pattern = re.compile(rf'\s{re.escape(name)}="[^"]*"')
    replacement = f' {name}="{value}"'
    if pattern.search(opening):
        return pattern.sub(replacement, opening, count=1)
    return f"{opening}{replacement}"


def _standalone_svg(html: str, theme: str) -> str:
    """Convert a rendered Archify HTML document into a self-contained SVG."""
    style = _extract_tag(html, "style")
    svg = _extract_tag(html, "svg")
    style_opening_end = style.find(">")
    filtered_css = _extract_svg_css(style[style_opening_end + 1 : -len("</style>")])
    if not filtered_css or "]] >".replace(" ", "") in filtered_css:
        _fail("Archify output did not contain usable static SVG CSS.")
    font_stack = (
        "svg { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', 'Noto Sans Mono CJK SC', 'PingFang SC', "
        "'Hiragino Sans GB', 'Microsoft YaHei', monospace; }"
    )
    css = f"{font_stack}\n{filtered_css}"
    _validate_svg_css_coverage(svg, css)

    svg_opening_end = svg.find(">")
    opening = svg[:svg_opening_end]
    opening = _replace_attribute(opening, "xmlns", "http://www.w3.org/2000/svg")
    opening = _replace_attribute(opening, "data-theme", theme)
    viewbox = VIEWBOX_RE.search(opening)
    if viewbox:
        opening = _replace_attribute(opening, "width", viewbox.group("width"))
        opening = _replace_attribute(opening, "height", viewbox.group("height"))
    result = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{opening}>\n"
        f'  <style type="text/css"><![CDATA[\n{css}\n  ]]></style>'
        f"{svg[svg_opening_end + 1 :]}\n"
    )
    try:
        root = ET.fromstring(result)  # noqa: S314
    except ET.ParseError as error:
        _fail(f"Extracted Archify SVG is not valid XML: {error}", error)
    if root.tag.rsplit("}", maxsplit=1)[-1] != "svg":
        _fail("Extracted Archify artifact does not have an SVG root.")
    return result


def _run_node(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one Archify command with update checks disabled."""
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "ARCHIFY_UPDATE_CHECK_DISABLED": "1"},
        )
    except OSError as error:
        _fail(f"Could not start Archify: {error}", error)


def _archify_cli(archify_root: Path) -> Path:
    """Return the required Archify CLI path."""
    cli = archify_root / "bin/archify.mjs"
    if not cli.is_file():
        _fail(f"Archify CLI not found at {cli}.")
    if shutil.which("node") is None:
        _fail("Node.js is required to render an Archify diagram.")
    return cli


def _validate(cli: Path, archify_root: Path, source: Path, quality: str) -> None:
    """Validate one source and require a successful structured receipt."""
    result = _run_node(
        [str(cli), "validate", "architecture", str(source), "--quality", quality, "--json"],
        cwd=archify_root,
    )
    if result.returncode != 0:
        detail = (result.stdout or result.stderr or "unknown validation failure").strip()
        _fail(f"Archify validation failed with exit code {result.returncode}: {detail}")
    try:
        receipt: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        _fail(f"Archify validation did not return JSON: {error}", error)
    if not isinstance(receipt, dict) or receipt.get("ok") is not True:
        _fail("Archify validation returned an unsuccessful receipt.")


def render_diagram(
    source: Path,
    output: Path,
    *,
    theme: str = "light",
    quality: str = "showcase",
    offline: bool = False,
) -> None:
    """Validate and atomically render one Archify architecture source."""
    if not source.is_file():
        _fail(f"Architecture source not found: {source}.")
    if output.resolve() == source.resolve():
        _fail("Architecture source and SVG output must be different files.")
    archify_root = ensure_archify(offline=offline)
    cli = _archify_cli(archify_root)
    _validate(cli, archify_root, source, quality)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="owlbear-archify-render-"))
    try:
        html_output = temporary_root / "candidate.html"
        result = _run_node(
            [str(cli), "render", "architecture", str(source), str(html_output), "--quality", quality],
            cwd=archify_root,
        )
        if result.returncode != 0:
            detail = (result.stdout or result.stderr or "unknown render failure").strip()
            _fail(f"Archify render failed with exit code {result.returncode}: {detail}")
        try:
            svg = _standalone_svg(html_output.read_text(encoding="utf-8"), theme)
        except (OSError, UnicodeDecodeError) as error:
            _fail(f"Could not read Archify render output: {error}", error)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as candidate:
            candidate.write(svg)
            candidate_path = Path(candidate.name)
        try:
            candidate_path.replace(output)
        finally:
            candidate_path.unlink(missing_ok=True)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the static renderer command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Archify architecture JSON source")
    parser.add_argument("--output", type=Path, required=True, help="standalone SVG output path")
    parser.add_argument("--theme", choices=("dark", "light"), default="light")
    parser.add_argument("--quality", choices=("standard", "showcase"), default="showcase")
    parser.add_argument("--offline", action="store_true", help="require the pinned release in the local cache")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the static Archify renderer."""
    arguments = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        render_diagram(
            arguments.input.resolve(),
            arguments.output.resolve(),
            theme=arguments.theme,
            quality=arguments.quality,
            offline=arguments.offline,
        )
    except (RenderError, SyncError) as error:
        print(f"Archify render failed: {error}", file=sys.stderr)
        return 1
    print(arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
