# my-academic-skills

Agent skills for research work, built on one principle: **every judgement a
domain expert would want to see is a checkpoint the human signs off, and every
rule that can be checked mechanically is a script rather than a paragraph.**

Works with Claude Code, Codex, opencode and anything else that reads a
`SKILL.md` or an `AGENTS.md`. No runtime; Python 3.8+ for the checks.

[中文说明](README.zh-CN.md) · [Installation](docs/installation.md) · [Responsible use](RESPONSIBLE_USE.md)

## Skills

| Skill | What it does | Docs |
|---|---|---|
| [`binder-design-campaign`](skills/binder-design-campaign/) | Gated computational protein campaigns: de novo miniprotein binder design, structure and complex prediction, protein engineering | [rationale](docs/binder-design-campaign/design-rationale.md) · [source mapping](docs/binder-design-campaign/source-mapping.md) |

---

## binder-design-campaign

Adapted from the [protocol prompt Anthropic released][prompt] with its
[autonomous binder-design campaigns][blog] and [technical report][report], with
one deliberate inversion. The source prompt was written for a fully autonomous
48-hour run and was explicitly forbidden to ask questions. This skill keeps the
science and reverses that: **every decision a domain expert would want to see is
a gate, and the campaign stops there until a human signs off.**

[prompt]: https://huggingface.co/datasets/Anthropic/claude-protein-binder-design
[blog]: https://www.anthropic.com/research/Claude-accelerates-protein-design
[report]: https://www-cdn.anthropic.com/30bf50e22a01388bb29bf077ee3f244531594b7a.pdf

### Why it exists

The source prompt is 16,000 words of unbroken prose with no headings, roughly a
third of which is infrastructure specific to one company's internal stack — a
cloud billing governor, a Slack threading contract, a Drive upload coordinator.
Nobody is going to paste that into a terminal every time they want to design a
binder, and most of it would not run outside the environment it was written for.

| Source material | Here |
|---|---|
| internal orchestration (~1/3 of the prompt) | a four-verb compute backend contract, with a first-class Slurm adapter |
| the scientific method | kept, restructured into `references/` loaded on demand |
| mechanical invariants stated in prose | runnable checks in `scripts/` |
| "do not ask the operator anything" | seven gates with review checklists |
| one 48-hour cloud campaign | three scale presets, from a few GPU-hours to the original |

The result is a 159-line `SKILL.md` that points at the rest. It also absorbs
material the source prompt lacked — absolute cutoffs, campaign sizing, pass-rate
diagnostics and per-method cost — from Adaptyv Bio's and Claude Science's public
skill collections; see [NOTICE.md](NOTICE.md).

### The gates

```
G0 scope  ->  setup + tool bring-up  ->  G1 dossier  ->  G2 epitope
   ->  G3 instrument validation  ->  G4 scale  ->  generate & screen
   ->  optimisation  ->  final scoring  ->  G5 selection  ->  G6 delivery
```

| Gate | What the human decides |
|---|---|
| G0 | targets, backend, scale, licence regime, deliverables |
| G1 | assay construct, reference structure, cofactor list |
| G2 | epitope and hotspot residues |
| G3 | that the scoring instrument can actually separate binders from noise **on this target** |
| G4 | compute allocation per target |
| G5 | the ranked set that will be ordered |
| G6 | acceptance, against a checklist run from artifacts |

G3 matters most and is skipped most easily, so it is mechanical: until
`state/gates/<target>.json` reads `PASS`, the submit gate refuses every
production scoring job.

### The calibration fact it is built around

In the published campaign, 1,320 designs were synthesised across 15 targets and
354 bound — a 27% hit rate, 49% among the top-ranked design per target. Three
targets produced almost nothing: maltose-binding protein 0 of 90, the de novo
beta-barrel BBF-14 3 of 90, and 15-PGDH 1.

**The co-folding scores gave no warning.** Designs against the failed targets
scored about as well as designs against the targets that yielded many binders.
Within a target the ensemble ranked binders above non-binders on 12 of 13
evaluable targets (mean average precision 0.52 against 0.31 by chance), but
across targets it could not have flagged the failures in advance, and among
binders it related only weakly to affinity.

So the skill treats in silico confidence as a **filter, never an oracle**, and
requires that phrase's substance to appear in every report it produces.

## Install

```bash
git clone https://github.com/SPYfighting/my-academic-skills.git
```

**Claude Code / opencode** — symlink the skill you want:

```bash
ln -s "$PWD/my-academic-skills/skills/binder-design-campaign" \
      ~/.claude/skills/binder-design-campaign
```

**Codex and other AGENTS.md readers** — copy [`AGENTS.md`](AGENTS.md) into your
project root, or append its contents to an existing one.

Windows, project-local installs and verification steps are in
[docs/installation.md](docs/installation.md).

## Use

Ask in your own words:

> Design miniprotein binders against PD-L1. I have 4 A100s on a Slurm cluster
> and about a week.

The skill takes over at G0, asks what it needs, and stops at every gate.

## Layout

```
skills/binder-design-campaign/
  SKILL.md                  the protocol, 159 lines
  workflows/                binder design · structure prediction · protein engineering
  references/               scoring instrument · thresholds · validation gates
                            tool catalogue · target dossiers · failure modes
                            deliverables · compute backends
  checklists/               what to present at each gate
  templates/                dossier · config · sheet schema · scoring policy
                            report outline
  scripts/                  runnable checks, standard library only
examples/binder-design-campaign/minimal/   fixture the scripts run against
docs/                       installation, per-skill rationale and source mapping
check.py                    repository self-check
```

## Checks

```bash
python check.py
```

Runs every script against the fixture, then against a corrupted copy, and
asserts the validators reject the corrupted one and say why.

## Scope and limits

- These skills do **in silico** work. Binding is established experimentally, by
  you or a CRO; nothing here predicts it.
- Tool names, flags and licence facts were correct at their recorded date and
  must be re-verified upstream before use. Where this repo and an upstream
  README disagree, the README wins.
- Dual-use: see [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md).
- Not run end to end on a real campaign. What is verified is that the checks
  catch what they claim to catch.

## Attribution and licence

Repository code and prose: MIT ([LICENSE](LICENSE)). Adapted from Anthropic's
CC-BY-4.0 release and from MIT-licensed public skill collections; details in
[NOTICE.md](NOTICE.md). Not affiliated with or endorsed by any of them.

Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
