#!/usr/bin/env python3
"""In-job dead-man switch. First executable step inside every campaign job.

Runs before any weight download or model load. A stand-down has a distinct
exit code so the caller cannot mistake it for permission to run the job.

    python preflight.py --root <campaign_root> --stage screen --target EGFR

Exit codes:
    0   proceed
    10  stand down without starting the job
    2   invalid arguments or missing campaign root

Reads, all under <campaign_root>/state/:
    governor.json    {"ceiling": int, "set_at_utc": iso8601, "basis": str}
    heartbeat.json   {"set_at_utc": iso8601}
    authorization.json  {"authorized_through_stage": 0..10, ...}
    gates/<target>.json  {"status": "PASS" | ...}
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import NoReturn

GATED_TARGET_STAGES = {"generate", "gen_screen", "screen", "intermediate",
                       "optimize", "final"}
STAGE_NUMBER = {
    "setup": 1, "bringup": 1,
    "generate": 6, "gen_screen": 6, "screen": 6,
    "intermediate": 7, "optimize": 7,
    "final": 8, "audit": 10,
}
GOVERNOR_STALE_MINUTES = 25
HEARTBEAT_STALE_MINUTES = 30


def stand_down(reason) -> NoReturn:
    print("PREFLIGHT stand-down: {}".format(reason), file=sys.stderr)
    sys.exit(10)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def age_minutes(iso_string):
    if not iso_string:
        return None
    try:
        stamp = datetime.fromisoformat(str(iso_string).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamp).total_seconds() / 60.0


def valid_gate(gate, target, allow_fold_only):
    """Check the recorded decision and its minimum numerical evidence."""
    if not isinstance(gate, dict) or gate.get("target") != target:
        return "gate target does not match the job target"
    if gate.get("status") != "PASS":
        return "gate status is not PASS"
    level = gate.get("evidence_level")
    if level not in ("CONTROL_SEPARATED", "FOLD_ONLY"):
        return "gate has no recognised evidence_level"
    if level == "FOLD_ONLY" and allow_fold_only is not True:
        return "fold-only instrument is outside approved scope"
    mask = gate.get("instrument_mask")
    arms = gate.get("arms")
    if not isinstance(mask, list) or not mask or len(mask) != len(set(mask)):
        return "instrument_mask is empty or contains duplicates"
    if not isinstance(arms, dict):
        return "gate has no per-arm evidence"
    for name in mask:
        arm = arms.get(name)
        if not isinstance(arm, dict):
            return "arm {} has no evidence".format(name)
        rmsd = arm.get("fold_recapitulation_ca_rmsd")
        threshold = arm.get("fold_threshold")
        if (not isinstance(rmsd, (int, float)) or
                not isinstance(threshold, (int, float)) or
                not math.isfinite(rmsd) or not math.isfinite(threshold) or
                not 0 <= rmsd <= threshold or threshold <= 0):
            return "arm {} does not meet its fold threshold".format(name)
        if level == "CONTROL_SEPARATED":
            separation = arm.get("control_separation_value")
            negatives = arm.get("negative_controls")
            if (not isinstance(separation, (int, float)) or
                    not math.isfinite(separation) or separation <= 0 or
                    not isinstance(negatives, list) or not negatives):
                return "arm {} lacks positive-control separation".format(name)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--target", default=None)
    ap.add_argument("--stage", required=True, choices=sorted(STAGE_NUMBER))
    ap.add_argument("--require-heartbeat", action="store_true",
                    help="stand down when no heartbeat file exists at all "
                         "(use on backends with a live orchestrator)")
    args = ap.parse_args()

    state = os.path.join(args.root, "state")
    if not os.path.isdir(state):
        print("PREFLIGHT error: {} is not a directory".format(state), file=sys.stderr)
        sys.exit(2)

    if args.stage in GATED_TARGET_STAGES and not args.target:
        ap.error("--target is required for target production stages")

    authorization = load_json(os.path.join(state, "authorization.json"))
    if not isinstance(authorization, dict):
        stand_down("authorization.json missing or unreadable")
    through = authorization.get("authorized_through_stage")
    if type(through) is not int or not 0 <= through <= 10:
        stand_down("authorization.json has no valid authorized_through_stage")
    if STAGE_NUMBER[args.stage] > through:
        stand_down("stage {} exceeds authorization through stage {}"
                   .format(args.stage, through))

    governor = load_json(os.path.join(state, "governor.json"))
    if governor is None:
        stand_down("governor.json missing or unreadable")
    ceiling = governor.get("ceiling")
    if type(ceiling) is not int or ceiling <= 0:
        stand_down("ceiling is not positive (basis={})".format(governor.get("basis")))
    gov_age = age_minutes(governor.get("set_at_utc"))
    if gov_age is None:
        stand_down("governor.json has no readable set_at_utc")
    if gov_age > GOVERNOR_STALE_MINUTES:
        stand_down("governor.json is {:.0f} min old (limit {}); a governor no live "
                   "process refreshes is a dead governor"
                   .format(gov_age, GOVERNOR_STALE_MINUTES))

    heartbeat = load_json(os.path.join(state, "heartbeat.json"))
    if heartbeat is None:
        if args.require_heartbeat:
            stand_down("heartbeat.json missing")
    else:
        hb_age = age_minutes(heartbeat.get("set_at_utc"))
        if hb_age is not None and hb_age > HEARTBEAT_STALE_MINUTES:
            stand_down("orchestrator heartbeat is {:.0f} min old (limit {})"
                       .format(hb_age, HEARTBEAT_STALE_MINUTES))

    if args.stage in GATED_TARGET_STAGES:
        gate = load_json(os.path.join(state, "gates", "{}.json".format(args.target)))
        if gate is None:
            stand_down("no validation gate file for target {}".format(args.target))
        gate_error = valid_gate(gate, args.target,
                                authorization.get("allow_fold_only_instrument"))
        if gate_error:
            stand_down("validation gate for {}: {}".format(args.target, gate_error))

    print("PREFLIGHT ok (ceiling={}, governor age {:.1f} min)".format(ceiling, gov_age),
          file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
