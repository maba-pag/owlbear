"""RED-phase tests for task #602 — rename data/ to store/.

Verifies that all default-path constants, docstrings, help text, config patterns,
and scripts reference store/ instead of data/ after the rename.

All tests fail on current HEAD: constants still point to data/.
"""

from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# AC2 — mcp-memory: _DEFAULT_DB_PATH in server.py, migrate.py, approve.py
# ---------------------------------------------------------------------------


class TestFromAC_MemoryDefaultPaths:
    """AC2: _DEFAULT_DB_PATH must equal 'store/memory/memory.db' in all three mcp-memory modules."""

    def test_server_default_db_path_uses_store(self) -> None:
        """AC2: server.py _DEFAULT_DB_PATH must reference store/, not data/."""
        import owlbear_mcp_memory.server as mod

        assert mod._DEFAULT_DB_PATH == "store/memory/memory.db", (
            f"Expected 'store/memory/memory.db', got {mod._DEFAULT_DB_PATH!r}"
        )

    def test_migrate_default_db_path_uses_store(self) -> None:
        """AC2: migrate.py _DEFAULT_DB_PATH must reference store/, not data/."""
        import owlbear_mcp_memory.migrate as mod

        assert mod._DEFAULT_DB_PATH == "store/memory/memory.db", (
            f"Expected 'store/memory/memory.db', got {mod._DEFAULT_DB_PATH!r}"
        )

    def test_approve_default_db_path_uses_store(self) -> None:
        """AC2: approve.py _DEFAULT_DB_PATH must reference store/, not data/."""
        import owlbear_mcp_memory.approve as mod

        assert mod._DEFAULT_DB_PATH == "store/memory/memory.db", (
            f"Expected 'store/memory/memory.db', got {mod._DEFAULT_DB_PATH!r}"
        )

    def test_server_docstring_references_store(self) -> None:
        """AC2: app_lifespan docstring must say 'store/memory/memory.db', not 'data/memory/memory.db'."""
        import owlbear_mcp_memory.server as mod

        docstring = mod.app_lifespan.__doc__ or ""
        assert "store/memory/memory.db" in docstring, (
            "app_lifespan docstring must reference 'store/memory/memory.db'; "
            f"got: {docstring!r}"
        )

    def test_server_docstring_no_data_reference(self) -> None:
        """AC2: app_lifespan docstring must not still reference data/memory/memory.db."""
        import owlbear_mcp_memory.server as mod

        docstring = mod.app_lifespan.__doc__ or ""
        assert "data/memory/memory.db" not in docstring, (
            "app_lifespan docstring still contains 'data/memory/memory.db'"
        )


# ---------------------------------------------------------------------------
# AC3 — mcp-knowledge: _DEFAULT_KB_PATH in server.py
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeDefaultPath:
    """AC3: _DEFAULT_KB_PATH must equal 'store/knowledge/knowledge.db' in mcp-knowledge server.py."""

    def test_knowledge_server_default_kb_path_uses_store(self) -> None:
        """AC3: _DEFAULT_KB_PATH must reference store/, not data/."""
        import owlbear_mcp_knowledge.server as mod

        assert mod._DEFAULT_KB_PATH == "store/knowledge/knowledge.db", (
            f"Expected 'store/knowledge/knowledge.db', got {mod._DEFAULT_KB_PATH!r}"
        )

    def test_knowledge_server_no_data_reference_in_constant(self) -> None:
        """AC3: _DEFAULT_KB_PATH must not still reference data/."""
        import owlbear_mcp_knowledge.server as mod

        assert "data/" not in mod._DEFAULT_KB_PATH, (
            f"_DEFAULT_KB_PATH still points into data/: {mod._DEFAULT_KB_PATH!r}"
        )


# ---------------------------------------------------------------------------
# AC4 — knowledge/loader.py default path
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeLoaderDefault:
    """AC4: knowledge/loader.py default db path must use store/knowledge/knowledge.db."""

    def test_loader_source_default_uses_store(self) -> None:
        """AC4: os.environ.get fallback in loader.py load() must reference store/knowledge/knowledge.db."""
        loader_path = (
            WORKSPACE
            / "serve"
            / "knowledge"
            / "src"
            / "owlbear_knowledge"
            / "loader.py"
        )
        source = loader_path.read_text(encoding="utf-8")
        assert "store/knowledge/knowledge.db" in source, (
            "loader.py default path must reference 'store/knowledge/knowledge.db'"
        )

    def test_loader_source_no_data_fallback(self) -> None:
        """AC4: loader.py must not contain the old data/knowledge/knowledge.db fallback."""
        loader_path = (
            WORKSPACE
            / "serve"
            / "knowledge"
            / "src"
            / "owlbear_knowledge"
            / "loader.py"
        )
        source = loader_path.read_text(encoding="utf-8")
        assert "data/knowledge/knowledge.db" not in source, (
            "loader.py still references 'data/knowledge/knowledge.db'"
        )


