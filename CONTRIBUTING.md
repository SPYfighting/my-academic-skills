# Contributing

Contributions are welcome, especially from people who have run a real campaign
and found where a protocol here is wrong.

**The conventions live in [`AGENTS.md`](AGENTS.md)**: repository layout, how to
add a skill, version and commit rules, and the writing discipline for anything
an agent reads. That file is the single source; this one only says what is most
useful to send and how to check it before you do.

## Most useful contributions

1. **Corrections from practice.** A flag that changed, an install recipe that no
   longer works, a threshold that behaved badly on a real target. Say what you
   ran and what happened.
2. **New compute adapters.** LSF, PBS, SGE, Kubernetes, a specific cloud. Write
   it against the four verbs in
   `binder-design-campaign/references/compute-backends.md`; nothing above the
   adapter should need to change.
3. **New failure modes.**
   `binder-design-campaign/references/failure-modes.md` is the most valuable
   file here. If you hit one that is not listed, describe how it shows up and
   how to catch it mechanically.
4. **Stronger checks.** A rule currently stated in prose that could be a script.
5. **A new skill.** See the steps in `AGENTS.md`.

## Before opening a pull request

```bash
python check.py
```

Every skill must pass. Then corrupt a copy of the fixture you touched — swap a
duplicate in, null a required column, break an ordering — and confirm the
validators exit 1 and name the problem. **A check that never fails is broken**,
which is `binder-design-campaign/references/failure-modes.md` §4 applied to this
repository itself.

If you changed prose in a skill, update the affected row in that skill's
`docs/source-mapping.md` where one exists.

## Scope

Read [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md) before proposing anything that
widens what a skill will design.

## Licensing

Contributions are accepted under this repository's MIT licence. Content adapted
from Anthropic's CC-BY-4.0 release stays attributed in
[`NOTICE.md`](NOTICE.md); do not remove or weaken that file. Do not vendor code
from another project — reference it.
