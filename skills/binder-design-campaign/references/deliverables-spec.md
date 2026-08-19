# Deliverables specification

Column definitions live in `../templates/sheet_schema.json`. The checks live in
`../scripts/`. This file explains what the artifacts are and the invariants
that make them trustworthy.

---

## 1. Design sheet

One CSV containing **exactly N ranked rows per target** (default 30) — the rows
to be ordered, and only those.

### 1.1 Schema is frozen at kickoff

Write `sheet_schema.json` once, at campaign kickoff: exact column names,
dtypes, enums (including the `structure_method` and `seq_method` vocabularies),
units, and the `mandatory_nonnull` set. Per-target writers validate every row
against it before writing. A merge across targets refuses sheets with renamed,
retyped, missing or duplicated columns.

### 1.2 Required columns

Identity and provenance: `design_id`, `target`, `sequence`, `binder_len`,
`structure_method`, `seq_method`, `opt_round`, `root_backbone_id`,
`parent_design_id`, `designed_structure_path`.

Ranking: `rank`, `rank_zscore`, `final_score`, `score_instrument`, `n_seeds`,
`pose_PASS`, `pose_dockq`.

Gates and diversity: `novelty_verdict_path`, `tm90_cluster_id`, `fold_class`,
`relaxation_step`, `missing_metrics`.

Structures: one `predicted_structure_path_<arm>` per ranking arm, each pointing
at that arm's best-seed prediction.

Metrics: one column per scoring arm and shadow metric actually computed —
`ipsae_<arm>`, `sc_dockq_<arm>`, `monomer_plddt`, `lcp_score`, `esmc_ll`, and
on counter-screened targets `ipsae_offtarget_<arm>` and
`selectivity_delta_<arm>`.

### 1.3 Provenance keys

`root_backbone_id` is assigned once per de novo backbone at generation time and
is shared by every derived sequence and every partial-diffusion variant, through
every optimisation round.

`structure_method` and `seq_method` are **not free text**. They are tokens from
a campaign-frozen `method_vocab.json` written once at roster validation: one
token per tool, with related-but-distinct tools kept distinct (RFdiffusion and
RFdiffusion3 are two tokens), plus a tool-to-family map and an alias map. A row
whose canonical token is absent from the enum is rejected.

### 1.4 Null policy

`mandatory_nonnull` = identity, provenance, `rank`, `rank_zscore`,
`final_score`, `score_instrument`, `pose_PASS`, `pose_dockq`,
`designed_structure_path`. Non-null on every ranked row.

Per-arm score and shadow-metric columns carry the real computed value, or
`NaN`. **A sentinel — 0.0, -1, -999, empty string — is never written in place of
a missing score.**

`NaN` alone loses the distinction that matters for the next round, so every
`NaN` is accompanied by a reason in the row's `missing_metrics` column, written
as `metric=REASON` pairs separated by semicolons and empty when nothing is
missing:

| Reason | Means | What to do about it |
|---|---|---|
| `NOT_RUN` | never dispatched for this design | top it up, or disclose the gap |
| `FAILED` | ran and errored, or produced an unusable result | a tool problem: diagnose before the next wave |
| `UNSUPPORTED` | the tool cannot represent this system — see the roster's `unsupported_inputs` | an instrument problem: it should have surfaced at G3 |
| `CONSTRUCT_FAIL` | ran, but its own output did not match the frozen construct | the scored molecule was the wrong one; never a numeric |

Three `NaN`s that are all `NOT_RUN` mean the campaign ran out of time. Three
that are `UNSUPPORTED` mean the instrument never suited the target. The sheet
should be able to tell you which.

`final_score` is computed under the frozen instrument mask recorded in
`score_instrument` (`default_3arm`, `ef2full_ptxv2_afm`, ...), so a reader can
always tell which arms produced the live ranking score for that row. A
diagnostic score from a failed arm stays in its own column, never mixed into
`final_score`.

At close-out, a null in a **required but not load-bearing** column (for example
`seq_method`, or one `predicted_structure_path_<arm>`) downgrades the row to
disclosed-with-deviation rather than dropping it.

### 1.4a The reject ledger

A design filtered out before scoring leaves the sheet, but it does not leave the
campaign. Every rejection appends one row to `ledger/rejects/<writer>.jsonl`
(`../scripts/ledger.py reject`):

```json
{"ts_utc": "...", "design_id": "...", "target": "...", "stage": "gen_screen",
 "gate": "novelty", "reason_code": "DIVERSITY_FAIL", "detail": "62% identity over 71% coverage to UniRef90 A0A...",
 "writer_id": "..."}
```

