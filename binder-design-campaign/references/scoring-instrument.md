# The scoring instrument

Everything here is adapted from the source campaign prompt. Numeric defaults
are the source's defaults; they are starting points you freeze at G3, not
universal constants. Re-verify every tool flag against its upstream
documentation before use.

---

## 1. Vocabulary

**Arm** — one co-folding predictor with fixed settings. **Instrument** — the
set of arms used to rank on a given target. **Mask** — which arms are live in
the instrument; frozen at G3, identical at every seed tier. **Tier** — how many
distinct seeds each arm runs per design.

Two summary numbers per design:

- `final_score` — the **raw mean** of the instrument's terms. This is the
  headline value. Under a disclosed reduced mask, the mean runs over the
  realised terms only, and `score_instrument` names them.
- `rank_zscore` — the per-target weighted mean of the **z-scores** of the same
  terms. Ranking only.

## 2. Default instrument

The source campaign ranked with three arms, one sample per seed:

| Arm | Model | MSA usage |
|---|---|---|
| `ef2full` | ESMFold2-Full | target-chain MSA (`msa_max_seq=2048`); binder single-sequence |
| `ef2fast` | ESMFold2-Fast | single-sequence only — its released checkpoint has no MSA encoder, so passing an a3m is a silent no-op |
| `ptxv2` | Protenix v2 | target-chain MSA via a precomputed MSA cache; binder single-sequence |

ESMFold2 inference parameters used for both variants: `num_loops=10`,
`num_sampling_steps=68`, `num_diffusion_samples=1`, blind mode (no template, no
initial guess).

All three are all-atom co-folders that accept non-protein context (ions,
small-molecule ligands, nucleic acids, modified residues, by CCD code or
SMILES). A cofactor flagged fold- or interface-required in the dossier is
supplied to **every** arm. Never waive it on the assumption that an arm is
protein-only; check the model's own paper and API before recording that it
cannot represent something.

**Substitutes.** If an arm cannot be validated on a target, bring up one
independent-lineage co-folder per missing arm. Source preference order:
AlphaFold-Multimer-v3, then AlphaFold3 code with OpenFold3 weights, then Chai-1,
then Boltz-2 or Boltz-1 — all with target-chain MSAs, all representing the
dossier cofactors. Record which arm each substitute stood in for.

**Choosing your own instrument.** If your site cannot run these, the contract
that matters is structural, not brand-specific: at least two arms of
**different lineage**, each validated at G3 on the actual target, each saving
its predicted structures at the ranking stage. A single-arm instrument is
allowed only as a disclosed limitation, and it removes cross-arm agreement,
which is the strongest evidence available **within this class**. It is not
independent validation: three co-folding models that agree are still three
co-folding models, trained on overlapping data and sharing the failure modes in
`failure-modes.md` §1. Independent validation is an experiment.

## 3. Per-design metrics

### 3.1 ipSAE_min — the primary confidence term

ipSAE (Dunbrack, bioRxiv 2025.02.10.637595) is an interface-restricted PAE
summary. `ipSAE_min` is the **minimum over both alignment directions**, then
the **maximum over seeds**, then combined across arms.

**On multimeric targets, use a union mask.** For binder chain B and target
protomers T1..Tn, compute ipSAE on the (n+1)-chain prediction with
`mask_binder = {residues where asym_id == B}` and
`mask_target = {residues where asym_id != B}`, re-deriving `n0` and `d0` from
the union mask sizes. This single union-mask call **replaces** the stock
pairwise loop over (B, Ti). The positive control at G3 is measured on the same
(n+1)-chain construct with the same pairing.

Absolute ipSAE compresses as chain count rises, so raw cross-target comparison
is invalid.

### 3.2 sc_DockQ — pose self-consistency

`sc_DockQ_<arm> = DockQ(designed_complex, prediction_at_argmax_seed_ipSAE)`.

Three rules that are easy to get wrong:

1. The DockQ for an arm is computed on **the same seed** whose ipSAE_min became
   that arm's score — not on a separately chosen max-DockQ seed. Record both
   `argmax_seed(ipSAE_min)` and `argmax_seed(DockQ)` per arm in the per-seed
   companion so seed concordance is auditable.
