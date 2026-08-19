# Source mapping

Where each part of the source prompt went. The source is
`prompts/prompts/multi_target_binder_design_prompt.md` from Anthropic's
CC-BY-4.0 release (113,932 bytes, 16,281 words, 288 lines as retrieved
2026-08-19). It has no Markdown headings; its sections are marked by line-initial
keywords such as `Task:`, `Compute:`, `Deliverables:`, which are the section
names used below.

Use this table when you want to check that an adaptation is faithful, or when
you want to go back to the original wording of a rule.

Paths in the right-hand column are relative to `skills/binder-design-campaign/`;
paths in the left-hand column are relative to the HuggingFace release.

| Source section | Disposition | Where it lives now |
|---|---|---|
| `Addressing:` (obligations by agent depth) | adapted | `SKILL.md` §2, §10 |
| `Task:` + the 14-target list | generalised | `templates/campaign_config.yaml`, `templates/target_dossier.md` — targets become user input at G0 |
| The 29 reference links | generalised | `references/tool-catalog.md` §6, `references/target-dossier-guide.md` §6 — the campaign-specific competition links are not reproduced |
| Per-target dossier requirements (oligomeric state, cofactors, assay construct, deposited structures) | kept, expanded | `references/target-dossier-guide.md`, gate G1 |
| Epitope and hotspot selection guidance | kept, made interactive | `references/target-dossier-guide.md`, gate G2 in `checklists/gate-checklists.md` |
| `Models and Tools:` roster | kept as dated pointers | `references/tool-catalog.md` §§2–4 |
| Tool-specific install notes (ESMFold2, Protenix v2, AF3+OF3, FoldCraft) | kept verbatim in substance, marked re-verify | `references/tool-catalog.md` §4 |
| Licence exclusions (AF3 weights, PyRosetta, ESM3) | kept **and made conditional** | `references/tool-catalog.md` §5 — the source's commercial-licence regime is one of two options chosen at G0 |
| Output-format adapter warning | kept, promoted | `references/tool-catalog.md` §1 criterion 5, `references/failure-modes.md` §9 |
| Design strategy: binder length, de novo only, structure→sequence vs co-design | kept | `references/tool-catalog.md` §2, `workflows/binder-design.md` stage 6 |
| Method floor (50 backbones per asterisked method per target) | kept, parameterised | `workflows/binder-design.md` stage 6 |
| Target-fold mimicry warning | kept, promoted | `references/failure-modes.md` §2 |
| Fold diversity (10% non-all-alpha, DSSP definition) | kept | `references/tool-catalog.md` §2, `templates/sheet_schema.json` |
| Sequence design (SolubleMPNN, SolubleCaliby, Protpardelle ensemble) | kept | `references/tool-catalog.md` §3 |
| LCP restraint | kept as a pointer to the source figure | `references/scoring-instrument.md` §3.4 |
| Pre-scoring filters (novelty, liability, foldability, plausibility) with thresholds | kept | `references/scoring-instrument.md` §8 |
| Redundancy clustering | kept | `references/scoring-instrument.md` §8 |
| Provenance keys, method_vocab, alias map | kept | `references/deliverables-spec.md` §1.3 |
| Selection caps (a)–(f) | kept, made runnable | `references/deliverables-spec.md` §1.6, `scripts/check_diversity.py` |
| Scoring instrument (3 arms, ipSAE_min, sc_DockQ, pose_PASS) | kept | `references/scoring-instrument.md` §§2–3 |
| final_score and rank_zscore formulas, 4:1 weighting | kept | `references/scoring-instrument.md` §4 |
| Seed tiers (SCREEN / INTERMEDIATE / FINAL) | kept, with an `explore` variant | `references/scoring-instrument.md` §5, `SKILL.md` §5 |
| Validation gate, conditions (a) and (b), control selection | kept, made a human gate too | `references/validation-gates.md`, gate G3 |
| MSA caching rules | kept | `references/tool-catalog.md` §4 |
| ipSAE union-mask construction for multimers | kept | `references/scoring-instrument.md` §3.1 |
| z-score transductivity | kept, promoted | `references/scoring-instrument.md` §6, `references/failure-modes.md` §8 |
| Pose self-consistency and seed concordance | kept | `references/scoring-instrument.md` §3.2 |
| Oligomeric 1:N and N:N scoring | kept | `references/scoring-instrument.md` §3.2, `templates/sheet_schema.json` |
| ipTM inflation note | kept | `references/failure-modes.md` §7 |
| Calibration bands (Barnase/Barstar ceiling, constructed floor) | kept | `references/scoring-instrument.md` §7 |
| ESMC log-likelihood | kept | `references/scoring-instrument.md` §3.4 |
| In silico optimisation and round discipline | kept | `references/scoring-instrument.md` §9, `workflows/binder-design.md` stage 7 |
| "Nothing is discarded" storage rule | kept | `SKILL.md` §4 |
| `Compute:` — Modal pricing, governor arithmetic, `submit_gate.py`, bootstrap exception, billing calibration | **replaced** | `references/compute-backends.md` §§1, 4, 5 — the ideas kept (fail-closed gate, metered canonicality, single ceiling, evidence-based reaping), the implementation dropped |
| Design-count ledger, per-writer subfiles, stage definitions | kept, made runnable | `references/compute-backends.md` §6, `scripts/ledger.py` |
| `gen_screen` coupled job type | kept | `references/compute-backends.md` §5 |
| Generation-vs-scoring backlog cap | kept, made runnable | `references/compute-backends.md` §5, `scripts/ledger.py backlog` |
| `Resources:` — $50,000 Modal budget, spend-to-target rule | generalised | `references/compute-backends.md` §4 — asks at G0 whether the budget is a ceiling or a target |
| Per-target weight blending (prior + live observables) | kept | `workflows/binder-design.md` stage 5, gate G4 |
| `Deliverables:` Slack cadence, threading invariant, status block | **dropped** | not portable; the reporting discipline it enforced is in `SKILL.md` §4 ("ledger before narrative") |
| Google Drive invariants, single-writer rule | **dropped** | `references/deliverables-spec.md` §8 keeps the transactional close-out that mattered |
| Design sheet schema, null policy, rank key, relaxation ladder | kept, made runnable | `references/deliverables-spec.md` §1, `templates/sheet_schema.json`, `scripts/check_design_sheet.py` |
| per_seed_metrics companion | kept | `references/deliverables-spec.md` §2 |
| instrument_realization.csv | kept | `references/deliverables-spec.md` §3 |
| Scoreboard columns | kept, made runnable | `references/deliverables-spec.md` §4, `scripts/make_scoreboard.py` |
| Supplement / ordered_structures bundle and retrievability check | kept | `references/deliverables-spec.md` §5, `references/failure-modes.md` §13 |
| Report requirements | kept | `templates/report_outline.md` |
| Review fleet (5+ auditors, one with GPU, one blind) | kept, scaled | `SKILL.md` §10 |
| `Timeline:` / `Timing:` — 48-hour window, zero-dormancy rule, CLOCK singleton, orchestrator sleep bans | **dropped** | artefacts of one autonomous run; the close-out reserve survives in `references/deliverables-spec.md` §8 |
| `Sub-agents:` / `Delegation:` — 100+ concurrent agents, delegation architecture | adapted, made optional | `SKILL.md` §10 |
| WATCHDOG / BUDGET / SCRIBE singletons, heartbeat protocol | **replaced** | `references/compute-backends.md` §§7–8 and `scripts/preflight.py`, which keeps the in-job dead-man switch |
| `Literature:` — triggered re-reads | kept | `references/tool-catalog.md` §8 |
| `Behavior:` — establish before stating, no identifiers from memory, anomalies are bugs, lead with the unfavourable result | kept, promoted to the top | `SKILL.md` §2 |
| `Verification:` — roster PASS criteria, canary before fan-out, reconciliation | kept | `references/tool-catalog.md` §1, `references/compute-backends.md` §§1, 7 |
| Ranking-artifact writer invariants | kept, made runnable | `scripts/check_design_sheet.py` |
| `Unavailability:` — query before declaring a tool missing | kept | `references/tool-catalog.md` §7 |
| `Logistics:` — design_id scheme, script version stamping, secret handling | kept | `references/compute-backends.md` §1, `references/deliverables-spec.md` §1.3 |
| `Isolation:` / `Volume layout:` | adapted | `references/compute-backends.md` §9 |
| `Slack input:` — verify relayed directives | dropped as written | the gate model makes the human the direct channel |
| `Creativity and perseverance:` — evidence-based allocation, living ideas document | kept | `workflows/binder-design.md` stage 5, stage 7 |
| `Autonomy:` — never ask the operator | **inverted** | the seven gates in `checklists/gate-checklists.md` |
| `Safety:` — no bioweapons work, comply immediately with a stop | kept, expanded | `SKILL.md` §2 rule 8, `../RESPONSIBLE_USE.md` |

