#!/usr/bin/env python3
"""In-job dead-man switch. First executable step inside every campaign job.

Runs before any weight download or model load, costs well under a second, and
is the only control that still works when every orchestrating process is dead.
It exits 0 with a message and no work done when the campaign is halted or the
orchestrator has gone stale, so a halt binds even on jobs that were already
queued.

    python preflight.py --root <campaign_root> [--target EGFR] [--stage screen]

Exit codes:
    0  proceed, or stand down cleanly (a stood-down job is not a failed job)
    2  the campaign root is unreadable  -  treat as a configuration error

Reads, all under <campaign_root>/state/:
    governor.json    {"ceiling": int, "set_at_utc": iso8601, "basis": str}
    heartbeat.json   {"set_at_utc": iso8601}
    gates/<target>.json  {"status": "PASS" | ...}
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import NoReturn

SCORING_STAGES = {"screen", "intermediate", "final"}
GOVERNOR_STALE_MINUTES = 25
HEARTBEAT_STALE_MINUTES = 30


def stand_down(reason) -> NoReturn:
    print("PREFLIGHT stand-down: {}".format(reason))
    sys.exit(0)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--target", default=None)
    ap.add_argument("--stage", default=None)
    ap.add_argument("--require-heartbeat", action="store_true",
                    help="stand down when no heartbeat file exists at all "
                         "(use on backends with a live orchestrator)")
    args = ap.parse_args()

    state = os.path.join(args.root, "state")
    if not os.path.isdir(state):
        print("PREFLIGHT error: {} is not a directory".format(state), file=sys.stderr)
        sys.exit(2)

    governor = load_json(os.path.join(state, "governor.json"))
    if governor is None:
        stand_down("governor.json missing or unreadable")
    ceiling = governor.get("ceiling")
    if ceiling == 0:
        stand_down("ceiling is 0 (basis={})".format(governor.get("basis")))
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

    if args.stage in SCORING_STAGES and args.target:
        gate = load_json(os.path.join(state, "gates", "{}.json".format(args.target)))
        if gate is None:
            stand_down("no validation gate file for target {}".format(args.target))
        if gate.get("status") != "PASS":
            stand_down("validation gate for {} is {!r}, not PASS"
                       .format(args.target, gate.get("status")))

    print("PREFLIGHT ok (ceiling={}, governor age {:.1f} min)".format(ceiling, gov_age))
    sys.exit(0)


if __name__ == "__main__":
    main()
