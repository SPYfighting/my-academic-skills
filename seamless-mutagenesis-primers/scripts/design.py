"""Design and verify mutagenesis, PCR or Sanger primers on a circular plasmid."""

import argparse
import csv
import json
from itertools import groupby, pairwise
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import ExactPosition
from maps import write_map
from mutagenesis import construct, rc


def read_map(path):
    fmt = "snapgene" if path.suffix.lower() == ".dna" else "genbank"
    record = SeqIO.read(path, fmt)
    if record.annotations.get("topology") != "circular" or set(str(record.seq).upper()) - set(
        "ACGT"
    ):
        raise ValueError("A circular plasmid with resolved A/C/G/T sequence is required")
    return record


def read_target(record, label, genetic_code):
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
    return rotated, indexes[0], strand, code, protein


def outputs(folder, rows, args, record):
    with (folder / "primers.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    if args.mode == "mutagenesis" and any(row["pcr"] > 1 for row in rows):
        with (folder / "fragments.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "construct",
                    "pcr",
                    "forward_primer",
                    "reverse_primer",
                    "product_bp",
                    "start_junction",
                    "end_junction",
                    "pair_delta_tm_c",
                ]
            )
            for _, reaction in groupby(rows, key=lambda r: (r["construct"], r["pcr"])):
                forward, reverse = reaction
                writer.writerow(
                    [
                        forward["construct"],
                        forward["pcr"],
                        forward["name"],
                        reverse["name"],
                        forward["product_bp"],
                        forward["junction"],
                        reverse["junction"],
                        round(abs(forward["flank_tm_c"] - reverse["flank_tm_c"]), 2),
                    ]
                )
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
    record = read_map(args.template)
    conditions = [args.min_tm, args.max_delta, args.primer_nm, args.na, args.mg, args.dntp]
    if not all(map(isfinite, conditions)) or min(conditions[1:]) < 0 or args.primer_nm == 0:
        raise ValueError("Invalid Tm or concentration settings")
    items = json.loads(args.requests.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        raise ValueError("Supply a nonempty list of requests")
    if args.mode == "mutagenesis":
        if (
            not args.cds
            or not 1 <= args.flank <= args.max_flank
            or (args.min_fragment is not None and args.min_fragment < 1)
        ):
            raise ValueError("Select a CDS and valid length ranges")
        template, first, strand, code, protein = read_target(record, args.cds, args.genetic_code)
        if args.max_flank >= len(template) or (
            args.arm_min_tm is not None and not isfinite(args.arm_min_tm)
        ):
            raise ValueError("Invalid flank length or overlap Tm threshold")
        names = [str(i.get("name", i.get("variant", ""))).casefold() for i in items]
        if len(set(names)) != len(names):
            raise ValueError("Construct names must be distinct")
        rows = [
            row
            for item in items
            for row in construct(template, first, strand, code, protein, item, args)
        ]
    else:
        from target_primers import choose

        if (
            not 1 <= args.primer_min_len <= args.primer_opt_len <= args.primer_max_len
            or not args.min_tm <= args.opt_tm <= args.max_tm
        ):
            raise ValueError("Invalid primer length or Tm range")
        rows = [row for item in items for row in choose(str(record.seq).upper(), item, args)]
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
    p.add_argument("--mode", choices=("mutagenesis", "pcr", "sanger"), default="mutagenesis")
    p.add_argument("--cds")
    p.add_argument("--chemistry", choices=("generic", "nebuilder"), default="generic")
    p.add_argument("--max-overlap", type=int, help="Largest permitted junction length, in bp")
    p.add_argument(
        "--arm-min-tm", type=float, help="Minimum 2/4-rule overlap temperature, in degrees C"
    )
    p.add_argument("--min-fragment", type=int)
    p.add_argument("--primer-min-len", type=int, default=18)
    p.add_argument("--primer-opt-len", type=int, default=20)
    p.add_argument("--primer-max-len", type=int, default=25)
    p.add_argument("--opt-tm", type=float, default=60)
    p.add_argument("--max-tm", type=float, default=65)
    p.add_argument("--genetic-code", type=int)
    p.add_argument("--order", action="store_true", help="Write generic XLSX oligo order sheet")
    p.add_argument("--map", choices=("append", "replace"), help="Write an annotated copy")
    for name, default in (("overlap", None), ("flank", 20), ("max-flank", 24)):
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
