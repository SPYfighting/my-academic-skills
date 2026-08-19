# Installation

A skill is a plain directory: `binder-design-campaign/`. Installing it
means making that directory visible to your agent. Nothing is compiled and
nothing is installed system-wide.

Requirements: Python 3.8 or newer, for the scripts in `scripts/`. Standard
library only.

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
cd my-academic-skills
```

---

## Claude Code

**User-level** (available in every project):

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/binder-design-campaign" ~/.claude/skills/binder-design-campaign
```

**Project-level** (this project only, and committable alongside it):

```bash
mkdir -p /path/to/project/.claude/skills
ln -s "$PWD/binder-design-campaign" \
      /path/to/project/.claude/skills/binder-design-campaign
```

Copy instead of symlinking if you prefer to pin a version:

```bash
cp -r binder-design-campaign ~/.claude/skills/
```

Verify with `/skills` (or ask the agent to list its skills); the entry appears
as `binder-design-campaign`.

## Windows

Symlinks need Developer Mode or an elevated shell. Copying is simpler:

```powershell
$dest = "$env:USERPROFILE\.claude\skills\binder-design-campaign"
New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
Copy-Item -Recurse -Force .\binder-design-campaign $dest
```

Or, with Developer Mode enabled:

```powershell
New-Item -ItemType SymbolicLink -Path $dest `
         -Target (Resolve-Path .\binder-design-campaign)
```

## opencode

opencode discovers skills in the same layout. Place the directory under either:

```
~/.config/opencode/skill/binder-design-campaign/
<project>/.opencode/skill/binder-design-campaign/
```

If your version does not discover skills, use the AGENTS.md route below —
opencode reads `AGENTS.md` from the project root.

## Codex and other AGENTS.md readers

These runtimes have no skill mechanism, but they read `AGENTS.md`. Two options.

**Vendored** — copy the skill into your project and point at it:

```bash
mkdir -p .agent-skills
cp -r /path/to/my-academic-skills/binder-design-campaign .agent-skills/
```

Then append to your project's `AGENTS.md`:

```markdown
## Protein design work

For any request involving protein binder design, structure prediction, epitope
selection, or protein engineering, read
`.agent-skills/binder-design-campaign/SKILL.md` in full and follow it. It is a
gated protocol: at each gate you present the material listed in its
`checklists/gate-checklists.md` and wait for the human before proceeding.
```

**Submodule** — if you would rather track upstream:

```bash
git submodule add https://github.com/SPYfighting/my-academic-skills.git .agent-skills/my-academic-skills
```

and point the `AGENTS.md` paragraph at
`.agent-skills/my-academic-skills/binder-design-campaign/SKILL.md`.

## Any other agent

The skill is Markdown with relative links. Give the agent the path to
`SKILL.md`, make sure it can read sibling directories, and it will work. There
is no frontmatter requirement beyond the two fields at the top of `SKILL.md`
(`name`, `description`), which follow the Anthropic skill specification.

---

## Verify the install

Ask the agent something in scope and check that it goes to the gates rather than
starting work:

> Design binders against PD-L1.

Expected: it opens G0 and asks what the experiment will measure, what would
count as success and failure, and what the design must not do, before it says
anything about pipelines or tools.

Then check the scripts run:

```bash
python check.py
```

Every skill's self-check runs against its bundled fixture, then against a
corrupted copy. Exit code 0 means all of them behaved as expected.

---

## Setting up a campaign directory

The skill writes campaign state under a root you choose at G0:

```
<campaign_root>/
  state/
    campaign_config.yaml
    decisions.jsonl
    method_vocab.json
    sheet_schema.json
    roster.jsonl
    governor.json
    heartbeat.json
    dossiers/<target>.md
    epitopes/<target>.json
    gates/<target>.json
  ledger/
    <writer>.jsonl
    job_metadata/<writer>.jsonl
    rejects/<writer>.jsonl
    deviations.jsonl
  out/                     job outputs, one directory per job_id
  deliverables/
```

`binder-design-campaign/examples/` is a miniature of this, with two targets and six rows each.
Copy its `sheet_schema.json` as a starting point, edit `ranking_arms`,
`designs_per_target`, `final_seed_tier` and the method enums to match your
campaign, and freeze it before the first production job.

The protocol keeps every intermediate. Check your quota at G0 and again at G4.
