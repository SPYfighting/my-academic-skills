#!/usr/bin/env python3
"""Check the selection caps and diversity targets on a shipped design sheet.

Diversity is a property of the SELECTED SET, not of a row, so it gets its own
check. Standard library only.

    python check_diversity.py --sheet design_sheet.csv --schema sheet_schema.json
    python check_diversity.py --sheet design_sheet.csv --schema sheet_schema.json --relaxed

--relaxed applies the relaxed_caps_floor from the schema instead of the normal
caps, for a campaign that invoked the documented relaxation ladder. It never
loosens the absolute floors.

Exit code 0 when there are no errors, 1 otherwise.
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict


def parse_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def cap_count(n_rows, share):
    """Ceiling of share * n_rows, matching the 'rounded up' rule in the spec."""
    return int(math.ceil(share * n_rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--relaxed", action="store_true",
                    help="apply relaxed_caps_floor instead of selection_caps")
    args = ap.parse_args()

    with open(args.schema, encoding="utf-8") as fh:
        schema = json.load(fh)
    with open(args.sheet, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    caps = dict(schema.get("selection_caps", {}))
    if args.relaxed:
        caps.update(schema.get("relaxed_caps_floor", {}))
    targets_cfg = schema.get("diversity_targets", {})

    errors, warnings = [], []
    by_target = defaultdict(list)
    for row in rows:
        by_target[row.get("target")].append(row)

    for target, trows in sorted(by_target.items()):
        n = len(trows)
        print("")
        print("=== {} ({} rows{}) ===".format(target, n, ", relaxed caps" if args.relaxed else ""))

        backbones = Counter(r.get("root_backbone_id") for r in trows)
        clusters = Counter(r.get("tm90_cluster_id") for r in trows)
        smethods = Counter(r.get("structure_method") for r in trows)
        qmethods = Counter(r.get("seq_method") for r in trows)
        folds = Counter(r.get("fold_class") for r in trows)

        print("  distinct root backbones : {} (largest {})".format(
            len(backbones), backbones.most_common(1)[0][1] if backbones else 0))
        print("  TM-0.90 clusters        : {} (largest {})".format(
            len(clusters), clusters.most_common(1)[0][1] if clusters else 0))
        print("  structure methods       : {} {}".format(len(smethods), dict(smethods)))
        print("  sequence methods        : {} {}".format(len(qmethods), dict(qmethods)))
        print("  fold classes            : {}".format(dict(folds)))

        limit = cap_count(n, caps.get("max_share_per_root_backbone", 1.0))
        for key, count in backbones.items():
            if count > limit:
                errors.append("{}: root_backbone_id {!r} supplies {} rows, cap is {}"
                              .format(target, key, count, limit))

        limit = cap_count(n, caps.get("max_share_per_tm90_cluster", 1.0))
        for key, count in clusters.items():
            if count > limit:
                errors.append("{}: tm90 cluster {!r} supplies {} rows, cap is {}"
                              .format(target, key, count, limit))

        limit = cap_count(n, caps.get("max_share_per_structure_method", 1.0))
        for key, count in smethods.items():
            if count > limit:
                errors.append("{}: structure_method {!r} supplies {} rows, cap is {}"
                              .format(target, key, count, limit))

        min_methods = caps.get("min_distinct_structure_methods", 1)
        if len(smethods) < min_methods:
            errors.append("{}: only {} distinct structure_method(s), minimum is {}"
                          .format(target, len(smethods), min_methods))

        limit = cap_count(n, caps.get("max_share_per_seq_method", 1.0))
        for key, count in qmethods.items():
            if count > limit:
                errors.append("{}: seq_method {!r} supplies {} rows, cap is {}"
                              .format(target, key, count, limit))

        want = targets_cfg.get("min_share_not_all_alpha")
        if want is not None:
            got = folds.get("not_all_alpha", 0)
            need = cap_count(n, want)
            if got < need:
                warnings.append("{}: {} not_all_alpha row(s), target is {} ({:.0%}). "
                                "This is a reported target, not a gate; state the count "
                                "and the reason in the sheet and the report."
                                .format(target, got, need, want))

        relaxations = Counter(r.get("relaxation_step") for r in trows
                              if (r.get("relaxation_step") or "").strip())
        if relaxations:
            warnings.append("{}: relaxation steps applied {}; each must be disclosed "
                            "in the sheet and the report".format(target, dict(relaxations)))
        if relaxations.get("NOVELTY_LAST_RESORT"):
            warnings.append("{}: NOVELTY_LAST_RESORT rows present. Confirm the absolute "
                            "floors still hold: no identical rows, no target-mimic binder "
                            "chain, no natural-sequence copy.".format(target))

    print("")
    for msg in warnings:
        print("WARN  {}".format(msg))
    for msg in errors:
        print("ERROR {}".format(msg))
    print("")
    print("{} error(s), {} warning(s)".format(len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
