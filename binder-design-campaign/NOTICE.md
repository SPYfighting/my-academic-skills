# Attribution

This repository is an independent adaptation. It is not affiliated with,
endorsed by, or reviewed by any of the projects named below.

---

## Primary source

The protocol in `binder-design-campaign/` is adapted from the campaign
prompt and technical report that Anthropic released with its autonomous binder
design work.

**Prompt and data release** — *Claude protein binder design (data release
v1.0)*, Anthropic, on HuggingFace Datasets, licensed **CC-BY-4.0**:
<https://huggingface.co/datasets/Anthropic/claude-protein-binder-design>

The specific file adapted here is
`prompts/prompts/multi_target_binder_design_prompt.md` (113,932 bytes,
16,281 words, 288 lines as retrieved on 2026-08-19). The release also contains
sixteen single-target variants of comparable length, the campaign figures, and
the binding data.

An unmodified reference copy is stored at
`sources/anthropic/multi_target_binder_design_prompt.md`. It remains under
Anthropic's CC-BY-4.0 license and is not relicensed by this repository's MIT
license. Its historical campaign instructions are reference material only.

**Technical report** — *Autonomous de novo protein binder design with Claude*,
Claude Science and Amir Shanehsazzadeh, Anthropic, 18 August 2026:
<https://www-cdn.anthropic.com/30bf50e22a01388bb29bf077ee3f244531594b7a.pdf>

**Announcement** — *How Claude is accelerating protein design and analytical
chemistry*, Anthropic:
<https://www.anthropic.com/research/Claude-accelerates-protein-design>

CC-BY-4.0 permits adaptation with attribution, which this file provides.

### What was taken, and what was not

Paths below are relative to `binder-design-campaign/`.

**Adapted from the source prompt**: the scoring-instrument design (multi-arm
co-folding, ipSAE_min with union masking, sc_DockQ pose self-consistency, the
4:1 weighted z-score, the seed tiers); the validation-gate concept and its two
conditions; the pre-scoring filter set and its thresholds; the selection caps
and the relaxation ladder; the deliverable schema and its null policy; the
verification and behaviour rules; the tool roster and its PASS criteria.

**Not carried over**: the campaign's internal orchestration — the cloud billing
governor and its submit gate implementation, the Slack threading contract, the
Google Drive coordinator, the host API surface, the watchdog and heartbeat
singletons as specified. These are replaced by a portable compute-backend
contract in `references/compute-backends.md`, which keeps their *ideas*
(fail-closed submission, metered-spend canonicality, evidence-based reaping,
generation-versus-scoring backlog capping) without the implementation.

**Adapted**: the source prompt's autonomy clause. This skill requires one
user-approved staged plan and lets the user choose whether execution stops at
intermediate checkpoints or continues through computational delivery. Agent
scientific choices and resource use stay within that approved boundary.

Numbers quoted in `references/failure-modes.md` §1 are from
the technical report as published.

---

## Adapted skill collections

No code from these is vendored; the material named below is adapted prose,
attributed here and at its point of use.

**Adaptyv Bio protein design skills** — MIT.
<https://github.com/adaptyvbio/protein-design-skills>

Adapted into `references/thresholds.md`, from three of its skills:

- `protein-qc` — the absolute cutoff table (pLDDT, pTM, scRMSD, ipSAE_min,
  ipTM, PAE_interaction, shape complementarity, interface dG, buried unsatisfied
  H-bonds, instability index, GRAVY, ESM2 pseudo-log-likelihood, folding dG),
  the sequence liability patterns, the observation that individual metrics reach
  only ~0.64–0.66 ROC AUC on their own, and the reported filtering strategies.
- `campaign-manager` — the campaign sizing table and the 50x rule of thumb, the
  pass-rate diagnostic bands, the failure tree, and the target-difficulty bands.
- `binder-design` — the Adaptyv Nipah-G head-to-head hit-rate table and the
  per-method cost-per-design figures, adapted into
  `references/tool-catalog.md` §2.1.

**Claude Science skill set**, mirrored in AcademicForge — MIT.
<https://github.com/HughYau/AcademicForge/tree/site-first/skills/claude-science>

- `esmfold2` — the three ESMFold2 bring-up gotchas in
  `references/tool-catalog.md` §4, and the Full/Fast layer-count and
  speed comparison.
- `PORTABILITY.md` — the de-vendoring pattern this repository applies to the
  campaign prompt: hand the raw material to whatever base model is running, and
  keep the skill working single-agent with parallelism as an optimisation.

**Anthropic skills** (specification and template) —
<https://github.com/anthropics/skills>

**writing-for-agents** — the document-design vocabulary used to structure
`SKILL.md` and this repository's agent-facing prose: context pointers, the
information hierarchy and progressive disclosure, completion criteria, leading
words, and the pruning discipline (single source of truth, no-ops, relevance).

---

## Cited literature

Identifiers below were resolved against Crossref while writing this file.

- Overath et al., *Predicting Experimental Success in De Novo Binder Design: A
  Meta-Analysis of 3,766 Experimentally Characterised Binders*, bioRxiv 2025,
  doi:10.1101/2025.08.14.670059 — the basis for ranking on `ipSAE_min` and for
  the absolute cutoffs in `references/thresholds.md` §3.
- Dunbrack, ipSAE, bioRxiv 2025, doi:10.1101/2025.02.10.637595 — the definition
  of `ipSAE_min` used in `references/scoring-instrument.md` §3.1.

---

## Scientific methods

The methods this protocol orchestrates are the work of their authors and carry
their own licences and citation requirements. Cite the method, not this
repository, when you use one: RFdiffusion, BindCraft, BoltzGen, PXDesign,
ProteinMPNN and SolubleMPNN, Caliby, LigandMPNN, ESMFold2, Protenix, AlphaFold
and AlphaFold-Multimer, OpenFold, Chai-1, Boltz, ipSAE, DockQ, MMseqs2,
Foldseek, DSSP, ESM-C, and any other tool you bring onto the roster.

Local Composition Perplexity is credited in the source prompt to Richard Shuai,
with its definition given as a figure in the CC-BY-4.0 data release.

---

## This repository

Original prose, structure, checklists, templates and scripts: MIT, see
`LICENSE`.
