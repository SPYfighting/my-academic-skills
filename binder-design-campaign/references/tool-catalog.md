# Tool catalogue and roster discipline

**Read this first.** Everything in §§2–4 is a *pointer*, recorded as of the
source release (August 2026). Model names, flags, weight locations and licence
terms change. For every tool you actually use, derive the install and
invocation recipe from **the project's own GitHub README, HuggingFace card, or
paper**, and record what you derived. Where this file and an upstream source
disagree, the upstream source wins.

The same applies to any skill, including the ones listed in §6: a skill is
reference material for flags, weight URLs and pitfalls. Its existence is not
evidence that the tool works in *your* environment, and its helper code is not
production code.

---

## 1. Roster discipline

A tool is on the roster only when it has a `status: PASS` row. PASS requires
**all** of the following, on a **real campaign target** (not a toy peptide), in
the **same environment and the same flags** production will use:

1. The environment builds and every package imports.
2. Weight checksums match the upstream release.
3. One end-to-end run with `n_designs` in [2, 4] exits 0.
4. The output directory holds at least `n_designs` PDB or CIF files that parse
   (gemmi or Bio.PDB; at least one chain, at least 30 residues, no NaN
   coordinates).
5. **The downstream consumer accepts one of them and produces its own output** —
   for a structure generator, the sequence-design model emits at least one
   sequence from it.

Criterion 5 is the one that gets skipped and the one that catches the most
failures. See `failure-modes.md` §9.

Roster ledger row, one per tool:

```
{tool, version_or_commit, status, environment_id, weights_sha256,
 wall_clock_s, gpu_type, seconds_per_design, output_shape, output_sha256_first,
 validated_at_utc, notes,
 capability, supported_inputs, unsupported_inputs, license, adapter_version}
```

The last five turn the roster into the campaign's answer to "can this tool
represent what this target actually is" — asked **before** dispatch rather than
discovered from a silently wrong number afterwards:

- `capability` — what stage it serves: `structure_generation`,
  `sequence_design`, `complex_prediction`, `docking`, `stability_prediction`,
  `clustering`, `sequence_search`. Two tools with the same capability are
  substitutable; that is the only sense in which this field is used.
- `supported_inputs` / `unsupported_inputs` — metals, ligands by CCD or SMILES,
  nucleic acids, modified residues, membranes, chain-count or length limits.
  Fill these **from the tool's own paper and API during bring-up**, and record
  what you checked. A dossier cofactor that lands in some tool's
  `unsupported_inputs` is a G3 problem, surfaced at G3 rather than at close-out.
- `license` — against the regime chosen at G0 (§5).
- `adapter_version` — which parser or converter consumed its output in the
  criterion-5 handoff, so a later adapter change invalidates the right rows.

This is a **record of what this campaign measured**, not a maintained catalogue
of the field. It goes stale the moment the campaign ends, which is correct: the
next campaign runs bring-up again. Do not build a routing layer on top of it —
the mechanical protection against a misrepresented target is the construct
assertion at scoring time (`failure-modes.md` §5), which needs no registry and
cannot go stale.

Production dispatch uses exactly that environment id. A wave must not dispatch
a method without a PASS row; log the floor miss instead. Re-run the check on
any environment or flag change.

**Fold tools into production as they pass.** Do not commit more than ~10% of
the compute budget to any single model until every roster model has passed or
been logged as a drop with its consequence stated (which design-diversity
objective the drop affects).

At PASS, freeze the submission configuration — environment, script, mounts,
parameter schema — as a template every subsequent wave imports rather than
re-typing.

---

## 2. Structure design and co-design

Named in the source prompt. Asterisked entries carried a per-target minimum
backbone contribution in the source campaign; keep that idea (a floor per
method per target) even if your roster differs.

| Tool | Notes recorded at source release |
|---|---|
| RFdiffusion* | backbone generation conditioned on target and hotspots |
| RFdiffusion3* | distinct from RFdiffusion; keep as a separate method token |
| BindCraft / FreeBindCraft* | hallucination-based binder design; FreeBindCraft is the PyRosetta-free variant |
| BoltzGen* | co-design |
| PXDesign* | co-design |
| Proteina-Complexa* | structure generation |
| Genie3* | AlQuraishi lab; not the DeepMind world model of the same name |
| Mosaic | Escalante Bio |
| FoldCraft | install from `KhondamirRustamov/FoldCraft`; no PyRosetta needed. Known install failures at source release: the `tqdm.notebook` import, and `--binder_template` being required in `--vhh` mode. Can produce beta-containing and mixed alpha/beta miniproteins, not only helical bundles, when given small beta-containing reference folds |
| BoltzDesign1 | |
| HalluDesign, Protein Hunter | both hallucinate via Protenix v2, Chai-1, Boltz-2 or Boltz-1 |

### 2.1 Which to start with

**There is no fixed leaderboard.** Hit rate is strongly target-dependent and the
ranking reshuffles between targets, so a method that won one head-to-head tells
you little about the next one. Choose a starting point by **cost and effort to a
testable design**, then let the campaign's own screening data reallocate.