2. Chain mapping is the **best symmetric relabelling** (the one maximising
   DockQ). This applies on monomeric targets too, because chain IDs in the
   designed and predicted structures may simply differ.
3. `pose_dockq = min` over the arms that ran.
   `pose_PASS = (pose_dockq >= threshold)`, default 0.23 unless G3 froze
   something stricter. A NaN pose result is a **missing measurement**, not a
   fail flag: the row is not rank-eligible until the pose check has run.

For N:N stoichiometry on oligomeric targets, build the reference designed
complex by applying the target multimer's own Cn symmetry operators to the
single designed pose, then co-fold N independent binder chains.

### 3.3 Shadow metrics

Tracked from the same forward pass, never used for ranking:

- `ipTM` — on multimeric targets, whole-complex ipTM is **inflated** by native
  protomer-protomer interfaces and compresses design-vs-control separation. If
  you track it there, also compute a binder-masked `iptm_binder` on the union
  masks.
- `LIS`, `monomer_plddt`, `lcp_score`, `esmc_ll`.

### 3.4 Sequence-level metrics

- **LCP (Local Composition Perplexity)** — a mandatory per-position sequence
  design restraint against homopolymer stretches; record `lcp_score` for every
  sequence designed. The definition is given as a figure in the source release
  (`prompts/prompts/Figure 1.jpg` in the HuggingFace dataset); implement it
  from that figure, and record your implementation in the campaign log.
- **ESM-C log-likelihood** (or pseudo-perplexity) on every design that receives
  a rank.

## 4. Combining terms

The formula below is described here and **written** in
`../templates/scoring_policy.yaml`, which is what the sheet writer and the
checks read. Change it there; a change described in prose but not made in the
policy file has not happened.

With the default three-arm instrument, six raw terms per design: three
`ipSAE_min` (one per arm, max over seeds) and three `sc_DockQ`.

```
final_score  = mean(six raw terms)                      # headline, raw units
rank_zscore  = weighted mean of per-target z-scores     # ranking only
               weight 4 on each ipSAE_min z-term
               weight 1 on each sc_DockQ z-term
```

The 4:1 weighting says: confidence dominates the ranking, but a design whose
predicted pose disagrees with its designed pose is penalised rather than
ignored. Every promotion step — screen to a higher seed tier, and parent
selection for each optimisation round — ranks on both together, so the pool
reaching the final tier is enriched for cross-arm agreement rather than for
high ipSAE alone.

**Counter-screened targets** extend both formulas. For each arm add

```
selectivity_delta_<arm> = ipSAE_min(on-target, arm) - ipSAE_min(off-target paralog, arm)
```

computed at the **same seed count and aggregation** as that arm's on-target
score — an instrument-mismatched subtraction is invalid. `final_score` becomes
a nine-term mean; each `z(selectivity_delta_<arm>)` carries the ipSAE weight of
4 in `rank_zscore`. On-target, off-target and selectivity values are also
recorded as their own columns regardless. A null off-target or selectivity
value on any ranked row of a counter-screened target is a fail-loud, not a
documented gap.

**Changing either formula** requires pre-registration: demonstrate at G3 that
the alternative separates controls substantially better, freeze it, and
disclose it before scoring any production design on that target.

## 5. Seed tiers

| Tier | Seeds per arm | Use |
|---|---|---|
| SCREEN | 1 | fast iteration; keep the top fraction the budget supports |
| INTERMEDIATE | 5 (3 under `explore`) | iteration between waves and optimisation rounds |
| FINAL | 5 (3 under `explore`) | the ranked deliverable |

Seeds are **distinct integers** per arm: assert `len(set(seeds)) == n_seeds`. A
per-design standard deviation of exactly 0 across `n_seeds > 1` is a bug, not a
stable model.

Before running the final tier at production scale, validate the metric at the
exact parameters you will rank with: if ranking by max over N seeds, run N
seeds on the control set, demonstrate the ensemble adds ranking information
over a single-seed baseline, and report the measured seed variance.

