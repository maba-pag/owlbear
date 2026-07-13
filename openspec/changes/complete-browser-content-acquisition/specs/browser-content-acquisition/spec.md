## ADDED Requirements

### Requirement: Shared single-page acquisition capability
The system SHALL expose single-page browser content acquisition through both a reusable programmatic API and an agent-callable MCP tool. Both surfaces SHALL use the same result semantics and SHALL acquire only the caller-requested page unless a later caller explicitly requests another URL.

#### Scenario: Agent acquires a rendered page
- **WHEN** an agent invokes the MCP acquisition tool with a valid HTTP(S) URL
- **THEN** the system returns the structured outcome produced by the shared acquisition capability
- **AND** the MCP surface does not apply independent extraction, authentication, or success rules

#### Scenario: Library caller acquires a rendered page
- **WHEN** an in-process consumer invokes the reusable acquisition API with the same request
- **THEN** the system provides the same acquisition behavior and result fields without requiring an MCP-to-MCP call

### Requirement: Structured Markdown-first success result
For a successful acquisition, the system SHALL return a machine-readable result containing a success status, requested URL, canonical final URL, redirect chain, page title, non-empty cleaned Markdown, normalized discovered links, content hash, fetch timestamp, and non-sensitive diagnostics. Markdown SHALL be the canonical content representation.

#### Scenario: Successful rendered acquisition
- **WHEN** the requested page reaches meaningful rendered content and extraction succeeds
- **THEN** the result status is successful
- **AND** every required provenance and content field is present
- **AND** the Markdown represents the meaningful page content rather than raw rendered HTML or navigation chrome

#### Scenario: Diagnostic HTML is requested
- **WHEN** a caller explicitly enables supported HTML diagnostics
- **THEN** the system may include sanitized HTML as diagnostic evidence
- **AND** raw or sanitized HTML does not replace canonical Markdown in the normal result

### Requirement: User-authorized web navigation
The system SHALL accept any explicitly requested syntactically valid HTTP(S) URL as authorization to navigate that page and follow its HTTP(S) web redirects. It SHALL record redirects and SHALL NOT reject a requested URL solely because it resolves to a private, loopback, link-local, or otherwise non-public network address.

#### Scenario: Caller requests an intranet URL
- **WHEN** the caller supplies a valid HTTP(S) URL that resolves to a private network address
- **THEN** the system attempts acquisition under the same content and authentication rules as other web URLs
- **AND** private addressing alone is not a rejection reason

#### Scenario: Page redirects during navigation
- **WHEN** acquisition follows one or more HTTP(S) redirects
- **THEN** the result records the redirect chain and canonical final URL
- **AND** validation applies to the final rendered page before success is reported

#### Scenario: Caller requests an unsupported operation
- **WHEN** the request contains a non-HTTP(S) scheme, a download target, or caller-supplied JavaScript
- **THEN** the system rejects the operation with a structured non-success result
- **AND** it does not execute or persist the rejected content

### Requirement: Session-assisted authentication
The system SHALL use a dedicated persistent browser session so existing authentication can be reused. When user interaction is required, it SHALL return an `authentication_required` outcome and keep the visible browser session available for manual completion within the supported interaction window. The acquisition interface MUST NOT accept, store, return, or automate passwords, MFA codes, or other corporate credentials.

#### Scenario: Existing session is authenticated
- **WHEN** the persistent browser profile already has valid authorization for the requested page
- **THEN** acquisition proceeds without asking the caller for credentials

#### Scenario: Manual login or MFA is required
- **WHEN** the final rendered state requires login, consent, trust confirmation, or MFA interaction
- **THEN** the system reports `authentication_required` rather than content success
- **AND** the visible persistent browser remains available for the user to complete the interaction
- **AND** a subsequent acquisition can reuse the completed session

#### Scenario: Caller supplies credential material
- **WHEN** a caller attempts to provide a password, MFA code, or equivalent credential through the acquisition interface
- **THEN** the system rejects that credential input
- **AND** the credential is not logged, stored, or submitted

### Requirement: Capability-based authentication support
The system SHALL report authentication integrations according to capabilities available in the current environment rather than treating the operating system as a blanket allow or deny condition. Absence of an optional corporate SSO integration MUST NOT prevent public or ordinarily authenticated pages from using the persistent browser session.

#### Scenario: Optional corporate SSO integration is unavailable
- **WHEN** the host cannot provide a platform-specific corporate SSO integration
- **THEN** the system reports that capability as unavailable
- **AND** it still permits public acquisition and manual or ordinary persistent-session authentication

