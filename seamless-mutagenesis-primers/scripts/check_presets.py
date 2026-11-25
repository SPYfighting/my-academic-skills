"""Synthetic, offline end-to-end checks for joined edits and interval presets."""

import csv
import json
import random
import subprocess
import sys

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
from openpyxl import load_workbook


def check(folder, script):
    rng = random.Random(721)
    sequence = list("".join(rng.choices("ACGT", k=1560)))
    codons = [
        a + b + c
        for a in "ACGT"
        for b in "ACGT"
        for c in "ACGT"
        if a + b + c not in ("TGA", "TAA", "TAG")
    ]
    sequence[60:1260] = "".join(rng.choices(codons, k=400))
    sites = [
        (40, "GAA", "Q", "CAA"),
        (41, "GCT", "S", "AGC"),
        (179, "GAT", "N", "AAC"),
        (307, "CTT", "P", "CCG"),
    ]
    expected = sequence.copy()
    changes = []
    for residue, wt, alt, codon in sites:
        i = 60 + 3 * (residue - 1)
        sequence[i : i + 3] = wt
        expected[i : i + 3] = codon
        changes.append({"variant": f"{Seq(wt).translate()}{residue}{alt}", "codon": codon})
    template = "".join(sequence)
    expected = "".join(expected)
    record = SeqRecord(
        Seq(template), id="invented", annotations={"molecule_type": "DNA", "topology": "circular"}
    )
    record.features = [
        SeqFeature(SimpleLocation(60, 1260, strand=1), type="CDS", qualifiers={"gene": ["demo"]})
    ]
    path = folder / "fixture.gb"
    SeqIO.write(record, path, "genbank")
    request = folder / "inputs.json"

    def invoke(tag, items, options, fail=""):
        dest = folder / tag
        request.write_text(json.dumps(items))
        result = subprocess.run(
            [sys.executable, "-B", str(script), str(path), str(request), str(dest), *options],
            check=False,
            capture_output=True,
            text=True,
        )
        if fail:
            assert result.returncode and fail in result.stderr and not dest.exists(), result.stderr
            return []
        assert result.returncode == 0, result.stderr
        with (dest / "primers.csv").open(encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    job = {"name": "combined", "edits": changes, "protein": str(Seq(expected[60:1260]).translate())}
    options = [
        "--cds",
        "demo",
        "--genetic-code",
        "1",
        "--chemistry",
        "nebuilder",
        "--order",
        "--map",
        "replace",
    ]
    rows = invoke("multi", [job], options)
    assert len(rows) == 6 and len({r["junction"] for r in rows}) == 3
    assert len({r["pcr"] for r in rows}) == 3
    assert all(int(r["arm_wallace_c"]) >= 48 for r in rows)
    with (folder / "multi" / "fragments.csv").open(encoding="utf-8-sig") as handle:
        plan = list(csv.DictReader(handle))
    assert len(plan) == 3 and [p["reverse_primer"] for p in plan] == [r["name"] for r in rows[1::2]]
    cluster = invoke("cluster", [{"name": "near", "edits": changes[:2]}], options)
    assert len(cluster) == 2 and cluster[0]["variant"] == ",".join(
        e["variant"] for e in changes[:2]
    )
    invoke("small", [job], [*options, "--min-fragment", "1000"], "below the configured")
    book = load_workbook(folder / "multi" / "order.xlsx", read_only=True)
    assert [r[:2] for r in list(book.active.values)[1:]] == [
        (r["name"], r["sequence"]) for r in rows
    ]
    book.close()
    new = SeqIO.read(folder / "multi" / "primers.gb", "genbank")
    assert new.seq == record.seq and len(new.features) == 7
    assembled = ""
    for f, r in zip(rows[::2], rows[1::2]):
        assert f["pcr"] == r["pcr"] and f["junction"] != r["junction"]
        left = int(f["tail_last_bp"])
        right = int(r["tail_last_bp"]) - 1
        body = (template + template)[left : left + (right - left) % len(template)]
        fragment = f["sequence"] + body + str(Seq(r["sequence"]).reverse_complement())
        assert len(fragment) == int(f["product_bp"])
        assert fragment.startswith(f["arm_sequence"]) and fragment.endswith(r["arm_sequence"])
        assembled += fragment[: -len(r["arm_sequence"])]
    pivot = int(rows[0]["arm_first_bp"]) - 1
    assert assembled == expected[pivot:] + expected[:pivot]
    # Reuse the same coding sequence on the opposite strand. PCR sequences should
    # be identical, while every mapped coordinate must be reflected on the plasmid.
    reverse = record.reverse_complement(id="reversed", name="reversed", annotations=True)
    SeqIO.write(reverse, path, "genbank")
    reflected = invoke("reverse-multi", [job], options)
    assert [(r["name"], r["sequence"]) for r in reflected] == [
        (r["name"], r["sequence"]) for r in rows
    ]
    for old, new in zip(rows, reflected):
        assert int(new["tail_first_bp"]) == len(template) + 1 - int(old["tail_first_bp"])
        assert new["primer_strand"] == str(-int(old["primer_strand"]))
    SeqIO.write(record, path, "genbank")
    invoke(
        "duplicate",
        [{"name": "conflict", "edits": [changes[0], changes[0]]}],
        options,
        "duplicate site",
    )
    invoke(
        "fixed", [job], [*options, "--overlap", "16", "--arm-min-tm", "80"], "no compatible overlap"
    )
    # A user-specified bound can force lengthening after fixed-length windows are exhausted.
    wider = invoke(
        "wide",
        [dict(changes[0])],
        [*options, "--overlap", "16", "--max-overlap", "25", "--arm-min-tm", "58"],
    )
    assert 16 < int(wider[0]["overlap_bp"]) <= 25 and float(wider[0]["arm_wallace_c"]) >= 58
    pcr = invoke(
        "pcr",
        [{"name": "origin", "start": 1510, "end": 45, "product_range": [150, 280]}],
        ["--mode", "pcr", "--map", "append"],
    )
    assert len(pcr) == 2
    start = int(pcr[0]["product_start_bp"]) - 1
    length = int(pcr[0]["product_bp"])
    product = (template + template)[start : start + length]
    assert 150 <= length <= 280 and template[1509:] + template[:45] in product
    assert product.startswith(pcr[0]["sequence"]) and product.endswith(
        str(Seq(pcr[1]["sequence"]).reverse_complement())
    )
    reads = invoke(
        "reads",
        [{"name": "verify", "start": 1510, "end": 45, "direction": "both"}],
        ["--mode", "sanger", "--map", "replace"],
    )
    assert len(reads) == 2 and {r["primer_strand"] for r in reads} == {"1", "-1"}
    for row in reads:
        s = int(row["primer_strand"])
        target = 1510 if s == 1 else 45
        distance = ((target - int(row["tail_last_bp"])) * s) % len(template)
        assert 50 <= distance <= 120 and distance == int(row["target_near_base"])
        assert int(row["target_far_base"]) == distance + 95 and int(row["target_far_base"]) <= 650
    invoke(
        "short-read",
        [{"name": "too-long", "start": 1, "end": 800}],
        ["--mode", "sanger"],
        "infeasible",
    )
