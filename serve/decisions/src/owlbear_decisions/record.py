"""Parse the hand-edited decision record into topics, in-force bullets, rows and the owner's words."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

ORIGINS = ("decided", "approved", "autonomous")
STANDALONE = "Standalone"
UNKNOWN = "?"
_TD = re.compile(r"\bTD-\d+\b")
_ROW_TOKEN = re.compile(r"\b(decided|approved|autonomous)\b|\b(TD-\d+)\b")
_REFERENCE = re.compile(r"\[([^\[\]]+)\](?!\()")
_REFERENCE_START = re.compile(r"^(TD-\d+|R\d+|Q\d+|C-\d+)\b")
# every token of a reference bracket; any other bracket is the statement's own text and stays verbatim
_REFERENCE_TOKEN = re.compile(r"^(TD-\d+|R\d+|Q\d+|C-\d+|decided|approved|autonomous|partly|report \d{4}-\d{2}-\d{2})$")
_SECTION = re.compile(r"^\*\*([A-Z][A-Za-z' ]+):\*\*\s*(.*)$")
_HEADING = re.compile(r"^## (?:(C-\d+) (.+)|Standalone decisions)\s*$")
_WORDS = re.compile(r"^(TD-\d+), (\d{4}-\d{2}-\d{2}): (.+)$")
_QUOTED = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
IN_FORCE = "in force"
_KNOWN = frozenset({IN_FORCE, "rows", "owner's words", "replaced", "spent", "open"})


@dataclass
class Item:
    """One bullet or section line, continuation lines joined."""

    text: str
    line: int


@dataclass(frozen=True)
class Reference:
    """A bracket of row references, e.g. `[TD-17, TD-402, decided; TD-266]`."""

    raw: str
    cited: tuple[str, ...]
    own: tuple[str, ...] = ()
    origin: str = ""
    qualifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Bullet:
    """An in-force line of a topic."""

    text: str
    line: int
    references: tuple[Reference, ...]
    statement: str

    @property
    def cited(self) -> tuple[str, ...]:
        """Every TD the bullet's brackets cite, first mention first."""
        return tuple(dict.fromkeys(td for ref in self.references for td in ref.cited))


@dataclass(frozen=True)
class Words:
    """One line of a topic's owner's words."""

    alias: str
    date: str
    text: str
    line: int


@dataclass
class Topic:
    """One `## ` section of the record."""

    key: str
    title: str
    line: int
    rows: dict[str, str] = field(default_factory=dict)
    rows_note: list[str] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)
    words: list[Words] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    spent: list[str] = field(default_factory=list)
    open: list[str] = field(default_factory=list)
    unparsed: list[Item] = field(default_factory=list)

    @property
    def heading(self) -> str:
        """`C-nn Title`, or `Standalone`."""
        return f"{self.key} {self.title}" if self.key != STANDALONE else STANDALONE


def _sections(lines: list[tuple[int, str]]) -> tuple[dict[str, list[Item]], list[Item]]:
    sections: dict[str, list[Item]] = defaultdict(list)
    stray: list[Item] = []
    name, current = IN_FORCE, None
    for number, line in lines:
        if match := _SECTION.match(line):
            name, current = match.group(1).lower(), None
            if match.group(2):
                current = Item(match.group(2), number)
                sections[name].append(current)
        elif not line.strip():
            current = None
            name = IN_FORCE if name == "rows" else name
        elif line.startswith("- "):
            current = Item(line[2:].strip(), number)
            sections[name].append(current)
        elif current is not None:
            current.text = f"{current.text} {line.strip()}"
        else:
            stray.append(Item(line.strip(), number))
    return sections, stray


def _rows(text: str) -> tuple[dict[str, str], list[str]]:
    rows: dict[str, str] = {}
    origin = ""
    for match in _ROW_TOKEN.finditer(text):
        if match.group(1):
            origin = match.group(1)
        elif origin:
            rows.setdefault(match.group(2), origin)
    notes = [part.strip(" .") for part in text.split(";") if not _TD.search(part)]
    return rows, notes


