# Gate checklists

Read the relevant section at each checkpoint. Save the tables and evidence in
the campaign state. Present them to the user when the approved plan names a
review stop or its stage limit has been reached; otherwise continue within the
approved boundary.

Rules that apply to every gate:

- **Respect the approved stage limit.** G0 always waits for user approval.
  Later checkpoints stop only when the plan requires review, a material premise
  changes, or the approved limit has been reached.
- **Show the evidence, not the conclusion.** Every row that carries a fact
  carries where the fact came from (accession, PDB ID, DOI, or the command that
  produced it). A row you could not source says `unsourced` and explains why.
- **Record the decision.** Append its source (`agent` or `user`), evidence,
  timestamp and wording to `state/decisions.jsonl` before moving on. A user
  review receives a recommendation and its reason; an agent decision cites the
  same evidence rather than implying the user approved a scientific judgment.
- **A gate re-opens when its premise changes.** If a fold-recapitulation
  failure at G3 shows the construct was wrong, you are back at G1.

---

## G0 — Scope and resources

Blocks execution beyond planning until the user authorizes a stage range.

Use `../references/campaign-planning.md` for the one-round intake and the
campaign plan. Research discoverable facts before asking. The first three
topics below define the brief; unanswered technical fields may be sourced or
marked as assumptions in the plan rather than blocking its preparation.

1. **The endpoint**: what the experiment will actually measure, and how. Not
   "a high-scoring binder" - "SPR K_D against the human ECD, with no response
   on the mouse ortholog at 1 uM". An in silico metric is the **proxy**, never
   the objective; record both separately in `brief:` of
   `../templates/campaign_config.yaml`. If the user states a proxy as the goal,
   say so and ask what it is a proxy for.
2. **Success and failure**: what would make this campaign worth having run, and
   what would make it a failure. Both are stated **before** any compute, so the
   answer is not written after seeing the data.
3. **What it must not do**: `negative_objectives`. Counter-targets, unwanted
   self-association, competing substrates, aggregation-prone states. Asking
   only what the user wants is how a selective binder becomes a promiscuous
   one. Each scorable entry becomes a counter-screen; each unscorable one is
   checked at G5 by inspection and said so.
4. **Workflow**: binder design / structure prediction / general protein design.
5. **Target(s)**: name or sequence from the user; fetch the accession,
   organism and oligomeric state where possible.
6. **Deliverable**: how many designs per target, and what happens to them
   (in-house expression, CRO order, computational only). Default 30 per target.
7. **Compute resources**: inspect available local, Slurm or cloud resources;
   ask for an explicit spending ceiling before using paid compute. Account
   balance or available GPUs do not themselves grant spending authority.
8. **Scale preset**: `explore` / `standard` / `full`, or explicit numbers.

    | Preset | Generated per target | Screen | Final | Optimisation rounds | Envelope |
    |---|---|---|---|---|---|
    | `explore` | 1e2 - 1e3 | 1 seed | 3 seeds | 1 | a few GPU-hours; proves the pipeline end to end |
    | `standard` | 1e3 - 1e4 | 1 seed | 5 seeds | 2 - 3 | 1 - 3 days on a small allocation |
    | `full` | 1e5 - 1e6 | 1 seed | 5 seeds | 2 - 5+ | matches the source campaign; large cluster or cloud budget |

    Default to `standard`. Under `explore`, say so in every deliverable: it is a
    pipeline validation, and its yield expectations are not the published
    campaign's. Size against the number of binders actually wanted using
    `../references/thresholds.md` §4, then adjust to the real quota.
9. **Licence constraints**: whether the work must stay
   commercially-licensable. This changes the tool roster materially — see
   `../references/tool-catalog.md` §5. Academic-only use unlocks PyRosetta and
   several other tools that the source campaign excluded.
10. **Storage**: where campaign state, intermediates and deliverables live, and
   the available quota. The protocol discards nothing; a campaign that runs out
   of disk mid-wave loses provenance.
11. **Existing assets**: structures, prior designs, or an epitope the user
    already wants used. Also **what an earlier round measured**, in their own
    words: which designs expressed, which bound, which were promiscuous, what
    the assay could not resolve. That is the only route by which experimental
    outcomes reach this protocol, and it is one-way - the campaign uses them to
    choose an epitope, a difficulty prior and a negative objective, and it does
    not analyse the data or claim conclusions from it.

Present `state/campaign_plan.md` before execution: the brief, stages, proposed
scientific decisions, backend, deliverables, estimated GPU-hours with arithmetic,
resource ceiling and review stops. Ask the user how far to authorize, 0–10.

