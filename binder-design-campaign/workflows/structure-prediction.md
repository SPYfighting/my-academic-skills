# Workflow: structure and complex prediction

For predicting a fold, a complex, or an interface, and reporting confidence that
someone else can act on. This is the same protocol as `binder-design.md` with
the generation stages removed and the calibration stages strengthened — because
without an experimental readout at the end, the confidence estimate *is* the
deliverable.

Read `../SKILL.md` and `../checklists/gate-checklists.md` first.

---

## What changes relative to binder design

| Stage | Change |
|---|---|
| G0 | Ask what the prediction will be **used for**: a hypothesis to test, an input to design, a figure, or a decision. This sets how much calibration work is warranted. |
| G1 | The dossier is still required, and for the same reason: the construct, oligomeric state and cofactors determine what you are predicting. |
| G2 | Replaced by **prediction scope**: which chains, which stoichiometry, which conformational state, apo or holo. |
| G3 | Becomes a **recapitulation check** — see below. |
| G4 | Allocation is over predictors x seeds x states, not over design methods. |
| Generation | Absent. |
| Optimisation | Absent; replaced by sampling depth (more seeds, more MSA depths, more states). |
| G5 | Selection of the models to report, and the confidence statement attached to each. |
| G6 | Same delivery discipline. |

---

## G3 for prediction: recapitulation instead of separation

There is no design pool to separate, so replace positive-control separation with
a **held-out recapitulation set**:

1. Assemble a set of experimentally determined structures of the same class as
   the target — same fold family, comparable size, comparable stoichiometry,
   comparable cofactor situation.
2. Predict each at **exactly the settings** you will use for the target: same
   predictor, same MSA depth, same seed count, same aggregation.
3. Report the **error distribution**, not a single number: CA-RMSD and, for
   complexes, DockQ and interface RMSD.
4. State the relationship between the predictor's own confidence and the
   observed error **on this set**. That relationship is what licenses you to
   interpret the target's confidence score.

Freeze at PASS: the predictor set, the settings, the seed count, the MSA
strategy, and the confidence-to-error relationship you measured.

If no adequate held-out set exists, say so plainly. It means the confidence you
report on the target is uncalibrated for this class of system.

---

## Sampling and aggregation

- **Multiple predictors of different lineage**, for the same reason binder
  design uses multiple arms: agreement across lineages is stronger evidence
  than one model's confidence.
- **Distinct seeds**, asserted distinct. A zero standard deviation across seeds
  is a bug.
- **Multiple MSA depths** where the arm has an MSA encoder — shallow-MSA
  behaviour is diagnostic for whether the model is reading coevolution or
  memorising.
- **Multiple conformational states** where apo and holo differ, rather than
  reporting one and implying it is the only one.

Save every predicted structure and every per-seed confidence value. The
per-seed companion applies unchanged.

---

## Reporting confidence

Report, for every model delivered:

- Per-residue and per-interface confidence, with the metric named and its scale
  stated (pLDDT on 0–1 or 0–100 is a recurring source of silent error).
- Seed-to-seed variance.
- Cross-predictor agreement.
- The recapitulation error distribution from G3, as the reference frame.
- What is **not** supported: regions of low confidence, unmodelled context,
  states not sampled, and any interface whose confidence sits inside the
  error band you measured at G3.

The equivalent of `failure-modes.md` §1 applies here in a different form: a
confident prediction is not a solved structure, and confidence calibrated on one
class of system does not transfer to another. Say which class yours was
calibrated on.

---

## Deliverables

Same shape as `../references/deliverables-spec.md`, with these substitutions:

| Binder design | Prediction |
|---|---|
| design sheet | model sheet: one row per (system, state, predictor, seed-aggregate) |
| `ipsae_*`, `sc_dockq_*` | the confidence and error metrics you froze at G3 |
| selection caps | not applicable |
| structure bundle | every delivered model plus every per-seed prediction |
| scoreboard | one row per system: predictors run, seeds, agreement, confidence summary, recapitulation reference |

The write-time recompute rule stands: every number in the deliverable is
recomputed from the raw per-seed data at write time and must agree.
