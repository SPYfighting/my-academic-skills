# Changelog

All notable changes to this project are recorded here.
Format follows Keep a Changelog; versioning is semantic.

## [0.9.2] - 2026-11-16

### Changed

- `paper-anchor` 0.4.2 clarifies evidence completion across tasks, how to
  reconcile conflicting records, when to reuse an evidence ID for a rerun,
  who writes back during parallel work, and when to update a local skill copy.

## [0.9.1] - 2026-11-16

### Changed

- `paper-anchor` 0.4.1 uses `PAPER.md` as the project overview. Evidence
  rows link to their tasks, available interim or final results, and figures
  or tables. Refresh the links and next steps when status, results, or paths
  change. The example and offline self-check cover an in-progress analysis.

## [0.9.0] - 2026-11-16

### Changed

- `paper-anchor` 0.4.0 uses a Markdown workflow. Projects whose rules adopt it
  use it by default, creating `PAPER.md` when they first need to record the paper
  design. Each claim carries its next scientific step.

### Removed

- Removed the separate activation snippet, initialization command, generated
  dashboard, handoff section, installer, and Git hook. The offline Python
  self-check remains for maintainers and validates the bundled fixtures.

## [0.8.0] - 2026-11-16

### Added

- `paper-anchor` 0.3.1: organize paper claims, evidence, reviewable artifacts,
  and research handoffs in `PAPER.md`. Includes a template, a fictional example,
  a standard-library checker, and an optional staged-file Git hook.
- Offline self-checks for legacy tables, artifact paths, dashboard updates,
  and malformed evidence. Scientific interpretation, external sources, and
  native agent discovery require separate validation.

## [0.7.0] - 2026-09-30

### Changed
- Binder campaigns now begin with one reviewable staged plan. The user chooses
  an execution limit from plan-only through computational delivery; later
  scientific checkpoints are recorded and reviewed when requested or when the
  approved boundary changes.
- Bundled the unmodified Anthropic multi-target prompt as CC-BY-4.0 reference
  material, separate from the active skill instructions.
- `preflight.py` now distinguishes permission to proceed from a stand-down,
  checks the authorized stage and target gate, and requires explicit stage and
  target arguments for production jobs.
- The design-sheet checker now recomputes `final_score` and `rank_zscore` from
  frozen scoring terms and full-pool normalization statistics.

### Validation
- Extended the synthetic fixture and self-check to exercise authorized and
  blocked execution paths, plus altered summary scores. No real-target
  end-to-end campaign or experimental binder yield has been validated.

## [0.6.0] - 2026-09-28

### Added
- `scientific-ppt-drawing` 0.1.0: create scientific figures from descriptions, reference images, or SVG as native editable PowerPoint paths and live text. It launches PowerPoint for a new file and can transfer objects into a specified open deck. The Baker panel-a workflow was visually and editability checked in macOS PowerPoint 16.113.2. Windows native editing remains untested.
- Offline self-check for native shapes, text, unsupported input, fallback font, and conservative PPTX markup. A compatibility command identifies versioned Office extensions, linked resources, media, and picture objects; the renderer's blank template no longer contains newer Office extension markers.

### Changed
- Added the new skill to the bilingual indexes, installation guidance, routing table, and attribution index.

## [0.5.0] - 2026-09-08

### Added
- `scientific-illustrator-local` 0.2.1: English instructions, local vector reconstruction with live text, Windows/macOS adapters, and a portable self-check. Native drawing has been tested on Windows with Illustrator 27.2.0; other native environments remain unverified.

### Changed
- Concise bilingual repository indexes and general maintenance/installation guidance, following the structure of `my-skills`.
- Correct project skill discovery paths for Codex, Claude Code, and OpenCode; dependencies are declared per skill.
- Protein-design attribution, license, and responsible-use details now travel with that skill. Its scientific workflow is unchanged.
- Repository checks validate skill entry points and report missing self-checks as failures.

## [0.4.0] - 2026-08-19

Repository layout and documentation. No change to what the protocol does.

### Changed
- **Skills now live in top-level directories**, matching the layout of the
  author's other skill repositories: `binder-design-campaign/` rather than
  `skills/binder-design-campaign/`. Each skill is self-contained, so symlinking
  the directory is the whole installation. Its fixture and its rationale docs
  moved inside it.
- **`README.md` is Chinese** and leads with what the skill is adapted from, what
  it deliberately does not do, and a flowchart of who decides what at each of the
  seven gates. English moved to `README.en.md`.
- **`check.py` discovers skills by convention** and delegates to each one's
  `scripts/selfcheck.py`, so adding a skill needs no change to it. A skill
  without a self-check is reported as unchecked rather than passing silently.
- Repository conventions - layout, how to add a skill, version and commit rules,
  writing discipline - consolidated into `AGENTS.md`. `CONTRIBUTING.md` points
  at it instead of restating it.

### Removed
- `examples/binder-design-campaign/minimal/scoreboard.csv`, a derived artifact
  the self-check regenerates.

## [0.3.0] - 2026-08-19

Response to an external design review. The theme: add what the model will not
do reliably under pressure, put it where it costs nothing at runtime, and cut
what the model already does by default.