**Pass criterion**: the user confirms a specific plan and stage limit. Write
`state/authorization.json` only then. A plan without approval has stage limit 0.

---

## G1 — Target dossier review

Blocks: epitope selection.

Build one dossier per target per `../references/target-dossier-guide.md`, using
`../templates/target_dossier.md`. Present as a table, one row per target:

| Field | What must be in it |
|---|---|
| `target` | name and UniProt accession, as fetched |
| `assay_construct` | exact residue range, tags, fusion context, expression host |
| `oligomeric_state` | state **at assay conditions**, with the evidence |
| `cofactors` | structural metals, nucleic acids, glycans, lipids, small molecules; each marked fold-required / interface-required / incidental |
| `reference_structures` | candidate PDB IDs with method, resolution, state (apo/holo), and whether the intended epitope region is **ordered** |
| `chosen_structure` | which one, and why it matches the assay construct |
| `known_binders` | literature binders usable as positive controls, and their format (natural ligand / receptor ectodomain / peptide / antibody) |
| `counter_target` | paralog to select against, if any, with accession |
| `prior_difficulty` | your read on difficulty from primary literature, with reasoning |
| `open_questions` | what you could not resolve |

Flag explicitly, above the table, any of these:

- The convenience crop differs from the assay construct.
- A cofactor is fold- or interface-required (this forces instrument choices at
  G3 — every ranking arm must represent it).
- No deposited structure has the intended epitope ordered.
- No non-antibody positive control exists (this changes what G3 can prove).

**Pass criterion**: the construct, chosen structure and cofactor list are
sourced and recorded as frozen inputs. The agent can make this decision inside
the approved range; use a user review stop only if requested or if a material
assumption about the intended assay remains unresolved. Changing these inputs
later invalidates scores computed under the old ones.

---

## G2 — Epitope and hotspot selection

Blocks: any design generation.

Present, per target, **3 to 6 candidate epitopes** as a table:

| Field | What must be in it |
|---|---|
| `epitope_id` | short label |
| `residues` | residue list in the numbering of the chosen structure, and the mapping to UniProt numbering |
| `surface_character` | area, hydrophobic fraction, convexity/concavity, secondary structure |
| `biological_role` | what natural partner binds here, cited |
| `design_precedent` | published binders at this site, and their outcome |
| `mechanistic_hypothesis` | what a binder here would *do* — block, stabilise, degrade, report |
| `assay_accessibility` | is this site exposed in the assay construct and format |
| `risks` | flexibility, glycan shielding, membrane proximity, cofactor occlusion, shallowness |
| `recommendation` | your ranking of this epitope, with one sentence |

Also state, per target:

- The **hotspot residues** you would pass to the generator, per epitope.
- Whether you propose a **second epitope** as a hedge, and the cost.
- For homo-oligomeric targets, the **target-fold mimicry risk** and how the
  novelty gate will catch it (`../references/failure-modes.md` §2).

**Pass criterion**: the chosen epitope(s), rejected alternatives and hotspot
residues have recorded evidence. The agent may choose them within the approved
range; the user can review or override. Every downstream contig cites the
recorded residue list.

---

## G3 — Instrument validation

Blocks: **all production scoring**. Mechanical, non-waivable.

This gate tests whether the scoring instrument can separate known binding from
negative controls on this target when such controls exist. Full
procedure in `../references/validation-gates.md`.

Produce `state/gates/<target>.json` and present its contents:

| Condition | What it proves | Recorded value |
|---|---|---|
| (a) fold recapitulation | the arm can model this target at all | CA-RMSD to the reference structure, per arm, against a named threshold; any core-scoping disclosed |
| (b) positive-control separation | the arm can distinguish a real binder from noise **on this target** | control score minus negative-control scores, per arm, at full native stoichiometry |

Also present:

- The **frozen instrument mask**: which arms are in, which are out, why.
- The **frozen construct**: chains, crop, cofactors — asserted in the output
  structure file, not merely intended in the input script.
- The **frozen thresholds**: monomer pLDDT (with its scale), pose_dockq,
  novelty identity and coverage, structural-plausibility cutoffs. Published
  starting values are in `../references/thresholds.md` §2; freeze them against
  the controls you just ran, not against the table.
- The **calibration bands**: raw-score ceiling from native high-affinity
  complexes, floor from constructed negatives.
- The filled **`../templates/scoring_policy.yaml`**, including any alternative
  ranking formula you want to pre-register instead of the default and the
  control-separation evidence that justifies it.

