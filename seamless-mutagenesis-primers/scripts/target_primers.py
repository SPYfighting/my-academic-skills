"""Primer3 selection around a specified forward-reference target interval."""

import primer3
from mutagenesis import circular, rc, safe_name, source_id, unique


def choose(template, item, args):
    name = safe_name(item["name"])
    size = len(template)
    start, end = item["start"], item["end"]
    if not all(type(pos) is int and 1 <= pos <= size for pos in (start, end)):
        raise ValueError(f"{name}: target coordinates must lie on the plasmid")
    width = (end - start) % size + 1
    params = {
        "PRIMER_NUM_RETURN": 80,
        "PRIMER_MIN_SIZE": args.primer_min_len,
        "PRIMER_OPT_SIZE": args.primer_opt_len,
        "PRIMER_MAX_SIZE": args.primer_max_len,
        "PRIMER_MIN_TM": args.min_tm,
        "PRIMER_OPT_TM": args.opt_tm,
        "PRIMER_MAX_TM": args.max_tm,
        "PRIMER_DNA_CONC": args.primer_nm,
        "PRIMER_SALT_MONOVALENT": args.na,
        "PRIMER_SALT_DIVALENT": args.mg,
        "PRIMER_DNTP_CONC": args.dntp,
        "PRIMER_EXPLAIN_FLAG": 1,
    }

    def row(direction, seq, tm, first, strand, **extra):
        if circular(template, first if strand == 1 else first - len(seq) + 1, len(seq)) != (
            seq if strand == 1 else rc(seq)
        ):
            raise ValueError("Primer3 position disagrees with the template sequence")
        return dict(
            name=f"{name}-{direction}",
            source_id=source_id(item),
            sequence=seq,
            flank_bp=len(seq),
            flank_tm_c=round(tm, 2),
            tail_first_bp=first % size + 1,
            tail_last_bp=(first + strand * (len(seq) - 1)) % size + 1,
            primer_strand=strand,
            target_start_bp=start,
            target_end_bp=end,
            **extra,
        )

    if args.mode == "pcr":
        low, high = item.get(
            "product_range", [max(width + 2 * args.primer_min_len, 100), min(size, width + 400)]
        )
        if not 1 <= low <= high <= size:
            raise ValueError(f"{name}: invalid amplicon size range")
        # Split spare template between both sides if a second full revolution would be needed.
        spare = size - width
        pad = min(high - width, spare // 2)
        after = min(high - width, spare - pad)
        if min(pad, after) < args.primer_min_len:
            raise ValueError(f"{name}: insufficient sequence for flanking primers")
        offset = start - 1 - pad
        window = circular(template, offset, pad + width + after)
        result = primer3.bindings.design_primers(
            {"SEQUENCE_TEMPLATE": window, "SEQUENCE_TARGET": [pad, width]},
            dict(
                params,
                PRIMER_PRODUCT_SIZE_RANGE=[[low, high]],
                PRIMER_PAIR_MAX_DIFF_TM=args.max_delta,
            ),
        )
        for i in range(result["PRIMER_PAIR_NUM_RETURNED"]):
            l, r = f"PRIMER_LEFT_{i}", f"PRIMER_RIGHT_{i}"
            f, rev = result[l + "_SEQUENCE"], result[r + "_SEQUENCE"]
            if not (unique(template, f) and unique(template, rev)):
                continue
            a, n = result[l]
            b, m = result[r]
            product = window[a : b + 1]
            if not (
                a + n <= pad
                and b - m + 1 >= pad + width
                and low <= len(product) <= high
                and product == f + window[a + n : b - m + 1] + rc(rev)
                and len(product) == result[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"]
            ):
                continue
            extra = {
                "product_bp": len(product),
                "product_start_bp": (offset + a) % size + 1,
                "product_end_bp": (offset + b) % size + 1,
            }
            return [
                row("F", f, result[l + "_TM"], offset + a, 1, **extra),
                row("R", rev, result[r + "_TM"], offset + b, -1, **extra),
            ]
    else:
        directions = {"forward": [1], "reverse": [-1], "both": [1, -1]}.get(
            item.get("direction", "forward")
        )
        near, far = item.get("distance_range", [50, 120])
        reach = item.get("read_length", 650)
        if not directions or not (1 <= near <= far and near + width - 1 <= min(size, reach)):
            raise ValueError(f"{name}: direction, spacing or read coverage is infeasible")
        rows = []
        for sense in directions:
            dna = template if sense == 1 else rc(template)
            target = start - 1 if sense == 1 else size - end
            far_limit = min(far, reach - width + 1, size - width - args.primer_max_len + 1)
            offset = target - far_limit - args.primer_max_len + 1
            window_len = target - near - offset + 1
            if window_len < args.primer_min_len:
                raise ValueError(f"{name}: insufficient Sanger search window")
            window = circular(dna, offset, window_len)
            result = primer3.bindings.design_primers(
                {"SEQUENCE_TEMPLATE": window},
                dict(params, PRIMER_PICK_LEFT_PRIMER=1, PRIMER_PICK_RIGHT_PRIMER=0),
            )
            for i in range(result["PRIMER_LEFT_NUM_RETURNED"]):
                key = f"PRIMER_LEFT_{i}"
                a, n = result[key]
                seq = result[key + "_SEQUENCE"]
                distance = target - (offset + a + n - 1)
                if (
                    near <= distance <= far
                    and distance + width - 1 <= reach
                    and unique(template, seq)
                ):
                    first = offset + a if sense == 1 else size - 1 - (offset + a)
                    rows.append(
                        row(
                            "F" if sense == 1 else "R",
                            seq,
                            result[key + "_TM"],
                            first,
                            sense,
                            target_near_base=distance,
                            target_far_base=distance + width - 1,
                            assumed_read_bp=reach,
                        )
                    )
                    break
            else:
                raise ValueError(
                    f"{name}: no unique Sanger primer meets read direction, distance and coverage"
                )
        return rows
    raise ValueError(f"{name}: no unique Primer3 pair covers the target within the product range")