## Added here, not in the source

- The seven-gate model and its checklists.
- The `explore` and `standard` scale presets.
- The Slurm and local compute adapters.
- The runnable checks in `scripts/`, and the fixture in `examples/binder-design-campaign/minimal/`.
- The two generalised workflows (`structure-prediction.md`,
  `protein-design-general.md`).
- `failure-modes.md` §1, which turns the technical report's post-hoc finding
  about score calibration into a standing instruction.
- The licence-regime question at G0, which re-admits tools the source campaign
  excluded on commercial-licence grounds.
- The **campaign brief** at G0 (`templates/campaign_config.yaml`): the
  experimental endpoint, success and failure criteria, and
  `negative_objectives`. The source prompt fixed all of these itself, so it
  never needed to ask; a skill that serves an arbitrary target must.
- The **campaign failure vocabulary** and the **reject ledger**
  (`scripts/ledger.py`), so "why was this design discarded" and "where is this
  campaign failing" are aggregations rather than reading exercises.
- **Distinguishable missing-value semantics** (`NOT_RUN` / `FAILED` /
  `UNSUPPORTED` / `CONSTRUCT_FAIL`). The source banned sentinels and required
  NaN; NaN alone cannot tell a timed-out arm from an unsuitable one.
- `templates/scoring_policy.yaml`, so the ranking formula is frozen as a file
  the checks read rather than as prose in three documents.
- The **perturbation control** at G3 (hotspot-deleted positive control), which
  tests whether an arm is scoring the specified epitope rather than merely
  noticing two plausible proteins.
- The **selection portfolio** at G5 (exploit / explore / cross-arm disagreement),
  replacing an unexamined top-N.
- Enzyme and catalysis fields in the general protein-design dossier.
