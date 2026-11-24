---
name: seamless-mutagenesis-primers
description: Design and verify outward-facing primer pairs for independent single-codon substitutions in a circular plasmid by seamless cloning. Deliver primer sequences, an optional annotated template copy, and an optional oligo order sheet.
---

# Seamless mutagenesis primers

## Resolve the request

Take substitutions from the user's actual source, including prose, a list, spreadsheet, ranked results, or an annotated sequence. Apply the requested selection and ordering. Inspect column meanings, protein identifiers and existing primers before choosing a numbering convention. For full-length or mature-protein numbering, map residues to the construct by sequence alignment or an explicit verified mapping. Check for gaps and ambiguous mappings. A wild-type residue match alone cannot establish an offset.

Identify the exact circular template, coding feature, strand, frame and translation table. Translate the template and verify **every** supplied wild-type residue before release. If a mutant protein sequence is supplied, compare its entire translated region on the same coordinate basis. Surface conflicting positions or identities with their source labels. Independent substitutions each use the original template.

Choose the target triplets from the user's codons or from a cited host/strain usage table when host preference is requested. Record the criterion, resolve ties consistently, and verify translation. With no codon preference, one reasonable choice is the synonymous target codon requiring the fewest base changes from wild type. Document ties. Preserve the user's numbering and naming conventions in the deliverables.

## Design and verify

Use the requested assembly chemistry and lengths. For this centered-overlap method the defaults are a 16 bp shared arm spanning the mutant triplet and at least 20 bp of consecutive wild-type match **after** that triplet toward each primer's 3′ end. Existing pairs can establish arm placement and naming. Extend a flank only as needed for specificity or paired melting temperatures. The exact-match flank and shared arm overlap physically. Concatenating a full arm and a full flank duplicates bases.

Run the local helper using [the input and output guide](references/usage.md). It works in coding orientation, maps the tails to both reference strands, selects the shortest pair meeting the configured constraints, and reconstructs the circular product from both oligos. Compare the overlap and complete assembled sequence with the requested substitution. Review terminal complementarity, hairpins and near matches under the relevant chemistry if they could affect the choice. The built-in uniqueness check counts full exact matches on the template.

## Deliver

Return the validated design CSV in input order with source IDs/ranks and coordinate conventions meaningful to the user. If a map is requested, add primers to a new copy. Remove pre-existing primers only when requested. Read the copy back and compare the template sequence, expected primer inventory, orientations and coordinates. For a supplied vendor form or an optional generic XLSX, follow the order-sheet instructions in the guide. Report resolved host/codon policy, departures from requested lengths, and the extent of computational or experimental verification.
