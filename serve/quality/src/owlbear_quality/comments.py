"""Language comment locations and Python logical statements for directive scope."""

from __future__ import annotations

import io
import re
import tokenize

import yaml

JS_TOKENS = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/""", re.DOTALL)


def python(source: str) -> tuple[dict[int, str], list[tuple[int, int]]]:
    """Python comment tokens and complete logical statement spans."""
    comments, statements = {}, []
    start = None
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
            if (
                token.type
                not in {
                    tokenize.COMMENT,
                    tokenize.NL,
                    tokenize.NEWLINE,
                    tokenize.INDENT,
                    tokenize.DEDENT,
                    tokenize.ENDMARKER,
                    tokenize.ENCODING,
                }
                and start is None
            ):
                start = token.start[0]
            if token.type == tokenize.NEWLINE and start is not None:
                statements.append((start, token.end[0]))
                start = None
    except tokenize.TokenError:
        # An unfinished statement has no reliable extent; the caller binds such a directive to the whole file.
        statements = []
    return comments, statements


def _yaml(source: str) -> dict[int, str]:
    scalars = [
        (source.find("\n", t.start_mark.index) if t.style in {"|", ">"} else t.start_mark.index, t.end_mark.index)
        for t in yaml.scan(source)
        if isinstance(t, yaml.ScalarToken)
    ]
    comments = {}
    offset = 0
    for number, line in enumerate(source.splitlines(keepends=True), 1):
        for match in re.finditer(r"#", line):
            at = offset + match.start()
            if not any(a <= at < b for a, b in scalars):
                comments[number] = line[match.start() :]
                break
        offset += len(line)
    return comments


def comments(path: str, source: str) -> tuple[dict[int, str], list[tuple[int, int]]]:
    """Only comments where the language defines them; other text keeps language-agnostic tool directives."""
    if path.endswith((".py", ".pyi")):
        return python(source)
    if path.endswith((".yml", ".yaml")):
        return _yaml(source), []
    if path.endswith((".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".css")):
        found = {}
        for match in JS_TOKENS.finditer(source):
            if match[0].startswith(("//", "/*")):
                first = source.count("\n", 0, match.start()) + 1
                found.update(enumerate(match[0].splitlines(), first))
        return found, []
    if path.endswith((".md", ".html")):
        found = {}
        for match in re.finditer(r"<!--.*?-->", source, re.DOTALL):
            first = source.count("\n", 0, match.start()) + 1
            found.update(enumerate(match[0].splitlines(), first))
        return found, []
    return dict(enumerate(source.splitlines(), 1)), []
