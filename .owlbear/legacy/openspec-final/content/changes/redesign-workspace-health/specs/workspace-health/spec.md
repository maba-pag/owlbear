## ADDED Requirements

### Requirement: Workspace health API
The system SHALL expose read-only aggregate workspace health at `GET /health`, focused module health at `GET /health/tasks`, `GET /health/requests`, `GET /health/memory`, and `GET /health/ideas`, and cheap process liveness at `GET /health/live`. Health reads MUST NOT mutate workspace files.

#### Scenario: Aggregate health read
- **WHEN** a client requests `GET /health`
- **THEN** the system checks tasks, requests, memory, and ideas and returns an independently typed result for every module

#### Scenario: Focused health read
- **WHEN** a client requests one module health endpoint
- **THEN** the system checks and returns only that module without mutating its storage

#### Scenario: Process liveness
- **WHEN** a client requests `GET /health/live` while the Cockpit process can serve requests
- **THEN** the system returns a successful liveness response without scanning workspace storage

#### Scenario: One module check fails
- **WHEN** one module raises an error while aggregate health is being calculated
- **THEN** that module is returned as check-failed and the completed results from the other modules are still returned

#### Scenario: Integrity findings exist
- **WHEN** the system successfully assembles a health document containing attention or unhealthy findings
- **THEN** it returns HTTP 200 because the document was produced successfully and Cockpit remains available to diagnose it

### Requirement: Evidence-based status states
The Cockpit SHALL represent overall and module health as checking, unknown, healthy, attention, unhealthy, or check-failed states with visible text and status lights. Checking and unknown SHALL use gray, healthy SHALL use green, attention SHALL use yellow, and unhealthy or check-failed SHALL use red.

#### Scenario: First health check is pending
- **WHEN** Cockpit has not yet received a completed module check
- **THEN** the overall and affected module indicators are gray and do not claim healthy, stale, or failed state

#### Scenario: Aggregate status precedence
- **WHEN** module results contain different states
- **THEN** the overall indicator uses the precedence unhealthy or check-failed, then attention, then checking or unknown, then healthy

#### Scenario: Health request cannot complete
- **WHEN** Cockpit cannot obtain an aggregate health response
- **THEN** the overall indicator reports a check failure and module rows without evidence remain unknown rather than healthy

#### Scenario: Connection state is degraded
- **WHEN** Cockpit loses its backend connection
- **THEN** the overall indicator is red and explicitly reports the connection problem without presenting task-feed freshness as task-storage health

### Requirement: Module-aware status presentation
The Workspace Status surface SHALL show separate task, request, memory, and ideas rows with each module's status, finding summary, and available module action. It SHALL expose detailed findings only when they remain unresolved or a repair attempt failed.

#### Scenario: All modules are healthy
- **WHEN** all four module checks complete without findings
- **THEN** the overall status and every module row show healthy state and no repair action

#### Scenario: Repairable task drift exists
- **WHEN** task health detects one or more deterministic repair opportunities
- **THEN** the task row shows attention, summarizes the repairable count, and offers one task repair action without presenting per-file choices or comparison screens

#### Scenario: Unresolved findings exist
- **WHEN** a module check finds a condition with no deterministic repair
- **THEN** its row shows unhealthy state and exposes enough path, code, and detail information for manual correction

#### Scenario: Repairable and unresolved task findings coexist
- **WHEN** task health contains at least one deterministic repair opportunity and at least one unresolved finding
- **THEN** the task row remains unhealthy, exposes the unresolved details, and still offers the single task repair action

### Requirement: Health refresh ordering
Cockpit SHALL refresh aggregate health periodically after the initial read and after workspace mutations known to affect health. It MUST NOT replace a newer module result with an older response that completed later.

#### Scenario: Workspace changes after initial health read
- **WHEN** Cockpit remains open after the initial health result
- **THEN** a later periodic or mutation-triggered aggregate read reflects subsequent workspace changes without requiring a page reload

#### Scenario: Older request completes after repair
- **WHEN** an aggregate health request started before task repair completes after Cockpit has applied the repair response's task-health snapshot
- **THEN** Cockpit ignores the older task result using request generation or `checked_at` ordering

### Requirement: Complete task-file validation
Task health SHALL validate every readable active and archived task against the complete persisted task contract and configured status and priority values. It SHALL report unreadable files and SHALL collect independently actionable defects instead of stopping after the first defect when parsing can safely continue.

