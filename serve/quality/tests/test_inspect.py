"""Commit-bound exception counts and protected-data evidence."""

from pathlib import Path

from owlbear_quality import trees
from owlbear_quality.inspect import added, inventory, protected


def commit(repo: Path, contents: dict[str, str]) -> str:
    for path, text in contents.items():
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
    trees.git(repo, "add", "--all")
    trees.git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "work")
    return trees.git(repo, "rev-parse", "HEAD").strip()


def test_protected_compares_parsed_tables_and_invoked_scripts_not_dependencies(tmp_path: Path) -> None:
    trees.git(tmp_path, "init", "-q")
    base = commit(
        tmp_path,
        {
            "pyproject.toml": '[project]\ndependencies = []\n[project.scripts]\nscan = "app:old"\n',
            "package.json": '{"dependencies": {}}',
        },
    )
    deps = commit(
        tmp_path,
        {
            "pyproject.toml": '[project]\ndependencies = ["lib"]\n[project.scripts]\nscan = "app:old"\n',
            "package.json": '{"dependencies": {"lib": "1"}}',
        },
    )
    assert protected(tmp_path, base, deps) is None
    changed = commit(
        tmp_path,
        {
            "pyproject.toml": '[project.scripts]\nscan = "app:new"\n[tool.ruff]\nline-length = 100\n',
            ".github/workflows/check.yml": "name: checks\n",
        },
    )
    evidence = protected(tmp_path, deps, changed, (("uv", "run", "scan"),))
    assert evidence is not None
    assert evidence.paths == (".github/workflows/check.yml", "pyproject.toml")
    assert all(text in evidence.text for text in ("tool.ruff", "project.scripts", "app:old", "app:new"))
    further = commit(tmp_path, {".github/workflows/check.yml": "name: changed\n"})
    assert protected(tmp_path, deps, further).digest != evidence.digest


def test_inventory_scope_and_added_copies_come_from_commits(tmp_path: Path) -> None:
    trees.git(tmp_path, "init", "-q")
    source = (
        'text = "# noqa: F401"\n'
        "value = (\n    1\n)  # fmt: skip\n"
        "# fmt: off\nx=1\n# fmt: on\ny = 2\n"
        "same = 1  # noqa: E501\n"
    )
    forms = (
        "# zizmor: ignore[unpinned-uses]\n"
        "key: value  # yamllint disable-line rule:line-length\n"
        "# yamllint disable-line\nnext: value\n"
        "# yamllint disable rule:comments\nkey: other\n# yamllint enable rule:comments\n"
        "<!-- markdownlint-disable-next-line MD013 -->\nlong text\n"
        "<!-- markdownlint-disable-line MD013 -->\n"
        "<!-- markdownlint-disable MD013 -->\ntext\n<!-- markdownlint-enable MD013 -->\n"
        "// editorconfig-checker-disable-next-line\ntext\n"
        "text // editorconfig-checker-disable-line\n"
        "// editorconfig-checker-disable\ntext\n// editorconfig-checker-enable\n"
    )
    files = {
        "a.py": source,
        "forms.txt": forms,
        "file.py": "# ruff: noqa\nx = 1\n",
        "workflow.yml": 'run: | # zizmor: ignore[template-injection]\n  echo "# zizmor: ignore[fake]"\n',
    }
    for name in ("yamllint disable-file", "markdownlint-disable-file", "editorconfig-checker-disable-file"):
        files[name.split()[0] + ".txt"] = f"# {name}\ntext\n"
    base = commit(tmp_path, files)
    items = inventory(tmp_path, files)
    assert [d.directive for d in items if d.path == "workflow.yml"] == ["zizmor: ignore[template-injection]"]
    py = [d for d in items if d.path == "a.py"]
    assert len(py) == 3  # the directive inside the string is not a comment
    assert py[0].code == "value = (\n    1\n)  # fmt: skip\n"
    assert "y = 2" not in py[1].code
    assert len([d for d in items if d.path == "forms.txt"]) == 10
    head = commit(
        tmp_path,
        {
            "a.py": source.replace("# fmt: on\n", "") + "same = 1  # noqa: E501\n",
            "file.py": "# ruff: noqa\nx = 2\n",
        },
    )
    # Deliberately leave a different index: added must still inspect head's immutable blobs.
    (tmp_path / "a.py").write_text("no_directives = True\n")
    trees.git(tmp_path, "add", "a.py")
    changes = added(tmp_path, base, head)
    assert len(changes) == 3
    assert all(d.count == 1 for d in changes)
    copies = next(d for d in changes if len(d.places) == 2)
    assert {p.line for p in copies.places} == {8, 9}
    assert any("y = 2" in d.places[0].code for d in changes)
    assert any("x = 2" in d.places[0].code for d in changes)
