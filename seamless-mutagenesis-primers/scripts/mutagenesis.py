"""Place mutation-bearing junctions and reconstruct PCR fragments in assembly order."""

import re
from dataclasses import dataclass
from itertools import product

from Bio.Seq import Seq
from Bio.SeqUtils.MeltingTemp import Tm_NN


def rc(seq):
    return str(Seq(seq).reverse_complement())


def circular(seq, start, length):
    if not 0 <= length <= len(seq):
        raise ValueError("Interval exceeds one plasmid revolution")
    start %= len(seq)
    return (seq + seq)[start : start + length]


def unique(seq, word):
    extended = seq + seq[: len(word) - 1]
    if word == rc(word):
        return False
    return sum(len(re.findall(f"(?={w})", extended)) for w in (word, rc(word))) == 1


def safe_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError("Use a plain oligo name starting with a letter or digit")
    return name


def source_id(item):
    value = str(item.get("source_id", ""))
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


@dataclass
class Edit:
    variant: str
    pos: int
    codon: str


def edits_for(item, protein, code):
    combined = "edits" in item
    changes = item["edits"] if combined else [item]
    if not isinstance(changes, list) or not changes or combined and "variant" in item:
        raise ValueError("Use either one variant or a named group of edits")
    wanted = list(protein)
    edits = []
    seen = set()
    for change in changes:
        variant = change["variant"]
        match = re.fullmatch(
            r"([ACDEFGHIKLMNPQRSTVWY])([1-9][0-9]*)([ACDEFGHIKLMNPQRSTVWY])", variant
        )
        if not match:
            raise ValueError(f"Invalid substitution: {variant!r}")
        wt, number, alt = match.groups()
        k = int(number) - 1
        if k in seen or wt == alt or k >= len(protein) or protein[k] != wt:
            raise ValueError(f"{variant}: duplicate site, wild type or CDS position mismatch")
        seen.add(k)
        codon = change["codon"].upper()
        if not re.fullmatch("[ACGT]{3}", codon) or str(Seq(codon).translate(table=code)) != alt:
            raise ValueError(f"{variant}: target codon does not encode requested residue")
        edits.append(Edit(variant, k * 3, codon))
        wanted[k] = alt
    if "protein" in item and item["protein"].rstrip("*") != "".join(wanted).rstrip("*"):
        raise ValueError("Supplied mutant protein differs from requested substitutions")
    return sorted(edits, key=lambda e: e.pos), "".join(wanted)


