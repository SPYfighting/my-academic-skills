# Failure modes

Read §1 before G2, read the whole file before G5, and read the relevant entry
whenever a result looks too good.

---

## 1. A filter, never an oracle

**The instrument is a filter, never an oracle.** That sentence is the skill's
load-bearing calibration fact, it appears as a non-negotiable in `../SKILL.md`,
and this section is where it is earned. It means: confidence ranks designs
*within* a target, and carries no reliable signal about whether the target will
yield anything at all.

It is measured, not assumed.

In the published campaign (technical report, Anthropic, 18 Aug 2026, released
alongside the source prompt), 1,320 designs were synthesised across 15
interpretable targets and 354 bound, a 27% hit rate. Three targets produced
almost nothing: **maltose-binding protein 0 of 90**, the de novo beta-barrel
**BBF-14 3 of 90**, and **15-PGDH 1**. The report's finding on those failures:

> the co-folding scores that guided the campaign gave little warning ... Designs
> against MBP, BBF-14, and 15-PGDH scored nearly as highly as designs against
> targets that yielded many binders, such as VEGF-A and Nipah G.

Re-scored uniformly after the fact:

| Question | Answer from the campaign data |
|---|---|
| Does confidence rank binders above non-binders **within** a target? | Yes, on 12 of 13 evaluable targets; mean average precision 0.52 against 0.31 expected by chance |
| Does it tell you **which targets** will work? | Median score rose with hit rate, but not steeply enough to have flagged the failures in advance |
| Does it predict **affinity** among binders? | Only weakly |

**What follows for practice.** A confident co-fold is a useful requirement for
selection and a poor predictor of campaign success. Do not tell a user their
campaign looks promising because the scores are high. Report scores as what
they are: a within-target ranking signal. Experimental screening remains the
only way to learn whether a target worked and what the affinities are.

Say this explicitly at G5. It is the caveat most likely to be dropped from a
summary, and dropping it is the failure this skill exists to prevent.

---

## 2. Target-fold mimicry

A structure generator conditioned on the full target complex, asked for a
binder length close to a target chain's, may simply reproduce that chain's
fold. From the training data, a protomer is an excellent binder of its
oligomeric neighbours. Most acute on homo-oligomeric targets.

**Catch it in the novelty gate, not downstream**: TM-score >=0.5 to any target
or control chain is a reject, alongside the sequence-identity criteria.
Verify the reject list is traceably absent from every scoring pool.

---

## 3. Ubiquitin and other natural-sequence emergence

Ubiquitin (UniProt P0CG47 / P0CG48) recurs as a designed "binder", often with
short terminal extensions that defeat exact-match detection. Screen by **local
alignment** against UniRef90, not by exact or full-length match. The relevant
criterion is >=30% gapped local identity over >=40 aligned residues.

The binder-chain target-mimic ban and the natural-sequence-copy ban are
**absolute** and are never relaxed, even when relaxing everything else fails to
fill the sheet.

---

## 4. A gate that passes everything, fails everything, or returns a constant

Broken until investigated. After the first shard of any scoring or filtering
stage, confirm from its outputs that the stage ran as specified — item counts,
pass and fail counts, at least one spot-checked example — **before** launching
the full fleet.

The related anomaly list: a score of exactly zero, a perfect metric, an
impossible runtime, a per-design standard deviation of exactly zero across
multiple seeds.

---

## 5. Convenience crop is not the assay construct

The scoring construct must match the system that will actually be measured:
correct residue range, correct oligomeric state, correct cofactors. A crop
chosen for GPU memory that silently becomes the scoring construct produces
scores about a molecule nobody will assay.

Enforce mechanically, not by intent: the scoring job parses **its own output
structure**, compares asserted chain count and cofactor atom counts against the
frozen construct in `state/gates/<target>.json`, and on mismatch writes the
score as `NaN` with `construct_status = CONSTRUCT_FAIL` — never a numeric.

---

## 6. Silently dropped cofactors