**Pass criterion**: the gate file has `status: PASS` and a truthful
`evidence_level`, with frozen mask, construct and thresholds. If (b) fails on
every arm, try the three recovery options in
`../references/validation-gates.md` §4 within the approved resources. If none
works, stop and present the weaker evidence and a revised plan; do not silently
declare the instrument validated.

If no literature control exists after a documented search, record
`evidence_level: FOLD_ONLY`. It permits exploratory scoring only when the
approved plan explicitly allows it. Say plainly that binding discrimination
has not been demonstrated on this target.

---

## G4 — Production scale and budget

Blocks: the production waves.

Present:

- **Per-target allocation**: designs to generate, methods and their share,
  seeds per tier, optimisation rounds, and the arithmetic from those to
  GPU-hours and (on metered backends) to money.
- **Method floor**: the minimum backbones each roster method must contribute
  per target, and which methods are at risk of missing it.
- **Wave plan**: what runs in parallel, what has a data dependency, and the
  first checkpoint at which you will report measured throughput against this
  plan.
- **What you will cut first** if the allocation proves optimistic.
- **The expected pass rate** for each target's difficulty, from
  `../references/thresholds.md` §5, so the first wave's realised rate can be
  read as a diagnostic rather than a surprise.

**Pass criterion**: allocation is inside the G0 resource ceiling and recorded.
Any increase needs a revised user-approved ceiling; in-range reallocations are
agent decisions with ledger evidence.

---

## G5 — Final selection review

Blocks: delivery.

Run `../scripts/check_design_sheet.py` and `../scripts/check_diversity.py` first and
paste their output. Then present, per target:

1. **The ranked sheet**, all N rows, with at minimum: rank, design_id,
   sequence length, `final_score`, `rank_zscore`, `pose_PASS`, `pose_dockq`,
   `structure_method`, `seq_method`, `opt_round`, `n_seeds`, `fold_class`.
2. **Diversity summary**: distinct root backbones, largest single-backbone
   share, TM-0.90 cluster count and largest cluster share, method shares,
   minimum pairwise edit distance, non-all-alpha count.
3. **What this set buys, beyond the top N scores.** A plate that tests one
   hypothesis N times is a wasted plate. State the split you are shipping and
   why, in three parts:

    - **exploit** - the highest-ranked designs;
    - **explore** - structural and sequence diversity the caps preserved;
    - **disagree** - designs where the ranking arms disagree most.

    The third is the one that gets forgotten, and it is free: the per-seed
    companion already holds every arm's score, so cross-arm variance is a
    column away. A design the arms disagree about is where an experiment
    removes the most uncertainty, which is not the same as where it is most
    likely to succeed. No fixed ratio is prescribed; ship a stated split rather
    than an unexamined top-N, and record it as the answer to "why these".

4. **Every relaxation applied**, in the order applied, with the row IDs it
   admitted and the wall it worked around.
5. **Every deviation** logged during the campaign, as a list.
6. **The honest caveats**: that the instrument is a **filter, never an
   oracle**; the seed variance you measured; the realised pass rate against the
   dossier's `prior_difficulty`; anything about this target that makes you less
   confident than the numbers suggest.

**Pass criterion**: the sheet passes its checks and the selection rationale is
recorded. If the approved range ends here, present it for review. A user edit
is recorded as a row-level annotation, never silently applied. Ordering is an
external action and requires its own authorization.

---

## G6 — Delivery and archive

Blocks: declaring completion.

Run the relevant validators against the **as-shipped** artifacts and save
their output. Then confirm each of these with the evidence beside it:

- [ ] Design sheet passes schema, null-policy and diversity checks.
- [ ] Per-seed companion covers 100% of ranked design_ids, exact match.
- [ ] `final_score` recomputed from the companion alone agrees with the sheet
      to within 1e-4 on a random sample per target.
- [ ] Instrument realisation table agrees row-for-row with a recount over the
      companion.
- [ ] Scoreboard has a real numeric in every non-target column.
- [ ] Every `designed_structure_path` and every non-null
      `predicted_structure_path_*` **opens** from the shipped bundle.
- [ ] Every quantitative claim in the report reproduces from the shipped sheet.
- [ ] Adversarial review complete: at least one re-derivation from raw inputs,
      at least one blind verdict. All blockers resolved.
- [ ] Deviations file is the deduplicated union, one JSON object per line.
- [ ] Archive location and its total size stated.

**Pass criterion**: every box checked with evidence shown. If a box cannot be
checked, deliver an explicit open defect, not a claim of completion. Present
the result when the authorized range ends; user acceptance can follow delivery.
