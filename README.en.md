# My Academic Skills

Research skills for Claude Code, Codex, and OpenCode. Each top-level skill directory is maintained independently; its `SKILL.md` describes the workflow, dependencies, and validation limits.

[中文](README.md) · [Installation](docs/installation.md) · [Repository conventions](AGENTS.md)

## Skills

| Skill | Purpose |
|---|---|
| [binder-design-campaign](binder-design-campaign/SKILL.md) | Plan protein binder design, structure prediction, or protein engineering with a user-approved execution limit and optional review checkpoints |
| [scientific-illustrator-local](scientific-illustrator-local/SKILL.md) | Rebuild scientific diagrams as editable vectors with live text and draw them in local Illustrator |
| [scientific-ppt-drawing](scientific-ppt-drawing/SKILL.md) | Draw editable scientific figures with native PowerPoint shapes and live text |

## Use

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
```

Copy the complete skill directory into your project's skill directory, or ask your agent to read its `SKILL.md` directly.

| Agent | Project skill directory |
|---|---|
| Codex | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| OpenCode | `.opencode/skills/` |

Prepare dependencies separately for each skill. See [installation](docs/installation.md) for examples.

## Check and maintain

```bash
python check.py
```

The checker discovers skills, validates their entry points, and runs each `scripts/selfcheck.py`. Prepare the relevant dependencies first. Automated checks do not establish scientific validity or compatibility with every application version. Follow [AGENTS.md](AGENTS.md) when adding a skill; keep detailed workflows inside that skill.

## License

The repository uses [MIT](LICENSE). See [NOTICE.md](NOTICE.md) for per-skill attribution and third-party terms.
