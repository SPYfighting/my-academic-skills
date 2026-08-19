# AGENTS.md

Routes agents to the skills in this repository, and states the rules for
changing them.

---

## Using a skill

| Ask | Read in full, then follow it |
|---|---|
| protein binders, miniproteins, epitope or hotspot choice, design campaigns | `skills/binder-design-campaign/SKILL.md`, then its `workflows/binder-design.md` |
| structure or complex prediction, confidence assessment | same `SKILL.md`, then `workflows/structure-prediction.md` |
| protein stability, enzyme, interface or scaffold redesign | same `SKILL.md`, then `workflows/protein-design-general.md` |

Two properties of that protocol matter more than the rest:

- **A gate is a hard stop.** Present what
  `skills/binder-design-campaign/checklists/gate-checklists.md` lists for the
  gate, then wait for the human. Keep the presentation and the next action in
  separate messages.
- **State only what you computed, and fetch every external identifier.**
  Accessions, PDB IDs, residue ranges and DOIs are the literal output of a
  lookup executed in the same session that wrote them.

To install a skill into another project instead of reading it here, see
`docs/installation.md`.

---

## Changing this repository

### What it is

A collection of agent skills. The deliverable is prose another agent reads and
acts on, plus standard-library Python checks. No build step, no runtime
dependency.

```
skills/<skill-name>/
  SKILL.md          the protocol; keep it under ~200 lines
  workflows/        one file per branch, stage by stage
  references/       long-form detail, loaded on demand
  checklists/       what to present at each gate
  templates/        starting points the agent copies and fills
  scripts/          runnable checks, standard library only
examples/<skill-name>/   fixtures the scripts run against
docs/                    installation, then per-skill rationale
check.py                 repository self-check
```

### Rules

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

### Before committing

```bash
python check.py
```

It runs every script against its fixture, then against a corrupted copy, and
asserts the validators reject the corrupted one and name the problem. Both
halves must pass: a check that never fails is broken.

If you changed prose, update the affected row in
`docs/<skill-name>/source-mapping.md`.

### Attribution

Content adapted from Anthropic's CC-BY-4.0 release and from MIT-licensed skill
collections stays attributed in `NOTICE.md`, both there and at its point of use.
Do not vendor code from another project — reference it.
