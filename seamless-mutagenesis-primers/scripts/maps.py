"""Write a primer-annotated copy and check its sequence, features and bindings."""

import copy
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from itertools import groupby

from Bio import SeqIO
from Bio.SeqFeature import CompoundLocation, SeqFeature, SimpleLocation


def location(row, size):
    strand = row["primer_strand"]
    first = row["tail_first_bp"] - 1
    coords = [(first + j * strand) % size for j in range(row["flank_bp"])]
    chunks = groupby(enumerate(coords), key=lambda t: t[1] - strand * t[0])
    parts = []
    for _, chunk in chunks:
        bases = [b for _, b in chunk]
        parts.append(SimpleLocation(min(bases), max(bases) + 1, strand=strand))
    return parts[0] if len(parts) == 1 else CompoundLocation(parts)


def xml_bytes(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def native_copy(source, rows, replace):
    data = source.read_bytes()
    blocks = []
    offset = 0
    while offset + 5 <= len(data):
        kind, length = struct.unpack_from(">BI", data, offset)
        offset += 5
        if offset + length > len(data):
            raise ValueError("Truncated SnapGene packet")
        blocks.append((kind, data[offset : offset + length]))
        offset += length
    counts = Counter(k for k, d in blocks)
    if (
        offset != len(data)
        or not blocks
        or blocks[0] != (9, struct.pack(">8sHHH", b"SnapGene", 1, 15, 17))
        or counts[0] != 1
        or counts[5] > 1
        or counts[10] > 1
    ):
        raise ValueError("Unsupported native map layout; use a native editor to annotate a copy")
    primer_root = ET.fromstring(dict(blocks)[5]) if counts[5] else ET.Element("Primers")
    if primer_root.tag != "Primers":
        raise ValueError("Unexpected primer packet")
    existing = primer_root.findall("Primer")
    if not replace and {p.get("name") for p in existing} & {r["name"] for r in rows}:
        raise ValueError("Native primer list already includes one of the new names")
    next_id = max(
        [int(primer_root.get("nextValidID", "0"))]
        + [int(p.get("recentID", "0")) + 1 for p in existing]
    )
    if replace:
        for p in existing:
            primer_root.remove(p)
    for row in rows:
        p = ET.SubElement(
            primer_root, "Primer", recentID=str(next_id), name=row["name"], sequence=row["sequence"]
        )
        next_id += 1
        a, b = row["tail_first_bp"] - 1, row["tail_last_bp"] - 1
        reverse = row["primer_strand"] == -1
        coords = f"{b}-{a}" if reverse else f"{a}-{b}"
        n = row["flank_bp"]
        tail = row["sequence"][-n:]
        for extra in ({}, {"simplified": "1"}):
            site = ET.SubElement(
                p,
                "BindingSite",
                location=coords,
                boundStrand=str(int(reverse)),
                annealedBases=tail,
                meltingTemperature=str(round(row["flank_tm_c"])),
                **extra,
            )
            if len(row["sequence"]) > n:
                ET.SubElement(site, "Component", bases=row["sequence"][:-n])
            ET.SubElement(site, "Component", bases=tail, hybridizedRange=coords)
    primer_root.set("nextValidID", str(next_id))
    if counts[5] == 0:
        blocks.append((5, b""))
    packed = []
    for kind, block in blocks:
        if kind == 5:
            block = xml_bytes(primer_root)
        if kind == 10 and replace:
            features = ET.fromstring(block)
            removed = [f for f in features.findall("Feature") if f.get("type") == "primer_bind"]
            for f in removed:
                features.remove(f)
            if removed:
                block = xml_bytes(features)
        packed.append(struct.pack(">BI", kind, len(block)) + block)
    return b"".join(packed)


def write_map(source, record, folder, rows, mode):
    replace = mode == "replace"
    native = source.suffix.lower() == ".dna"
    original = [f for f in record.features if f.type == "primer_bind"]
    wanted = {r["name"]: r for r in rows}
    if not replace and any(wanted.keys() & set(f.qualifiers.get("label", [])) for f in original):
        raise ValueError("Existing primer name collides with a requested primer")
    if native:
        path = folder / "primers.dna"
        path.write_bytes(native_copy(source, rows, replace))
        result = SeqIO.read(path, "snapgene")
    else:
        path = folder / "primers.gb"
        result = copy.deepcopy(record)
        if replace:
            result.features = [f for f in result.features if f.type != "primer_bind"]
        for row in rows:
            result.features.append(
                SeqFeature(
                    location(row, len(record)),
                    type="primer_bind",
                    qualifiers={"label": [row["name"]], "primer_seq": [row["sequence"]]},
                )
            )
        SeqIO.write(result, path, "genbank")
        result = SeqIO.read(path, "genbank")

    def other(rec):
        return [f for f in rec.features if f.type != "primer_bind"]

    if result.seq != record.seq or other(result) != other(record):
        raise ValueError("Annotated copy changed template or other features")
    bindings = [f for f in result.features if f.type == "primer_bind"]
    preserved = [] if replace else original
    if len(bindings) != len(preserved) + len(rows) or any(f not in bindings for f in preserved):
        raise ValueError("Primer inventory mismatch after map readback")
    for name, row in wanted.items():
        matches = [f for f in bindings if name in f.qualifiers.get("label", [])]
        if len(matches) != 1 or list(matches[0].location) != list(location(row, len(record))):
            raise ValueError(f"{name}: incorrect mapped position after readback")
        if str(matches[0].extract(result.seq)).upper() != row["sequence"][-row["flank_bp"] :]:
            raise ValueError(f"{name}: binding strand or sequence mismatch")
