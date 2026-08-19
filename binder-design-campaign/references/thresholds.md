# Absolute thresholds and campaign sizing

`scoring-instrument.md` describes a **relative** instrument: per-target z-scores
that rank a pool against itself. That is the right way to select from one
campaign's designs, and it says nothing about whether a number is good.

This file holds the **absolute** side — published cutoffs, expected pass rates,
and how many designs it takes to get what you want. Use it to set the frozen
thresholds at G3, to size the campaign at G4, and to diagnose a pass rate that
comes back wrong.

Sources are named per block. Everything here is a starting point to freeze at
G3 against your own controls, not a constant.

---

## 1. What these numbers can and cannot do

Individual in silico metrics separate binders from non-binders barely better
than chance on their own — reported ROC AUC around 0.64–0.66 in the binder-QC
literature. They are **prefilters**. Composite scoring is what produces a
usable ranking, and even then the instrument is a **filter, never an oracle**
(`failure-modes.md` §1).

So: use a threshold to discard obvious failures, use the composite z-score to
rank what survives, and use the experiment to learn whether the campaign worked.

---

## 2. Cutoffs

From Adaptyv Bio's `protein-qc` skill (MIT), which compiles them from binder
design competitions and published benchmarks. Cross-check each against your
own G3 controls before freezing.

| Class | Metric | Standard | Stringent | Computed by |
|---|---|---|---|---|
| Structural | pLDDT | > 0.85 | > 0.90 | any co-folder |
| | pTM | > 0.70 | > 0.80 | any co-folder |
| | scRMSD (design vs prediction) | < 2.0 Å | < 1.5 Å | structural comparison |
| Binding | ipSAE_min | > 0.61 | > 0.70 | ipSAE |
| | ipTM | > 0.50 | > 0.60 | any co-folder |
| | PAE_interaction | < 12 Å | < 10 Å | any co-folder |
| | shape complementarity | > 0.50 | > 0.62 | PyRosetta |
| | interface dG | < -10 | < -15 | PyRosetta |
| | interface buried unsatisfied H-bonds | <= 4 | <= 2 | PyRosetta |
| Expression | instability index | < 40 | < 30 | BioPython |
| | GRAVY | < 0.4 | < 0.2 | BioPython |
| | ESM2 pseudo-log-likelihood | > 0.0 | > 0.2 | ESM2 |
| | folding dG (60–80 aa) | < -2 kcal/mol | < -4 kcal/mol | SaProt-dG |

The PyRosetta rows need an academic or commercial Rosetta licence; under a
commercial-only regime they are unavailable and the interface is assessed from
co-folding metrics alone (`tool-catalog.md` §5).

**Scale check before comparing anything.** pLDDT is emitted on 0–1 by some
builds and 0–100 by others. Record the scale beside every threshold you freeze;
a silent scale mismatch turns a filter into a pass-through.

### Sequence liability patterns

Detected on the sequence, not thresholded on a score:

| Pattern | Risk | Action |
|---|---|---|
| odd cysteine count | unpaired disulfide | redesign |
| NG, NS, NT motifs | deamidation | flag |
| 3+ consecutive K or R | proteolysis | flag |
| 6+ hydrophobic run | aggregation | redesign |

---

## 3. Which single metric to rank on

A meta-analysis of 3,766 experimentally characterised binders across 15 targets
(Overath et al., *Predicting Experimental Success in De Novo Binder Design*,
bioRxiv 2025, doi:10.1101/2025.08.14.670059 — verified) found **ipSAE_min the
single best in silico predictor of binding**, and a three-feature linear model
the best generaliser across targets. Gradient-boosted and many-feature models
did not beat it.

That result is why the default instrument in `scoring-instrument.md` ranks on
ipSAE_min, and it is the same benchmark the source campaign validated its
co-folding arms against.

Filtering strategies reported there:

1. Threshold on any one of: `ipSAE_min > 0.61`; or
   `ipSAE_min x interface_dG/dSASA < -1.5`; or
   `LIS x shape_complementarity > 0.42`.
2. Pre-filter on `shape_complementarity > 0.62` and `RMSD_binder < 3.73`
   (input versus re-predicted), then take the top K by `ipSAE_min`.

`ipSAE_min` is the **minimum** of the two asymmetric directions, not the mean or
the max. The RMSD_binder filter is over-restrictive on some targets; prefer it
as a soft pre-filter.

---

## 4. Campaign sizing

From Adaptyv Bio's `campaign-manager` skill (MIT). Rule of thumb: **generate
roughly 50x more designs than the number of binders you want**, which is the
10–15% QC pass rate multiplied by the loss to diversity clustering.

| Binders wanted | Backbones | Sequences per backbone | Total sequences | Expected to pass QC |
|---|---|---|---|---|
| 5 | 200 | 8 | 1,600 | 160–240 |
| 10 | 500 | 8 | 4,000 | 400–600 |
| 20 | 1,000 | 8 | 8,000 | 800–1,200 |
| 50 | 2,500 | 8 | 20,000 | 2,000–3,000 |

This sizing sits between the skill's `explore` and `standard` presets. It is
two to three orders of magnitude below the source campaign's 1e5–1e6, which
bought its extra scale in optimisation rounds and method diversity rather than
in first-pass yield — both are defensible; state which you are running.

### Stage funnel

| Stage | Count | Purpose |
|---|---|---|
| backbone generation | 500–1,000 | diversity |
| sequences per backbone | 8–16 | sequence space |
| co-folding predictions | all survivors | validation |
| after filtering | 50–200 | candidates |
| experimental testing | 10–50 | final selection |

---

## 5. Reading the pass rate

Compute the fraction of designs clearing **all** structural and binding
thresholds, then read it as a diagnostic rather than a score:

| Overall pass rate | Reading | Action |
|---|---|---|
| > 15% | excellent | proceed to selection |
| 10–15% | normal | proceed |
| 5–10% | marginal | work the failure tree below before scaling |
| < 5% | poor | diagnose and restart the wave |

**Failure tree** — which gate is failing tells you where the problem is:

| Symptom | Likely cause |
|---|---|
| low pLDDT pass rate | backbone or sequence problem: check the generator output and the sequence-design handoff |
| low ipTM or ipSAE pass rate | hotspot or interface problem: revisit G2, and check the construct and cofactors reached the scorer |
| low scRMSD pass rate | the sequence does not specify the backbone: raise sequences per backbone, lower sampling temperature |
| every metric passing | the gate is broken (`failure-modes.md` §4), not the designs are perfect |

Target difficulty shifts the whole band. A concave, conserved, rigid site with
known binders sits at 15–20%; a flat or convex, poorly conserved, flexible site
with no precedent sits at 5–10%. Record which you expect in the dossier's
`prior_difficulty` and compare the realised rate against it.

---

## 6. Cost per design

Adaptyv Bio's measured compute cost per accepted design, averaged over 7
targets, varying several-fold by target:

| Method | Cost per design |
|---|---|
| RSO | ~$0.15 |
| RFdiffusion | ~$0.25 |
| Mosaic | ~$0.55 |
| ESMFold2 inversion | ~$0.85 |
| mBER | ~$1.40 |
| Germinal | ~$1.60 |
| BoltzGen | ~$1.80 |
| BindCraft | ~$2.90 |

**Cost per design is not cost per binder.** The gradient methods are cheap per
design and expensive in human setup; the turnkey methods invert that. Divide by
your realised hit rate on this target before comparing.

Use these for the G4 arithmetic when you have no local benchmark yet, then
replace them with your own measured seconds-per-design from the roster as soon
as bring-up produces it — a rented-cloud dollar figure does not transfer to a
cluster allocation.
