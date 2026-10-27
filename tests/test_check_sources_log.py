from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / ".owlbear/scripts/check_sources_log.py"
_SPEC = importlib.util.spec_from_file_location("check_sources_log", _SCRIPT)
assert _SPEC is not None
assert _SPEC.loader is not None
_CHECKER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECKER)

_HEADER = "| Source | URL | Licence | What | Where Used |\n| --- | --- | --- | --- | --- |\n"
_VALID = "| Lib | <https://example.org/lib> | MIT | A parser | `src/parser.py` |\n"


def _code_root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/parser.py").write_text("")
    return tmp_path


def test_accepts_a_valid_row(tmp_path: Path) -> None:
    assert _CHECKER.check_sources_log("# Sources\n\n" + _HEADER + _VALID, _code_root(tmp_path)) == []


def test_rejects_a_malformed_row(tmp_path: Path) -> None:
    problems = _CHECKER.check_sources_log(_HEADER + "| Lib | <https://example.org/lib> | MIT |\n", _code_root(tmp_path))
    assert len(problems) == 1
    assert "5 cells" in problems[0]


def test_rejects_an_empty_required_field(tmp_path: Path) -> None:
    row = "| Lib | <https://example.org/lib> |  | A parser | `src/parser.py` |\n"
    problems = _CHECKER.check_sources_log(_HEADER + row, _code_root(tmp_path))
    assert len(problems) == 1
    assert "must not be empty" in problems[0]


def test_rejects_a_url_that_is_not_https(tmp_path: Path) -> None:
    row = "| Lib | <http://example.org/lib> | MIT | A parser | `src/parser.py` |\n"
    problems = _CHECKER.check_sources_log(_HEADER + row, _code_root(tmp_path))
    assert len(problems) == 1
    assert "<https://" in problems[0]


def test_rejects_a_path_that_does_not_exist(tmp_path: Path) -> None:
    row = "| Lib | <https://example.org/lib> | MIT | A parser | `src/parser.py`, `src/gone.py` |\n"
    problems = _CHECKER.check_sources_log(_HEADER + row, _code_root(tmp_path))
    assert len(problems) == 1
    assert "src/gone.py does not exist" in problems[0]


def test_rejects_a_row_without_a_path(tmp_path: Path) -> None:
    row = "| Lib | <https://example.org/lib> | MIT | A parser | the parser |\n"
    problems = _CHECKER.check_sources_log(_HEADER + row, _code_root(tmp_path))
    assert len(problems) == 1
    assert "no backticked path" in problems[0]


def test_rejects_a_log_without_its_table(tmp_path: Path) -> None:
    assert _CHECKER.check_sources_log("# Sources\n", _code_root(tmp_path)) != []


def test_main_exits_non_zero_on_a_problem(tmp_path: Path) -> None:
    log = tmp_path / "overview.md"
    log.write_text(_HEADER + "| Lib | <https://example.org/lib> | MIT | A parser | `src/gone.py` |\n")
    assert _CHECKER.main([str(log), str(_code_root(tmp_path))]) == 1
    log.write_text(_HEADER + _VALID)
    assert _CHECKER.main([str(log), str(tmp_path)]) == 0
