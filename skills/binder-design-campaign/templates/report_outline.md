# Campaign report outline

Every number in this document is regenerated from the as-shipped design sheet,
scoreboard and per-seed companion immediately before the report is declared
final. A number that does not reproduce is corrected; a number that cannot be
traced is deleted.

---

## Title, authors, date

## Abstract

What was designed, against what, with what methods, at what scale, and what the
deliverable is. State the campaign's limits in the abstract, not only in the
discussion: what was **not** tested, and what the scores do and do not support.

Every quantitative claim here appears again, identically, in the results.

## 1. Objective

The targets, the design objective per target, and the success criterion agreed
at G0. Where a target carried a selectivity or cross-reactivity requirement,
state it here.

## 2. Targets

One subsection per target, condensed from the confirmed dossier: identity,
assay construct, oligomeric state, cofactors, reference structure, prior
difficulty, and the epitope chosen at G2 with its mechanistic hypothesis.

State which construct decisions were **frozen** and when.

## 3. Methods

### 3.1 Computational environment

Backend, hardware, environments or images with their identifiers, and the
software versions with commits or checksums.

### 3.2 Roster

The roster table: every tool, its status, and — for every drop — the
consequence of dropping it.

### 3.3 Design pipeline

Structure design, sequence design, pre-scoring filters with their frozen
thresholds, redundancy clustering, and the optimisation rounds actually run per
target.

### 3.4 Scoring instrument

Generated from `instrument_realization.csv`. Arms, MSA strategy, seed tiers,
the ranking formula, and every target whose realised instrument differed from
the campaign default, called out explicitly.

### 3.5 Validation gates

Per target: fold recapitulation values, positive-control identity and
separation, negative controls, calibration bands, and measured seed variance.
Name any target where condition (b) was dropped for lack of a control.

### 3.6 Selection

The ordering key, the selection caps, and every relaxation applied with the rows
it admitted.

## 4. Results

### 4.1 Scale actually achieved

Designs generated, screened and ranked per target, from the ledger. Compute
consumed. Where measured disagrees with planned, report **measured** and the gap.

### 4.2 Ranked designs

Per target: the score distribution, the top designs, fold classes, diversity
statistics, pose-check pass rates.

### 4.3 Method performance

Which structure and sequence methods contributed the ranked designs, per target.
Note any method that met its floor but contributed nothing ranked.

### 4.4 Calibration

Where the top designs sit relative to the ceiling and floor bands, in raw units,
on the same arms.

### 4.5 Deviations

Every logged deviation, its cause and its consequence.

## 5. Discussion

Lead with the **worst defensible reading** of the data.

Required content:

- The instrument is a **filter, never an oracle**, with the measured evidence
  cited (`../references/failure-modes.md` §1).
- Every claim is labelled **predicted**, **inferred** or **measured**, and the
  verb matches: a model score supports "the ensemble ranks these highest", an
  argument from it supports "these are the most likely to bind", and only an
  experiment supports "these bind". Where the label is not obvious from the
  sentence, make it explicit.
- Every pose shown is a **prediction** unless a structure was solved. The
  evidence available at delivery is computational.
- Targets where the campaign is least confident, and why — surface character,
  epitope flexibility, absent controls, dropped arms.
- What would change the answer: which experiment, at what scale.

## 6. Limitations

At minimum: no experimental validation at time of writing (or: which
measurements exist and which do not); sequence variants of one backbone are not
independent observations; single run per configuration where that is the case;
any target whose G3 condition (b) was dropped.

## 7. Data and code availability

Where the design sheet, per-seed companion, instrument realisation table,
scoreboard, structure bundle and deviations file live, with sizes and checksums.

## 8. References

Every method used, cited to its own paper. Every identifier fetched, not
recalled.

---

## Pre-final checklist

- [ ] Every abstract number reproduces from the shipped sheet.
- [ ] Every results number reproduces from the shipped sheet or companion.
- [ ] Every method's flags match the frozen submission template.
- [ ] Every citation resolves.
- [ ] The scoring caveat in §5 is present and not softened.
- [ ] Deviations section is complete against `deviations.jsonl`.
