# Workflow: de novo miniprotein binder design

Stage detail for the main workflow. Read `../SKILL.md` first for the gate model
and the non-negotiables; read `../checklists/gate-checklists.md` at each gate.

Every stage below lists **inputs**, **work**, **outputs**, and a **done
criterion** that is checkable from artifacts.

---

## Stage 0 — Scope (gate G0)

**Inputs**: the user's request.
**Work**: run the G0 checklist. Produce the one-page campaign plan.
**Outputs**: `state/campaign_config.yaml` (from `../templates/campaign_config.yaml`),
`state/decisions.jsonl` with the G0 answers.
**Done**: the human confirmed the plan; the config file exists and every field
is filled or explicitly marked `unresolved`.

---

## Stage 1 — Setup and tool bring-up

Runs before G1 because it is slow and because its result constrains what you can
promise later.

**Inputs**: the config, the target list.
**Work**:

1. Create the campaign directory tree and the ledger tree. Verify write access
   and record the available quota.
2. Bring up one tool at a time (or one worker per tool where the runtime allows
   parallel sub-tasks) against the roster criteria in
   `../references/tool-catalog.md` §1. **Bring the ranking arms up first** —
   without them, nothing can be scored, and every other tool's output is
   unusable.
3. Validate the **generator to sequence-design adapter** for each structure
   method on a real campaign target. Not the generator alone.
4. Stage the novelty databases: full UniRef90 or a precomputed MMseqs2 index,
   plus a known-binder corpus. Production screening is not blocked on this
   staging, but **no row reaches the final sheet without the full novelty
   check**.
5. Stage target-chain MSAs once per target into a shared cache.
6. Write `state/method_vocab.json` (method tokens, tool-to-family map, alias
   map) and `state/sheet_schema.json`. Both are frozen from here.

**Outputs**: `state/roster.jsonl`, `state/method_vocab.json`,
`state/sheet_schema.json`, the MSA cache, the novelty database.
**Done**: every roster row is `PASS` or a logged drop with its consequence
stated; at least one ranking arm is `PASS`; the adapter check passed for every
`PASS` structure method.

**If a ranking arm cannot be brought up**, stop and report. A campaign with no
validated scoring instrument cannot rank, and generating designs it cannot rank
wastes the budget.

---

## Stage 2 — Target dossier (gate G1)

**Inputs**: the target list.
**Work**: build one dossier per target per
`../references/target-dossier-guide.md`. Every identifier fetched, every field
sourced.
**Outputs**: `state/dossiers/<target>.md`.
**Done**: the human confirmed the assay construct, the reference structure and
the cofactor list for every target. These three are now frozen.

---

## Stage 3 — Epitope and hotspot selection (gate G2)

**Inputs**: the confirmed dossiers.
**Work**:

- Enumerate candidate epitopes. Prioritise **biologically relevant interfaces
  already explored in the design literature**; a novel epitope is allowed when
  you have a differentiated hypothesis for it.
- Prefer **functional** epitopes where a miniprotein can plausibly achieve a
  measurable mechanism of action.
- Account for non-protein context: metals, ligands, glycans, membrane
  proximity.
- Note that cross-species reactivity (mouse, rat, cyno orthologs) is a
  **secondary** objective, pursued only where it does not compromise affinity or
  hit rate against the primary antigen.
- Propose hotspot residues per epitope, in the numbering of the chosen
  structure, with the mapping to UniProt numbering shown.

**Outputs**: `state/epitopes/<target>.json` with the chosen epitope(s), the
hotspot residue list verbatim, and the mechanistic hypothesis.
**Done**: the human picked the epitope(s) and confirmed or edited the hotspots.

A second epitope per target is encouraged once the primary is on track and the
budget allows. It is not required, and it is proposed at G2 rather than added
silently later.

---

## Stage 4 — Instrument validation (gate G3)

**Inputs**: frozen construct, chosen structure, cofactor list, roster.
**Work**: run `../references/validation-gates.md` end to end — fold
recapitulation per arm, positive-control separation per arm, calibration bands,
seed-variance measurement, threshold freezing.
**Outputs**: `state/gates/<target>.json` with `status`.
**Done**: `status: PASS` **and** the human acknowledged the mask, the construct
and the thresholds.

Until this file says PASS, the submit gate refuses every scoring dispatch for
that target. That is the intended behaviour; do not work around it.

---

## Stage 5 — Production scale (gate G4)

**Inputs**: the roster with measured seconds-per-design, the dossiers'
`prior_difficulty`, the storage and compute quota.
**Work**: derive the per-target allocation. Per-target shares are **derived,
not flat**: blend the literature prior with live observables as screening data
accumulates. Early on the prior dominates; later the live signal does. The only
hard bound is a floor — every target gets enough compute to produce its full
ranked set.
**Outputs**: `state/allocation.json`, the wave plan.
**Done**: the human confirmed the allocation and, on metered backends, the spend
ceiling.

