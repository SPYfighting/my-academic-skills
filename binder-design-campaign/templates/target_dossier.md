# Target dossier: <TARGET NAME>

> Every identifier below is the literal output of a lookup executed while
> writing this file. Every field states its source. A field that could not be
> resolved says `unresolved` and says what was tried.
>
> Status: DRAFT / CONFIRMED AT G1 (<date>)

## 1. Identity

| Field | Value | Source |
|---|---|---|
| Name | | |
| Synonyms / gene symbol | | |
| UniProt accession | | |
| Organism (taxid) | | |
| Canonical isoform, length | | |
| Name-collision check | | |

## 2. Assay construct

| Field | Value | Source |
|---|---|---|
| Residue range (UniProt numbering) | | |
| Domain boundaries | | |
| Tags / fusions, terminus, cleaved? | | |
| Expression host | | |
| Glycosylation present, sites | | |
| Immobilisation format (surface vs analyte) | | |
| Construct decided or provisional | | |

## 3. Oligomeric state at assay conditions

| Field | Value | Source |
|---|---|---|
| State | | |
| Evidence (SEC-MALS / AUC / native MS / literature) | | |
| Point group, symmetry operator source | | |
| Disulfide-linked? | | |
| Does the intended epitope span protomers? | | |

## 4. Cofactors and non-protein context

| Species | CCD / SMILES | Stoichiometry | Role | Source |
|---|---|---|---|---|
| | | | fold_required / interface_required / incidental | |

Membrane or lipid context:

## 5. Candidate reference structures

| PDB ID | Method | Resolution | Chains | State (apo/holo) | Epitope region ordered? | Construct match | Engineered changes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

**Chosen structure**: <PDB ID> — because <match to assay construct and state>.

**Alternative structures to cross-check top designs against**:

**Apo/holo conformational note**:

## 6. Known binders and control candidates

| Binder | Format | Affinity (method) | Complex structure | Epitope | Eligible as G3 positive control? |
|---|---|---|---|---|---|
| | natural ligand / receptor ECD / viral entry protein / peptide / antibody / de novo miniprotein | | | | yes / secondary (antibody) / excluded (de novo, circular) |

**Negative control plan**:

## 7. Counter-target and selectivity

| Field | Value | Source |
|---|---|---|
| Paralog accession | | |
| Sequence identity to target | | |
| Structural similarity at the intended epitope | | |
| Structure available | | |
| Selectivity requirement (fold, log units) | | |

## 8. Prior difficulty

| Factor | Assessment | Reasoning and source |
|---|---|---|
| Binder precedent | | |
| Interface character (polar/hydrophobic, convex/concave, area) | | |
| Oligomeric state | | |
| Epitope flexibility / disorder | | |
| Cofactor requirement | | |
| Selectivity requirement | | |
| Evolutionary history (natural partners exist?) | | |

**Overall prior_difficulty**: low / medium / high / very high — because <one sentence>.

**Expectation to communicate**:

## 9. Open questions

| Question | What was tried | Why it matters |
|---|---|---|
| | | |

## 10. Frozen at G1

| Frozen item | Value | Confirmed by | Date |
|---|---|---|---|
| Assay / scoring construct | | | |
| Reference structure | | | |
| Cofactor list | | | |

Changing any of these re-opens G3 and invalidates every score computed under
the old values.
