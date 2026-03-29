# Sharing OwlBear with Teammates

> How to give a teammate access to OwlBear for an existing project.

## Sharing Model

OwlBear uses a **shared installation** model: a single owlbear repository lives on a
developer's machine alongside their project directories. Each project references owlbear
using relative paths (e.g., `../owlbear/agents`). There is no packaging step — clone is
install.

This means sharing owlbear with a teammate means they clone <strong>both</strong>:

1. The **owlbear** repository (shared tooling)
2. The **project** repository (their actual project)

Both repos must sit on the same drive and in a sibling layout for the relative paths to
work.

> **Windows limitation:** owlbear and the project must be on the **same drive**.
> Cross-drive relative paths raise a `ValueError` in `setup.py` before any files are
> written. macOS and Linux are not affected.

---

## Set Up for a Teammate

Walk the teammate through these steps:

```powershell
# 1. Clone owlbear to a convenient parent directory (same drive as the project)
git clone https://github.com/your-org/owlbear.git C:\Dev\owlbear

# 2. Clone the project repository as a sibling
git clone https://github.com/your-org/my-project.git C:\Dev\my-project

# 3. Bootstrap owlbear into the project workspace
cd C:\Dev\my-project
python ..\owlbear\scripts\setup.py

# 4. Download kanban-md (Windows only)
.\kanban\setup.ps1

# 5. Open the project in VS Code
code .
```

After VS Code opens, have the teammate verify the setup using the **Diagnostics view**
(right-click the Chat panel → "Diagnostics") — it should show owlbear agents, skills,
and instructions loaded from the shared installation.

See [setup-guide.md](setup-guide.md) for the full verification checklist and
troubleshooting reference.

---

## What's Shared vs. Project-Local

| Resource | Location | Shared? |
|----------|----------|---------|
| Agents (`.agent.md`) | `../owlbear/agents/` | Yes — all teammates get the same agents |
| Skills (`SKILL.md`) | `../owlbear/skills/` | Yes — all teammates get the same skills |
| Instructions (`*.instructions.md`) | `../owlbear/instructions/` | Yes — shared baseline |
| MCP server code | `../owlbear/packages/` | Yes — started from owlbear via `uv run --project` |
| Kanban board | `kanban/tasks/` in project | No — per-project |
| `owlbear-project.json` | project root | No — per-project |
| `.github/copilot-instructions.md` | project root | No — per-project (override layer) |
| `data/knowledge/` | project root | No — per-project |

Project-local resources can override or extend shared owlbear resources. See the
[Customization](setup-guide.md#adding-local-agents) section of the setup guide.

---

## Team Conventions

### Agent naming

Each teammate's project can add local agents, but agent names must be unique. VS Code
loads agents from all configured locations simultaneously and does **not** deduplicate
same-name agents. Two agents named `reviewer.agent.md` from different locations will
both appear in the picker.

**Convention:** Prefix project-specific agents with the project name:
`my-project-reviewer.agent.md`, not `reviewer.agent.md`.

### Project-specific instructions

The `.github/copilot-instructions.md` file in the project directory is the right place
for project-specific rules (coding style, domain conventions, restricted tools). This
file takes priority over the owlbear shared instructions and is already created by
`setup.py` — teammates just need to keep it in source control.

### Monorepo alternative

If the project is a monorepo, VS Code's `chat.useCustomizationsInParentRepositories`
setting allows owlbear customizations to be discovered from a parent directory. This
eliminates the need for the sibling-dir setup but requires all developers to have the
same directory structure. Use this sparingly — the sibling layout is simpler.

---

## Organization-Level Sharing (GitHub Teams)

For organizations with GitHub Copilot Business or Enterprise, VS Code supports
**organization-level agents** that are discovered automatically for all members without
any local setup step. This is an alternative to the filesystem sharing model above,
but it covers agents only (not MCP servers, skills, or instructions).

If your team has org-level Copilot access, consider publishing owlbear agents to the
organization agent registry as a complement to the local installation.

---

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| `ValueError` during `setup.py` | Ensure owlbear and project are on the same Windows drive |
| Agents missing after setup | Run `setup.py` again; check that `.vscode/settings.json` was created and contains `chat.agentFilesLocations` pointing to the owlbear installation |
| `uv` not found | Install uv globally: `pip install uv` or see [uv docs](https://docs.astral.sh/uv/) |
| `kanban-md.exe` missing | Run `.\kanban\setup.ps1` (Windows only; PowerShell required) |
| Different owlbear versions between teammates | Pin owlbear to a tag or commit SHA in team onboarding docs; `git pull` + re-run `setup.py` to update |