#### Scenario: Supported corporate SSO integration is available
- **WHEN** the host provides a validated corporate SSO integration
- **THEN** the persistent browser session can use it without changing the acquisition result contract

### Requirement: Rendered-content readiness
The system SHALL wait within explicit navigation and readiness deadlines for meaningful rendered content. By default it SHALL require non-empty meaningful content to remain stable across observations; when a readiness selector is supplied, it SHALL also require that selector to become ready. A fixed delay alone MUST NOT establish readiness.

#### Scenario: JavaScript content appears after initial navigation
- **WHEN** the initial document is a shell and meaningful content renders before the deadline
- **THEN** acquisition waits for stable meaningful content before extraction

#### Scenario: Default content never becomes meaningful
- **WHEN** meaningful rendered content does not stabilize before the readiness deadline
- **THEN** the system returns `content_not_ready`
- **AND** it does not report an empty shell as successful content

#### Scenario: Readiness selector does not become ready
- **WHEN** a supplied readiness selector does not reach its required state before the deadline
- **THEN** the system returns `content_not_ready` with selector diagnostics

### Requirement: Explicit content selection
The system SHALL support an optional content selector that limits canonical extraction to the matched rendered region. A missing or empty selected region SHALL be a structured non-success result.

#### Scenario: Content selector matches meaningful content
- **WHEN** the supplied content selector matches a non-empty rendered region
- **THEN** canonical Markdown and discovered links are derived from that region

#### Scenario: Content selector is missing or empty
- **WHEN** the supplied content selector has no match or its matched region has no meaningful content
- **THEN** the system returns a selector-specific non-success result
- **AND** it does not silently fall back to unrelated page content

### Requirement: Page-state validation
The system SHALL validate the final rendered page before reporting success. Login, consent, trust, access-denied, unrelated redirect, empty-content, and extraction-failure states MUST produce structured non-success outcomes rather than plausible Markdown success.

#### Scenario: Final page is an authentication or consent page
- **WHEN** final-page validation identifies login, consent, trust, or equivalent authentication interaction
- **THEN** the system returns `authentication_required`
- **AND** extracted page chrome or form text is not returned as successful content

#### Scenario: Final page denies access
- **WHEN** final-page validation identifies an access-denied or insufficient-permission state
- **THEN** the system returns an access-denied non-success outcome

#### Scenario: Final page is unrelated to the requested flow
- **WHEN** redirects end on a page that is neither requested content nor a recognized authentication step for that content
- **THEN** the system returns a redirect-validation non-success outcome with the observed final URL

#### Scenario: Meaningful page cannot be converted
- **WHEN** rendered content is present but canonical Markdown extraction fails or produces no meaningful content
- **THEN** the system returns an extraction non-success outcome with non-sensitive diagnostics

### Requirement: Inert normalized link discovery
The system SHALL return normalized HTTP(S) links discovered in the canonical content region without opening, approving, registering, or ingesting them. It SHALL exclude unsupported schemes and fragment-only duplicates from the discovered-link result.

#### Scenario: Page contains relative and absolute links
- **WHEN** successful canonical content contains navigable relative and absolute HTTP(S) links
- **THEN** the result contains normalized absolute links resolved against the canonical page URL
- **AND** duplicate equivalent links are represented once

#### Scenario: Page contains discovered links
- **WHEN** acquisition returns one or more discovered links
- **THEN** no discovered link is navigated, approved, registered, refreshed, or ingested as a side effect

### Requirement: Non-sensitive diagnostics
The system SHALL provide diagnostics sufficient to distinguish navigation, authentication, readiness, selection, validation, and extraction failures. Diagnostics MUST NOT include credential values, browser storage secrets, session tokens, or unredacted sensitive headers.

#### Scenario: Acquisition fails
- **WHEN** any acquisition stage returns a non-success status
- **THEN** diagnostics identify the failed stage and useful observed state
- **AND** prohibited secret material is absent

### Requirement: Acquisition remains non-interactive automation
The acquisition capability SHALL remain distinct from interactive browser action tools and SHALL NOT expose arbitrary click, type, script, or form-submission operations through its request contract.

#### Scenario: Caller needs interactive page manipulation
- **WHEN** a workflow requires arbitrary clicking, typing, scripting, or form submission beyond manual authentication in the visible browser
- **THEN** the caller must use a separately authorized interactive browser capability
- **AND** the acquisition request contract remains unchanged
