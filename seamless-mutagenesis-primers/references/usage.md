# Running a design

Use a Python environment with the versions in `requirements.txt`. Prepare it explicitly if needed with `python -m pip install -r requirements.txt` from the skill root. All computation is local.

## Inputs

The agent adapts the user's source to a small, private intermediate JSON list in selection order. One record looks like `{"variant":"E12Q","codon":"CAA"}`. The variant uses the one-based residue in the selected plasmid CDS. An optional `protein` field is the complete expected mutant translation in that coordinate system. Set optional `source_id` to a source key or rank and `name` to a user-selected oligo name stem. The same stem is used for the CSV, map and order sheet. No particular source headers, file names, row counts or ranking convention are required.

The helper reads a single annotated GenBank or SnapGene circular plasmid. For raw FASTA or pasted DNA, first construct a temporary annotated GenBank record using established topology and CDS coordinates. A protein alone cannot determine the flanking plasmid DNA. Resolve exceptions such as discontinuous coding segments, alternative initiator translation, or ambiguous residues against the source. A contiguous CDS may run on either strand or span base one.

From the skill root, for example:

```sh
python scripts/design.py template.gb requests.json designs --cds reporter --order --map replace
```

Use a new output directory with an existing parent. `--genetic-code` supplies a missing translation table. See `--help` for flank length, overlap and approximate Tm settings. The default comparison is Biopython DNA/DNA nearest-neighbor Tm of the fully matched 3′ flank alone, at 250 nM primer, negligible template, 50 mM monovalent salt, 1.5 mM Mg and 0.8 mM total dNTP. The default search tries 20–24 bp flanks, minimum 55 °C and maximum within-pair difference 6 °C. These are design settings. Use actual reaction conditions when known. If no pair qualifies, inspect the conflicting condition before changing it.

## Outputs

- `primers.csv` contains both full oligos in synthesis orientation (5′ to 3′). Coordinates are one-based. Tail first/last follow the oligo's direction on the reference. `codon_first_bp` follows the CDS direction. The `source_id` column links back to the original request. Record the codon source and design settings with the delivery.
- `--map append` retains old primers. `--map replace` replaces primer records and annotated `primer_bind` features in the copy. Binding intervals describe the fully matched 3′ flank. The full oligo includes the 5′ extension. The native writer supports the DNA cookie version pair 15/17 and preserves other packet payloads, apart from primer annotations. If readback rejects a file or its native revision is unsupported, produce the requested native copy using a compatible editor when available. A GenBank conversion can omit native metadata and requires agreement if it changes the requested deliverable.
- `--order` produces a separate Excel workbook with one oligo per row, name and uppercase 5′→3′ sequence first, followed by blank scale, purification and modification fields. For a vendor template, preserve its sheet names, columns and layout, fill only supplied order choices, and reopen it to compare every name and sequence against the final CSV. If names are customized, update all deliverables consistently. Preparing the workbook is separate from submitting an order.

The self-check uses invented templates and runs offline. It tests sequence and file behavior. Native application display, vendor import, reaction performance and synthesis are separate validations.