---

## Stage 6 — Generate and screen

**Inputs**: epitopes, hotspots, roster, allocation.
**Work**, per (target, method) cell, as coupled `gen_screen` jobs
(`../references/compute-backends.md` §5):

1. **Structure design** — generate backbones conditioned on the target and
   hotspots. Supply non-protein context where the model accepts it and the
   dossier indicates it is part of the biological system. Assign
   `root_backbone_id` and `structure_method` at generation time; both propagate
   unchanged through every downstream stage.
2. **Sequence design** — SolubleMPNN / SolubleCaliby for anything that may be
   ordered; base variants are fine for backbone search. Record `lcp_score` for
   every sequence. For co-design models, score both the native sequence and a
   redesign.
3. **Pre-scoring filters, in job** — novelty, liability, monomer foldability,
   structural plausibility, at the frozen thresholds
   (`../references/scoring-instrument.md` §8). Record every rejected
   `design_id`.
4. **Redundancy clustering** — de novo pools at ~90% identity before scoring;
   for close-variant pools, drop only exact duplicates and enforce diversity at
   selection instead.
5. **Screen scoring** — one seed per arm on all ranking arms; append the
   `n_scored` ledger row.

**Method floor.** Recompute the (target, method) backbone-count matrix every
governor cycle. Treat every cell below its floor as an open obligation and give
under-represented methods dispatch priority until the cell fills or a deviation
is logged. Beyond the floor, reallocate freely toward whichever methods perform
best per target and epitope — that reallocation is the point of the floor, not
a violation of it. A method that passed bring-up but contributed zero ranked
backbones campaign-wide is logged with **which of the two happened**: the
screening data eliminated it on this target, which is the floor working as
intended, or an engineering problem kept it from competing, which is a defect.
Throughput or convenience are not the second answer.

**Watch for target-fold mimicry** (`../references/failure-modes.md` §2),
especially on homo-oligomeric targets and whenever the requested binder length
approaches a target chain's length.

**Outputs**: survivor structures and sequences, screen scores, ledger rows,
reject lists.
**Done**: every allocated cell has met its floor or logged a deviation;
generation has not outrun scoring; the reject lists are traceably absent from
the scoring pools.

---

## Stage 7 — In silico optimisation

**Inputs**: screen-ranked pools.
**Work**: at least two rounds per target, five or more on hard targets,
continuing while metrics improve. Methods and round discipline are in
`../references/scoring-instrument.md` §9.

The three approaches, used together rather than in isolation: partial diffusion
with sequence redesign; predict-then-redesign cycling that feeds the
**predicted** complex back into sequence design; and sequence redesign by model
sampling and mutagenesis.

Diversity is guarded by the selection caps, not by throttling optimisation —
optimisation is expected to concentrate the pool, and the caps are what prevent
that concentration from reaching the shipped sheet.

**Outputs**: per-round design pools under the same `root_backbone_id`s, scores
at the tier that ranked the pool which seeded them.
**Done**: rounds continue until metrics stop improving, the allocation is
exhausted, or the wall-clock binds; the stopping reason is recorded per target.

---

## Stage 8 — Final-tier scoring

**Inputs**: the promoted pool, from any round.
**Work**: score at the final seed tier on every arm, with distinct seeds.
Compute `sc_DockQ` on the argmax-ipSAE seed per arm. On oligomeric targets,
score at **both** 1:N and N:N and record the N:N metrics and the binder-binder
clash count. On counter-screened targets, run the matched off-target arm at the
same seed count.
**Outputs**: the per-seed companion, the aggregated per design x arm rows.
**Done**: every candidate for the sheet has a non-null `pose_dockq` and a real
`n_seeds` on every arm, or a recorded top-up failure.

---

## Stage 9 — Selection (gate G5)

**Inputs**: the final-tier pool.
**Work**: the writer selects rows under the ordering key and the selection caps
(`../references/deliverables-spec.md` §§1.5–1.7), recomputing every gate at
write time. Run `../scripts/check_design_sheet.py` and
`../scripts/check_diversity.py`.
**Outputs**: the design sheet, the diversity summary, the relaxation record.
**Done**: the human approved the sheet as the set to be ordered.

---

## Stage 10 — Delivery (gate G6)

**Inputs**: the approved sheet.
**Work**: the transactional close-out in `../references/deliverables-spec.md`
§8 — seed top-up, freeze, derive companions, rebuild and open the structure
bundle, regenerate every report number, adversarial review.
**Outputs**: the full deliverable set.
**Done**: every G6 checklist box checked with evidence shown, and the human
accepted delivery.

---

## What to say when reporting results

Two statements belong in every summary of this workflow, and they are the two
most likely to be dropped:

1. The instrument is a **filter, never an oracle**
   (`../references/failure-modes.md` §1).
2. Every pose shown is a **prediction**. Unless a structure was solved, the
   campaign's evidence is binding, not structure or function.
