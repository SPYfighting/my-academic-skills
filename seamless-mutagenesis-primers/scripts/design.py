"""Design outward-facing primers for independent codon substitutions."""

import argparse
import csv
import json
import re
from itertools import pairwise, product
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import ExactPosition
from Bio.SeqUtils.MeltingTemp import Tm_NN
from maps import write_map

AMINO = "ACDEFGHIKLMNPQRSTVWY"


def rc(sequence):
    return str(Seq(sequence).reverse_complement())


def read_target(path, label, genetic_code):
    fmt = "snapgene" if path.suffix.lower() == ".dna" else "genbank"
    record = SeqIO.read(path, fmt)
    if record.annotations.get("topology") != "circular":
        raise ValueError("A confirmed circular template is required")
    hits = [
        f
        for f in record.features
        if f.type == "CDS"
        and any(
            label in f.qualifiers.get(key, [])
            for key in ("gene", "label", "name", "locus_tag", "protein_id", "product")
        )
    ]
    if len(hits) != 1:
        raise ValueError("Select one CDS by an exact name or identifier")
    feature = hits[0]
    strand = feature.location.strand
    if strand not in (1, -1) or any(
        p.ref or not isinstance(p.start, ExactPosition) or not isinstance(p.end, ExactPosition)
        for p in feature.location.parts
    ):
        raise ValueError("CDS requires local, exact, single-strand coordinates")
    if any(k in feature.qualifiers for k in ("transl_except", "ribosomal_slippage", "exception")):
        raise ValueError("Resolve exceptional CDS translation separately")
    declared = feature.qualifiers.get("transl_table", [None])[0]
    if declared and genetic_code and int(declared) != genetic_code:
        raise ValueError("Genetic code conflicts with the CDS annotation")
    if not (declared or genetic_code):
        raise ValueError("Supply --genetic-code for a CDS without transl_table")
    code = int(declared or genetic_code)
    phase = int(feature.qualifiers.get("codon_start", ["1"])[0])
    if phase not in (1, 2, 3):
        raise ValueError("Invalid CDS codon_start")
    indexes = list(feature.location)[phase - 1 :]
    seq = str(record.seq).upper()
    if set(seq) - set("ACGT"):
        raise ValueError("Resolve ambiguous template bases before specificity checks")
    if any((b - a) % len(seq) != strand % len(seq) for a, b in pairwise(indexes)):
        raise ValueError(
            "The helper expects a contiguous plasmid CDS (origin wrapping is supported)"
        )
    oriented = seq if strand == 1 else rc(seq)
    origin = indexes[0] if strand == 1 else len(seq) - 1 - indexes[0]
    rotated = oriented[origin:] + oriented[:origin]
    if len(indexes) % 3:
        raise ValueError("Resolve partial terminal codon")
    protein = str(Seq(rotated[: len(indexes)]).translate(table=code))
    if feature.qualifiers.get("translation"):
        annotated = "".join(feature.qualifiers["translation"][0].split()).rstrip("*")
        if annotated != protein.rstrip("*"):
            raise ValueError(
                "CDS translation disagrees with annotation; resolve numbering or initiation"
            )
    return record, rotated, indexes[0], strand, code, protein


