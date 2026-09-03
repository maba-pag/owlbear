---
description: "Review and remove low-value tests from a scoped current suite"
agent: test-curator
---

Curate tests in ${input:scope:package, directory, test file, or changed-commit range (optional)}

## Execution Contract

Use the user's language unless they ask otherwise. Review current tests in the supplied scope using
the configured runners and Durable Test Admission. Inspect assertions and neighboring coverage
before editing. The curator may edit only test and scratch paths; it must not use task IDs, legacy
manifests, or acceptance-criteria labels as current ownership evidence.

Stop successfully when the selected scope has been reviewed and every changed test has focused
verification. An empty result means no low-value test was identified in that scope, not that the
entire repository is healthy.
