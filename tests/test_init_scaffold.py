"""Tests for #1284: Update setup/init.py — scaffold consumer copilot-instructions.md.

Verifies that:
- init() generates a consumer-generic copilot-instructions.md (AC1)
- Generated file has a commented path-mapping section covering required dimensions (AC2)
- Template uses illustrative examples with customization instruction comments (AC3)
- Re-running init() on a customized file preserves the existing content (AC4)
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

_INIT_PY_REL = "setup/init.py"
_CI_REL = ".github/copilot-instructions.md"


def _load_init(project_root: Path) -> types.ModuleType:
    init_path = project_root / _INIT_PY_REL
    spec = importlib.util.spec_from_file_location("owlbear_init_1284", init_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_directory_section(content: str) -> str:
    """Return the text block between the directory/path heading and the next ## heading."""
    lines = content.splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        if line.startswith("## ") and any(kw in line.lower() for kw in ("directory", "path", "structure")):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            section_lines.append(line)
    return "\n".join(section_lines)


# ---------------------------------------------------------------------------
# AC1 — Generated file is a consumer-generic scaffold
# ---------------------------------------------------------------------------


class TestFromAC_ConsumerScaffoldGeneration:
    """AC1: init() generates a consumer-generic .github/copilot-instructions.md."""

    def test_generated_file_is_consumer_generic(self, project_root: Path, tmp_path: Path) -> None:
        """Generated copilot-instructions.md must not contain OwlBear-dev branding.

        The seed template must be replaced with a consumer-generic scaffold.
        OwlBear-dev internal phrases (used in the current template) must not
        appear in the output delivered to consumers.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        owlbear_dev_phrases = [
            "laptop-resident AI development system",
            "OwlBear is a laptop-resident",
        ]
        for phrase in owlbear_dev_phrases:
            assert phrase not in content, (
                f"Generated consumer scaffold must not contain OwlBear-dev-specific "
                f"phrase: {phrase!r}. Replace seed/{_CI_REL} with a consumer-generic "
                "template."
            )


# ---------------------------------------------------------------------------
# AC2 — Commented path-mapping section covering required dimensions
# ---------------------------------------------------------------------------


class TestFromAC_CommentedPathMappingSection:
    """AC2: Generated file has a commented path-mapping section.

    Required dimensions: project layout, source packages, frontend root, test paths.
    """

    def test_has_html_comments_in_template(self, project_root: Path, tmp_path: Path) -> None:
        """Generated copilot-instructions.md contains HTML comments (<!-- ... -->).

        The 'commented' path-mapping section requires inline HTML comments to
        guide consumers on what to fill in. The current seed has no such comments.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        assert "<!--" in content, (
            "Generated copilot-instructions.md must contain HTML comments (<!-- ... -->) "
            "to guide consumers on which fields to customize. "
            "No HTML comments found in the generated file."
        )

    def test_directory_section_has_source_package_entry(self, project_root: Path, tmp_path: Path) -> None:
        """Directory section references the source/packages directory (e.g. 'src/').

        AC2 requires a 'source packages' dimension in the path-mapping section.
        Consumer scaffolds use generic names like 'src/' — not OwlBear-specific
        paths like 'serve/' or 'share/'.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        section = _extract_directory_section(content).lower()
        assert "src/" in section, (
            "Directory section must contain a 'src/' entry representing source packages. "
            f"Directory section content:\n{section}"
        )

    def test_directory_section_has_frontend_entry(self, project_root: Path, tmp_path: Path) -> None:
        """Directory section references the frontend root (e.g. 'frontend' or 'web/').

        AC2 requires a 'frontend root' dimension. The current OwlBear-dev seed
        does not include a generic frontend entry in the Directory Structure table.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        section = _extract_directory_section(content).lower()
        assert any(kw in section for kw in ("frontend", "web/")), (
            "Directory section must have an entry for the frontend root "
            "(e.g. 'frontend/' or 'web/'). "
            f"Directory section content:\n{section}"
        )

    def test_directory_section_has_test_path_entry(self, project_root: Path, tmp_path: Path) -> None:
        """Directory section references test paths (e.g. 'tests/').

        AC2 requires all four dimensions: project layout, source packages, frontend
        root, AND test paths. The directory section must contain an explicit test-path
        entry so generated Copilot answers are path-aware for test-related tasks.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        section = _extract_directory_section(content).lower()
        assert "tests/" in section, (
            "Directory section must contain a 'tests/' entry representing test paths. "
            "AC2 requires all four dimensions: project layout, source packages, "
            "frontend root, and test paths. "
            f"Directory section content:\n{section}"
        )


# ---------------------------------------------------------------------------
# AC3 — Illustrative examples with customization instruction comments
# ---------------------------------------------------------------------------


class TestFromAC_IllustrativeExamples:
    """AC3: Template uses concrete examples with comments indicating customization needed."""

    def test_has_customization_instruction_comment(self, project_root: Path, tmp_path: Path) -> None:
        """Generated file has an HTML comment instructing consumers to customize.

        AC3 requires comments that tell the consumer to replace or adapt the
        illustrative examples. Phrases like 'replace', 'customize', or 'your project'
        inside HTML comments signal this intent.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8").lower()
        # Extract all HTML comment bodies
        import re

        html_comments = re.findall(r"<!--(.*?)-->", content, re.DOTALL)
        customization_keywords = ("replace", "customize", "your project", "your ")
        has_instruction = any(any(kw in comment for kw in customization_keywords) for comment in html_comments)
        assert has_instruction, (
            "Generated copilot-instructions.md must have at least one HTML comment "
            "instructing the consumer to customize the content "
            "(e.g., '<!-- Replace with your project name -->'). "
            f"HTML comments found: {html_comments!r}"
        )

    def test_directory_section_uses_generic_example_paths(self, project_root: Path, tmp_path: Path) -> None:
        """Directory section uses generic illustrative paths, not OwlBear-specific ones.

        The consumer scaffold must replace OwlBear-internal paths ('serve/', 'share/',
        'seed/') with generic illustrative examples ('src/', 'lib/', 'app/', etc.)
        that consumers can adapt to their own projects.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        section = _extract_directory_section(content).lower()
        owlbear_specific = ["`serve/`", "`share/`", "`seed/`", "`owlbear/`"]
        present = [p for p in owlbear_specific if p in section]
        assert not present, (
            "Directory section must use generic illustrative paths, not OwlBear-internal "
            f"paths. Found OwlBear-specific entries: {present}. "
            "Replace seed/.github/copilot-instructions.md with a consumer-generic template."
        )


# ---------------------------------------------------------------------------
# AC4 — Re-running init() preserves an existing customized file
# ---------------------------------------------------------------------------


class TestFromAC_SkipIfExistsPreservation:
    """AC4: Re-running init() on a project with a customized file preserves it."""

    def test_preserves_customized_file_on_reinit(self, project_root: Path, tmp_path: Path) -> None:
        """init() does not overwrite a pre-existing customized copilot-instructions.md.

        This tests skip-if-exists behaviour: once the consumer has customized their
        copilot-instructions.md, subsequent init() calls must leave it intact.
        This requires '.github/copilot-instructions.md' to be in _SKIP_IF_EXISTS_REL.
        """
        custom_content = (
            "# My Project — Custom Instructions\n\n"
            "## Project Identity\n\n"
            "This is my custom copilot instructions file.\n"
            "It has been edited and must not be overwritten.\n"
        )
        github_dir = tmp_path / ".github"
        github_dir.mkdir(parents=True)
        (github_dir / "copilot-instructions.md").write_text(custom_content, encoding="utf-8")

        module = _load_init(project_root)
        module.init(tmp_path, project_root)

        after = (tmp_path / _CI_REL).read_text(encoding="utf-8")
        assert after == custom_content, (
            "init() overwrote a pre-existing customized copilot-instructions.md. "
            "Add '.github/copilot-instructions.md' to _SKIP_IF_EXISTS_REL in setup/init.py "
            "so that consumer customizations are preserved on re-init.\n"
            f"Expected (custom):\n{custom_content!r}\n"
            f"Got (after init):\n{after!r}"
        )

    def test_skip_if_exists_constant_includes_copilot_instructions(self, project_root: Path) -> None:
        """_SKIP_IF_EXISTS_REL in setup/init.py contains '.github/copilot-instructions.md'.

        The skip-if-exists frozenset must be updated so that existing consumer files
        are not overwritten. This is a direct contract check on the module constant.
        """
        module = _load_init(project_root)
        skip_set = module._SKIP_IF_EXISTS_REL
        assert ".github/copilot-instructions.md" in skip_set, (
            "_SKIP_IF_EXISTS_REL does not include '.github/copilot-instructions.md'. "
            "Add it to the frozenset in setup/init.py to preserve consumer customizations. "
            f"Current _SKIP_IF_EXISTS_REL: {sorted(skip_set)}"
        )