# ---------------------------------------------------------------------------
# AC5 — mcp-project: project_list reads store/projects/
# ---------------------------------------------------------------------------


class TestFromAC_ProjectListPath:
    """AC5: project_list tool must construct path using store/projects/ not data/projects/."""

    def test_project_list_docstring_references_store(self) -> None:
        """AC5: project_list docstring must mention store/projects/."""
        import owlbear_mcp_project.server as mod

        fn = mod.project_list
        docstring = fn.__doc__ or ""
        assert "store/projects" in docstring, (
            f"project_list docstring must reference 'store/projects'; got: {docstring!r}"
        )

    def test_project_list_source_uses_store_projects(self) -> None:
        """AC5: server.py source must construct 'store' / 'projects' path."""
        server_path = (
            WORKSPACE
            / "serve"
            / "mcp-project"
            / "src"
            / "owlbear_mcp_project"
            / "server.py"
        )
        source = server_path.read_text(encoding="utf-8")
        assert '"store"' in source or "'store'" in source, (
            "mcp-project server.py must reference 'store' directory segment"
        )

    def test_project_list_source_no_data_projects(self) -> None:
        """AC5: server.py must not still reference data/projects."""
        server_path = (
            WORKSPACE
            / "serve"
            / "mcp-project"
            / "src"
            / "owlbear_mcp_project"
            / "server.py"
        )
        source = server_path.read_text(encoding="utf-8")
        # Check the project_list function specifically doesn't use "data" / "projects"
        assert '"data" / "projects"' not in source, (
            "mcp-project server.py still references data/projects"
        )
        assert '"data/projects"' not in source, (
            "mcp-project server.py still references data/projects (slash form)"
        )


# ---------------------------------------------------------------------------
# AC6 — analysis/_cli.py: _DEFAULT_AUDIT_DIR and help text
# ---------------------------------------------------------------------------


class TestFromAC_AuditDirDefault:
    """AC6: _DEFAULT_AUDIT_DIR must equal Path('store/audit/') and help text must say store/audit/."""

    def test_default_audit_dir_uses_store(self) -> None:
        """AC6: _DEFAULT_AUDIT_DIR must be Path('store/audit/')."""
        from owlbear_orchestrator.analysis import _cli as mod

        assert Path("store/audit/") == mod._DEFAULT_AUDIT_DIR, (
            f"Expected Path('store/audit/'), got {mod._DEFAULT_AUDIT_DIR!r}"
        )

    def test_default_audit_dir_no_data_reference(self) -> None:
        """AC6: _DEFAULT_AUDIT_DIR must not reference data/."""
        from owlbear_orchestrator.analysis import _cli as mod

        assert "data" not in str(mod._DEFAULT_AUDIT_DIR), (
            f"_DEFAULT_AUDIT_DIR still references data/: {mod._DEFAULT_AUDIT_DIR!r}"
        )

    def test_audit_dir_help_text_references_store(self) -> None:
        """AC6: --audit-dir argparse help text must say store/audit/, not data/audit/."""
        cli_path = (
            WORKSPACE
            / "serve"
            / "orchestrator"
            / "src"
            / "owlbear_orchestrator"
            / "analysis"
            / "_cli.py"
        )
        source = cli_path.read_text(encoding="utf-8")
        assert "store/audit/" in source, (
            "analysis/_cli.py help text must reference 'store/audit/'"
        )

    def test_audit_dir_help_text_no_data_audit(self) -> None:
        """AC6: --audit-dir help text must not still say data/audit/."""
        cli_path = (
            WORKSPACE
            / "serve"
            / "orchestrator"
            / "src"
            / "owlbear_orchestrator"
            / "analysis"
            / "_cli.py"
        )
        source = cli_path.read_text(encoding="utf-8")
        assert "data/audit/" not in source, (
            "analysis/_cli.py still references 'data/audit/' in help text"
        )


# ---------------------------------------------------------------------------
# AC7 — setup/init.py: no legacy data/knowledge/ references (replaces scripts/setup.py)
# ---------------------------------------------------------------------------


