"""The guard's walk through one shell text: the scripts its shells run, and the input it can't read.

Each command is read in order, as the shell runs it. A shell's -c script, its script file, its startup files and a
here-document or here-string it reads are judged like the text itself; so are a sourced file, eval's words and a shell
script run by path. What can't be read is refused: a shell reading input from another program, a command or script
built at run time, a file missing or not text, a script run after an earlier write in the same command (the file read
now may not be the one that runs) and a relative path once the folder is unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import shell_programs
from owlbear_delivery_next.local_system.shell_parse import Word

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from owlbear_delivery_next.local_system.shell_parse import Command
    from owlbear_delivery_next.local_system.shell_programs import Run

_DEVICE_STDIN = frozenset({"/dev/stdin", "/dev/fd/0"})  # a path naming the shell's own input
_STDIN = _DEVICE_STDIN | {"-"}  # as a shell's script operand; source reads a file named -
_FOLDER = frozenset({"cd", "pushd", "popd"})
_STARTUP = ("BASH_ENV", "ENV")  # variables naming a file a shell runs before its script
_DECLARE = frozenset({"declare", "typeset", "readonly", "local"})
_SHOWN = 60  # characters of a script built at run time shown in a reason


@dataclass
class Effects:
    """What earlier text did that outlives the shell that did it."""

    wrote: bool = False  # it wrote, so a file read now may not be the one that runs


@dataclass
class State:
    """Where one shell stands while the guard reads its text in order."""

    at: Path | None  # its folder; None once a change of folder can't be followed
    effects: Effects = field(default_factory=Effects)
    stdin_plain: bool = True  # its standard input is the step's own: no pipe and no redirection
    exec_in: bool = False  # an exec redirected its standard input
    startup: dict[str, Word | None] = field(default_factory=dict)  # BASH_ENV, ENV as set; None when not followable
    current: int = 0  # above 0 while sourced or eval text runs in this shell

    def child(self, *, plain: bool) -> State:
        """The state a shell this one starts begins with: writes are shared, folder and variables copied."""
        return State(self.at, self.effects, plain, startup=dict(self.startup))

    def plain(self) -> bool:
        """Whether this shell's standard input is still the step's own."""
        return self.stdin_plain and not self.exec_in


@dataclass(frozen=True)
class Walk:
    """The walk through one text: its name in reasons, its depth, and how nested text and writes are judged."""

    name: str
    depth: int
    judge: Callable[[str, int, State, str], str | None]  # text, depth, state, its name in reasons -> a refusal
    writes: Callable[[Command], bool]
    bypass: Callable[[str, Run], str | None]  # the refusal of a run's environment that turns hooks or signing off

    def commands(self, commands: Sequence[Command], state: State) -> str | None:
        """Read *commands* in order and return the first refusal."""
        for command in commands:
            self._environment(command, state)
            if reason := self._command(command, state):
                return reason
            if self.writes(command):
                state.effects.wrote = True
        return None

    def _command(self, command: Command, state: State) -> str | None:
        """Each program a command runs, in order: its launchers by path, then the program; a write marks the rest."""
        head = next((w for w in command.words if not shell_programs.ASSIGNMENT.match(w)), None)
        runs = shell_programs.runs(command.words)
        checked: set[str] = set()
        for run in runs if runs or head is None else [shell_programs.Run(words=[head])]:
            for word in (*run.launchers, run.words[0]):  # a launcher by path is checked even with nothing to run
                if "/" in word and word not in checked and not _built(run, word):
                    checked.add(word)
                    if reason := self._by_path(command, run, word, state):
                        return reason
            if runs and (reason := self._run(command, run, state)):
                return reason
            if self.writes(replace(command, words=run.words, raw=" ".join(run.words))):  # find's next action sees it
                state.effects.wrote = True
        return None

    def _environment(self, command: Command, state: State) -> None:
        """Note startup variables a command sets for later shells, and an exec that redirects this shell's input."""
        words = command.words
        i = shell_programs.builtin(words)  # then export ..., command -p -- exec ...: the builtin itself
        first = words[i] if i < len(words) else None
        if first is None or first == "export":
            assigned = shell_programs.assignments(words[:i] if first is None else words[i + 1 :])
            for key in _STARTUP:
                if key in assigned:
                    state.startup[key] = assigned[key] if command.top_level else None
        elif first in _DECLARE:
            state.startup |= {k: None for k in _STARTUP if any(w.partition("=")[0] == k for w in words[i + 1 :])}
        if first == "exec" and command.stdin() is not None:
            state.exec_in = True

    def _run(self, command: Command, run: Run, state: State) -> str | None:
        program = run.words[0]
        if _built(run, program):
            return f"`{self.name}` builds a command at run time (`{program}`); write the program and its script out"
        match shell_programs.name(program):
            case name if name in _FOLDER:
                self._folder(command, run, state)
            case name if name in shell_programs.SHELLS:
                return self._shell(command, run, state)
            case "source" | ".":
                return self._current(state, command, run, self._source)
            case "eval":
                return self._current(state, command, run, self._eval)
        return None

    def _by_path(self, command: Command, run: Run, word: Word, state: State) -> str | None:
        """A program run by path: refused after a write, read when it is a shell script."""
        if state.effects.wrote:
            return self._written(word)
        path, reason = self._locate(run, word, state)
        if path is None:
            return reason
        try:
            interpreter = shell_programs.shebang(path)
        except OSError as error:
            return self._unreadable(word, error)
        context = shell_programs.Run(env=dict(run.env), chdir=run.chdir)  # its interpreter starts as it was started
        for sub in shell_programs.runs([*interpreter, Word(str(path))], context=context) if interpreter else ():
            if reason := self.bypass(self.name, sub):
                return reason
            if shell_programs.name(sub.words[0]) in shell_programs.SHELLS and (
                reason := self._shell(command, sub, state)
            ):
                return reason
        return None

    def _shell(self, command: Command, run: Run, state: State) -> str | None:
        """A shell: its startup files first, then its -c script, script file or standard input, in one child state."""
        args = shell_programs.shell_args(run.words)
        plain = state.plain() and not command.opaque_stdin and not run.from_input
        child = state.child(plain=plain and command.stdin() is None)
        if run.chdir:  # env -C, find -execdir: it starts in another folder
            child.at = None
        for file in [*_startup(run, state), *args.startup]:
            if file is None:
                return f"`{self.name}` starts a shell whose startup file was set where the guard can't follow it"
            if file and (reason := self._current(child, command, run, self._starts(file))):
                return reason
        if args.script is not None:
            return self._built(args.script) if _built(run, args.script) else self._text(args.script, child)
        if args.operand is not None and args.operand not in _STDIN:
            return self._file(run, args.operand, child)
        return self._stdin(command, run, child, plain=plain)

    def _starts(self, file: Word) -> Callable[[Command, Run, State], str | None]:
        """Reading one startup file, which runs in the shell it starts."""
        return lambda _command, run, state: self._file(run, file, state)

    def _stdin(self, command: Command, run: Run, state: State, *, plain: bool) -> str | None:
        """A shell's standard input as its script: readable from a here-document, here-string or file only."""
        given = command.stdin()
        if given is None:
            return None if plain else self._piped()
        if given.kind in {"here", "string"}:
            return self._built(given.word) if given.word.expanded else self._text(given.word, state)
        return self._file(run, given.word, state) if given.kind == "file" else self._piped()

    def _current(
        self, state: State, command: Command, run: Run, read: Callable[[Command, Run, State], str | None]
    ) -> str | None:
        """Read text that runs in this shell (sourced, eval, startup): its input is the command's, its cd unknown."""
        saved = state.stdin_plain
        state.stdin_plain = state.plain() and not command.opaque_stdin and command.stdin() is None
        state.current += 1
        try:
            return read(command, run, state)
        finally:
            state.current -= 1
            state.stdin_plain = saved

    def _source(self, command: Command, run: Run, state: State) -> str | None:
        operands = _operands(run)
        if not operands:
            return None
        word = operands[0]
        if word in _DEVICE_STDIN:
            return self._stdin(command, run, state, plain=state.stdin_plain and not run.from_input)
        if "/" not in word and not word.expanded:
            return f"`{self.name}` sources `{word}` through PATH; write `./{word}`"
        return self._file(run, word, state)

    def _eval(self, _command: Command, run: Run, state: State) -> str | None:
        words = _operands(run)
        if built := next((w for w in words if _built(run, w)), None):
            return self._built(built)
        return self._text(" ".join(words), state)

    def _folder(self, command: Command, run: Run, state: State) -> None:
        """Follow a cd to a plain absolute path; any other change of folder leaves the folder unknown."""
        operands = run.words[1:]
        word = operands[0] if len(operands) == 1 else Word("-")
        path = Path(word).expanduser() if word.tilde else Path(word)
        followed = shell_programs.name(run.words[0]) == "cd" and command.top_level and not state.current
        # cd fails into anything but an existing folder, and the shell stays where it was
        plain = not word.expanded and path.is_absolute() and ".." not in path.parts and path.is_dir()
        state.at = path if followed and plain else None

    def _file(self, run: Run, word: Word, state: State) -> str | None:
        """A script file a shell runs: judged like its text, under its own name."""
        if state.effects.wrote:
            return self._written(word)
        path, reason = self._locate(run, word, state)
        if path is None:
            return reason
        if self.depth >= shell_programs.NESTING:
            return self._nests()
        try:
            text = shell_programs.read_script(path)
        except (OSError, UnicodeDecodeError) as error:
            return self._unreadable(word, error)
        return self.judge(text, self.depth + 1, state, str(word))

    def _locate(self, run: Run, word: Word, state: State) -> tuple[Path | None, str]:
        if _built(run, word):
            return None, f"`{self.name}` runs `{word}`, a path built at run time; write the path out"
        path = Path(word).expanduser() if word.tilde else Path(word)
        if path.is_absolute():
            return path, ""
        if state.at is None or run.chdir:
            return None, f"`{self.name}` runs `{word}` from a folder the guard can't follow; use an absolute path"
        return state.at / path, ""

    def _text(self, text: str, state: State) -> str | None:
        if self.depth >= shell_programs.NESTING:
            return self._nests()
        return self.judge(str(text), self.depth + 1, state, "")

    def _nests(self) -> str:
        return f"`{self.name}` nests scripts more than {shell_programs.NESTING} deep"

    def _built(self, word: str) -> str:
        shown = word if len(word) <= _SHOWN else f"{word[:_SHOWN]}…"
        return f"`{self.name}` hands a shell a script built at run time (`{shown}`); single-quote it or write it out"

    def _piped(self) -> str:
        return (
            f"`{self.name}` pipes input into a shell, which the guard can't read; pass the commands with -c or as a"
            " script file"
        )

    def _written(self, word: str) -> str:
        return (
            f"`{self.name}` runs `{word}` after writing in the same command; write it in one command and run it in"
            " the next"
        )

    def _unreadable(self, word: str, error: OSError | UnicodeDecodeError) -> str:
        why = "it is not UTF-8 text" if isinstance(error, UnicodeDecodeError) else error.strerror or str(error)
        return f"`{self.name}` runs `{word}`, which can't be read: {why}"


def _built(run: Run, word: Word) -> bool:
    """Whether the shell, xargs or find fills *word* in at run time."""
    return word.expanded or (run.replaced is not None and run.replaced in word)


def _startup(run: Run, state: State) -> list[Word | None]:
    """The startup files a shell runs first: BASH_ENV and ENV from its command, else as earlier text set them."""
    files = state.startup | run.env
    return [files[key] for key in _STARTUP if key in files]


def _operands(run: Run) -> list[Word]:
    return run.words[2 if run.words[1:2] == ["--"] else 1 :]