Rows below protocol seed count are **topped up first**, not dropped. Only after
a top-up attempt fails do they ship, ranked below all full-seed rows with the
actual `n_seeds` disclosed per arm.

## 6. z-score discipline

z-scores are **transductive**: mu and sigma depend on the pool that was scored.
Consequences, all load-bearing:

- A z-score is comparable only within the batch that produced it. Never across
  targets, never across waves, never across campaigns.
- Record the **raw** metric vector and the seed count on every row so any batch
  can be re-standardised later.
- Rank and select with z-scores. Report raw values.
- **Calibration runs report raw scores only.** z-scoring is reserved for the
  design pool.

## 7. Calibration bands

Establish, per target, on the same arms and the same seed count as the designs:

- **Ceiling band** — raw scores of native high-affinity protein-protein
  complexes outside the campaign target set (the source used Barnase/Barstar,
  K_D ~1e-14 M). This is a reference to push toward, with headroom above it.
  Consider a target saturated only when its top designs' raw ipSAE_min sits at
  or above the band on the same model.
- **Floor band** — constructed negatives: a non-interacting pair, a
  sequence-shuffled binder, a cross-pair mismatch.

Both calibration complexes and per-target positive controls run with MSAs on
**both** chains (or single-sequence where the arm has no MSA encoder), at the
same seed count, chain construct and ipSAE pairing as the designs.

## 8. Pre-scoring filters

Run before spending any co-folding compute. Every candidate is assessed for:

1. **Novelty** — MMseqs2 against UniRef90, plus a known-binder corpus, plus
   every chain of the target's own reference structure and positive-control
   complex. Source reject thresholds: >60% identity over >50% coverage to
   UniRef90 or the binder corpus; **or** >=30% gapped local identity over >=40
   aligned residues; **or** TM-score >=0.5 to any target or control chain (this
   is what catches target-mimic protomers, and it must catch them *here*, not
   downstream). Detect ubiquitin by local alignment rather than exact match —
   it emerges with short terminal extensions.
2. **Liability** — cysteine parity, homopolymer runs, surface hydrophobic
   patches.
3. **Monomer foldability** — the binder alone, at a per-target mean-pLDDT
   threshold frozen at G3. Default 70 on a 0-100 scale (0.7 on 0-1; ESMFold2
   emits 0-1 — check the scale your build emits before comparing).
4. **Structural plausibility** — backbone geometry, steric clashes, core
   packing, at thresholds chosen at kickoff and frozen.

Record every rejected `design_id` and verify its absence from every downstream
scoring pool. **A gate counts as run only when its rejects are traceably absent
downstream.**

**Redundancy**: cluster de novo pools at ~90% identity before scoring. For
mutagenesis and other close-variant pools, drop only exact duplicates before
scoring, and enforce diversity at selection time instead.

## 9. In silico optimisation

Required: at least two rounds per target, five or more on hard targets,
continuing while metrics improve. Approaches:

- **Partial diffusion with sequence redesign** around hits.
- **Predict-then-redesign cycling**: take a design whose predicted complex
  passes the pose and confidence gates, feed **the predicted complex** (not the
  original designed structure) back into a sequence design model, re-score,
  repeat while confidence improves.
- **Sequence redesign** by model sampling and point mutagenesis.

Every round's outputs keep the same `root_backbone_id` as their ancestor.

**Round discipline.** Round 1 on a target starts only after at least one full
generation plus sequence-design wave for that target is indexed and
screen-scored. Each round is scored on the **same instrument and seed count**
that ranked the pool which seeded it. Promotion to the final seed tier happens
**before** selecting parents for the next round. Designs selected for order may
come from any round.

## 10. What this instrument does not tell you

A **filter, never an oracle**: read `failure-modes.md` §1 before treating any of
these numbers as a prediction of experimental success.

For the absolute side of the instrument — published cutoffs, expected pass
rates, campaign sizing and the failure tree for a low pass rate — see
`thresholds.md`. This file ranks a pool against itself; that one says whether a
number is any good.
