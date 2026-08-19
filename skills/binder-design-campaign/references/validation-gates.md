# G3: instrument validation

The purpose of this gate is narrow and important: **prove, on this target, that
the instrument you are about to rank thousands of designs with can tell a real
binder from noise.** Nothing downstream recovers from failing to establish this.

Production scoring on a target is blocked until
`state/gates/<target>.json` exists with `status: PASS`. This is enforced in the
submit path (`compute-backends.md` §4), not by convention. A verbal
claim, a message, or an in-memory variable does not satisfy the gate.

---

## 1. The two conditions

### (a) Target fold recapitulation

Each ranking arm must model the target itself, without a binder, and reach a
named CA-RMSD threshold against the campaign reference structure. Disclose any
core-scoping used (which residues were included in the RMSD).

Failing (a) usually means the construct is wrong, not the model — go back to
G1 and revisit the residue range, the oligomeric state and the cofactors before
concluding the arm is unusable.

### (b) Positive-control separation

A known literature binder, run at **full native stoichiometry**, must score
clearly above the negative controls on that arm.

This is the condition that actually validates the ranking. A geometry-only or
pose-only score with no demonstrated positive-control separation **fails (b) by
definition**.

---

## 2. Choosing controls

**Positive control, in preference order:**

1. Natural ligand.
2. Receptor or co-receptor ectodomain.
3. Viral entry protein.
4. Peptide ligand.
5. Antibody or nanobody — **secondary only**. Co-folding models systematically
   underperform on antibody-antigen interfaces. An antibody-only control that
   fails separation is weak evidence, and the gate may PASS on condition (a)
   alone; one that passes is strong evidence.

**Excluded as separation controls:** published de novo miniprotein binders.
They were themselves likely selected by co-folding metrics, so their separation
is circular.

**Negative controls:** a non-interacting pair, a sequence-shuffled version of
the positive control, and a cross-pair mismatch (the positive control of a
different target).

**Perturbation control** (add one wherever the epitope is known): the positive
control with its hotspot contacts deleted or mutated away. The three negatives
above test whether the arm can reject an unrelated pair. This one tests
something narrower and more useful: whether the arm is scoring **the interface
you specified**, or merely noticing that two proteins are plausible together. An
arm that scores the hotspot-deleted control as highly as the intact one is not
reading the epitope, and its ranking on this target means less than its
separation value suggests.

**MSA handling for controls:** MSAs on both target chains **and** the
control-ligand chain, at the same seed count, chain construct and ipSAE pairing
used for the designs.

**No literature control exists.** After a documented, comprehensive search,
condition (b) is dropped and the gate can PASS on (a). Record the search in the
gate file and say so in plain language at G3 and in the report: the campaign is
running without a demonstrated ability to distinguish binders from non-binders
on this target.

---

## 3. What the gate file records

```json
{
  "target": "<name>",
  "status": "PASS",
  "frozen_at_utc": "<ISO-8601, from an executed clock call>",
  "construct": {
    "chains": ["A", "B"],
    "residue_range": "<as fetched, with source>",
    "cofactors": [{"ccd": "ZN", "count": 3, "role": "fold_required"}],
    "native_oligomer_n": 2,
    "reference_structure": "<PDB ID, as fetched>"
  },
  "instrument_mask": ["ef2full", "ef2fast", "ptxv2"],
  "arms": {
    "ef2full": {
      "fold_recapitulation_ca_rmsd": 1.42,
      "fold_threshold": 2.0,
      "core_scoping": "<disclosed, or null>",
      "control_separation_value": 0.31,
      "control_id": "<control name and source>",
      "negative_controls": [{"id": "...", "score": 0.04}],
      "gate_status": "PASS"
    }
  },
  "thresholds": {
    "monomer_plddt": 0.70,
    "monomer_plddt_scale": "0-1",
    "pose_dockq": 0.23,
    "novelty_identity": 0.60,
    "novelty_coverage": 0.50,
    "novelty_local_identity": 0.30,
    "novelty_local_aligned_residues": 40,
    "novelty_tmscore": 0.50
  },
  "calibration": {
    "ceiling_complexes": [{"id": "barnase-barstar", "raw_ipsae_min": 0.0}],
    "floor_constructs": [{"id": "shuffled-control", "raw_ipsae_min": 0.0}]
  },
  "ranking_formula": "default_4to1",
  "seed_variance_measured": {"ef2full": 0.0},
  "notes": ""
}
```

Every numeric in this file is the output of an executed run. The file is
written once and frozen; a change after production scoring begins invalidates
every score computed under the old values.

---

## 4. When (b) fails on every arm

**Self-authorisation is barred.** Report the failure, present these three
recovery options, and wait for the human:

1. Re-run the control with the **control-ligand MSA enabled** — the most common
   cause is a control run single-sequence when the arm has an MSA encoder.
2. Try an **alternative co-folder** of different lineage as a substitute arm.
3. Try **AF_Unmasked with template injection** as a diagnostic, to establish
   whether any co-folder recapitulates the target at all. This is a
   validation-gate diagnostic only — it stays outside the production scoring
   and pose-check path.

If none succeeds, the honest outcomes are: proceed with condition (b) dropped
and say so everywhere; change the target construct; or stop. Present all three.

---

## 5. Freezing

At PASS, freeze and record:

- The **instrument mask** — which arms rank. Dropping a validated arm from a
  frozen mask afterwards is sheet corruption.
- The **scoring construct** per arm — chains, crop, cofactors. Identical at
  every seed tier. Asserted from the output structure file on **every**
  production scoring row, not from input-script intent.
- The **thresholds** — monomer pLDDT (with its scale), pose_dockq, novelty
  criteria, structural-plausibility cutoffs.
- The **ranking formula** — `../templates/scoring_policy.yaml`, filled in and
  stamped with `frozen_at_utc`. An alternative to the default goes in the same
  file, with the control-separation evidence that justified it. The formula is
  frozen as a *file*, not as a sentence in a report: a formula described in
  prose but absent from the policy file has not been frozen.
- The **submission template** — environment or image id, script version,
  mounts, parameter schema. Every subsequent wave imports this rather than
  re-typing it.

---

## 6. Re-opening the gate

The gate re-opens, and everything scored under it is invalidated, if any of
these changes: the construct, the cofactor list, the reference structure, the
instrument mask, any frozen threshold, or the ranking formula.

Re-opening is not a failure. Shipping scores computed under a construct that
changed underneath them is.

---

## 7. Adapting this gate to the other workflows

**Structure prediction.** Condition (a) is the whole gate: recapitulate a known
structure of the same class, at the same settings, and report the error. There
is no design pool to separate, so replace (b) with a held-out recapitulation
set and report its error distribution.

**General protein design.** Condition (b) becomes: the scoring function
separates known-functional variants from known-nonfunctional ones on this
system. If no such labelled set exists, say so — the design campaign then has
no validated in silico discriminator, which is a materially different situation
to communicate at G3.