def _reference(raw: str) -> Reference:
    cited = tuple(_TD.findall(raw))
    for part in raw.split(";"):
        tokens = [token.strip() for token in part.split(",")]
        origins = [token for token in tokens if token in ORIGINS]
        if origins:
            own = tuple(token for token in tokens if _TD.fullmatch(token))
            qualifiers = tuple(token for token in tokens if token not in ORIGINS and not _TD.fullmatch(token))
            return Reference(raw, cited, own, origins[0], qualifiers)
    return Reference(raw, cited)


def _is_reference(content: str) -> bool:
    tokens = [token.strip() for part in content.split(";") for token in part.split(",")]
    return bool(_REFERENCE_START.match(content)) and all(_REFERENCE_TOKEN.match(token) for token in tokens)


def statement_of(text: str) -> str:
    """The bullet without its reference brackets, whitespace joined."""
    bare = _REFERENCE.sub(lambda m: "" if _is_reference(m.group(1)) else m.group(0), text)
    bare = re.sub(r"\s+", " ", bare)
    return re.sub(r"\s+([.,;:])", r"\1", bare).strip()


def _bullet(item: Item) -> Bullet:
    references = tuple(_reference(m.group(1)) for m in _REFERENCE.finditer(item.text) if _is_reference(m.group(1)))
    return Bullet(item.text, item.line, references, statement_of(item.text))


def _words(item: Item) -> Words | None:
    if not (match := _WORDS.match(item.text)):
        return None
    text = match.group(3).strip()
    if quoted := _QUOTED.match(text):
        text = quoted.group(1)
    return Words(match.group(1), match.group(2), text.replace('\\"', '"'), item.line)


def _replaced(text: str) -> list[str]:
    return [td for part in text.split(";") for td in _TD.findall(part.split(" by ", 1)[0])]


def _topic(key: str, title: str, line: int, body: list[tuple[int, str]]) -> Topic:
    topic = Topic(key, title, line)
    if key == UNKNOWN:
        topic.unparsed = [Item(text, number) for number, text in body if text.strip()]
        return topic
    sections, stray = _sections(body)
    for item in sections.get("rows", []):
        rows, notes = _rows(item.text)
        topic.rows.update(rows)
        topic.rows_note.extend(notes)
    topic.bullets = [_bullet(item) for item in sections.get(IN_FORCE, [])]
    for bullet in topic.bullets:
        for ref in bullet.references:
            topic.rows.update({td: ref.origin for td in ref.own if td not in topic.rows})
    for item in sections.get("owner's words", []):
        if (words := _words(item)) is None:
            topic.unparsed.append(item)
        else:
            topic.words.append(words)
    topic.replaced = [td for item in sections.get("replaced", []) for td in _replaced(item.text)]
    topic.spent = [td for item in sections.get("spent", []) for td in _TD.findall(item.text)]
    topic.open = [td for item in sections.get("open", []) for td in _TD.findall(item.text)]
    unknown = (item for name, items in sections.items() if name not in _KNOWN for item in items)
    topic.unparsed.extend(Item(f"(unknown section) {item.text}", item.line) for item in unknown)
    topic.unparsed.extend(stray)
    return topic


def parse_record(text: str) -> list[Topic]:
    """Every `## C-nn` topic and the standalone section; lines before the first heading are ignored."""
    topics: list[Topic] = []
    heading: tuple[str, str, int] | None = None
    body: list[tuple[int, str]] = []
    for number, line in enumerate([*text.splitlines(), "## end"], start=1):
        if line.startswith("## "):
            if heading is not None:
                topics.append(_topic(*heading, body))
            match = _HEADING.match(line)
            heading = (
                (match.group(1) or STANDALONE, match.group(2) or "decisions", number)
                if match
                else (UNKNOWN, line[3:].strip(), number)
            )
            body = []
        elif heading is not None:
            body.append((number, line))
    return topics
