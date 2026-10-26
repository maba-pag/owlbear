# Sources

External sources whose code, text or patterns OwlBear adopted and still ships. One row per source and use. A row
leaves when its asset leaves the repository.

Sources only read for research are not listed here. The full reading log up to 2026-10-26 is in owlbear-data:
[sources reading log](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/sources-reading-log.md).
Research cites its sources itself.

| Source | URL | Licence | What | Where Used |
| --- | --- | --- | --- | --- |
| Impeccable (Paul Bakaus), tag `skill-v4.5.2` | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Design rules and the critique, condensed and rewritten for unattended workers; notice and licence text beside the skills | `serve/delivery-next/src/owlbear_delivery_next/skills/NOTICE.md`, `serve/delivery-next/src/owlbear_delivery_next/skills/owlbear-interface-design/SKILL.md`, `serve/delivery-next/src/owlbear_delivery_next/skills/owlbear-design-review/SKILL.md` |
| Impeccable (Paul Bakaus) | <https://github.com/pbakaus/impeccable> | Apache-2.0 | Design domains and anti-pattern classification of the frontend design reference | `share/skills/h-frontend-design/SKILL.md` |
| Anthropic frontend-design skill | <https://github.com/anthropics/skills/tree/main/skills/frontend-design> | Apache-2.0 | Baseline design-direction wording beneath the frontend design reference | `share/skills/h-frontend-design/SKILL.md` |
| nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | MIT | Workflow phases, content-type routing table, aesthetic constraints | `share/skills/h-visual-output/SKILL.md` |
| Porsche Design System components-js 4.8.0 | <https://github.com/porsche-design-system/porsche-design-system> | Apache-2.0 (code); fonts and assets load from the PDS CDN under the PDS Assets License | Vendored stylesheet and loader; the notice heads each file | `serve/delivery-next/src/owlbear_delivery_next/web/pds/index.css`, `serve/delivery-next/src/owlbear_delivery_next/web/pds/load.mjs` |
| lit-html 3.3.3 | <https://github.com/lit/lit> | BSD-3-Clause | Unmodified npm files; licence text and checksums beside them | `serve/delivery-next/src/owlbear_delivery_next/web/vendor/lit-html/LICENSE` |
| agentskills skills-ref | <https://github.com/agentskills/agentskills/tree/main/skills-ref> | Apache-2.0 | Module shape and `validate_metadata` API of the SKILL.md validator; the spec's name and description rules | `.owlbear/scripts/skills_ref/validator.py` |
| bytedance/deer-flow | <https://github.com/bytedance/deer-flow> | MIT | Angle-bracket rejection in skill descriptions | `.owlbear/scripts/skills_ref/validator.py` |
| bytedance/deer-flow | <https://github.com/bytedance/deer-flow> | MIT | AST-based import boundary test | `tests/test_package_boundary.py` |
| bytedance/deer-flow | <https://github.com/bytedance/deer-flow> | MIT | Memory facts with a confidence floor and a fixed category set | `serve/memory/src/owlbear_memory/models.py` |
| PinchTab `internal/idpi/content.go` | <https://github.com/pinchtab/pinchtab/blob/main/internal/idpi/content.go> | MIT | Untrusted-content wrapping with sentinel tags and an advisory preamble | `serve/knowledge/src/owlbear_knowledge/content_safety.py` |
