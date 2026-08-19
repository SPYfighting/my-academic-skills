# Workflow: general protein design

For design campaigns that are not binder design: thermostabilisation, enzyme
activity or specificity engineering, interface redesign, solubility and
expression optimisation, scaffold generation, and de novo functional-site
design.

Read `../SKILL.md` and `../checklists/gate-checklists.md` first. This file lists
only what differs from `binder-design.md`.

---

## The one structural difference

Binder design has a strong, general in silico discriminator — co-folding
confidence at a designed interface — which is why that workflow can rank
thousands of designs before spending a wet-lab dollar.

**Most other protein design objectives do not.** Predicted ddG, predicted
melting temperature, docking scores, MD-derived stability proxies and
activity-prediction models each have far narrower validated ranges. The single
most important adaptation is therefore at G3: **establish what your scoring
function can actually discriminate on your system, and say so honestly when the
answer is "less than you would like".**

---

## Stage changes

### G0 — additionally ask

- **The objective, quantified.** "More stable" is not a design objective; "+5 °C
  in apparent Tm by DSF, without losing more than 20% of specific activity" is.
- **The experimental readout** that will judge the designs, and its throughput.
  Throughput sets the design count far more than compute does here.
- **The starting point**: a natural sequence, an existing engineered variant, or
  de novo.
- **Hard constraints**: catalytic residues, binding sites, disulfides, PTM
  sites, expression host, immunogenicity limits.

### G1 — dossier

Same discipline, different fields. Add: catalytic mechanism and the residues
that must not change; known engineering precedent on this protein and what it
achieved; the structure-function literature for the region being designed;
known stability or expression liabilities; any labelled variant dataset that
exists for this system.

**For an enzyme, the reaction is part of the construct**, and leaving it
implicit is the same class of error as scoring the wrong residue range. Record,
each with its source:

| Field | Why it changes the answer |
|---|---|
| substrate, product | defines the site being designed; a binder-shaped model of an empty pocket is a different molecule |
| cofactor, and its state | NAD(P)H vs NAD(P)+, FAD vs FADH2 — different charge, different geometry |
| metal identity and oxidation state | Fe(II) and Fe(III) are not interchangeable in a model or in an assay |
| catalytic residues, and their role | acid, base, nucleophile, oxyanion hole — these are hard constraints, not preferences |
| protonation assumptions | at assay pH; a catalytic His modelled in the wrong tautomer inverts the mechanism |
| structurally conserved waters | often part of the active site, usually stripped by default preparation |
| reaction conditions: pH, temperature, ionic strength, buffer | the state you are designing for, and the state the assay will report |
| competing substrates and side reactions | the negative objectives; promiscuity is the usual failure |
| assay readout | continuous or endpoint, coupled or direct, and what it cannot see |

An entry left blank here is an assumption you have made without recording it.
Write `unresolved` and say what you tried.

### G2 — design scope instead of epitope

Present, as a table: which positions or regions are designable, which are
frozen, the rationale for each, and the size of the resulting sequence space.
Then present two or three **strategies** (conservative resurfacing, focused
library at a defined region, backbone redesign) with their cost and risk, and
let the human choose.

### G3 — discriminator validation

This is the adapted gate, and it is the one that decides whether the campaign is
worth running.

1. Assemble a **labelled set** for this system or the closest relative you can
   find: variants with measured values of the objective.
2. Score them with the discriminator you intend to rank with, at the exact
   settings.
3. Report **rank correlation and top-k enrichment** on that set — not a
   correlation coefficient alone, because ranking is what you will actually do.
4. Report a baseline: what a naive strategy (conservation-based, or random from
   the allowed space) achieves on the same set.

**PASS** means the discriminator beats the baseline by a margin worth the
compute. If no labelled set exists, the gate fails to prove anything, and that
is the finding to report at G3: the campaign will be selecting on an
unvalidated score, and the design count should be set by the experimental
throughput rather than by in silico filtering.

Freeze at PASS: the discriminator, its settings, the thresholds, and the
measured enrichment.

### G4 — allocation

Allocate by **experimental throughput first**. If the readout can measure 96
variants, generating 100,000 in silico candidates is only useful to the extent
that the G3 enrichment is real. State that arithmetic explicitly.

### Generation and optimisation

Same discipline as binder design: provenance keys assigned at generation and
propagated; nothing discarded; canary before fan-out; the method floor idea
applies to design strategies as it does to structure methods.

Diversity caps still apply and matter more, not less: an unvalidated
discriminator makes concentrating the shipped set on one parent a bad bet.

### G5 — selection

Add to the presentation: the **hypothesis each selected design tests**. A
96-variant plate that tests one hypothesis 96 times is a wasted plate. State the
spread of hypotheses and the number of designs per hypothesis, and include
appropriate controls — wild type, a known-positive variant, and a
known-negative — as named rows.

### G6 — delivery

Same close-out discipline. The sheet's per-arm score columns become the
discriminator's outputs; the null policy, the write-time recompute and the
structure-bundle rules are unchanged.

---

## Reporting

The honest framing for this workflow is usually weaker than for binder design,
and it should be stated as such:

- Name the discriminator and its measured enrichment on the G3 labelled set.
- State the class of system that set covered, and whether the target is inside
  that class.
- Where G3 could not be run for lack of labels, say that the ranking is
  unvalidated and that the design set is a **hypothesis-spread**, not a
  filtered set of likely successes.
