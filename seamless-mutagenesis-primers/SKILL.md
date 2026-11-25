---
name: seamless-mutagenesis-primers
description: Design primers on a circular plasmid map for single or combined site-directed mutagenesis by seamless cloning, target-spanning PCR, or Sanger verification. Write and verify primers on a SnapGene or GenBank copy and optionally export an oligo order sheet.
---

# Plasmid primer design

Start from the user's experimental endpoint and the actual template. Accept prose, variant lists, tables, features or intervals. Resolve aliases, selected rows and numbering before converting them to private helper input. A feature on the reverse strand or across base one must follow the map coordinates in biological order. Use existing primers to infer conventions the user wants to retain.

| Intended product | Preset | Verify |
|---|---|---|
| Independent plasmids with one substitution each | Mutagenesis, one request per construct | Each circular product differs from the original at its requested codon |
| Several substitutions together in one plasmid | Mutagenesis, one named request with grouped edits | Actual F/R pairs per PCR, compatible junctions, all edits in the same reconstructed circle |
| An amplicon containing an interval, feature or clone junction | PCR | Inward-facing primers, intended boundaries, product size and sequence |
| A Sanger read through a site or interval | Sanger | Primer strand, distance from its 3′ end to both target edges and available read length |

When “multiple mutants” could mean either separate constructs or a combined construct, resolve it from the request or ask before grouping them. For clone screening with multiple possible products, compare the predicted result for each relevant control template before calling the assay diagnostic.

## Mutagenesis

Map each substitution to the selected CDS by sequence or an explicit verified mapping. A matching wild-type residue alone cannot establish a numbering offset. Confirm the strand, frame, genetic code and every original residue. Where supplied, check the complete expected mutant translation. Use requested codons or a cited host/strain table for host preference. If the user leaves codon choice open, minimizing base changes is a reasonable convention. Record the choice.

Distinguish exact constraints from preferred lengths. Start from a 16 bp shared arm and 20 bp of consecutive wild-type match on the 3′ side of each mutated block. Evaluate the **assembly arm** under the chosen chemistry and the **matched PCR flank** under PCR conditions. Search alternative positions at the preferred arm length before extending it. Permit extensions within the user's range. In a multi-fragment construct, evaluate annealing temperatures for the two primers used in each physical PCR. Check any relevant hairpins, 3′ dimers and competing partial junction homologies before delivery. The helper verifies full exact matches on the supplied plasmid.

See [mutagenesis inputs and assembly settings](references/usage.md#mutagenesis) for construct grouping, fixed versus flexible lengths, adjacent sites, thermodynamic assumptions and fragment pairing.

## PCR and Sanger

Translate the user's feature or target bases into a one-based inclusive interval on the forward reference. For Sanger, interpret requested read direction relative to the intended strand. Use the provider's usable read span when available. For a PCR with specified product boundaries, verify both endpoints explicitly. The automated preset searches for primers flanking the supplied interval. See [PCR and Sanger inputs](references/usage.md#pcr-and-sanger).

## Map and order delivery

Use the checked design on a **copy** when annotations are requested. Append primers by default for a requested copy, or replace the old primer inventory on explicit request. Reopen the copy and compare its sequence, other features and primer binding locations with the template and design table. Preserve the mapping between construct names, PCR reactions and oligo names. Export the optional generic Excel order sheet or fill the user's vendor form from the final approved sequences. See [outputs and compatibility](references/usage.md#outputs).
