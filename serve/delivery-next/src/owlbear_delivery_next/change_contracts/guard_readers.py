"""Commands in an interpreter's inline code: python's -c, node's -e, perl's -e, or code on standard input.

The guard reads no program, but its string literals often hold the commands it runs: os.system("git push -f"),
subprocess.run(["git", "commit", "--no-verify"]). Each literal, and each list literal's strings joined by spaces, is
read as shell text. A script file an interpreter runs stays unread.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import shell_parse, shell_programs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.local_system.shell_parse import Command

_INTERPRETER = re.compile(r"(python)[\d.]*|(node)|(perl)")
_CODE = {  # its code option, alone or closing a cluster of flags, the code attached or in the next word
    "python": re.compile(r"-[bBdEhiIOPqsSuvVx]*c(.*)", re.DOTALL),
    "node": re.compile(r"-p?e|-p|--(?:eval|print)(?:=(.*))?", re.DOTALL),
    "perl": re.compile(r"-[acnlpstTuUwW]*[eE](.*)", re.DOTALL),
}
_VALUED = {  # options whose value is the next word
    "python": {"-W", "-X"},
    "node": {"-r", "--require", "--import", "--loader", "-C", "--conditions", "--input-type"},
    "perl": {"-I"},
}
_STRING = re.compile(r"""(['"`])((?:\\.|(?!\1).)*)\1""", re.DOTALL)  # a quoted literal, its escapes kept
_LIST = re.compile(r"\[([^\[\]]*)\]")  # a list or array literal without nested ones


def code(command: Command, words: Sequence[str]) -> str | None:
    """The inline code the interpreter in *words* runs: its code option's value, or its here-document or -string.

    None for a script file or module, which stays unread.
    """
    m = _INTERPRETER.fullmatch(shell_programs.name(words[0]))
    if not m:
        return None
    language = next(filter(None, m.groups()))
    i = 1
    while i < len(words) and words[i].startswith("-") and words[i] not in {"-", "--"}:
        if given := _CODE[language].fullmatch(words[i]):
            return given[1] or (words[i + 1] if i + 1 < len(words) else None)
        i += 2 if words[i] in _VALUED[language] else 1
    i += i < len(words) and words[i] == "--"
    stdin = command.stdin()
    if (i < len(words) and words[i] != "-") or stdin is None or stdin.kind not in {"here", "string"}:
        return None
    return stdin.word


def commands(text: str) -> list[list[str]]:
    """The shell commands the code's literals may hold: each string, and each list's strings joined by spaces."""
    texts = [m[2] for m in _STRING.finditer(text)]
    texts += [" ".join(m[2] for m in _STRING.finditer(lst[1])) for lst in _LIST.finditer(text)]
    found: list[list[str]] = []
    for literal in texts:
        try:
            found += [c.words for c in shell_parse.parse(literal)]
        except ValueError:
            continue
    return found