#### Scenario: Readable task has multiple independent defects
- **WHEN** a task file can be parsed and violates more than one independently actionable persisted-field invariant
- **THEN** task health returns each defect that can be determined safely from that parse

#### Scenario: Task file cannot be read
- **WHEN** a task file cannot be read because of encoding or filesystem failure
- **THEN** task health reports the file as unhealthy and does not treat the read failure as a clean result

#### Scenario: Task location conflicts with state
- **WHEN** a valid task with archived state remains only in active task storage
- **THEN** task health reports deterministic archive reconciliation as an attention finding

### Requirement: Task graph integrity
Task health SHALL validate board-wide identity and references across active and archived tasks, including duplicate IDs, missing parent targets, missing dependency targets, missing archival-reference targets, self-references, and dependency cycles.

#### Scenario: Duplicate IDs in one directory
- **WHEN** more than one task file in active storage or more than one task file in archive storage has the same task ID
- **THEN** task health identifies the complete duplicate set before classifying it as deterministic or unresolved

#### Scenario: Duplicate ID across active and archive
- **WHEN** the same task ID exists in active and archive storage
- **THEN** task health identifies both records and classifies the conflict using their normalized content and state

#### Scenario: Duplicate set has mixed relationships
- **WHEN** three or more records share a task ID and no deterministic rule holds for the complete set
- **THEN** task health classifies the complete set as unresolved instead of repairing selected pairs independently

#### Scenario: Broken task reference
- **WHEN** a parent, dependency, or archival reference targets no active or archived task
- **THEN** task health reports the owning task, reference field, and missing target as unresolved

#### Scenario: Dependency cycle
- **WHEN** task dependencies contain a self-reference or multi-task cycle
- **THEN** task health reports every task participating in the cycle as unresolved

### Requirement: Decision and action request integrity
Request health SHALL validate every structured pending and resolved request record, including file readability, schema validity, request-ID uniqueness, owning-task existence, and consistency between request resolution state and storage location. Invalid records MUST NOT disappear through log-only skipping.

#### Scenario: Invalid request record
- **WHEN** a structured request file is unreadable or fails its persisted schema
- **THEN** request health reports the path and validation failure as unhealthy

#### Scenario: Request owner is missing
- **WHEN** a request references a task that exists in neither active nor archived task storage
- **THEN** request health reports the request and missing task ID as unresolved

#### Scenario: Request location drift
- **WHEN** a completed request remains in pending storage or an unresolved request appears in resolved storage
- **THEN** request health reports the location mismatch

### Requirement: Memory integrity
Memory health SHALL report unreadable memory records and duplicate memory UUIDs. It MUST NOT classify valid memory lifecycle states or their counts as health failures.

#### Scenario: Unreadable memory exists
- **WHEN** a memory file cannot be parsed as a valid persisted memory entry
- **THEN** memory health reports the unreadable record as unhealthy

#### Scenario: Duplicate memory UUID exists
- **WHEN** more than one memory file has the same UUID
- **THEN** memory health reports the conflicting paths instead of silently presenting one as canonical

#### Scenario: Memory lifecycle work is pending
- **WHEN** memories are pending, stale, contested, disputed, or soft-deleted but all records are valid
- **THEN** memory health remains healthy

### Requirement: Ideas integrity
Ideas health SHALL check only whether the configured ideas document is accessible and readable as UTF-8. A missing or empty ideas document MUST be healthy.

#### Scenario: Ideas document is absent
- **WHEN** no ideas document has been created
- **THEN** ideas health reports healthy state

#### Scenario: Ideas document is unreadable
- **WHEN** the ideas document exists but cannot be accessed or decoded as UTF-8
- **THEN** ideas health reports the failure as unhealthy

### Requirement: Deterministic task duplicate repair
`POST /health/tasks/repair` SHALL apply all currently discoverable deterministic task repairs without per-file user choices. It MUST NOT renumber task IDs or modify ambiguous duplicate content.

#### Scenario: Identical active and archived record
- **WHEN** active and archive storage contain semantically identical records with the same ID and archived state
- **THEN** repair deletes the redundant active copy and retains the archived copy

#### Scenario: Identical records in one directory
- **WHEN** every record in a same-directory duplicate set is semantically identical
- **THEN** repair keeps one deterministic canonical record and deletes the redundant copies

