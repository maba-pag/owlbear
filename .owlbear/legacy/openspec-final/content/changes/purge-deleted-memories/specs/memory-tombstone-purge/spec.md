## ADDED Requirements

### Requirement: Deleted memories remain tombstones until explicit purge
The system SHALL preserve soft-deleted memory entries as tombstones until a user explicitly confirms a purge request. Existing deletion behavior for pending and non-pending memories MUST remain unchanged.

#### Scenario: Ordinary deletion creates a tombstone
- **WHEN** a user deletes a memory in a currently soft-deletable non-pending state
- **THEN** the system transitions the entry to `deleted` without physically removing its file

#### Scenario: Pending deletion remains immediate
- **WHEN** a user deletes a pending memory
- **THEN** the system physically removes the pending entry without creating a tombstone

### Requirement: Purge eligibility uses an ephemeral whole-day threshold
The system SHALL accept a minimum tombstone age expressed as a whole number of days greater than or equal to zero. The threshold SHALL default to 30 whenever the Memory view loads and SHALL apply only to the purge request initiated from that view state.

#### Scenario: Exact cutoff is eligible
- **WHEN** a deleted memory's deletion time is exactly the selected whole-day cutoff
- **THEN** the system includes that memory in the eligible purge set

#### Scenario: Zero days includes every tombstone
- **WHEN** the selected threshold is zero days
- **THEN** every memory already in the `deleted` state is eligible, including newly deleted memories

#### Scenario: Newer tombstone is skipped
- **WHEN** a deleted memory is newer than a positive selected threshold
- **THEN** the system preserves the tombstone and accounts for it as skipped

#### Scenario: Invalid threshold cannot start purge
- **WHEN** the threshold is negative, fractional, empty, or nonnumeric
- **THEN** the system reports the input as invalid and does not start a purge operation

#### Scenario: Threshold resets with the view
- **WHEN** the Memory view reloads after a user selected a threshold other than 30
- **THEN** the purge threshold returns to 30 days without reading or writing a persisted preference

### Requirement: Purge scope is project-wide and filter-independent
The system SHALL preview and execute purge against all deleted memories in the project. Active Memory state, category, agent, and text filters MUST NOT constrain eligibility or execution scope.

#### Scenario: Restrictive filters do not narrow purge
- **WHEN** the user opens purge while active filters hide some or all deleted memories
- **THEN** the preview counts and subsequent purge consider the same complete project-wide deleted-memory set

#### Scenario: Confirmation communicates project-wide scope
- **WHEN** the purge confirmation is shown
- **THEN** it explicitly states that active filters are ignored and the operation applies across the project

### Requirement: Purge preview supports an informed irreversible decision
Before execution, the system SHALL show the total number of deleted memories, the number eligible at the selected threshold, and the number too recent to purge. The system MUST require an explicit irreversible confirmation before permanently deleting any tombstone.

#### Scenario: Threshold change updates the decision context
- **WHEN** the user changes the threshold to another valid whole-day value
- **THEN** the confirmation presents total, eligible, and too-recent counts for that value before purge can be confirmed

#### Scenario: Cancellation preserves every tombstone
- **WHEN** the user cancels or dismisses the irreversible confirmation
- **THEN** the system performs no purge and preserves all memory entries

### Requirement: Purge permanently removes only eligible tombstones
The system SHALL physically remove each eligible deleted-memory file using the memory store's containment and file-safety protections. It MUST preserve non-deleted entries and deleted entries newer than the cutoff.

#### Scenario: Mixed memory states and ages
- **WHEN** a purge request considers eligible deleted entries, too-recent deleted entries, and non-deleted entries
- **THEN** only the eligible deleted entries are physically removed

#### Scenario: One deletion fails
- **WHEN** one eligible tombstone cannot be physically removed but another can
- **THEN** the system continues the request, counts the successful removal as purged, counts the unsuccessful removal as failed, and leaves unrelated entries intact

#### Scenario: Eligible tombstone file is already absent
- **WHEN** an eligible tombstone file disappeared after classification but before its unlink attempt
- **THEN** the system reconciles the absent tombstone from its indexes and counts the outcome as purged rather than failed

### Requirement: Purge returns a reconciled outcome
The system SHALL return purged, skipped, and failed counts for each completed purge request. Those counts MUST account for every deleted memory considered against the request's single cutoff instant.

#### Scenario: Mixed purge outcome
- **WHEN** a request contains eligible removals, too-recent tombstones, and an eligible removal failure
- **THEN** the response reports each considered tombstone exactly once as purged, skipped, or failed

#### Scenario: No tombstone is eligible
- **WHEN** all deleted memories are newer than the selected threshold
- **THEN** the response reports zero purged, all considered tombstones skipped, and zero failed without modifying memory files

### Requirement: Deleted count remains maintenance context
The Memory page SHALL present deleted volume only through a compact secondary action labeled `Purge deleted (N)`, where `N` is the project-wide deleted count. It MUST NOT present deleted volume as a primary Memory metric or health failure.

#### Scenario: No deleted memories exist
- **WHEN** the project has zero deleted memories
- **THEN** `Purge deleted (0)` remains visible but disabled

#### Scenario: Deleted memories exist
- **WHEN** the project has one or more deleted memories
- **THEN** the action is enabled while the normal Memory entry count remains the page's only primary metric

### Requirement: Cockpit refreshes after purge and preserves the receipt
The Memory workflow SHALL derive its deleted action count from the latest complete Memory dataset loaded on view mount, browser visibility return, or successful Memory mutation. Filter changes MUST NOT trigger a count refetch, and the workflow MUST NOT add periodic polling for the count. After purge execution, the workflow SHALL refresh its entries and deleted action count and SHALL keep the purged, skipped, and failed result visible until the user dismisses it or starts another purge flow.

#### Scenario: Successful or partial purge completes
- **WHEN** the purge operation returns an outcome
- **THEN** the Memory list and `Purge deleted (N)` count reflect the current store and the result counts remain visible for review

#### Scenario: Filters change
- **WHEN** the user changes state, category, agent, or text filters
- **THEN** the action count remains derived from the latest complete Memory dataset without starting a count refresh

#### Scenario: Existing full-load trigger occurs
- **WHEN** the Memory view mounts, the browser tab returns to visible, or a Memory mutation succeeds
- **THEN** the action count updates from the resulting complete Memory dataset without periodic polling
