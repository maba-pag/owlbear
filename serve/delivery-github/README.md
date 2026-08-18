# owlbear-delivery-github — GitHub Publication Adapter

Fixed-operation GitHub publication adapters for Delivery. The package provides a GitHub CLI transport and a deterministic in-memory implementation of the transport-free provider contract owned by `owlbear-delivery`; it cannot merge pull requests or issue generic provider requests.

**Use this guide when:** you need to change or test the GitHub pull-request publication boundary used
by Delivery.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

There is no standalone launch command. Use `GitHubCliPublicationProvider` in application composition and `InMemoryPublicationProvider` in tests that need deterministic repository and pull-request state.

```python
from owlbear_delivery_github import GitHubCliPublicationProvider

provider = GitHubCliPublicationProvider(timeout_seconds=30)
repository = provider.read_repository("example/project")
```

The CLI adapter runs only code-owned `gh api` argument vectors for repository and pull-request reads, draft PR creation, generated metadata updates, and draft/ready transitions.

```python
from owlbear_delivery import PublicationRepository
from owlbear_delivery_github import InMemoryPublicationProvider

provider = InMemoryPublicationProvider()
provider.add_repository(PublicationRepository(repository="example/project", default_branch="main"))
```

The public provider models and `PublicationProvider` protocol are exported by `owlbear-delivery`.

## Configuration

`GitHubCliPublicationProvider` requires an authenticated `gh` executable on `PATH` and accepts a positive per-operation timeout in seconds. It reads no token or credential from Delivery configuration. The in-memory adapter has no environment variables, files, credentials, or command-line flags; callers register repository state explicitly.

## Dependencies

| Package | Purpose |
| --- | --- |
| `owlbear-delivery` | Owns the transport-free publication models and provider protocol |
| `pydantic` | Validates strict provider request and response models |

The GitHub CLI is an external runtime dependency for `GitHubCliPublicationProvider`; it is not required for the in-memory adapter.