#### Scenario: Same frontmatter with different body sizes in one directory
- **WHEN** every record in a same-directory duplicate set has identical normalized frontmatter and one record has a unique greatest normalized body line count
- **THEN** repair retains the unique largest-body record, quarantines every smaller-body record in Kanban quarantine, and does not create action-request tasks for those quarantined duplicates

#### Scenario: Same frontmatter and tied body size
- **WHEN** same-directory duplicates have identical normalized frontmatter, different body content, and more than one record is tied for greatest normalized body line count
- **THEN** repair leaves every record unchanged and returns an unresolved finding

#### Scenario: Duplicate records have different frontmatter
- **WHEN** duplicate task IDs have different normalized frontmatter
- **THEN** repair leaves every record unchanged and returns an unresolved finding

#### Scenario: Cross-directory duplicate is not identical
- **WHEN** active and archive records share an ID but are not semantically identical
- **THEN** repair leaves both records unchanged and returns an unresolved finding

#### Scenario: Identical cross-directory record is not archived
- **WHEN** active and archive records are semantically identical but their persisted state is not archived
- **THEN** repair leaves both records unchanged and returns an unresolved location finding

#### Scenario: Heterogeneous duplicate set
- **WHEN** no deterministic rule holds for every member of a duplicate set
- **THEN** repair leaves the complete set unchanged and returns one unresolved set finding

#### Scenario: Deterministic file operation fails
- **WHEN** deletion, movement, or quarantine for a deterministic repair fails
- **THEN** repair retains or reports the resulting on-disk state and returns a failed outcome rather than claiming success

### Requirement: Synchronous convergent repair contract
Task repair SHALL rediscover repairable conditions from current storage, complete its work before responding, and return timing metadata, outcome counts, failed outcomes, remaining unresolved findings, and a post-repair task-health snapshot. Repeating repair against an already repaired workspace SHALL be safe and SHALL not depend on exactly-once delivery.

#### Scenario: Repair completes
- **WHEN** the task repair endpoint returns a completed response
- **THEN** every reported repair has reached a terminal outcome and the included task-health snapshot reflects a scan performed after those outcomes

#### Scenario: Client held stale findings
- **WHEN** storage changed after the client's previous health read but before repair begins
- **THEN** repair uses newly discovered current conditions rather than applying the client's stale finding list

#### Scenario: Repair is repeated
- **WHEN** the same repair request is repeated after deterministic findings were fixed
- **THEN** already-fixed conditions require no further mutation and remaining conflicts are still reported

#### Scenario: Repair request fails before a trustworthy post-scan
- **WHEN** the endpoint cannot complete repair and produce its post-repair health snapshot
- **THEN** it returns failure and Cockpit does not claim that task health was refreshed

### Requirement: Repair feedback remains visible
Cockpit SHALL use the task-health snapshot returned by a completed repair response without an immediate follow-up health request. It SHALL retain the latest repair receipt in the current Cockpit session until the user dismisses it or a later task repair supersedes it.

#### Scenario: Repair dialog closes after completion
- **WHEN** a task repair completes and its confirmation dialog closes
- **THEN** the user can still see completion time and removed, quarantined, unresolved, and failed outcomes

#### Scenario: Routine health polling continues
- **WHEN** later health reads update current health
- **THEN** they do not erase the retained repair receipt

#### Scenario: User dismisses receipt
- **WHEN** the user dismisses the latest task repair receipt
- **THEN** the receipt disappears without changing current health

#### Scenario: Cockpit session restarts
- **WHEN** the page is fully reloaded or Cockpit restarts
- **THEN** the previous repair receipt need not be restored from the server

### Requirement: Health and maintenance separation
Workspace health repair SHALL NOT release expired claims or compact activity history. Cockpit SHALL remove the generic Cleanup action that combines claim release, archive reconciliation, duplicate repair, and session cleanup, while preserving claim sweeping as an explicit Kanban maintenance operation outside Workspace Status.

#### Scenario: Task health repair runs
- **WHEN** the user invokes task health repair
- **THEN** deterministic storage repair and archive reconciliation may run but claim leases and activity retention remain unchanged

#### Scenario: Claim maintenance is needed
- **WHEN** expired claims exist
- **THEN** they do not make workspace health unhealthy and can be released through the separate Kanban maintenance operation