`reason_code` comes from the campaign failure vocabulary
(`../scripts/ledger.py --list-failure-types`), so rejections aggregate. Free
text goes in `detail`.

This is what lets the campaign answer **"why was this sequence discarded"** —
`../SKILL.md` §2 rule 1 applied to the designs that did not ship. It is also
the input to the next round: a target whose rejects are dominated by
`STRUCTURE_FAIL` needs different generation settings, and one dominated by
`DIVERSITY_FAIL` needs different backbones, and those are different fixes.

Reject rows are counted, not just written: at G5, report the reject total per
gate alongside the survivor count, and confirm every rejected `design_id` is
traceably absent from every scoring pool.

### 1.5 Rank assignment

Exactly one ordering key, per target:

```
ORDER BY (n_seeds >= final_tier on all arms) DESC,
         pose_PASS DESC,
         rank_zscore DESC
```

So pose-failing rows ship only at the bottom of a target's ranked set, and the
count of pose-fail rows is disclosed in the sheet's target metadata.

The **unranked** section is reserved for rows with missing or zero scores.
Below-protocol seed count is not grounds for unranked: attempt a top-up first,
then rank with the true `n_seeds` disclosed.

### 1.6 Selection caps

Enforced by the writer at row-selection time, in this order:

| # | Cap |
|---|---|
| a | reject exact-sequence duplicates |
| b | reject pairs within Levenshtein distance 5 |
| c | any single `root_backbone_id` at most 5% of rows (rounded up) |
| d | any single TM-0.90 single-linkage cluster at most 10% (rounded up) |
| e | any single `structure_method` at most 50%, and at least 3 distinct structure methods |
| f | any single `seq_method` at most two-thirds, backfilling from the next-best alternate |

These are **ceilings, not quotas**. If the ranked pool cannot fill N rows under
them, the first response is upstream: more designs, more methods.

### 1.7 Relaxation ladder

Only after regeneration has been tried. One step at a time, recording on every
affected row which step admitted it:

1. **Diversity caps** — but never past 25% per `root_backbone_id`, never past
   50% per method, never fewer than 3 distinct structure methods.
2. **Liability flags.**
3. **Novelty — last resort only**, after regeneration and the full ladder have
   failed. Admitted rows carry `relaxation_step = NOVELTY_LAST_RESORT` plus a
   deviations row naming the wall. Absolute floors that are **never** relaxed:
   no two shipped rows identical; the binder-chain target-mimic ban; the
   natural-sequence-copy ban.

`pose_dockq` non-null is **never** relaxed. `final_score` non-null is **never**
relaxed.

If even the full ladder cannot reach N, **ship the actual number**. Padding
with duplicates or with under-scored rows is forbidden.

### 1.8 Write-time gate recompute

The writer recomputes every gate from the row's own sequence and predicted
structure at write time — novelty, liability, monomer foldability, structural
plausibility, `pose_dockq`, and `final_score` from the frozen mask — at the
**same thresholds** the carried flags were set at. The row is admitted only when
the recomputed result matches the carried value to within 1e-4. A mismatch halts
the writer and names the row.

A row missing any required gate result is routed to the unranked set with the
missing gate named. A row missing `root_backbone_id`, `structure_method`,
`tm90_cluster_id` or `fold_class` is routed to unranked with the missing column
named, regardless of its score.

**A gate that exists but was not run is a protocol violation.**

---

## 2. Per-seed companion

`per_seed_metrics.parquet` (or CSV): one row per `design_id` x `scoring_arm` x
`seed`, with the raw metric values and the per-seed structure path, plus one
aggregated row per design x arm.

Invariants:

- Companion `design_id`s cover **100%** of ranked sheet `design_id`s, exact and
  case-sensitive. Lower coverage is a deliverable defect.
- On counter-screened targets, the off-target arm appears at the same seed
  count.
- No (`design_id`, `scoring_arm`) group is uniformly null on the ranking metric.
- Recompute `final_score` for a random sample of sheet rows per target **from
  the companion alone**, using the pre-registered formula; agreement within
  1e-4 or the companion is regenerated.

---

## 3. Instrument realisation table

`instrument_realization.csv`: one row per (target, ranking arm), with

```
target, arm_name, gate_status, n_seeds_run, n_ranked_with_score,
used_in_final_score, control_separation_value, drop_reason,
cofactors_present, n_target_chains_folded, native_oligomer_n
```

Every numeric is **derived** from the per-seed companion and
`state/gates/<target>.json` at write time, never hand-authored. The writer
asserts:

- `control_separation_value` is non-null on every `gate_status = PASS` row,
  except rows whose gate file records the no-literature-control path — those
  write `NA` and name that path in `drop_reason`.
- `drop_reason` is non-empty wherever `used_in_final_score = false`.
- Row-for-row agreement with a recount over the companion.

The report's scoring section is generated from this table. Any target whose
realised instrument differs from the campaign default is called out explicitly.

---

## 4. Scoreboard

`scoreboard.csv`: one row per target, exactly these columns:

```
target, designs_generated, designs_screened, designs_ranked,
best_final_score, median_final_score_ranked, pose_check_pass_rate_top10,
gpu_hours, wallclock_hours_active_compute, n_distinct_root_backbones,
max_seqs_per_root_backbone, n_tm90_clusters, max_tm90_cluster_size,
n_structure_methods, top_method_share, min_pairwise_editdist,
n_non_all_alpha
```

Every non-target column is a real computed numeric on every row: no NaN, no
sentinel, no free text. A value that cannot be computed is a defect to remediate
before close-out, tracked as a `scoreboard_gaps.csv` row
`{target, column, reason, owner}`.

Diversity columns are computed from the final ranked sheet **by the same code
that enforced the caps**.

Definitions, fixed at kickoff and not redefined mid-campaign:

- `designs_generated` — sum of `n_generated` over the ledger; a design is
  generated when its sequence is written by a generation or sequence-design job.
- `designs_screened` — sum of `n_scored` over ledger rows with `stage = screen`.
- `designs_ranked` — sum of `n_scored` over ledger rows with `stage = final`.
- Intermediate tiers record under their own stage and count toward neither.

Any redefinition mid-campaign is a logged deviation with a one-time
reconciliation row.

---

## 5. Structure bundle

```
ordered_structures/<target>/<rank:02d>_<design_id>/
    designed.pdb
    predicted_<arm>_seedbest.cif      # one per ranking arm
```

- Sheet paths are **bundle-relative** — independent of per-job tarballs and of
  any scheduler or cloud path.
- The bundle is **rebuilt from the final ranked sheet as the last close-out
  step**, never accumulated during the campaign.
- After rebuild, assert for every row that `designed_structure_path` and every
  non-null `predicted_structure_path_<arm>` resolve to a real file inside the
  bundle, and that no path string embeds a rank prefix disagreeing with the
  sheet's rank.
- Then **open** every referenced file from the delivered copy. Below 100% on
  any target is a defect to remediate before close-out.
- Package as `.tar.gz` at a natural granularity, one per target where that
  keeps each archive manageable, and verify each opens with a stock unarchiver
  before declaring it delivered.

---

## 6. Report

A publication-style write-up with figures and citations. Two rules:

1. Immediately before declaring it final, **regenerate every quantitative claim
   in the abstract and key-results sections from the as-shipped sheet,
   scoreboard and companion.** Any number that does not reproduce is corrected;
   any number that cannot be traced is removed.
2. The headline states the **worst defensible reading** of the data. Deviations
   are disclosed. Analyses tuned after seeing results are named as such, with
   the number of configurations tried.

The report states, in its own words, that the instrument is a **filter, never
an oracle** (`failure-modes.md` §1).

Outline in `../templates/report_outline.md`.

---

## 7. Deviations file

`deviations.jsonl`, append-only, never rewritten in place. One
schema-conforming JSON object per line:

```
{"at_utc": "...", "kind": "...", "target": "...", "what": "...", "action": "..."}
```

The shipped file is the **deduplicated union** of all writer subfiles, exactly
one object per line. Reconstruction or forensic material goes in a separate
companion file, never in this ledger.

---

## 8. Close-out is transactional

1. Top up seeds on any ranked row below the final tier — including matched
   off-target and oligomer companion runs, so `selectivity_delta` and N:N stay
   seed-matched. This is the first close-out action.
2. **Freeze the ranked sheet.**
3. Derive every companion from **that snapshot**: per-seed metrics, instrument
   realisation, structure bundle, README manifest, and every number in the
   report.
4. Assert every `mandatory_nonnull` column is non-null and not a placeholder.
5. Reconcile every README and manifest claim against the actual delivered
   contents. A referenced-but-absent file is a blocking defect.
6. Run every script in `../scripts/` against the as-shipped artifacts.
7. Adversarial review, all blockers resolved.
8. Deliver.

Abstract numbers equal sheet aggregates. If a surplus design beats a frozen
sheet row on the **same instrument**, it is promoted and the sheet is re-frozen
— do not ship a known-better design outside the sheet.
