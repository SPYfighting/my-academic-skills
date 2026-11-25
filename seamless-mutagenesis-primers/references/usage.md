# Running the local helper

From the skill root, use Python 3.10+ with the versions in `requirements.txt`. If needed, prepare an environment explicitly with `python -m pip install -r requirements.txt`. Paths below are illustrative. Use a new output directory with an existing parent. All design computation uses local files.

## Mutagenesis

```sh
python scripts/design.py template.gb requests.json designs --cds reporter --order --map append
```

The user can supply any source format. Normalize the selected constructs into a private JSON list in the requested order. Each list item produces a separate construct on the original template. These invented examples describe one independent variant and one double mutant:

```json
[
  {"variant":"E12Q","codon":"CAA","source_id":"pick-1"},
  {"name":"double-QS","edits":[{"variant":"E12Q","codon":"CAA"},{"variant":"A83S","codon":"AGC"}]}
]
```

Residue numbers are one-based in the selected CDS. `source_id` retains a source key, `name` sets the oligo name stem, and optional `protein` on the construct is its **complete final** translation. The helper handles substitutions in a single contiguous CDS per invocation, on either strand and across the origin. For raw DNA use a temporary annotated GenBank file based on verified topology and coordinates. Use `--genetic-code` if the annotation omits it. Resolve exceptional translation, ambiguous bases or discontinuous CDS mappings separately.

### Choose the junction and PCR settings

| User's instruction | Example options | Selection rule |
|---|---|---|
| Exactly 16 bp | `--overlap 16` | Search window positions at that length. Report an unmet threshold by site. |
| Prefer 16 bp, allow up to 22 bp | `--overlap 16 --max-overlap 22` | Try the most centered valid window at each length, shortest first. |
| Evaluate for NEBuilder HiFi | `--chemistry nebuilder` | Apply a 48 °C arm threshold using 2 °C per A/T and 4 °C per G/C. By default search 16–24 bp, starting at 20 bp for four or more separate fragments. Use explicit limits for a specified protocol. |
| Specify another arm screening threshold | `--arm-min-tm 46 --max-overlap 22` | Apply that threshold using the same simple composition estimate. Use only when appropriate to the stated method. |
| Exactly 20 bp after the mutant block | `--flank 20 --max-flank 20` | Both 3′ flanks must satisfy constraints at 20 bp. |

Generic mode with no chemistry threshold starts with a fixed 16 bp arm and reports its composition-based Tm. It makes no claim of kit suitability. A shared arm spans every substituted codon at that junction. The default search keeps at least three bases on either side of the block. Exact-match PCR flanks extend from each outermost mutated codon toward the corresponding primer's 3′ end. Parts of these flanks also belong to the shared arm. Do not concatenate two full lengths.

The default flank search tries 20–24 bp and selects the least total extension meeting specificity and paired Tm criteria. Defaults for Biopython nearest-neighbor Tm are minimum 55 °C, maximum within-PCR difference 6 °C, primer 250 nM, Na 50 mM, Mg 1.5 mM and total dNTP 0.8 mM. Pass actual reaction conditions when known. PCR flank Tm and the overlap composition estimate have distinct models and columns.

### Multiple edits in one construct

Nearby codons that fit the permitted arm can share one junction. Distant blocks form separate junctions ordered along the CDS. **J1-F and J1-R describe opposite ends at the same junction.** With three junctions, the fragment PCRs use J1-F/J2-R, J2-F/J3-R and J3-F/J1-R. Follow the actual `pcr` assignments or `fragments.csv` for the selected construct. Each reaction uses the original template. Separate constructs are assembled independently.

The helper checks the two exact 3′ binding sites, within-reaction Tm difference, and each mutant junction's full-length uniqueness for multi-fragment designs. It reconstructs every PCR product from the oligos and intervening wild-type template, joins the ends once in circular order, then checks the entire sequence and CDS translation. Choose a practical fragment minimum using `--min-fragment` if needed (default 120 bp for multi-fragment NEBuilder screening). Closely spaced edits that cannot share an allowed arm can leave a fragment too short for this layout. Report which constraint failed. A longer allowed arm or a separately planned staged construction changes the design. The helper does not search every possible partition, assess all partial homologies or model assembly yield.

## PCR and Sanger

```sh
python scripts/design.py template.dna intervals.json pcr-design --mode pcr --map append
python scripts/design.py template.gb reads.json read-design --mode sanger --order
```

Use one named interval per list item. `start` and `end` follow forward-reference order, one-based and inclusive. A smaller end coordinate spans base one.

- **PCR** example: `[{"name":"junction","start":301,"end":380,"product_range":[160,400]}]`. Primer3 seeks inward-facing primers outside the interval. Read the predicted product boundaries and size from the CSV. Supply product limits for the assay. The default minimum is the larger of 100 bp and target width plus two minimum primer lengths. The default maximum is target width plus 400 bp, bounded by plasmid size.
- **Sanger** example: `[{"name":"site","start":301,"end":303,"direction":"both","distance_range":[50,120],"read_length":650}]`. Directions are `forward`, `reverse` or `both` relative to the forward reference. Each selected oligo is used in a separate sequencing reaction. Distance 1 is the first base after the primer's 3′ end. The nearest target base must lie in the chosen distance range, and the farthest must fit within the assumed read length. The example uses the configurable search defaults. Set them to the core facility's specifications.

Both presets use Primer3's sequence and thermodynamic filters, then check full-length template uniqueness and target geometry locally. Use `--help` for Tm and primer-size controls. The search examines up to 80 ranked candidates per interval and direction. Actual read quality, colony background and polymerase-specific annealing behavior require separate evidence.

## Outputs

- `primers.csv` contains synthesis-ready 5′→3′ sequences, binding coordinates in oligo direction and scenario-specific fields. Mutagenesis rows identify the construct, PCR, junction, codons, oriented overlap sequence and length, upstream/downstream split, estimated arm Tm and flank Tm. Include source mapping and chosen design conditions with delivery.
- `fragments.csv` lists actual primer pairs, product sizes and adjacent junction IDs when a run includes multi-fragment assembly. Rows are ordered by construct and PCR.
- `--map append` or `--map replace` writes a copy in the input format. Binding locations represent the matched template flank. Full oligo sequences include any 5′ extension. The SnapGene writer handles the native DNA cookie version pair 15/17. If an input revision or native readback is unsupported, use a compatible native editor when available. Converting to GenBank may lose native metadata and requires agreement if it changes the requested deliverable.
- `--order` adds an Excel sheet with name, uppercase sequence, and blank scale, purification and modification fields. For a supplied vendor template, preserve its layout, fill only stated ordering choices and compare all names and sequences to the design CSV after saving.

The offline self-check uses synthetic fixtures. It validates the exported data and computational predictions. Native GUI rendering, vendor import and experimental performance are separate checks.
