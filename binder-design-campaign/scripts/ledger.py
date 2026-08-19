#!/usr/bin/env python3
"""Campaign ledger: append-only JSONL, one subfile per writer.

Every count reported anywhere in the campaign is an aggregation over this tree,
computed at report time. Never a number carried in memory, never a count of
files in a directory.

One subfile per writer is not a style choice: concurrent appends to a single
shared file on a network filesystem are not atomic and silently clobber.

Usage:

    # one row per job completion
    python ledger.py append --root <campaign_root> --writer gen-worker-03 \
        --job-id J1234 --target EGFR --stage gen_screen \
        --structure-method rfdiffusion --n-generated 512 --n-scored 512 \
        --gpu-seconds 4210

    # one row at dispatch time, on every dispatch path
    python ledger.py dispatch --root <campaign_root> --writer gen-worker-03 \
        --job-id J1234 --target EGFR --stage gen_screen --gpu-type A100-80GB

    # aggregate; this is the only sanctioned source of campaign totals
    python ledger.py totals --root <campaign_root>
    python ledger.py totals --root <campaign_root> --json

    # deviations
    python ledger.py deviate --root <campaign_root> --writer orchestrator \
        --kind TOOL_RUNTIME_FAIL --target EGFR \
        --what "boltzgen contributed 0 backbones" --action "budget moved to pxdesign"

    # rejections: why a design never reached the scoring pool
    python ledger.py reject --root <campaign_root> --writer gen-worker-03 \
        --design-id EGFR_rfdiffusion_00412 --target EGFR --stage gen_screen \
        --gate novelty --reason DIVERSITY_FAIL \
        --detail "62% identity over 71% coverage to UniRef90 A0A123"

    # aggregate rejections by gate and reason; this table shapes the next round
    python ledger.py rejects --root <campaign_root>

    python ledger.py --list-failure-types

Idempotency: append is keyed on (job_id, stage). Re-appending the same pair is
ignored, so a re-run cannot double-count.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

LEDGER_DIR = "ledger"
DISPATCH_DIR = os.path.join("ledger", "job_metadata")
REJECT_DIR = os.path.join("ledger", "rejects")
DEVIATIONS = os.path.join("ledger", "deviations.jsonl")

# Campaign failure vocabulary. Shared by `deviate --kind` and `reject --reason`
# so that failures aggregate instead of accumulating as free text: the point of
# a controlled list is that "why did this campaign underperform" is a GROUP BY,
# not a reading exercise. Ordered roughly from input to selection.
#
# Every code names something this campaign can OBSERVE. Assay outcomes -
# expression, solubility, binding, specificity, activity - are deliberately
# absent: the protocol ends at the design sheet and never sees them. Prior
# results from an earlier round enter as operator input at G0, in the
# operator's own words, not as codes in this ledger.
FAILURE_TYPES = [
    "INPUT_ERROR",           # malformed or missing input
    "BIOLOGY_UNRESOLVED",    # the dossier could not settle a load-bearing fact
    "CONSTRUCT_MISMATCH",    # scored molecule differs from the frozen construct
    "TOOL_INSTALL_FAIL",     # environment or weights would not build
    "TOOL_RUNTIME_FAIL",     # ran and errored
    "PARSE_FAIL",            # output unreadable by the downstream adapter
    "UNSUPPORTED_CHEMISTRY", # tool cannot represent a required cofactor or partner
    "VALIDATION_FAIL",       # G3: fold recapitulation or control separation
    "GENERATION_FAIL",       # no usable backbone or sequence produced
    "STRUCTURE_FAIL",        # monomer foldability or structural plausibility
    "INTERFACE_FAIL",        # pose check or interface metric
    "PROPERTY_FAIL",         # liability: cysteines, homopolymers, hydrophobic patches
    "DIVERSITY_FAIL",        # novelty, redundancy, or a selection cap
    "BUDGET_STOP",           # stopped on cost or wall-clock, not on the science
    "DATA_INTEGRITY_FAIL",   # a number that cannot be traced to an artifact
]


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def writer_path(root, subdir, writer):
    d = os.path.join(root, subdir)
    os.makedirs(d, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in writer)
    return os.path.join(d, safe + ".jsonl")


def read_rows(root, subdir):
    d = os.path.join(root, subdir)
    if not os.path.isdir(d):
        return []
    rows = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    print("WARN malformed JSON at {}:{}".format(path, line_no),
                          file=sys.stderr)
    return rows


def append_row(path, row):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def cmd_append(args):
    existing = {(r.get("job_id"), r.get("stage")) for r in read_rows(args.root, LEDGER_DIR)}
    key = (args.job_id, args.stage)
    if key in existing:
        print("already recorded, ignoring: job_id={} stage={}".format(*key))
        return 0
    row = {
        "ts_utc": utcnow(),
        "job_id": args.job_id,
        "target": args.target,
        "stage": args.stage,
        "structure_method": args.structure_method,
        "n_generated": args.n_generated,
        "n_scored": args.n_scored,
        "gpu_seconds": args.gpu_seconds,
        "writer_id": args.writer,
    }
    append_row(writer_path(args.root, LEDGER_DIR, args.writer), row)
    print("appended {} {}".format(args.job_id, args.stage))
    return 0


def cmd_dispatch(args):
    row = {
        "job_id": args.job_id,
        "campaign": args.campaign,
        "target": args.target,
        "stage": args.stage,
        "submitted_at_utc": utcnow(),
        "gpu_type": args.gpu_type,
        "writer_id": args.writer,
    }
    append_row(writer_path(args.root, DISPATCH_DIR, args.writer), row)
    print("dispatch recorded {}".format(args.job_id))
    return 0


def check_failure_type(value):
    if value not in FAILURE_TYPES:
        print("ERROR {!r} is not in the campaign failure vocabulary.".format(value),
              file=sys.stderr)
        print("Use one of: " + ", ".join(FAILURE_TYPES), file=sys.stderr)
        return False
    return True


def cmd_reject(args):
    """One row per design that never reached the scoring pool."""
    if not check_failure_type(args.reason):
        return 1
    append_row(writer_path(args.root, REJECT_DIR, args.writer), {
        "ts_utc": utcnow(),
        "design_id": args.design_id,
        "target": args.target,
        "stage": args.stage,
        "gate": args.gate,
        "reason_code": args.reason,
        "detail": args.detail,
        "writer_id": args.writer,
    })
    print("rejection logged: {} {}".format(args.design_id, args.reason))
    return 0


def cmd_rejects(args):
    """Aggregate rejections. The shape of this table decides the next round."""
    rows = read_rows(args.root, REJECT_DIR)
    if not rows:
        print("no rejection rows. If filters have run, that is a fail-loud "
              "condition, not a zero to report.", file=sys.stderr)
        return 1
    by_target = defaultdict(lambda: defaultdict(int))
    for r in rows:
        key = "{}/{}".format(r.get("gate") or "?", r.get("reason_code") or "?")
        by_target[r.get("target") or "_campaign"][key] += 1
    print("rejection rows: {}".format(len(rows)))
    for target in sorted(by_target):
        print("")
        print("{}:".format(target))
        for key, n in sorted(by_target[target].items(), key=lambda kv: -kv[1]):
            print("  {:<40} {}".format(key, n))
    return 0


def cmd_deviate(args):
    if not check_failure_type(args.kind):
        return 1
    path = os.path.join(args.root, DEVIATIONS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    append_row(path, {
        "at_utc": utcnow(),
        "kind": args.kind,
        "target": args.target,
        "what": args.what,
        "action": args.action,
    })
    print("deviation logged: {}".format(args.kind))
    return 0


def aggregate(rows):
    per_target = defaultdict(lambda: {"generated": 0, "screened": 0,
                                      "ranked": 0, "intermediate": 0,
                                      "gpu_seconds": 0.0, "jobs": 0})
    per_method = defaultdict(lambda: defaultdict(int))
    for r in rows:
        t = r.get("target") or "_campaign"
        agg = per_target[t]
        agg["jobs"] += 1
        agg["generated"] += int(r.get("n_generated") or 0)
        agg["gpu_seconds"] += float(r.get("gpu_seconds") or 0)
        stage = r.get("stage")
        n_scored = int(r.get("n_scored") or 0)
        if stage == "screen" or stage == "gen_screen":
            agg["screened"] += n_scored
        elif stage == "final":
            agg["ranked"] += n_scored
        elif stage == "intermediate":
            agg["intermediate"] += n_scored
        m = r.get("structure_method")
        if m:
            per_method[t][m] += int(r.get("n_generated") or 0)
    return per_target, per_method


def cmd_totals(args):
    rows = read_rows(args.root, LEDGER_DIR)
    if not rows:
        print("ERROR ledger is empty. If a wave has completed, this is a "
              "fail-loud condition, not a zero to report.", file=sys.stderr)
        return 1
    per_target, per_method = aggregate(rows)

    if args.json:
        print(json.dumps({"per_target": per_target,
                          "per_method": {k: dict(v) for k, v in per_method.items()},
                          "n_rows": len(rows),
                          "as_of_utc": utcnow()},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print("ledger rows: {}".format(len(rows)))
    print("")
    header = "{:<20} {:>12} {:>12} {:>10} {:>12} {:>7}".format(
        "target", "generated", "screened", "ranked", "gpu_hours", "jobs")
    print(header)
    print("-" * len(header))
    tot = defaultdict(float)
    for t in sorted(per_target):
        a = per_target[t]
        print("{:<20} {:>12} {:>12} {:>10} {:>12.1f} {:>7}".format(
            t[:20], a["generated"], a["screened"], a["ranked"],
            a["gpu_seconds"] / 3600.0, a["jobs"]))
        for k in ("generated", "screened", "ranked", "gpu_seconds", "jobs"):
            tot[k] += a[k]
    print("-" * len(header))
    print("{:<20} {:>12} {:>12} {:>10} {:>12.1f} {:>7}".format(
        "TOTAL", int(tot["generated"]), int(tot["screened"]), int(tot["ranked"]),
        tot["gpu_seconds"] / 3600.0, int(tot["jobs"])))

    print("")
    print("backbones per (target, structure_method):")
    for t in sorted(per_method):
        for m in sorted(per_method[t]):
            print("  {:<20} {:<24} {}".format(t[:20], m[:24], per_method[t][m]))
    return 0


def cmd_backlog(args):
    """Generation must not outrun scoring. Mirrors the submit-gate rule."""
    rows = read_rows(args.root, LEDGER_DIR)
    per_target, _ = aggregate(rows)
    blocked = []
    for t, a in sorted(per_target.items()):
        gen, scr = a["generated"], a["screened"]
        if gen >= 200 and gen > 2 * max(scr, 50):
            blocked.append(t)
            print("BLOCK {}: generated={} screened={} -> GEN_BACKLOG_CAP".format(t, gen, scr))
        else:
            print("ok    {}: generated={} screened={}".format(t, gen, scr))
    return 1 if blocked else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-failure-types", action="store_true",
                    help="print the campaign failure vocabulary and exit")
    if "--list-failure-types" in sys.argv:
        for name in FAILURE_TYPES:
            print(name)
        sys.exit(0)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--root", required=True, help="campaign root directory")

    p = sub.add_parser("append", help="record one job completion")
    common(p)
    p.add_argument("--writer", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--target", default=None)
    p.add_argument("--stage", required=True,
                   choices=["setup", "bringup", "generate", "gen_screen", "screen",
                            "intermediate", "final", "optimize", "audit"])
    p.add_argument("--structure-method", default=None)
    p.add_argument("--n-generated", type=int, default=0)
    p.add_argument("--n-scored", type=int, default=0)
    p.add_argument("--gpu-seconds", type=float, default=0.0)
    p.set_defaults(func=cmd_append)

    p = sub.add_parser("dispatch", help="record one dispatch, before the job runs")
    common(p)
    p.add_argument("--writer", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--campaign", default=None)
    p.add_argument("--target", default=None)
    p.add_argument("--stage", required=True)
    p.add_argument("--gpu-type", default=None)
    p.set_defaults(func=cmd_dispatch)

    p = sub.add_parser("deviate", help="log a deviation")
    common(p)
    p.add_argument("--writer", required=True)
    p.add_argument("--kind", required=True, choices=FAILURE_TYPES,
                   metavar="FAILURE_TYPE")
    p.add_argument("--target", default=None)
    p.add_argument("--what", required=True)
    p.add_argument("--action", required=True)
    p.set_defaults(func=cmd_deviate)

    p = sub.add_parser("reject", help="log one design filtered out before scoring")
    common(p)
    p.add_argument("--writer", required=True)
    p.add_argument("--design-id", required=True)
    p.add_argument("--target", default=None)
    p.add_argument("--stage", default=None)
    p.add_argument("--gate", required=True,
                   help="which filter rejected it: novelty, liability, "
                        "monomer_foldability, structural_plausibility, redundancy")
    p.add_argument("--reason", required=True, choices=FAILURE_TYPES,
                   metavar="FAILURE_TYPE")
    p.add_argument("--detail", default="")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("rejects", help="aggregate rejections by gate and reason")
    common(p)
    p.set_defaults(func=cmd_rejects)

    p = sub.add_parser("totals", help="aggregate the ledger")
    common(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_totals)

    p = sub.add_parser("backlog", help="check the generation-vs-scoring backlog cap")
    common(p)
    p.set_defaults(func=cmd_backlog)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