Head-to-head on one target — the Adaptyv Nipah-G de novo competition, as
compiled in Adaptyv Bio's `binder-design` skill (MIT):

| Method | Tested | Binders | Hit rate |
|---|---|---|---|
| Mosaic (gradient, multi-model) | 9 | 8 | 89% |
| ProteinMPNN hybrid | 28 | 7 | 25% |
| RFdiffusion | 60 | 13 | 22% |
| BindCraft | 98 | 7 | 7% |
| BoltzGen | 182 | 6 | 3% |

Read this table with its sample sizes in view: the top row is nine designs from
an expert-tuned objective, the bottom row is 182 designs from a turnkey run.
It ranks *effort-adjusted outcomes on one target*, not method quality.

Starting points by situation:

| Situation | Start with | Why |
|---|---|---|
| lowest effort to testable designs | BoltzGen | turnkey, all-atom, single step |
| hard or important target, tuning time available | Mosaic | composable multi-model objective, high ceiling |
| ligand or small-molecule context | BoltzGen | all-atom |
| diversity and exploration | RFdiffusion + ProteinMPNN | highest backbone diversity |
| end-to-end with built-in validation | BindCraft | integrated design loop |

On a hard or important target, run more than one in parallel. The method floor
in `../workflows/binder-design.md` stage 6 exists precisely so that an early
guess about which method wins cannot quietly become the campaign's only bet.

Sizing, expected pass rates and cost per design: `thresholds.md` §§4–6.

**Length policy.** Miniprotein binders are single-chain, 50–120 residues, with
35–160 permitted where epitope geometry motivates it and the rationale is
recorded. Single-domain antibody and VHH formats are out of scope for this
workflow. Known binders — miniprotein, peptide, nanobody or antibody — are out
of scope as starting points or grafts; every binder is generated de novo.

**Fold diversity.** Aim for at least 10% non-all-alpha designs in the shipped
sheet. A design counts as not-all-alpha under DSSP (or equivalent) if it has at
least one beta strand of three or more consecutive E/B residues, or a helical
fraction below 70%. This is a **reported target, not a ranking gate**: if the
ranked pool cannot supply it without displacing materially better designs, ship
fewer and state the count and the reason.

---

## 3. Sequence design

| Tool | Notes |
|---|---|
| ProteinMPNN | base variant; fine for backbone search |
| **SolubleMPNN** | soluble variant; **use for designs that will be generated or selected for order** |
| Caliby | base variant |
| **SolubleCaliby** | soluble variant; use for order-bound designs |
| LigandMPNN | when non-protein context must be seen by sequence design |

Source protocol: run Caliby/SolubleCaliby in both fixed-backbone mode and on a
32-structure Protpardelle-1c ensemble, per the Caliby paper. For co-design
models, score **both** the native sequence and a sequence-design redesign. Mix
and match structure-design and sequence-design models across published
pipelines for diversity.

**LCP is a mandatory restraint** — see `scoring-instrument.md` §3.4.

---

## 4. Co-folding, filtering and metrics

Ranking arms and substitutes are specified in `scoring-instrument.md` §2. Notes
recorded at source release, all to be re-verified:

- **ESMFold2 / ESMFold2-Fast** — weights at HuggingFace `biohub/ESMFold2` and
  `biohub/ESMFold2-Fast` (ungated, MIT). Install the `esm` package from
  `github.com/Biohub/esm` on **Python 3.12 only**; **the PyPI package named
  `esm` is a different project and does not contain ESMFold2**. Full has 48 pair
  layers with MSA support; Fast has 24 and is single-sequence only, roughly
  1.7x faster. Original ESMFold is superseded.

    Three gotchas, from the Claude Science `esmfold2` skill (mirrored under an
    MIT licence) and worth checking on any build:

    1. **The default kernel backend is unset**, which falls back to reference
       PyTorch and runs an order of magnitude slower than the paper's numbers.
       Call `set_kernel_backend("fused")` after loading the model. A bring-up
       benchmark that looks impossibly slow is usually this, not the hardware.
    2. Installing `transformer-engine` raises a `RuntimeError` rather than an
       `ImportError` on import, which slips past the guard and kills the model
       import outright. Leave it out.
    3. Match the torch CUDA build to the driver, and point `HF_HOME` at
       persistent storage — the weights are a gigabyte-scale download you do not
       want to repeat per job.
- **Protenix v2** — `github.com/bytedance/Protenix`, `protenix==2.0.0`, CUDA
  12.4 devel base. Stage the v2 checkpoint and CCD cache into
  `PROTENIX_ROOT_DIR`. Invoke `protenix pred --input in.json --model_name
  protenix-v2 --seeds N --cycle 10 --need_atom_confidence true --use_msa`
  on Protenix-dialect proteinChain JSON. Per-token PAE requires
  `--need_atom_confidence true`. v2.0.0 uses `--use_msa`, not `--use_msa_server`.
  The first call JIT-compiles a CUDA layer-norm kernel (minutes on an H100), so
  point `TORCH_EXTENSIONS_DIR` at persistent storage shared across jobs and give
  the first call a generous timeout.
