# Setup

This folder owns the procedures for installing OwlBear into another project and sharing one
installation with teammates. It is an orientation layer; the exact first-time commands remain in
the [setup guide](setup-guide.md), and multi-project workflows remain in the
[sharing guide](sharing-guide.md).

## Choose a route

| Goal | Start here | Expected result |
| --- | --- | --- |
| Install OwlBear in one project | [Setup guide](setup-guide.md) | A project with merged VS Code settings, MCP servers, hooks, and Delivery configuration |
| Share one OwlBear checkout with several projects | [Sharing guide](sharing-guide.md) | Teammates use the same installation path and understand the update boundary |
| Change the initializer | [`init.py`](init.py) | The initializer is the implementation source of truth; its regression coverage is maintained in the development checkout |

## First-success checklist

1. Check the prerequisites in the [setup guide](setup-guide.md#prerequisites).
   **Expected result:** Python, `uv`, VS Code with GitHub Copilot, Git, and GitHub CLI are available.
2. Follow the four-step Quick Start in the [setup guide](setup-guide.md#quick-start).
   **Expected result:** setup completes from the target project root and writes the expected project
   configuration without replacing unrelated user settings.
3. Run the verification section in the [setup guide](setup-guide.md#verify-the-installation).
   **Expected result:** the shared customization roots and five seeded MCP servers are visible in
   VS Code.

If setup reports a path, profile, or hook conflict, stop and use the matching troubleshooting
section in the [setup guide](setup-guide.md) rather than editing generated configuration by hand.

## What belongs elsewhere

- [`seed/`](../seed/) contains the files that `init.py` copies into a consumer project. It is an input tree,
  not a documentation tree.
- [`share/`](../share/README.md) contains portable agents, skills, instructions, and prompts.
- [`serve/`](../serve/README.md) contains runtime packages and MCP servers.
- Repository-only CI automation lives in the OwlBear `dev` checkout's `.github/` tree; it is not
   installed into consumer projects.

There is intentionally no `seed/README.md`: `init.py` walks every seed file into the target, so a
root README there would be copied as the consumer project's `README.md` and could overwrite its
front door. This folder is the canonical place to explain the seed tree instead.
