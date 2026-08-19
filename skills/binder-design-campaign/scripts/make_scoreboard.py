#!/usr/bin/env python3
"""Derive scoreboard.csv from the shipped design sheet and the campaign ledger.

The scoreboard is DERIVED, never hand-authored, and its diversity columns are
computed by the same logic that enforces the selection caps. A column that
cannot be computed is a defect to remediate before close-out, recorded in
scoreboard_gaps.csv rather than filled with a sentinel.

    python make_scoreboard.py --sheet design_sheet.csv --root <campaign_root> \
        --out scoreboard.csv --gaps scoreboard_gaps.csv
"""

import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict

COLUMNS = [
    "target", "designs_generated", "designs_screened", "designs_ranked",
    "best_final_score", "median_final_score_ranked", "pose_check_pass_rate_top10",
    "gpu_hours", "wallclock_hours_active_compute", "n_distinct_root_backbones",
    "max_seqs_per_root_backbone", "n_tm90_clusters", "max_tm90_cluster_size",
    "n_structure_methods", "top_method_share", "min_pairwise_editdist",
    "n_non_all_alpha",
]


def parse_float(value):
    try:
        f = float(value)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def parse_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t", "pass")


def levenshtein(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                              previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def read_ledger(root):
    """Aggregate the ledger tree. Returns {} when there is no ledger."""
    d = os.path.join(root, "ledger")
    agg = defaultdict(lambda: {"generated": 0, "screened": 0, "ranked": 0,
                               "gpu_seconds": 0.0})
    if not os.path.isdir(d):
        return {}
    for name in sorted(os.listdir(d)):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = r.get("target")
                if not t:
                    continue
                a = agg[t]
                a["generated"] += int(r.get("n_generated") or 0)
                a["gpu_seconds"] += float(r.get("gpu_seconds") or 0)
                stage = r.get("stage")
                n_scored = int(r.get("n_scored") or 0)
                if stage in ("screen", "gen_screen"):
                    a["screened"] += n_scored
                elif stage == "final":
                    a["ranked"] += n_scored
    return dict(agg)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--root", required=True, help="campaign root (holds ledger/)")
    ap.add_argument("--out", default="scoreboard.csv")
    ap.add_argument("--gaps", default="scoreboard_gaps.csv")
    ap.add_argument("--wallclock", default=None,
                    help='JSON file mapping target -> active compute hours, taken '
                         'from scheduler accounting (sacct, provider report). '
                         'Without it that column is reported as a gap.')
    args = ap.parse_args()

    wallclock = {}
    if args.wallclock:
        with open(args.wallclock, encoding="utf-8") as fh:
            wallclock = json.load(fh)

    with open(args.sheet, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    ledger = read_ledger(args.root)

    by_target = defaultdict(list)
    for row in rows:
        by_target[row.get("target")].append(row)

    out_rows, gaps = [], []

    for target in sorted(by_target):
        trows = by_target[target]
        rec: Dict[str, Any] = {c: None for c in COLUMNS}
        rec["target"] = target

        led = ledger.get(target)
        if led:
            rec["designs_generated"] = led["generated"]
            rec["designs_screened"] = led["screened"]
            rec["designs_ranked"] = led["ranked"]
            rec["gpu_hours"] = round(led["gpu_seconds"] / 3600.0, 2)
        else:
            for col in ("designs_generated", "designs_screened", "designs_ranked",
                        "gpu_hours"):
                gaps.append({"target": target, "column": col,
                             "reason": "no ledger rows for this target",
                             "owning_writer": ""})

        scores = [parse_float(r.get("final_score")) for r in trows]
        scores = [s for s in scores if s is not None]
        med = median(scores)
        if scores and med is not None:
            rec["best_final_score"] = round(max(scores), 6)
            rec["median_final_score_ranked"] = round(med, 6)
        else:
            gaps.append({"target": target, "column": "best_final_score",
                         "reason": "no parseable final_score on any ranked row",
                         "owning_writer": ""})

        top10 = sorted(trows, key=lambda r: int(r.get("rank") or 10 ** 9))[:10]
        if top10:
            rec["pose_check_pass_rate_top10"] = round(
                sum(1 for r in top10 if parse_bool(r.get("pose_PASS"))) / len(top10), 4)

        backbones = Counter(r.get("root_backbone_id") for r in trows)
        clusters = Counter(r.get("tm90_cluster_id") for r in trows)
        methods = Counter(r.get("structure_method") for r in trows)
        rec["n_distinct_root_backbones"] = len(backbones)
        rec["max_seqs_per_root_backbone"] = max(backbones.values()) if backbones else 0
        rec["n_tm90_clusters"] = len(clusters)
        rec["max_tm90_cluster_size"] = max(clusters.values()) if clusters else 0
        rec["n_structure_methods"] = len(methods)
        rec["top_method_share"] = round(max(methods.values()) / len(trows), 4) if methods else 0.0
        rec["n_non_all_alpha"] = sum(1 for r in trows
                                     if (r.get("fold_class") or "") == "not_all_alpha")

        seqs = [(r.get("sequence") or "").strip().upper() for r in trows]
        if len(seqs) > 1:
            best = min(levenshtein(seqs[i], seqs[j])
                       for i in range(len(seqs)) for j in range(i + 1, len(seqs)))
            rec["min_pairwise_editdist"] = best
        else:
            rec["min_pairwise_editdist"] = 0

        if target in wallclock:
            rec["wallclock_hours_active_compute"] = float(wallclock[target])
        else:
            gaps.append({"target": target, "column": "wallclock_hours_active_compute",
                         "reason": "not derivable from the sheet or the minimal ledger "
                                   "schema; supply it with --wallclock from scheduler "
                                   "accounting",
                         "owning_writer": ""})

        out_rows.append(rec)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for rec in out_rows:
            writer.writerow(rec)

    if gaps:
        with open(args.gaps, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["target", "column", "reason",
                                                    "owning_writer"])
            writer.writeheader()
            writer.writerows(gaps)

    print("wrote {} ({} target rows)".format(args.out, len(out_rows)))
    if gaps:
        print("wrote {} ({} gap rows); every gap is a defect to remediate before "
              "close-out, not a value to leave empty".format(args.gaps, len(gaps)))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
