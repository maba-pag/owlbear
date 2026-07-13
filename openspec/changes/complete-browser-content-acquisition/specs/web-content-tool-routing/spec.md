## ADDED Requirements

### Requirement: Known-page acquisition routing
OwlBear's active agent and workflow guidance SHALL route a known public URL through built-in web access when browser rendering is unnecessary, a rendered or authenticated URL through browser content acquisition, and supported document formats through MarkItDown.

#### Scenario: Agent receives a known public URL
- **WHEN** an agent needs content from a known public page that built-in web access can read correctly
- **THEN** active guidance directs the agent to built-in web access

#### Scenario: Agent receives a rendered or authenticated URL
- **WHEN** an agent needs content that requires browser rendering or a persistent authenticated session
- **THEN** active guidance directs the agent to browser content acquisition

#### Scenario: Agent receives a supported document
- **WHEN** an agent needs content from a document format owned by MarkItDown
- **THEN** active guidance retains MarkItDown as the conversion path
- **AND** browser acquisition does not replace document conversion ownership

### Requirement: Complete DDGS retirement
The distributed OwlBear system SHALL NOT install, register, grant, bootstrap, or actively recommend DDGS. Workspace configuration, seed configuration, dependency metadata, setup behavior, agent tool grants, and active research guidance MUST be free of DDGS integration.

#### Scenario: A new OwlBear workspace is initialized
- **WHEN** setup creates its dependency and MCP configuration
- **THEN** DDGS is neither installed nor registered
- **AND** the browser MCP capability required for rendered or authenticated acquisition is available through the supported configuration path

#### Scenario: An agent loads acquisition or research guidance
- **WHEN** an OwlBear agent determines how to read a known URL
- **THEN** no active grant or instruction offers DDGS search or extraction
- **AND** the guidance selects built-in web access, browser acquisition, or MarkItDown according to content type

#### Scenario: Existing workspace dependencies are synchronized
- **WHEN** the project dependency set is installed from its declared lock and package metadata
- **THEN** DDGS is not a direct OwlBear dependency

### Requirement: Open-ended DDGS search is not preserved
The system SHALL treat open-ended DDGS web search as intentionally unavailable after this change and SHALL NOT retain a hidden or fallback DDGS path for compatibility.

#### Scenario: Workflow lacks a known URL
- **WHEN** a workflow requests open-ended DDGS web search rather than acquisition of a known URL
- **THEN** OwlBear does not invoke DDGS or silently substitute a DDGS-compatible fallback
- **AND** restoration of open-ended search requires a separately justified capability change

### Requirement: Existing browser interaction remains separate
The system SHALL preserve existing interactive browser operations as a separate capability from browser content acquisition. Routing guidance MUST NOT represent acquisition as a general-purpose replacement for authorized navigation, click, type, select, read, or snapshot workflows.

#### Scenario: Agent needs a browser action rather than content acquisition
- **WHEN** an agent workflow requires an existing interactive browser operation
- **THEN** it continues to use the separately granted interactive tool
- **AND** the acquisition tool is not expanded with arbitrary actions