- **AlphaFold3 code with OpenFold3 weights** — the AF3 JAX engine running OF3
  open weights. Permissive-license cross-check; the frozen instrument stays
  primary.
- **AlphaFold-Multimer-v3, Chai-1, Boltz-1, Boltz-2** — substitute arms.
- **AF_Unmasked** — validation-gate diagnostic only, with template injection;
  outside the production scoring and pose-check path.
- **ipSAE** — reference implementation `github.com/DunbrackLab/IPSAE`. Note the
  union-mask modification required for multimers (`scoring-instrument.md` §3.1).
- **DockQ** — pose self-consistency, with symmetry-aware chain mapping.
- **MMseqs2** — novelty gate against **full UniRef90**. Curated
  mini-databases are not a substitute.
- **Foldseek / TM-align** — structural novelty and TM-0.90 clustering.
- **DSSP** — fold classification for the diversity target.
- **ESM-C** — sequence log-likelihood on every ranked design.

**MSA caching.** Stage target-chain MSAs once per target (a ColabFold MSA
server or local MMseqs2) into a shared per-target cache during bring-up. Every
MSA-consuming arm reads from the cache rather than re-querying per call.
Binder chains are always single-sequence. Per-target positive controls use MSAs
on the target chains **and** the control-ligand chain. Running an MSA-capable
arm in single-sequence mode is a per-target deviation, taken only when it
clearly outperforms target-MSA on that target's control set, and disclosed.

---

## 5. Licensing

**This is a G0 decision, and it changes the roster materially.**

The source campaign required every tool to be **open source with a
commercially available licence**. Under that constraint it explicitly excluded
AlphaFold3 weights, Rosetta and PyRosetta, and ESM3.

Most academic laboratories are not under that constraint: PyRosetta, for
instance, is available under a free licence for non-commercial academic use,
which puts standard BindCraft and a large body of Rosetta-based interface
metrics back in scope.

So: ask at G0 which regime applies, record the answer, and check each tool's
licence against **that** regime rather than inheriting the source campaign's
exclusions. A tool whose licence you have not confirmed is out of scope — log a
deviation rather than shipping designs that depend on it.

Add a tool to the roster only after a production run has taken it end to end on
a real target.

---

## 6. Related public skill collections

Reference material, not dependencies — no code from them is vendored. Read for
flags, weight URLs and known pitfalls; verify against upstream.

**`github.com/adaptyvbio/protein-design-skills`** (MIT) — per-tool skills for
BindCraft, RFdiffusion, BoltzGen, Protenix, Chai, Boltz, AlphaFold, ESM,
ProteinMPNN and SolubleMPNN, LigandMPNN, ipSAE, Foldseek, Germinal, Mosaic, plus
`pdb` and `uniprot` fetchers. Its `protein-qc`, `campaign-manager` and
`binder-design` skills supply most of `thresholds.md`: the absolute cutoff
table, the sequence liability patterns, the campaign sizing rule of thumb, the
pass-rate diagnostic bands, the per-method cost figures, and the Nipah
head-to-head in §2.1. **Go there first for per-tool parameters** — this
catalogue deliberately does not duplicate them.

**`github.com/anthropics/skills`** — the skill specification and template.

**Claude Science skill set** (mirrored at `github.com/HughYau/AcademicForge`,
MIT) — `alphafold2`, `boltz`, `chai1`, `esmfold2`, `openfold3`, `proteinmpnn`,
`solublempnn`, `ligandmpnn`, `diffdock`, `remote-compute-modal`,
`remote-compute-ssh`, `compute-env-setup`. Its `esmfold2` skill is the source of
the three gotchas in §4. Its `PORTABILITY.md` documents the same problem this
repository solves for the campaign prompt — taking skills written against one
vendor's runtime and making them run anywhere — and the resolution it reaches is
the one used here: the deterministic helper hands the raw material to whatever
base model is running, and the skill works single-agent, with parallelism as an
optimisation rather than a requirement.

---

## 7. Declaring a tool unavailable

Before concluding that any named tool, model or resource is unavailable, query
HuggingFace, GitHub, PyPI and the relevant skill catalogues directly. Several
tools named in the source prompt postdate common model training cutoffs. A
failed URL is grounds to try alternate sources, not grounds to conclude
non-existence. Declare unavailable only after those queries, and log the exact
queries alongside the conclusion.

When a tool that *is* available cannot be made to work within a reasonable
budget, log the drop **with its consequence stated** — which design-diversity
or coverage objective it affects — rather than dropping it silently.

---

## 8. Re-reading primary sources

Re-consult the primary source on triggers, not on a schedule:

1. A tool under-produces, errors, or fails its validation gate — read that
   method's own paper **and** its source code before declaring it broken. A
   config flag or a documented limitation is the usual explanation.
2. You are substituting one model, metric or instrument for another — read both
   the outgoing and incoming methods' papers and confirm the substitute
   actually provides what the original did.
3. You are reallocating budget toward or away from a method — confirm the
   performance signal you are acting on matches its published behaviour.

Record each triggered re-read in the campaign log.
