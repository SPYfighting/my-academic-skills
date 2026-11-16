# Installation

Clone the collection, then select the skill you need:

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
cd my-academic-skills
```

## Project-local discovery

Copy the complete skill directory into one of these project locations:

| Agent | Directory | Invocation |
|---|---|---|
| Codex | `<project>/.agents/skills/<skill-name>/` | Mention `$<skill-name>` or request its workflow |
| Claude Code | `<project>/.claude/skills/<skill-name>/` | `/<skill-name>` |
| OpenCode | `<project>/.opencode/skills/<skill-name>/` | Ask the agent to load the named skill |

OpenCode also discovers project `.agents/skills` and `.claude/skills`; choose one location to avoid duplicate copies. You can instead give any capable agent the path to the skill's `SKILL.md` and access to its sibling files. The repository's `AGENTS.md` is a maintenance guide; it does not need to replace your project's instructions.

For example, on macOS or Linux, from this repository directory:

```bash
mkdir -p /path/to/project/.agents/skills
cp -R scientific-illustrator-local /path/to/project/.agents/skills/
```

On Windows, from this repository directory:

```powershell
$projectSkills = 'D:\Research\my-project\.agents\skills'
New-Item -ItemType Directory -Force -Path $projectSkills | Out-Null
Copy-Item -LiteralPath '.\scientific-illustrator-local' -Destination $projectSkills -Recurse
```

Use the corresponding directory from the table for Claude Code or OpenCode. If a copy already exists, review the intended update before replacing it. These examples do not install a global skill.

Discovery conventions checked on 2026-09-08: [Codex](https://developers.openai.com/codex/skills), [Claude Code](https://code.claude.com/docs/en/skills), [OpenCode](https://opencode.ai/docs/skills/).

## Dependencies and validation

Dependencies belong to each skill, not to the collection as a whole.

- `binder-design-campaign`: install its pinned Python validation dependency with `python -m pip install -r binder-design-campaign/requirements.txt`; its computational workflows require separately configured scientific tools and a validated compute backend.
- `paper-anchor`: daily use needs only Markdown. Projects whose rules adopt it use the [workflow](../paper-anchor/SKILL.md) and [template](../paper-anchor/templates/PAPER.md) directly. The maintainer self-check uses the Python standard library.
- `scientific-illustrator-local`: follow its [environment and native-application setup](../scientific-illustrator-local/references/installation-and-compatibility.md). It requires CPython 3.11-3.13 and declared Python packages; Illustrator is needed only for native drawing. The optional VTracer executable is installed separately.
- `scientific-ppt-drawing`: follow its [setup and application control](../scientific-ppt-drawing/references/setup-and-app-control.md). It requires CPython 3.11-3.13 and its pinned Python packages; PowerPoint is needed for native visual and editability review. Windows PowerPoint has not been tested on hardware.

Run all checks from the repository root, using an appropriate Python environment:

```text
python check.py
```

To check only one skill, append its directory name. The Illustrator self-check can use its local `.venv` or an explicitly supplied `SCIENTIFIC_ILLUSTRATOR_PYTHON` path. The PowerPoint self-check uses the Python interpreter running `check.py`; use its prepared `.venv` when the system interpreter lacks the pinned packages. The runner does not install packages, start a native application, or upload files. Native application and scientific validation remain separate from these automated checks.
