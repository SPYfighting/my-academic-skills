# My Academic Skills

Research skills for Claude Code, Codex, and OpenCode, covering paper and evidence planning, computational protein design, and editable scientific figures. Each top-level skill directory is maintained independently. Its `SKILL.md` describes the workflow, dependencies, and validation limits.

[中文](README.md) · [Installation](#installation) · [Repository conventions](AGENTS.md)

## Skills

| Skill | Purpose |
|---|---|
| [binder-design-campaign](binder-design-campaign/SKILL.md) | Plan protein binder design, structure prediction, or protein engineering with a user-approved execution limit and optional review checkpoints |
| [paper-anchor](paper-anchor/SKILL.md) | Use `PAPER.md` to track paper claims and evidence, with links to active tasks, available results, and figures. Projects whose rules adopt it use it by default |
| [scientific-illustrator-local](scientific-illustrator-local/SKILL.md) | Rebuild scientific diagrams as editable vectors with live text and draw them in local Illustrator |
| [scientific-ppt-drawing](scientific-ppt-drawing/SKILL.md) | Draw editable scientific figures with native PowerPoint shapes and live text |

## Installation

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
cd my-academic-skills
```

Copy the complete skill directory to the location for your agent. You can also give the agent the path to `SKILL.md` and access to its sibling files. For Codex, for example, copy `paper-anchor/` to `.agents/skills/paper-anchor/` in the target project.

| Agent | Project skill directory |
|---|---|
| [Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) | `.agents/skills/<skill-name>/` |
| [Claude Code](https://code.claude.com/docs/en/skills#choose-where-skills-load) | `.claude/skills/<skill-name>/` |
| [OpenCode](https://opencode.ai/docs/skills/#discovery) | `.opencode/skills/<skill-name>/` |

OpenCode also discovers project-local `.agents/skills/` and `.claude/skills/`. Use one location per skill.

### Per-skill dependencies

- **binder-design-campaign**. From the repository root, run `python -m pip install -r binder-design-campaign/requirements.txt` to prepare the self-check. Follow the [skill instructions](binder-design-campaign/SKILL.md) for its computational dependencies.
- **paper-anchor**. Daily use needs only Markdown. The maintainer self-check uses the Python standard library. See the [usage guide](paper-anchor/README.md).
- **scientific-illustrator-local**. Follow the [environment and compatibility guide](scientific-illustrator-local/references/installation-and-compatibility.md) for CPython 3.11–3.13 and its declared packages. Native drawing uses Illustrator. VTracer is optional.
- **scientific-ppt-drawing**. Follow the [setup and application control guide](scientific-ppt-drawing/references/setup-and-app-control.md) for CPython 3.11–3.13 and its pinned packages. Native rendering and editing checks require PowerPoint.

## Check and maintain

```bash
python check.py
python check.py paper-anchor
```

Run these commands from the repository root. The first checks all skills, and the second shows how to check one. The runner calls each skill's `scripts/selfcheck.py`. The Illustrator self-check can use its local `.venv` or `SCIENTIFIC_ILLUSTRATOR_PYTHON`. The PowerPoint self-check uses the interpreter running `check.py`. Validate scientific conclusions and native application behavior separately. Follow [AGENTS.md](AGENTS.md) when adding a skill.

## License

The repository uses [MIT](LICENSE). See [NOTICE.md](NOTICE.md) for per-skill attribution and third-party terms.
