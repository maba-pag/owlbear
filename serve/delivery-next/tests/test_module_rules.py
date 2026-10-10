"""Code-shape rules (TD-19): modules split by use case at about 400 logic lines; fixed vocabularies stay small."""

from __future__ import annotations

import ast
import asyncio
import io
import textwrap
import tokenize
from pathlib import Path

import pytest

from owlbear_delivery_next import mcp_server, tools
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind

SRC = Path(__file__).resolve().parents[1] / "src" / "owlbear_delivery_next"
LIMIT = 400
SUBMITS = (tools.SUBMIT, tools.REVIEW, tools.RECIPE, tools.PLAN)  # one per worker role and step
_SKIP = (ast.Import, ast.ImportFrom, ast.TypeAlias, ast.Pass)
_INTERFACE_BASES = {"Protocol", "TypedDict"}
_FIELD_CALLS = {"Field", "field"}


def _bare(stmt: ast.stmt) -> bool:
    """A docstring, other bare string or ``...``."""
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, (str, type(...)))
    )


def _plain(value: ast.expr | None) -> bool:
    """No value, a literal, a dotted name or a ``Field(...)``/``field(...)`` declaration - nothing computed."""
    if value is None or isinstance(value, ast.Name | ast.Attribute):
        return True
    if isinstance(value, ast.Call):
        return getattr(value.func, "id", getattr(value.func, "attr", "")) in _FIELD_CALLS
    try:
        ast.literal_eval(value)
    except ValueError, TypeError, SyntaxError, MemoryError, RecursionError:
        return False
    return True


def _declaration(stmt: ast.stmt) -> bool:
    """An annotation or assignment whose value is plain; meaningful only in module and class bodies."""
    return isinstance(stmt, ast.AnnAssign | ast.Assign) and _plain(stmt.value)


def _type_only(stmt: ast.stmt) -> bool:
    match stmt:
        case ast.ClassDef(bases=bases) if any(
            getattr(b, "id", getattr(b, "attr", "")) in _INTERFACE_BASES for b in bases
        ):
            return True
        case ast.ClassDef(body=body):
            return all(_declaration(s) or _bare(s) or isinstance(s, ast.Pass) or _type_only(s) for s in body)
        case ast.FunctionDef(body=body) | ast.AsyncFunctionDef(body=body):
            return all(_bare(s) or isinstance(s, ast.Pass) for s in body)
    return False


def _excluded(stmt: ast.stmt, *, declarative: bool) -> bool:
    if isinstance(stmt, _SKIP) or _bare(stmt) or _type_only(stmt) or (declarative and _declaration(stmt)):
        return True
    return isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Name) and stmt.test.id == "TYPE_CHECKING"


def _blocks(node: ast.AST) -> list[list[ast.stmt]]:
    out = [getattr(node, f) for f in ("body", "orelse", "finalbody") if isinstance(getattr(node, f, None), list)]
    out += [h.body for h in getattr(node, "handlers", [])] + [c.body for c in getattr(node, "cases", [])]
    return out


def _span(stmt: ast.stmt) -> set[int]:
    start = min([stmt.lineno] + [d.lineno for d in getattr(stmt, "decorator_list", [])])
    return set(range(start, (stmt.end_lineno or stmt.lineno) + 1))


def _statement_lines(body: list[ast.stmt], *, declarative: bool = True) -> set[int]:
    """Logic lines of *body*; *declarative* bodies (module, class) exclude plain declarations."""
    lines: set[int] = set()
    for stmt in body:
        if _excluded(stmt, declarative=declarative):
            continue
        own = _span(stmt)
        for block in _blocks(stmt):
            for child in block:
                own -= _span(child)
            lines |= _statement_lines(block, declarative=isinstance(stmt, ast.ClassDef))
        lines |= own
    return lines


def _code_lines(source: str) -> set[int]:
    """Lines holding a token other than a comment or line break."""
    ignored = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    lines: set[int] = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type not in ignored:
            lines.update(range(tok.start[0], tok.end[0] + 1))
    return lines


def logic_lines(source: str) -> int:
    """Distinct source lines of statements other than imports, docstrings, type-only declarations and interfaces."""
    return len(_statement_lines(ast.parse(source).body) & _code_lines(source))


def _modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_counter_ignores_what_is_not_logic() -> None:
    snippet = textwrap.dedent(
        '''
        """Module docstring."""
        from __future__ import annotations

        import os
        from typing import TYPE_CHECKING, Protocol

        if TYPE_CHECKING:
            from pathlib import Path

        type Name = str


        class Shape(Protocol):
            def area(self) -> float: ...


        class Point:
            """A point."""

            x: int
            y: int = 0


        def f(a: int) -> int:
            """Docstring
            over two lines."""
            # a comment

            if a:
                return os.sep + str(a)
            else:
                return 0
        '''
    )
    assert logic_lines(snippet) == 5  # def, if, return, else, return


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("LIMIT = 400\nNAMES = ('a', 'b')\nKIND = Exit.DONE\n", 0),  # plain module constants
        ("TABLE = build()\nPAIRS = {k: 1 for k in 'ab'}\n", 2),  # computed module values are logic
        ("class A:\n    x: int\n    y: list[int] = Field(default_factory=list)\n    z = 'z'\n", 0),
        ("class A:\n    x: int = compute()\n", 2),  # a computed default makes the class logic
        ("class A:\n    x: int = 0\n    items = [f(i) for i in range(3)]\n", 2),  # class line, computed body line
        ("class A:\n    x: int = 0\n\n    def m(self):\n        return 1\n", 3),  # class, def, return
        ("def f():\n    x = 0\n    return x\n", 3),  # function assignments always count
        ("if flag:\n    X = 1\n", 2),  # assignments under control flow count
    ],
)
def test_counter_counts_computation_in_declarations(snippet: str, expected: int) -> None:
    assert logic_lines(snippet) == expected


@pytest.mark.parametrize("path", _modules(), ids=lambda p: str(p.relative_to(SRC)))
def test_module_logic_within_limit(path: Path) -> None:
    count = logic_lines(path.read_text(encoding="utf-8"))
    assert count <= LIMIT, f"{path.relative_to(SRC)} has {count} logic lines; split it by use case"


def test_vocabularies_stay_small() -> None:
    assert len(StepKind) <= 10
    assert len(ErrorKind) <= 15
    assert {e for e in Exit if e is not Exit.PENDING} == {Exit.DONE, Exit.RETRY, Exit.ASK, Exit.BACK, Exit.STOP}
    assert len(Exit) == 6


def test_agent_tools_stay_few() -> None:
    per_role = [{s.name for s in (submit, tools.ASK, tools.PREMISE)} for submit in SUBMITS]
    chat = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert len(set().union(*per_role) | chat) <= 6
    assert all(len(names) <= 3 for names in [*per_role, chat])
