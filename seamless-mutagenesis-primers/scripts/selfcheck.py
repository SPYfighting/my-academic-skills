"""Exercise the public CLI using only generated, non-biological fixtures."""

import argparse
import csv
import json
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord
from openpyxl import load_workbook

SCRIPT = Path(__file__).with_name("design.py")


def native(path, sequence):
    def packet(kind, data):
        return struct.pack(">BI", kind, len(data)) + data

    features = (
        b'<Features><Feature type="CDS" name="demo"><Segment range="41-136"/></Feature>'
        b'<Feature name="old" type="primer_bind"><Segment range="1-10"/></Feature></Features>'
    )
    primers = ET.Element("Primers", nextValidID="1")
    old = ET.SubElement(primers, "Primer", name="legacy", recentID="0", sequence=sequence[10:30])
    ET.SubElement(
        old, "BindingSite", location="10-29", boundStrand="0", annealedBases=sequence[10:30]
    )
    path.write_bytes(
        b"".join(
            [
                packet(9, struct.pack(">8sHHH", b"SnapGene", 1, 15, 17)),
                packet(0, b"\x01" + sequence.encode()),
                packet(10, features),
                packet(5, ET.tostring(primers)),
            ]
        )
    )


def selfcheck(folder):
    rng = random.Random(823)
    triplets = [
        a + b + c
        for a in "ACGT"
        for b in "ACGT"
        for c in "ACGT"
        if a + b + c not in {"TGA", "TAG", "TAA"}
    ]
    sequence = list("".join(rng.choices("ACGT", k=240)))
    sequence[40:136] = "".join(rng.choices(triplets, k=32))
    sequence[70:73] = "GAA"
    seq = "".join(sequence)
    protein = str(Seq(seq[40:136]).translate())
    job = [
        {
            "variant": "E11Q",
            "codon": "CAA",
            "source_id": "pick-3",
            "name": "Trial3",
            "protein": protein[:10] + "Q" + protein[11:],
        },
        {"variant": "E11A", "codon": "GCT"},
    ]
    requests = folder / "selection.json"
    requests.write_text(json.dumps(job))
    dna = folder / "template.dna"
    native(dna, seq)

    def invoke(path, dest, options=(), success=True, reason=None):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(path),
                str(requests),
                str(dest),
                "--cds",
                "demo",
                "--genetic-code",
                "1",
                *options,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if (result.returncode == 0) != success or (reason and reason not in result.stderr):
            raise AssertionError(result.stderr or "unexpected CLI outcome")

    def inventory(path, fmt):
        return [f for f in SeqIO.read(path, fmt).features if f.type == "primer_bind"]

    original = dna.read_bytes()
    for mode in ("append", "replace"):
        dest = folder / mode
        invoke(dna, dest, ["--order", "--map", mode])
        assert len(inventory(dest / "primers.dna", "snapgene")) == 4 + 2 * (mode == "append")
        with (dest / "primers.csv").open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        book = load_workbook(dest / "order.xlsx", read_only=True)
        orders = list(book.active.values)[1:]
        book.close()
        assert [o[:2] for o in orders] == [(r["name"], r["sequence"]) for r in rows]
        packet = (dest / "primers.dna").read_bytes()
        pos = 0
        while pos < len(packet):
            kind, n = struct.unpack_from(">BI", packet, pos)
            if kind == 5:
                xml = ET.fromstring(packet[pos + 5 : pos + 5 + n])
                assert [
                    (p.get("name"), p.get("sequence"))
                    for p in xml.findall("Primer")
                    if p.get("name") != "legacy"
                ] == [o[:2] for o in orders]
            pos += 5 + n
        for j, item in enumerate(job):
            f, r = [Seq(row["sequence"]) for row in rows[2 * j : 2 * j + 2]]
            assert f[:16] == r[:16].reverse_complement()
            assert str(f[6:9]) == item["codon"] and seq[70:73] == "GAA"
            assert rows[2 * j]["codon_first_bp"] == "71"
            assert str(f[9:]) == seq[73 : 73 + len(f) - 9]
            assert str(r[10:].reverse_complement()) == seq[70 - (len(r) - 10) : 70]
    assert dna.read_bytes() == original
    # Reverse strand, translated in frame 2, rotated so the codon crosses base one.
    reverse = str(Seq(seq).reverse_complement())
    record = SeqRecord(
        Seq(reverse), id="test", annotations={"molecule_type": "DNA", "topology": "circular"}
    )
    cds = SeqFeature(
        SimpleLocation(104, 201, strand=-1),
        type="CDS",
        qualifiers={"gene": ["demo"], "codon_start": ["2"]},
    )
    record.features.append(cds)
    shift = 168
    loc = SimpleLocation(0, 201 - shift, strand=-1) + SimpleLocation(
        104 - shift + 240, 240, strand=-1
    )
    cds.location = loc
    record.seq = Seq(reverse[shift:] + reverse[:shift])
    gb = folder / "reverse.gb"
    SeqIO.write(record, gb, "genbank")
    dest = folder / "reverse"
    invoke(gb, dest, ["--map", "replace"])
    binds = inventory(dest / "primers.gb", "genbank")
    assert [f.location.strand for f in binds] == [-1, 1, -1, 1]
    assert not (dest / "order.xlsx").exists()
    with (dest / "primers.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["codon_first_bp"] == "2"
    assert rows[0]["name"] == "Trial3-F" and rows[0]["source_id"] == "pick-3"
    bad = folder / "invalid"
    for edits, message in [
        ({"variant": "K11Q"}, "wild type"),
        ({"codon": "TGG"}, "does not encode"),
        ({"protein": protein}, "mutant protein differs"),
    ]:
        requests.write_text(json.dumps([dict(job[0], **edits)]))
        invoke(dna, bad, success=False, reason=message)
        assert not bad.exists()
    repeated = folder / "repeat.dna"
    native(repeated, seq[:150] + seq[46:70] + seq[174:])
    requests.write_text(json.dumps(job))
    invoke(repeated, bad, success=False, reason="no unique paired flanks")
    invoke(dna, dest, success=False, reason="already exists")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        selfcheck(Path(temp))
    print(
        "PASS: synthetic native and GenBank maps, reverse/origin/frame mapping, ordering and invalid inputs"
    )
    print("Untested: native GUI rendering, vendor import and experimental outcomes")
