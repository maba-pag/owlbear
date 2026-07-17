## ADDED Requirements

### Requirement: Score-led memory overview
Cockpit SHALL present each memory entry with its title, scope agents, categories, and computed score, and SHALL order entries by score descending before applying the existing state, creation-time, and ID tie-breakers. The overview SHALL display score to two decimal places without score-dependent color or a confidence-based priority marker.

#### Scenario: Operator scans ranked entries
- **WHEN** the operator opens Memory with entries having different scores
- **THEN** Cockpit lists the higher-scoring entry first and shows each entry's title, scope agents, categories, and two-decimal score

#### Scenario: Scores are equal
- **WHEN** multiple entries have the same score
- **THEN** Cockpit orders them using state priority, creation time, and ID in that sequence

### Requirement: Complete lifecycle-state visibility
Cockpit SHALL recognize and expose `pending`, `curated`, `approved`, `contested`, `disputed`, `stale`, and `deleted` memory states in entry rendering and state filters.

#### Scenario: Operator filters exceptional states
- **WHEN** contested, disputed, and stale entries exist and the operator selects any corresponding state filter
- **THEN** Cockpit shows entries in the selected state without treating the state as unknown

### Requirement: Operator-relevant memory details
The expanded memory detail SHALL show the entry title as its heading, its content, and metadata for ID, categories, confidence, state, outstanding marks, score, source agent, scope agents, created time, updated time, approved time, and contested task. Score, scope agents, and categories SHALL remain present in both the overview and details. Cockpit SHALL label `outstanding_count` as **Outstanding marks** and show a star icon with its numeric count. Cockpit SHALL NOT display `unremarkable_count` or `didnt_use_count`.

#### Scenario: Operator expands an entry
- **WHEN** the operator expands a memory entry
- **THEN** Cockpit shows the entry content and every operator-relevant field with outstanding assessments presented as Outstanding marks

#### Scenario: Internal negative counters exist
- **WHEN** an entry has nonzero unremarkable or non-use counts
- **THEN** Cockpit uses the resulting score and lifecycle state without displaying either raw counter

### Requirement: Contested-task navigation
For a contested entry with `contested_by_task`, Cockpit SHALL render the task identifier as an action that opens the corresponding Cockpit task detail. When no contested task is present, Cockpit SHALL render a non-interactive empty-value indicator and SHALL NOT fail detail rendering.

#### Scenario: Operator opens the reporting task
- **WHEN** the operator activates the contested-task reference on a contested entry
- **THEN** Cockpit opens the referenced task in its task detail view

#### Scenario: Entry has no active contested task
- **WHEN** the operator expands an entry whose `contested_by_task` is null
- **THEN** Cockpit shows an empty-value indicator without rendering a task action

### Requirement: Detail-aligned editing
Cockpit SHALL allow the operator to edit title, content, categories, confidence, and scope agents on every memory entry except deleted entries. Edit mode SHALL preserve substantially the same information structure as the detail view and SHALL keep ID, state, outstanding marks, score, source agent, created time, updated time, approved time, and contested task visible but read-only.

#### Scenario: Operator edits a normal entry
- **WHEN** the operator enters edit mode for a pending, curated, or approved entry
- **THEN** Cockpit exposes controls for only title, content, categories, confidence, and scope agents while retaining system-managed metadata as read-only context

#### Scenario: Operator edits an exceptional entry
- **WHEN** the operator saves changes to a contested, disputed, or stale entry
- **THEN** the mutable fields change and the entry remains in its pre-edit lifecycle state

#### Scenario: Operator edits confidence
- **WHEN** the operator saves a new confidence value on a non-deleted entry
- **THEN** the persisted score is recomputed from the new confidence and the existing outstanding and unremarkable counts

#### Scenario: Operator views a deleted entry
- **WHEN** the operator expands a deleted entry
- **THEN** Cockpit shows its details without offering edit controls

#### Scenario: Operator edits an approved entry
- **WHEN** the operator saves changes to an approved entry
- **THEN** the entry transitions to curated and requires approval again

### Requirement: Human-only exceptional-state resolution
Cockpit SHALL provide an explicit resolve action for contested, disputed, and stale entries. Resolution SHALL be available through the Cockpit API and UI only; the memory MCP server SHALL NOT expose a resolve tool, and MCP curation SHALL remain blocked for contested, disputed, and stale entries.

#### Scenario: Operator resolves an exceptional entry
- **WHEN** the operator resolves a contested, disputed, or stale entry in Cockpit using its current concurrency token
- **THEN** the entry transitions to approved and receives current approved and updated timestamps

#### Scenario: Agent attempts exceptional-state recovery
- **WHEN** an agent uses the memory MCP surface
- **THEN** no resolution operation is available and curation of contested, disputed, or stale entries remains rejected

#### Scenario: Resolution uses stale data
- **WHEN** the operator attempts resolution with an outdated concurrency token
- **THEN** Cockpit rejects the mutation as a conflict without changing the entry

### Requirement: Accurate contested provenance
The first factually-wrong assessment from a task SHALL move an approved or curated entry to contested and store that task as `contested_by_task`. A repeated assessment from the same task SHALL leave the entry unchanged. A factually-wrong assessment from a different task SHALL move the entry to disputed and clear `contested_by_task`. Resolving any exceptional state SHALL clear `contested_by_task`.

#### Scenario: First task contests an entry
- **WHEN** a task first assesses an approved or curated entry as factually wrong
- **THEN** the entry becomes contested and records that task as the active contested-task provenance

#### Scenario: Same task repeats its report
- **WHEN** the task recorded in `contested_by_task` again assesses the contested entry as factually wrong
- **THEN** the entry and its contested-task provenance remain unchanged

#### Scenario: Different task confirms the problem
- **WHEN** a different task assesses the contested entry as factually wrong
- **THEN** the entry becomes disputed and `contested_by_task` becomes null

#### Scenario: Operator resolves an exceptional entry
- **WHEN** the operator resolves a contested, disputed, or stale entry
- **THEN** `contested_by_task` becomes null

### Requirement: Fresh stale recovery window
Resolving a stale entry SHALL reset `didnt_use_count` to zero while preserving confidence, outstanding count, unremarkable count, score, and all other assessment history. Resolving contested or disputed entries SHALL leave all assessment counters unchanged.

#### Scenario: Operator resolves a stale entry
- **WHEN** the operator resolves an entry in stale state
- **THEN** the entry becomes approved with zero accumulated non-use assessments and retains its positive and score-relevant history

#### Scenario: Operator resolves a contested or disputed entry
- **WHEN** the operator resolves an entry in contested or disputed state
- **THEN** the entry becomes approved without changing any assessment counter