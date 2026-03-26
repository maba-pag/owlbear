## Research

- Research doc: docs/research/context-hydration-extract-content.md
- External attribution updated: docs/sources/overview.md
- Key findings:
  - fetch_url() duplicates the same trafilatura.extract(..., output_format="markdown", include_links=True, url=url) call already wrapped by extract_content().
  - Unlike web_search, fetch_url() has no raw-HTML fallback. The migration should use extract_content(resp.text, url=url).text directly and delete the local wrap_web_content block.
  - Missing-trafilatura behavior stays equivalent: failure still occurs on first use, now via extract_content() instead of a local import.
  - Test blast radius: 4 direct trafilatura mocks in tests/test_context_hydration.py and 5 fetch-url-related mocks in tests/test_content_safety_integration.py.
- Follow-up created: #864 - Update context_hydration tests to mock extract_content instead of trafilatura
- No extra architecture split needed: #826 itself remains the implementation task.

Executed follow-up command:

```powershell
kanban\kanban-md.exe create "Update context_hydration tests to mock extract_content instead of trafilatura" --priority nice-to-have --status ideation --tags "test,type:test,scope:core,phase-9,dry" --body "TDD RED phase for #826. Update fetch_url-related tests in tests/test_context_hydration.py and tests/test_content_safety_integration.py that currently patch trafilatura via sys.modules to patch owlbear.core.context_hydration.extract_content instead. Source: docs/research/context-hydration-extract-content.md. AC: (1) 4 trafilatura mocks in tests/test_context_hydration.py are replaced with extract_content or ExtractionResult-based mocks, (2) 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced likewise, (3) wrapping assertions are preserved by controlling ExtractionResult.text values, (4) scoped tests pass."
```
