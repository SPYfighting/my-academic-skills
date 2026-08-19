# Building the target dossier

The dossier is the campaign's factual foundation. Everything downstream — the
scoring construct, the epitope, the controls, the instrument — is derived from
it. Build it before G1 using `../templates/target_dossier.md`.

Two rules govern the whole document:

- **Every identifier is fetched, never recalled.** UniProt accessions, PDB IDs,
  residue ranges, chain IDs, DOIs, PMIDs — each is the literal output of a
  lookup executed in this session, with the query recorded.
- **Every field states its source.** A field you could not resolve says
  `unresolved` and says what you tried. An unresolved field is a G1 discussion
  item, not a blank.

---

## 1. Identity

Name, synonyms and gene symbol; UniProt accession; organism with taxonomy ID;
sequence length and the canonical isoform used.

Watch for name collisions that silently change the molecule. The source
campaign had to disambiguate MBP: *E. coli* maltose-binding protein (malE,
P0AEX9), **not** human myelin basic protein. Confirm the identity against the
sequence, not the name.

---

## 2. Assay construct

This is the field most often wrong, and it is the one the scoring construct must
match.

Record:

- **Residue range** actually expressed, in UniProt numbering, with the source.
- **Domain boundaries** — for a receptor, is it the full ectodomain or one
  subdomain.
- **Tags and fusions** — His, Avi, Fc, Strep; N- or C-terminal; whether the
  fusion is cleaved before assay. An Fc fusion dimerises the target and changes
  the effective stoichiometry.
- **Expression host and glycosylation** — mammalian, insect or *E. coli*;
  whether N-glycans are present and where.
- **Immobilisation format** — which partner is on the surface, which is the
  analyte. This determines avidity effects and which side of the interface is
  sterically constrained.

If the assay construct is not yet decided (in-house work), say so and flag that
the scoring construct is provisional until it is.

---

## 3. Oligomeric state at assay conditions

Not the state in the crystal, not the state in the cell — the state in the
tube during the measurement. Record the evidence: SEC-MALS, AUC, native MS, or
the literature statement with its conditions.

Consequences of getting this wrong:

- The ipSAE union mask is built over the wrong chain set.
- The N:N stoichiometry companion runs are wrong or missing.
- A design that looks specific at 1:1 may clash with a symmetry mate at full
  occupancy.

For homo-oligomers, record the point group (C2, C3, D2) and the source of the
symmetry operators you will use to build N:N reference complexes.

Also record the **disulfide-linked** status where relevant — a disulfide-linked
antiparallel homodimer cannot be treated as two independent protomers.

---

## 4. Cofactors and non-protein context

List each, with a role classification that downstream stages act on:

| Role | Meaning | Consequence |
|---|---|---|
| `fold_required` | the protein does not adopt its native fold without it | every ranking arm must represent it; an all-cofactor-blind ranking is a logged deviation |
| `interface_required` | it participates in or shapes the intended epitope | same, plus it constrains epitope choice |
| `incidental` | present but not structurally or functionally load-bearing here | may be omitted, with the omission recorded |

Cover: structural metals (with stoichiometry — a RING domain coordinating three
zincs is not optional), catalytic ions, nucleic-acid partners (a nuclease's
functional unit may be a ribonucleoprotein, not the apo protein), glycans,
lipids and membrane context, and small-molecule ligands with their CCD codes or
SMILES.

Membrane proximity is context even when no lipid is modelled: an epitope
adjacent to the membrane may be inaccessible in the real system.

---

## 5. Reference structures

Enumerate candidates rather than picking one immediately. Per candidate:

- PDB ID, method, resolution, deposited chains.
- State: apo or holo; which ligands and metals are present.
- **Whether the intended epitope region is ordered.** A structure whose epitope
  loop is missing density cannot support hotspot selection there.
- Construct match: does the deposited construct match the assay construct.
- Any engineered mutations, truncations or crystallisation chaperones.

Then choose, and say why. The criterion is **match to the assay construct and
state**, not resolution alone.

Where several independent structures exist (independent crystals, X-ray versus
cryo-EM, apo versus holo with small rearrangement), designing against more than
one is preferable to overfitting a single deposition. Prioritise the best match;
where feasible, confirm top designs hold across the others.

Substantial apo/holo differences are a **conformational-state question** — they
belong in this section as a modelling decision, and they are separate from the
full-oligomer question in §3.

If no structure is adequate, record what you will use instead (a predicted
model), which predictor and settings produced it, and its confidence — and flag
at G1 that the campaign is designing against a prediction.

---

## 6. Known binders and controls

For each: identity, format (natural ligand / receptor ectodomain / viral entry
protein / peptide / antibody / de novo miniprotein), affinity with the method
that measured it, the structure of the complex if one exists, and the epitope
it engages.

Mark which are eligible as G3 positive controls under
`validation-gates.md` §2 — in particular, mark de novo miniprotein binders as
**excluded** (circular) and antibodies as **secondary**.

---

## 7. Counter-targets and selectivity

If the target has a close paralog that a binder must not engage, record it as a
first-class field: accession, sequence identity to the target, structural
similarity at the intended epitope, and whether a structure exists.

A counter-target changes the scoring formula (`scoring-instrument.md` §4), adds
required sheet columns, and roughly doubles the scoring cost. Surface that cost
at G4.

---

## 8. Prior difficulty

Your read, with reasoning, on how hard this target will be. Inputs:

- Binder precedent — have de novo binders been reported, by whom, at what hit
  rate and affinity.
- Interface character — polar versus hydrophobic, convex versus concave, flat
  versus pocketed, area available.
- Oligomeric state and whether the epitope spans protomers.
- Epitope flexibility and disorder.
- Cofactor requirements.
- Selectivity requirements.
- Evolutionary history — a de novo designed target has no natural partner to
  define a functional epitope.

This estimate does real work: it seeds the per-target compute allocation at G4,
and it sets the expectation you communicate. Two published examples worth
holding in mind: a large convex polar surface (MBP) and a de novo beta-barrel
(BBF-14) both proved very hard, and neither difficulty was visible in the
co-folding scores afterwards.

---

## 9. Open questions

Everything you could not resolve, each with what you tried. This section drives
the G1 conversation. An empty open-questions section on a non-trivial target
usually means the search was not thorough, not that the target is simple.

---

## 10. Freezing

At G1 pass, the construct, the chosen reference structure and the cofactor list
are **frozen** and copied into `state/gates/<target>.json` at G3. Changing any
of them later re-opens G3 and invalidates scores computed under the old values.
Revisit this record whenever a fold-recapitulation check fails.
