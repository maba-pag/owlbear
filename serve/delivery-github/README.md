# owlbear-delivery-github — GitHub Publication Adapter

Fixed-operation GitHub publication adapters for Delivery. The package currently provides a deterministic in-memory implementation of the transport-free provider contract owned by `owlbear-delivery`; it does not publish over the network, merge pull requests, or expose a generic provider request method.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

There is no standalone launch command. Use `InMemoryPublicationProvider` in Delivery tests that need deterministic repository and pull-request state without subprocess or network effects.

```python
from owlbear_delivery import PublicationRepository
from owlbear_delivery_github import InMemoryPublicationProvider

provider = InMemoryPublicationProvider()
provider.add_repository(
    PublicationRepository(repository="example/project", default_branch="main")
)
```

The public provider models and `PublicationProvider` protocol are exported by `owlbear-delivery`.

## Configuration

The in-memory adapter has no environment variables, files, credentials, or command-line flags. Callers register repository state explicitly before exercising publication operations.

## Dependencies

| Package | Purpose |
|---------|---------|
| `owlbear-delivery` | Owns the transport-free publication models and provider protocol |
| `pydantic` | Validates strict provider request and response models |
