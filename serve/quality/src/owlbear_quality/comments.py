"""Language comment locations and Python logical statements for directive scope."""

from __future__ import annotations

import io
import re
import tokenize

import yaml

# Quoted strings end on their line, so a lone quote in a regular expression cannot hide a later comment.
JS_TOKENS = re.compile(r""""(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/""", re.DOTALL)
MARKUP = re.compile(r"<!--.*?-->", re.DOTALL)


def _lines(source: str, pattern: re.Pattern[str], openers: tuple[str, ...]) -> dict[int, str]:
    """Each line's comment text; several comments on one line are kept together."""
    found: dict[int, str] = {}
    for match in pattern.finditer(source):
        if match[0].startswith(openers):
            first = source.count("\n", 0, match.start()) + 1
            for number, text in enumerate(match[0].splitlines(), first):
                found[number] = f"{found[number]} {text}" if number in found else text
    return found


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
        return _lines(source, JS_TOKENS, ("//", "/*")), []
    if path.endswith((".md", ".html")):
        return _lines(source, MARKUP, ("<!--",)), []
    return dict(enumerate(source.splitlines(), 1)), []