All three default ranking arms accept non-protein context. An arm that ran
without a fold-required metal or a required nucleic-acid partner produced a
number about the wrong molecule. Before recording that a co-folder cannot
represent something, check the model's own paper and API rather than your
wrapper: a missing wrapper input class is a bring-up fix, not a model
limitation. An oversized target is handled by a biologically reasonable crop
with the model retained in the panel.

Record per arm, in the instrument realisation table, which cofactors were
present and how many target chains were folded, against the dossier's native
oligomer count. An all-cofactor-blind or all-monomer ranking on a target whose
dossier flags a fold-required cofactor is a logged deviation.

---

## 7. ipTM inflation on multimers

Whole-complex ipTM on a multimeric target is inflated by the native
protomer-protomer interfaces and compresses design-versus-control separation.
Do not rank on it. If you track it, compute a binder-masked `iptm_binder` on the
union masks and interpret the whole-complex value with the inflation in mind.

---

## 8. Cross-target and cross-batch score comparison

Two separate invalidities, often conflated:

- **Raw** co-folding scores compress with chain count and vary with target
  size and composition. Comparing raw ipSAE across targets is meaningless.
- **z-scores** are transductive: mu and sigma come from the scored pool, so a
  z-score is meaningless outside the batch that produced it.

There is no correct way to say "target A scored better than target B" from
these numbers.

---

## 9. Generator to sequence-design adapter breakage

Several structure generators emit backbone files that break downstream sequence
design unless adapted: CA-only PDBs requiring CA-only weights or full-backbone
reconstruction; non-standard binder residue `comp_id` values requiring rewrite
to GLY; binder and target chain order swapped.

Validate the **handoff** during bring-up, on a real campaign target — not the
generator in isolation. A generator that passes bring-up alone and contributes
zero ranked backbones campaign-wide is a reportable defect.

---

## 10. Seed and aggregation mistakes

- Non-distinct seeds: assert `len(set(seeds)) == n_seeds`.
- DockQ taken from a different seed than the one that produced the arm's
  ipSAE_min. Record both argmax seeds.
- A design dropped for seed count before a top-up was attempted. A design a few
  seeds short of protocol is **incomplete**, not below-protocol.

---

## 11. Sentinel values and silent nulls

A missing score is `NaN`. Never `0.0`, `-1`, `-999` or an empty string — each
of those becomes a real number in a mean and silently reorders a ranking.

A null in a **required, load-bearing** column blocks the row. A null in a
required-but-not-load-bearing column downgrades the row to
disclosed-with-deviation rather than dropping it at close-out.

---

## 12. Ledger and count drift

Counts reconstructed from commanded volumes, from memory, or by listing output
files drift from reality. Every count is an aggregation over the ledger at
report time. If an aggregation finds the ledger empty after a scoring wave
completed, that is a fail-loud condition, not a zero to report.

Concurrent appends to a single shared ledger file on a network filesystem are
not atomic and silently clobber. Use one subfile per writer.

---

## 13. Path and rank mismatch in the shipped bundle

The structure bundle is **rebuilt from the final ranked sheet as the last
close-out step**, never accumulated during the campaign. After rebuild, assert
for every row that each path resolves to a real file inside the bundle and that
no path string embeds a rank prefix disagreeing with the sheet's rank. Then
**open** every file, from the delivered copy — path resolution is not proof of
a readable file.

---

## 14. Relaxation used as a first response

Relaxation is a disclosed last resort applied by changing the writer's
configured thresholds — never by deleting, commenting out, no-oping or
monkeypatching a gate predicate, and never as the first response to an
under-diverse pool or to low scores. The first response is upstream: more
designs, more methods.

---

## 15. Target difficulty that the literature already predicted

MBP is a two-lobed periplasmic protein with a large, convex, predominantly
**polar** surface; BBF-14 is a de novo beta-barrel with **no evolutionary
history**, so no natural partner defines a functional epitope. Both were hard
for reasons visible before any compute was spent.

At G2, state the surface character honestly. A large polar convex surface, a
shallow site, a glycan-shielded epitope, or a designed protein with no natural
binding partner are all reasons to lower the expectation you communicate — and
reasons to propose a second epitope as a hedge.
