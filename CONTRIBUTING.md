# Contributing

Contributions are welcome, particularly from people who have run a real campaign
and found where this protocol is wrong.

## Most useful contributions

1. **Corrections from practice.** A flag that has changed, an install recipe
   that no longer works, a threshold that behaved badly on a real target. Say
   what you ran and what happened.
2. **New compute adapters.** LSF, PBS, SGE, Kubernetes, a specific cloud. Write
   it against the four verbs in `skills/binder-design-campaign/references/compute-backends.md` and nothing
   above the adapter should need to change.
3. **New failure modes.** `skills/binder-design-campaign/references/failure-modes.md` is the most valuable
   file here and it is built from published evidence plus the source prompt's
   accumulated warnings. If you hit a new one, describe how it manifests and how
   to catch it mechanically.
4. **Stronger checks.** A rule currently stated in prose that could be a script.

## House rules

These are the same rules `AGENTS.md` gives to agents working in this repository.

- **`SKILL.md` stays under ~400 lines.** It is loaded on every invocation. New
  detail goes in `references/` with a pointer added to the index in §11.
- **Prefer a script to a paragraph.** Anything checkable mechanically belongs in
  `scripts/`.
- **No dependencies in `scripts/`.** Standard library only — these run inside
  compute jobs on clusters where installing anything is a negotiation.
- **English, ASCII in program output.** The skill body is English so it works
  for any user and any agent. Markdown may use typographic punctuation;
  `print()` may not, because console encodings on Windows and on cluster login
  nodes mangle it.
- **Do not add instructions about what language the agent should reply in.**
  That belongs to the user's own configuration.
- **Cite or delete.** Every empirical claim carries its source. Numbers from the
  published campaign are quoted as published.
- **Tool facts are dated pointers, never authoritative.** The upstream README,
  model card or paper wins, and the prose must say so.

## Before you open a pull request

Run every script against the fixture and confirm all exit 0:

```bash
python check.py
```

Then corrupt a copy of the fixture — duplicate a sequence, null a `pose_dockq`,
break the rank ordering, collapse `root_backbone_id` — and confirm the first two
scripts exit 1 and name the problem. **A check that never fails is broken**, per
this skill's own `failure-modes.md` §4.

If you changed prose, re-read `docs/binder-design-campaign/source-mapping.md` and update the row your
change affects.

## Scope

Please read `RESPONSIBLE_USE.md` before proposing anything that broadens what
the skill will design.

## Licensing

Contributions are accepted under the MIT licence of this repository. Content
adapted from Anthropic's CC-BY-4.0 release must remain attributed in
`NOTICE.md`; do not remove or weaken that file. Do not vendor code from other
projects — reference it.