### Added
- **Campaign brief at G0** (`templates/campaign_config.yaml`, `brief:`): the
  experimental endpoint, success and failure criteria stated before any
  compute, and `negative_objectives` as a first-class list. G0 now asks what
  the experiment measures before it asks how many designs to make.
- **Campaign failure vocabulary** (21 codes, `scripts/ledger.py`), shared by
  deviations and rejections and enforced by argparse.
- **Reject ledger** (`ledger.py reject` / `rejects`): one row per design
  filtered out before scoring, so "why was this discarded" and "where is this
  campaign failing" are aggregations.
- **Distinguishable missing-value semantics**: a `missing_metrics` column
  pairing every NaN with `NOT_RUN`, `FAILED`, `UNSUPPORTED` or
  `CONSTRUCT_FAIL`, checked both ways by `check_design_sheet.py`.
- `templates/scoring_policy.yaml`: the ranking formula as a file the checks
  read, frozen at G3, replacing the same formula restated in three documents.
- **Perturbation control** at G3 (hotspot-deleted positive control), which
  tests whether an arm scores the specified epitope.
- **Selection portfolio** at G5: exploit / explore / cross-arm disagreement,
  replacing an unexamined top-N.
- **Mid-run approval triggers** in `SKILL.md`: changing the construct, a
  load-bearing residue, the off-target definition or the endpoint returns to
  its gate rather than being logged as a deviation.
- Roster fields `capability`, `supported_inputs`, `unsupported_inputs`,
  `license`, `adapter_version` - a record of what this campaign measured, not a
  maintained catalogue, and explicitly not a routing layer.
- Enzyme and catalysis dossier fields in `workflows/protein-design-general.md`.
- `predicted` / `inferred` / `measured` labelling in `templates/report_outline.md`.
- Early stop, successive halving and diminishing-returns stopping rules.

### Changed
- `check_design_sheet.py` derives per-arm columns from the schema's
  `ranking_arms` instead of a hardcoded arm list, so a campaign that renamed or
  substituted an arm is checked against its own instrument.
- Cross-arm agreement is described as the strongest evidence *within its
  class*, explicitly not independent validation.
- The method floor logs a zero-contribution method with **which** happened -
  eliminated by data, or blocked by an engineering problem - instead of calling
  both a defect.
- Budget guidance drops the spend-to-target framing; the objective is
  information per unit cost.
- `check.py` covers the reject ledger and both directions of the
  missing-metrics check; the fixture carries reject rows.

### Removed
- Byte-splitting guidance for oversized archives, an artefact of the source
  campaign's upload connector.
- The six assay-outcome codes from the failure vocabulary (expression,
  solubility, binding, specificity, activity, assay ambiguity). The protocol
  ends at the design sheet and can never write them; a code that cannot occur
  is noise in an enum built for aggregation. Fifteen codes remain, all of them
  observable by the campaign itself.

### Scope
- **The protocol ends at the design sheet.** Analysing returned assay data is a
  different task and does not run under these gates. Earlier experimental
  results enter as operator input at G0, one-way, in the operator's own words -
  used to choose an epitope, a difficulty prior and a negative objective, never
  analysed or claimed as this campaign's evidence. Rationale in
  `docs/binder-design-campaign/design-rationale.md` §5.

## [0.2.0] - 2026-08-19

### Changed
- Repository restructured as a skill collection, `my-academic-skills`; per-skill
  docs moved to `docs/<skill>/` and fixtures to `examples/<skill>/`.
- `SKILL.md` rewritten against the `writing-for-agents` discipline: 261 to 148
  lines, description 754 to 590 characters, scale presets moved into the G0
  checklist, and the repeated scoring caveat collapsed into one leading phrase
  (*a filter, never an oracle*) defined once in `failure-modes.md` §1.
- Verification commands, previously duplicated across four documents, replaced
  by `check.py`, which also asserts `preflight.py` stands down when it should -
  the earlier check only read its exit code, which is 0 on both paths.

### Added
- `references/thresholds.md`: absolute cutoffs, campaign sizing, pass-rate
  diagnostic bands, failure tree, and per-method cost, adapted from Adaptyv
  Bio's public skills and the Overath et al. 2025 meta-analysis.
- `references/tool-catalog.md` §2.1: head-to-head hit rates and starting-point
  guidance, with the target-dependence caveat.
- ESMFold2 bring-up gotchas in `references/tool-catalog.md` §4.
- Bilingual README (`README.md`, `README.zh-CN.md`).

## [0.1.0] - 2026-08-19

First release.

### Added
- `skills/binder-design-campaign/` - the gated campaign protocol, adapted from
  Anthropic's CC-BY-4.0 autonomous binder design prompt and technical report.
- Seven review gates (G0-G6) with per-gate presentation checklists.
- Three workflows: de novo binder design, structure and complex prediction,
  general protein design.
- Seven reference documents: scoring instrument, validation gates, tool
  catalogue, target dossier guide, failure modes, deliverables specification,
  compute backends.
- Compute backend contract with Slurm, local and metered-cloud adapters.
- Five standard-library scripts: design sheet validation, diversity caps,
  ledger, scoreboard derivation, in-job preflight dead-man switch.
- Templates: campaign config, target dossier, frozen sheet schema, report
  outline.
- `examples/binder-design-campaign/minimal/` fixture, exercised by every script on clean and corrupted
  input.
- Documentation: installation, design rationale, source mapping.