class TestFromAC_SetupKnowledgeDir:
    """AC7: setup/init.py must not reference legacy data/knowledge/ paths."""

    def test_setup_create_knowledge_dir_docstring_uses_store(self) -> None:
        """AC7: setup/init.py must reference seed/ mechanism, not data/knowledge/."""
        setup_path = WORKSPACE / "setup" / "init.py"
        source = setup_path.read_text(encoding="utf-8")
        # init.py uses seed/ to bootstrap workspace dirs — must reference seed/
        assert "seed/" in source or "seed_dir" in source, (
            "setup/init.py must reference the seed/ mechanism (replaces create_knowledge_dir)"
        )

    def test_setup_create_knowledge_dir_code_uses_store(self) -> None:
        """AC7: setup/init.py must not reference any data/knowledge variants."""
        setup_path = WORKSPACE / "setup" / "init.py"
        source = setup_path.read_text(encoding="utf-8")
        assert '"data" / "knowledge"' not in source, (
            "setup/init.py still references data/knowledge"
        )
        assert '"data/knowledge"' not in source, (
            "setup/init.py still references data/knowledge (slash form)"
        )

    def test_setup_function_creates_store_segment(self) -> None:
        """AC7: setup/init.py must contain init() function (replaces create_knowledge_dir)."""
        setup_path = WORKSPACE / "setup" / "init.py"
        # Parse AST to find init() function — replaces create_knowledge_dir
        tree = ast.parse(setup_path.read_text(encoding="utf-8"))
        func_node = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and node.name == "init"
            ),
            None,
        )
        assert func_node is not None, "init() function not found in setup/init.py"
        # Verify no legacy data/ path constants inside init()
        strings_in_func = [
            node.value
            for node in ast.walk(func_node)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        assert "data" not in strings_in_func, (
            f"init() must not use legacy 'data' segment; found strings: {strings_in_func!r}"
        )


# ---------------------------------------------------------------------------
# AC8 — .gitignore: patterns reference store/ not data/
# ---------------------------------------------------------------------------


class TestFromAC_GitignorePatterns:
    """AC8: .gitignore must reference store/knowledge/*.db and store/audit/."""

    def test_gitignore_knowledge_pattern_uses_store(self) -> None:
        """AC8: .gitignore must contain store/knowledge/*.db."""
        gitignore = (WORKSPACE / ".gitignore").read_text(encoding="utf-8")
        assert "store/knowledge/" in gitignore, (
            ".gitignore must reference 'store/knowledge/' (not 'data/knowledge/')"
        )

    def test_gitignore_audit_pattern_uses_store(self) -> None:
        """AC8: .gitignore must contain store/audit/."""
        gitignore = (WORKSPACE / ".gitignore").read_text(encoding="utf-8")
        assert "store/audit/" in gitignore, (
            ".gitignore must reference 'store/audit/' (not 'data/audit/')"
        )

    def test_gitignore_no_data_knowledge_pattern(self) -> None:
        """AC8: .gitignore must not still contain data/knowledge/*.db."""
        gitignore = (WORKSPACE / ".gitignore").read_text(encoding="utf-8")
        assert "data/knowledge/" not in gitignore, (
            ".gitignore still contains 'data/knowledge/' pattern"
        )

    def test_gitignore_no_data_audit_pattern(self) -> None:
        """AC8: .gitignore must not still contain data/audit/."""
        gitignore = (WORKSPACE / ".gitignore").read_text(encoding="utf-8")
        assert "data/audit/" not in gitignore, (
            ".gitignore still contains 'data/audit/' pattern"
        )


# ---------------------------------------------------------------------------
# AC9 — .editorconfig: [data/**] section updated to [store/**]
# ---------------------------------------------------------------------------


class TestFromAC_EditorconfigSection:
    """AC9: .editorconfig must use [store/**] instead of [data/**]."""

    def test_editorconfig_store_section_exists(self) -> None:
        """AC9: .editorconfig must contain [store/**] glob section."""
        editorconfig = (WORKSPACE / ".editorconfig").read_text(encoding="utf-8")
        assert "[store/**]" in editorconfig, (
            ".editorconfig must contain '[store/**]' section (was '[data/**]')"
        )

    def test_editorconfig_no_data_section(self) -> None:
        """AC9: .editorconfig must not still contain [data/**] glob section."""
        editorconfig = (WORKSPACE / ".editorconfig").read_text(encoding="utf-8")
        assert "[data/**]" not in editorconfig, (
            ".editorconfig still contains '[data/**]' section"
        )


# ---------------------------------------------------------------------------
# AC1 — store/ directory exists with expected subdirectories
# ---------------------------------------------------------------------------


class TestFromAC_StoreDirExists:
    """AC1: git mv data/ store/ — store/memory/ and store/knowledge/ must exist."""

    def test_store_memory_dir_exists(self) -> None:
        """AC1: store/memory/ directory must exist after rename."""
        store_memory = WORKSPACE / "store" / "memory"
        assert store_memory.is_dir(), (
            f"store/memory/ directory not found at {store_memory} — git mv not yet done"
        )

    def test_store_knowledge_dir_exists(self) -> None:
        """AC1: store/knowledge/ directory must exist after rename."""
        store_knowledge = WORKSPACE / "store" / "knowledge"
        assert store_knowledge.is_dir(), (
            f"store/knowledge/ directory not found at {store_knowledge} — git mv not yet done"
        )

    def test_data_dir_no_longer_exists(self) -> None:
        """AC1: data/ directory must no longer exist after rename."""
        data_dir = WORKSPACE / "data"
        assert not data_dir.is_dir(), (
            f"data/ directory still exists at {data_dir} — git mv not complete"
        )