def pair(template, start, strand, code, protein, request, args):
    variant = request["variant"]
    match = re.fullmatch(f"([{AMINO}])([1-9][0-9]*)([{AMINO}])", variant)
    if not match:
        raise ValueError(f"Invalid substitution: {variant!r}")
    wt, number, alt = match.groups()
    k = int(number) - 1
    if wt == alt or k >= len(protein) or protein[k] != wt:
        raise ValueError(f"{variant}: wild type or CDS position mismatch")
    expected = protein[:k] + alt + protein[k + 1 :]
    if "protein" in request and request["protein"].rstrip("*") != expected.rstrip("*"):
        raise ValueError(f"{variant}: supplied mutant protein differs")
    name = request.get("name", variant)
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError(f"{variant}: use a plain oligo name starting with a letter or digit")
    source_id = str(request.get("source_id", ""))
    if source_id.lstrip().startswith(("=", "+", "-", "@")):
        source_id = "'" + source_id
    codon = request["codon"].upper()
    if not re.fullmatch("[ACGT]{3}", codon) or str(Seq(codon).translate(table=code)) != alt:
        raise ValueError(f"{variant}: target codon does not encode requested residue")
    size = len(template)
    i = 3 * k
    circle = template[i:] + template[:i]
    up = (args.overlap - 3) // 2
    down = args.overlap - 3 - up
    arm = circle[-up:] + codon + circle[3 : 3 + down]

    def coord(offset):
        return (start + strand * (i + offset)) % size

    def candidates(reverse):
        for length in range(args.flank, args.max_flank + 1):
            tail = rc(circle[-length:]) if reverse else circle[3 : 3 + length]
            orientations = (tail, rc(tail))
            expanded = circle + circle[: length - 1]
            if sum(len(list(re.finditer(f"(?={word})", expanded))) for word in orientations) != 1:
                continue
            tm = Tm_NN(tail, dnac1=args.primer_nm, dnac2=0, Na=args.na, Mg=args.mg, dNTPs=args.dntp)
            if tm >= args.min_tm:
                yield length, tail, tm

    viable = []
    for f, r in product(candidates(False), candidates(True)):
        delta = abs(f[2] - r[2])
        if delta <= args.max_delta:
            viable.append((f[0] + r[0], delta, f, r))
    if not viable:
        raise ValueError(f"{variant}: no unique paired flanks meet length and Tm constraints")
    _, _, f, r = min(viable)
    fseq = circle[-up:] + codon + f[1]
    rseq = rc(circle[3 : 3 + down]) + rc(codon) + r[1]
    amplicon = fseq + circle[3 + f[0] : size - r[0]] + rc(rseq)
    if (
        fseq[: args.overlap] != arm
        or rc(rseq[: args.overlap]) != arm
        or amplicon[: -args.overlap] != circle[-up:] + codon + circle[3 : size - up]
    ):
        raise ValueError(f"{variant}: circular assembly failed")
    rows = []
    for direction, oligo, flank, a, b, sense in (
        ("F", fseq, f, 3, 2 + f[0], strand),
        ("R", rseq, r, -1, -r[0], -strand),
    ):
        rows.append(
            {
                "variant": variant,
                "source_id": source_id,
                "name": f"{name}-{direction}",
                "sequence": oligo,
                "wt_codon": circle[:3],
                "target_codon": codon,
                "codon_first_bp": coord(0) + 1,
                "cds_strand": strand,
                "overlap_bp": args.overlap,
                "flank_bp": flank[0],
                "flank_tm_c": round(flank[2], 2),
                "tail_first_bp": coord(a) + 1,
                "tail_last_bp": coord(b) + 1,
                "primer_strand": sense,
            }
        )
    return rows


def outputs(folder, rows, args, record):
    with (folder / "primers.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    if args.order:
        from openpyxl import Workbook, load_workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Oligos"
        sheet.append(["Name", "Sequence (5' to 3')", "Scale", "Purification", "Modification"])
        for row in rows:
            sheet.append([row["name"], row["sequence"]])
        sheet.freeze_panes = "A2"
        for column, width in zip("ABCDE", (20, 55, 16, 18, 18)):
            sheet.column_dimensions[column].width = width
        path = folder / "order.xlsx"
        book.save(path)
        with path.open("rb") as handle:
            check = load_workbook(handle, read_only=True)
            values = list(check.active.values)[1:]
            check.close()
        if [r[:2] for r in values] != [(r["name"], r["sequence"]) for r in rows]:
            raise ValueError("Order sheet failed readback")
    if args.map:
        write_map(args.template, record, folder, rows, args.map)


def run(args):
    record, template, first, strand, code, protein = read_target(
        args.template, args.cds, args.genetic_code
    )
    if not (
        5 <= args.overlap
        and (args.overlap - 2) // 2 < args.flank <= args.max_flank
        and 2 * args.max_flank + 3 < len(template)
    ):
        raise ValueError("Incompatible overlap, flank lengths, or template length")
    conditions = [args.min_tm, args.max_delta, args.primer_nm, args.na, args.mg, args.dntp]
    if not all(map(isfinite, conditions)) or min(conditions[1:]) < 0 or args.primer_nm == 0:
        raise ValueError("Invalid Tm or concentration settings")
    items = json.loads(args.requests.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list) or not items or len({r["variant"] for r in items}) != len(items):
        raise ValueError("Supply a nonempty list of distinct variants")
    rows = [
        row for item in items for row in pair(template, first, strand, code, protein, item, args)
    ]
    if len({r["name"].casefold() for r in rows}) != len(rows):
        raise ValueError("Oligo names must be distinct")
    if args.out.exists():
        raise ValueError("Output directory already exists")
    with TemporaryDirectory(dir=args.out.parent) as tmp:
        staged = Path(tmp) / "deliverables"
        staged.mkdir()
        outputs(staged, rows, args, record)
        staged.rename(args.out)


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("template", type=Path)
    p.add_argument("requests", type=Path)
    p.add_argument("out", type=Path, help="New output directory")
    p.add_argument("--cds", required=True)
    p.add_argument("--genetic-code", type=int)
    p.add_argument("--order", action="store_true", help="Write generic XLSX oligo order sheet")
    p.add_argument("--map", choices=("append", "replace"), help="Write an annotated copy")
    for name, default in (("overlap", 16), ("flank", 20), ("max-flank", 24)):
        p.add_argument("--" + name, type=int, default=default)
    for name, default in (
        ("min-tm", 55),
        ("max-delta", 6),
        ("primer-nm", 250),
        ("na", 50),
        ("mg", 1.5),
        ("dntp", 0.8),
    ):
        p.add_argument("--" + name, type=float, default=default)
    return p


if __name__ == "__main__":
    parser = cli()
    try:
        run(parser.parse_args())
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"{error}\n")
