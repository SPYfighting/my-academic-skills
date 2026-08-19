# AGENTS.md

Routes agents to the skills here, and states the conventions for changing this
repository.

---

## Using a skill

| Ask | Read in full, then follow it |
|---|---|
| protein binders, miniproteins, epitope or hotspot choice, design campaigns | `binder-design-campaign/SKILL.md`, then its `workflows/binder-design.md` |
| structure or complex prediction, confidence assessment | same `SKILL.md`, then `workflows/structure-prediction.md` |
| protein stability, enzyme, interface or scaffold redesign | same `SKILL.md`, then `workflows/protein-design-general.md` |

Two properties of that protocol matter more than the rest:

- **A gate is a hard stop.** Present what
  `binder-design-campaign/checklists/gate-checklists.md` lists for the gate,
  then wait for the human. Keep the presentation and the next action in separate
  messages.
- **State only what you computed, and fetch every external identifier.**
  Accessions, PDB IDs, residue ranges and DOIs are the literal output of a
  lookup executed in the same session that wrote them.

To install a skill into another project instead of reading it here, see
`docs/installation.md`.

---

## Repository layout

One skill per top-level directory. Nothing else at the root except repository
documents and `check.py`.

```
<skill-name>/
  SKILL.md          the protocol; keep it under ~200 lines
  workflows/        one file per branch, stage by stage       (optional)
  references/       long-form detail, loaded on demand        (optional)
  checklists/       what to present at each human gate        (optional)
  templates/        starting points the agent copies and fills (optional)
  scripts/          runnable checks and helpers, plus selfcheck.py
  examples/         the fixture selfcheck.py runs against
  docs/             rationale and provenance, for humans, not loaded at runtime
```

`SKILL.md` is the only required file. The rest exist when the skill needs them.

A skill is self-contained: everything it needs travels with the directory, so
symlinking it into `~/.claude/skills/` is the whole installation.

## Adding a skill

1. Create `<skill-name>/SKILL.md` with `name` and `description` frontmatter.
   The directory name and the `name` field must match.
2. Write the mechanical parts as `scripts/`, the on-demand detail as
   `references/`, and keep `SKILL.md` short.
3. Add `scripts/selfcheck.py`. `check.py` finds it by convention and will report
   the skill as unchecked without it. Exercise the scripts on clean fixture data
   **and** on a deliberately corrupted copy; a check that never fails is broken.
4. Add one row to the table in `README.md` and in `README.en.md`.
5. Note it in `CHANGELOG.md`.

No change to `check.py` is needed.

## Version conventions

- Each skill lives in its own top-level directory; changes to one stay inside it.
- When editing a single skill, stage and commit that directory plus any
  repository-level document the change actually affects, and nothing else.
- Semantic versioning on the repository as a whole, recorded in `CHANGELOG.md`
  and `CITATION.cff`. A new skill is a minor bump; a change to how an existing
  skill behaves is a minor bump; a fix is a patch.
- Run `python check.py` before every push. All skills must pass.
- Credentials, private keys, local backups, campaign state and any material you
  do not have the right to publish stay out of Git. `.gitignore` covers the
  usual paths; confirm the rest yourself before pushing.
- Line endings are LF in the repository and in the checkout (`.gitattributes`).
  The scripts run on Linux clusters, where CRLF breaks a shebang.

## Writing rules

These follow the `writing-for-agents` discipline; load that skill before any
substantial edit to a `SKILL.md` or to this file.

1. **`SKILL.md` stays short.** It loads on every invocation, so every line costs
   on every turn. New detail goes into `references/` with a pointer added to the
   index at the foot of `SKILL.md`. Material only some branches reach belongs
   behind a pointer, not inline.
2. **Sharpen the pointer before inlining the material.** When the agent fails to
   reach a reference file, the fix is almost always the wording of the line that
   names it.
3. **Prefer a script to a paragraph.** Any rule checkable mechanically belongs
   in `scripts/`. This is why the protocol is a fraction of its source's length.
4. **One meaning, one place.** Repeat a *term* on purpose — `gate`, `frozen`,
   `roster`, `dossier`, `ledger`, *a filter, never an oracle* — and never repeat
   the explanation behind it. A restated rule is a maintenance bug and inflates
   its apparent rank.
5. **Prompt the positive.** State the target behaviour rather than banning its
   opposite; a prohibition earns its place only as a guardrail that cannot be
   phrased positively, and then it is paired with the positive target.
6. **Delete no-ops.** A line the model already obeys by default pays load to say
   nothing. Settle disagreements by running the document, not by arguing.
7. **No dependencies in `scripts/`.** Standard library only — these run inside
   compute jobs on clusters where installing anything is a negotiation.
8. **English prose, ASCII in program output.** The skill body is English so it
   works for any user and any agent. Markdown may use typographic punctuation;
   `print()` may not, because console encodings on Windows and on cluster login
   nodes mangle it. Do not add instructions about what language the agent should
   reply in — that belongs to the user's own configuration.
9. **Cite or delete.** Every empirical claim carries its source. Numbers from a
   published campaign are quoted as published.
10. **Tool facts are dated pointers, never authoritative.** The upstream README,
    model card or paper wins, and the prose says so.

## Before committing

```bash
python check.py
```

Every skill must pass. If you changed prose in `binder-design-campaign`, update
the affected row in `binder-design-campaign/docs/source-mapping.md`.

## Attribution

Content adapted from Anthropic's CC-BY-4.0 release and from MIT-licensed skill
collections stays attributed in `NOTICE.md`, both there and at its point of use.
Do not vendor code from another project — reference it.
