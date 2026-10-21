# owlbear-decisions — Decision Files

The file contract for OwlBear's decisions and every project's: one Markdown file per lasting decision, a
validator for a data repository's decision folders, a project's snapshot of them, and a preview of the first
migration from the hand-edited
[decision record](../../.owlbear/research/delivery-liveness-first-rebuild.md). It is slice 1 of the
[decision system design](../../.owlbear/research/decision-system-build.md); Delivery stores the files in
`owlbear-data` and indexes them (slice 3), and the Decisions page and step context come in later slices.

**Use this guide when:** you write or read decision files, change their rules, or run the migration preview.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run decisions-validate <data-repo-root>
uv run decisions-migrate-preview <record.md> <out-dir> [--project owlbear]
uv run decisions-view <data-repo-root> [--project owlbear] [--out .owlbear/decisions.md] [--commit SHA] [--check]
```

`decisions-validate` prints one line per finding (`path: rule: message`) and exits 1 on any. The Global layer is
the repository root (`<root>/decisions/`), each project's layer its folder (`<root>/<project>/decisions/`) and a
Change's layer `<root>/<project>/changes/<slug>/decisions/`, as in Delivery's data repository.

`decisions-migrate-preview` writes one proposed decision per in-force bullet into `<out-dir>/<project>/decisions/`
and a `REPORT.md` with counts, unclear clauses, orphan rows, a proposed-scope table for the owner to mark Global
topics, the validator's findings with their explanation and the row-to-entry concordance. It refuses a folder that
already holds a preview and never changes the record (TD-437).

`decisions-view` writes OwlBear's generated, read-only view of the Global and the project's decisions (slice 6,
TD-425): a header naming the data commit (`--commit`, default the root's `HEAD`; `none` only for a data repository
without decisions) and that the record stays authoritative (TD-437), the rules in force by layer and topic, history,
the validator's findings, and a last line `<!-- decisions-view sha256:... -->` over everything above it. `--check`
writes nothing and exits 1 when the view is missing, edited by hand, or shows other decisions than the data; a new
data commit alone never makes it stale. Pull-request CI checks only the hash (`.github/scripts/decisions_view_hash.py`,
a config hook); `.github/workflows/decisions-view.yml` runs `--check` with the read-only data token (TD-436).

```python
from owlbear_decisions import Decision, load_folder, queue, snapshot, validate_repo, write

revision = write(decision, layer_folder)  # create; refuses an existing file
write(successor, layer_folder)  # a change of wording is a successor
write(replaced, layer_folder, expected_revision=revision)  # update; refuses a stale revision
loaded = load_folder(layer_folder)  # decisions by path, and per-file errors
seen = snapshot(data_root, "shop-site")  # Global plus one project's layers, and every finding involving them
seen.active(decision.id)  # in force, not flagged `conflict` and involved in no finding
waiting = queue(e.decision for e in seen.entries)  # read-backs by kind, then oldest; a conflict queues itself
```

`snapshot(root, project)` is file-only: it loads the Global layer and the project's layers (its folder and its
Changes' folders; an empty project loads Global alone), validates every project's folder, and keeps Global's and the
project's entries (`Entry`: path, `Layer`, decision) and every finding whose `involves` names one of them, wherever
its file lies: another project's decision replacing a Global one leaves that Global decision not active everywhere.
A file in these layers that did not load is a finding involving no decision, also in `unreadable`, and makes the
snapshot not `complete`. A folder that cannot be looked into raises `OSError` (only a missing path counts as absent);
Delivery's `state_store/decision_store.py` turns that, or an incomplete snapshot, into a stop.

### File contract

`<layer>/decisions/<id>.md`: YAML front matter with every field but `rationale` in a fixed order, then the
rationale as the Markdown body. Writes are atomic (temporary file, fsync, rename) under a lock on the folder.

| Field | Notes |
| --- | --- |
| `id` | `D-` plus a 26-character ULID (Crockford base32: 48-bit milliseconds, 80 random bits), sortable by creation |
| `aliases` | Display names such as `TD-417`; one record row split into clauses names each of them |
| `title`, `topic`, `statement` | The statement is the in-force line, at most 240 characters |
| `applies_to` | `paths` (repository-relative globs), `roles`, `steps`; all empty means the whole scope |
| `scope`, `project`, `change` | `global` (no project), `project` (its folder name), `change` (project and the Change's folder, up to 96 characters: Delivery's record stem) |
| `origin`, `actor`, `source` | `decided`, `approved` or `autonomous`; who made it; where (chat, Change, PR, question) |
| `owner_words` | `{text, date, alias}` items; required for `decided` |
| `state` | `draft`, `in_force`, `replaced`, `withdrawn`, `spent`; nothing is deleted |
| `links` | `{type, target}`; types `replaces`, `refines`, `exception_to`, `depends_on`, `related_to`, `promoted_from` |
| `conflict`, `read_back` | A flag the owner resolves; `none`, `pending` or the ISO date of the last read-back |
| `read_back_why`, `read_back_kind` | Only while `read_back` is `pending`, then both required: why it is asked again and how urgent (`safety`, `blocked`, `uncertain`, `improvement`); written only when set, so older files keep their revision |
| `created_at` | Time-zone-aware timestamp |

`revision` is not stored: it is the sha256 of the canonical JSON of every other field, so any content change
gives a new one. `write` refuses a stale `expected_revision` and never edits the statement of an in-force
decision. A malformed file is reported by `load_folder`, never skipped.

### Validator rules

`schema`, `link-type`, `duplicate-id` (across all layers), `link-target`
(missing, self, or out of reach: a project may target Global and its own decisions, Global only Global, and
`promoted_from` anything), `two-successors` (two in-force decisions replace or promote one), `no-successor` (replaced
with no non-draft successor; a widening promotion counts), `promote-scope` (`promoted_from` must widen: Global from a
project or Change decision, a project from one of its own Changes'), `statement-length`, `placement` (scope fields against the folder, including a
change decision outside a change folder), `exception-target` (`exception_to` a non-Global decision) and
`replace-scope` (`replaces` reaches only the same or a narrower layer: Global only Global, a project its own project's
and Changes' decisions, a Change its own; widening goes through `promoted_from`, departing from Global through
`exception_to`).
Statement length is a validator finding rather than a load error, so such a file still loads and is reported. A
`decided` decision chosen without a quote has no owner's words (TD-388); that is no finding.

---

## Configuration

No environment variables. Pass folders explicitly; the package never locates `owlbear-data` itself.

## Dependencies

`pydantic` and `ruamel.yaml`; no other OwlBear package. Delivery Next may import it.