def make_arm(mutant, block, preferred, maximum, floor, flank_limit, multiple):
    start, end = block[0].pos, block[-1].pos + 3
    span = end - start
    for length in range(preferred, maximum + 1):
        sides = length - span
        # Visit centered windows first. A single-codon 16-mer starts with 6 upstream bases.
        margin = min(3, (preferred - 3) // 2)
        for up in sorted(range(margin, sides - margin + 1), key=lambda x: abs(2 * x - sides)):
            down = sides - up
            if max(up, down) > flank_limit:
                continue
            sequence = circular(mutant, start - up, length)
            wallace = 2 * length + 2 * (sequence.count("C") + sequence.count("G"))
            if (floor is None or wallace >= floor) and (not multiple or unique(mutant, sequence)):
                return start - up, sequence, up, down, wallace
    variants = ",".join(e.variant for e in block)
    raise ValueError(
        f"{variants}: no compatible overlap in {preferred}..{maximum} bp; review length, repeated junctions or staged assembly"
    )


def tails(template, boundary, reverse, minimum, args):
    for n in range(max(args.flank, minimum), args.max_flank + 1):
        tail = (
            rc(circular(template, boundary - n, n)) if reverse else circular(template, boundary, n)
        )
        if unique(template, tail):
            tm = Tm_NN(tail, dnac1=args.primer_nm, dnac2=0, Na=args.na, Mg=args.mg, dNTPs=args.dntp)
            if tm >= args.min_tm:
                yield n, tail, tm


def construct(template, first, strand, code, protein, item, args):
    edits, wanted = edits_for(item, protein, code)
    name = safe_name(item["name"] if "edits" in item else item.get("name", edits[0].variant))
    size = len(template)
    mutated = list(template)
    for e in edits:
        mutated[e.pos : e.pos + 3] = e.codon
    mutant = "".join(mutated)
    if str(Seq(mutant[: 3 * len(protein)]).translate(table=code)) != wanted:
        raise ValueError("Construct translation failed")
    neb = args.chemistry == "nebuilder"
    preferred = args.overlap if args.overlap is not None else 16
    maximum = args.max_overlap
    if maximum is None:
        adaptive = (neb or args.arm_min_tm is not None) and args.overlap is None
        maximum = 24 if adaptive else preferred
    floor = args.arm_min_tm if args.arm_min_tm is not None else (48 if neb else None)
    if not 5 <= preferred <= maximum <= size:
        raise ValueError("Incompatible overlap lengths")
    blocks = []
    for edit in edits:
        if (
            blocks
            and edit.pos + 3 - blocks[-1][0].pos + 2 * min(3, (preferred - 3) // 2) <= maximum
        ):
            blocks[-1].append(edit)
        else:
            blocks.append([edit])
    if neb and len(blocks) >= 4 and args.overlap is None:
        preferred = max(preferred, 20)
    arms = [
        make_arm(mutant, b, preferred, maximum, floor, args.max_flank, len(blocks) > 1)
        for b in blocks
    ]
    rows = []
    assembled = []
    for j, block in enumerate(blocks):
        nxt = (j + 1) % len(blocks)
        following = blocks[nxt]
        wrap = size if nxt == 0 else 0
        end = block[-1].pos + 3
        stop = following[0].pos + wrap
        a, arm, _, down, _ = arms[j]
        b, next_arm, next_up, _, _ = arms[nxt]
        product_size = b + wrap + len(next_arm) - a
        minimum = (
            args.min_fragment
            if args.min_fragment is not None
            else (120 if neb and len(blocks) > 1 else 0)
        )
        if product_size < minimum:
            raise ValueError(
                f"{name}: fragment {j + 1} is {product_size} bp, below the configured {minimum} bp minimum"
            )
        f_options = tails(template, end, False, down, args)
        r_options = tails(template, stop, True, next_up, args)
        pairs = [
            (f[0] + r[0], abs(f[2] - r[2]), f, r)
            for f, r in product(f_options, r_options)
            if f[0] + r[0] <= stop - end and abs(f[2] - r[2]) <= args.max_delta
        ]
        if not pairs:
            raise ValueError(
                f"{name}, PCR {j + 1}: no unique paired flanks fit spacing and Tm constraints; review nearby edits or use staged assembly"
            )
        _, _, f, r = min(pairs)
        fseq = arm[: len(arm) - down] + f[1]
        rseq = rc(next_arm[next_up:]) + r[1]
        fragment = fseq + circular(template, end + f[0], stop - end - f[0] - r[0]) + rc(rseq)
        expected_fragment = (
            circular(mutant, a, product_size)
            if len(blocks) > 1
            else circular(mutant, a, size) + arm
        )
        if fragment != expected_fragment:
            raise ValueError("Actual PCR fragment differs from intended construct")
        if not fragment.startswith(arm) or not fragment.endswith(next_arm):
            raise ValueError("Junction orientation mismatch")
        assembled.append(fragment[: -len(next_arm)])
        for direction, seq, flank, site, dx, dy, orientation in [
            ("F", fseq, f, j, end, end + f[0] - 1, strand),
            ("R", rseq, r, nxt, stop - 1, stop - r[0], -strand),
        ]:
            group = blocks[site]
            anchor, overlap, left, right, temperature = arms[site]
            stem = name if len(blocks) == 1 else f"{name}-J{site + 1}"

            def coord(idx):
                return (first + strand * idx) % size + 1

            rows.append(
                {
                    "variant": ",".join(e.variant for e in group),
                    "source_id": source_id(item),
                    "name": f"{stem}-{direction}",
                    "sequence": seq,
                    "wt_codon": ",".join(template[e.pos : e.pos + 3] for e in group),
                    "target_codon": ",".join(e.codon for e in group),
                    "codon_first_bp": ",".join(str(coord(e.pos)) for e in group),
                    "cds_strand": strand,
                    "overlap_bp": len(overlap),
                    "flank_bp": flank[0],
                    "flank_tm_c": round(flank[2], 2),
                    "tail_first_bp": coord(dx),
                    "tail_last_bp": coord(dy),
                    "primer_strand": orientation,
                    "construct": name,
                    "pcr": j + 1,
                    "product_bp": product_size,
                    "junction": site + 1,
                    "arm_sequence": overlap,
                    "arm_first_bp": coord(anchor),
                    "arm_upstream_bp": left,
                    "arm_downstream_bp": right,
                    "arm_wallace_c": temperature,
                    "arm_min_c": floor,
                    "chemistry": args.chemistry,
                }
            )
    if "".join(assembled) != circular(mutant, arms[0][0], size):
        raise ValueError("Circular assembly failed")
    return rows
