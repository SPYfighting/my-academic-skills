#!/usr/bin/env python3
"""Self-check for the binder-design-campaign skill.

Exercises every script in this skill against the bundled fixture, twice: once
on clean input, expecting success, and once on deliberately corrupted input,
expecting each validator to fail and name the problem. A check that never fails
is broken, so both halves have to pass.

    python scripts/selfcheck.py            # from the skill directory
    python scripts/selfcheck.py --verbose  # show each script's own output

The repository runner at ../check.py finds this file by convention and runs it
along with every other skill's, so adding a skill needs no change there.

The checker dependency is declared in ../requirements.txt. Exit code 0 when
everything behaves as expected.
"""

import argparse
import csv
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(SCRIPTS)
FIXTURE = os.path.join(SKILL, "examples")
SHEET = os.path.join(FIXTURE, "design_sheet.csv")
SCHEMA = os.path.join(FIXTURE, "sheet_schema.json")
POLICY = os.path.join(FIXTURE, "scoring_policy.yaml")
NORMALIZATION = os.path.join(FIXTURE, "score_normalization.json")
SCORE_ARGS = ["--policy", POLICY, "--normalization", NORMALIZATION]

# Corruptions injected into a copy of the fixture, and the validator expected
# to catch each. Keep this list in step with the checks themselves.
CORRUPTIONS = [
    ("duplicate sequence",            "check_design_sheet.py"),
    ("rank ordering violated",        "check_design_sheet.py"),
    ("summary score altered",         "check_design_sheet.py"),
    ("mandatory pose_dockq nulled",   "check_design_sheet.py"),
    ("sentinel in a score column",    "check_design_sheet.py"),
    ("value outside the frozen enum", "check_design_sheet.py"),
    ("NaN with no reason recorded",   "check_design_sheet.py"),
    ("reason claiming a live value",  "check_design_sheet.py"),
    ("diversity cap exceeded",        "check_diversity.py"),
]


def run(script, args, verbose):
    cmd = [sys.executable, os.path.join(SCRIPTS, script)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if verbose:
        print("\n$ " + " ".join(cmd))
        print(proc.stdout.rstrip())
        if proc.stderr.strip():
            print(proc.stderr.rstrip(), file=sys.stderr)
    return proc


def corrupt(source, dest):
    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    first = [r for r in rows if r["target"] == rows[0]["target"]]
    second_target = next(r["target"] for r in rows if r["target"] != rows[0]["target"])
    first[0]["sc_dockq_ef2fast"] = "NaN"        # missing, with no reason given
    first[1]["sequence"] = first[0]["sequence"]
    first[2]["rank_zscore"] = "9.9"
    first[2]["final_score"] = "0.99"
    first[3]["pose_dockq"] = ""
    first[4]["ipsae_ptxv2"] = "0.0"
    first[5]["structure_method"] = "not_a_frozen_token"
    for row in rows:
        if row["target"] == second_target:
            row["root_backbone_id"] = "collapsed"
    second = [r for r in rows if r["target"] == second_target]
    second[0]["missing_metrics"] = "ipsae_ptxv2=NOT_RUN"   # but it holds a value
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    failures = []
    tmp = tempfile.mkdtemp(prefix="skills-selfcheck-")
    try:
        print("clean fixture, expecting every script to succeed")
        clean = [
            ("check_design_sheet.py", ["--sheet", SHEET, "--schema", SCHEMA] + SCORE_ARGS),
            ("check_diversity.py",    ["--sheet", SHEET, "--schema", SCHEMA]),
            ("ledger.py",             ["totals", "--root", FIXTURE]),
            ("ledger.py",             ["backlog", "--root", FIXTURE]),
            ("ledger.py",             ["rejects", "--root", FIXTURE]),
            ("make_scoreboard.py",    ["--sheet", SHEET, "--root", FIXTURE,
                                       "--out", os.path.join(tmp, "scoreboard.csv"),
                                       "--gaps", os.path.join(tmp, "gaps.csv"),
                                       "--wallclock",
                                       os.path.join(FIXTURE, "wallclock_hours.json")]),
        ]
        for script, argv in clean:
            proc = run(script, argv, args.verbose)
            label = "{} {}".format(script, argv[0] if not argv[0].startswith("--") else "")
            if proc.returncode == 0:
                print("  ok    {}".format(label.strip()))
            else:
                print("  FAIL  {} exited {}".format(label.strip(), proc.returncode))
                failures.append("{} failed on the clean fixture".format(label.strip()))
                if not args.verbose:
                    print(proc.stdout.rstrip())

        print("")
        print("preflight, expecting it to proceed only when the campaign is live")
        live = os.path.join(tmp, "live")
        shutil.copytree(FIXTURE, live)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        for name, payload in (("governor.json", {"ceiling": 8, "basis": "BOOTSTRAP"}),
                              ("heartbeat.json", {"writer_id": "selfcheck"})):
            payload["set_at_utc"] = now
            with open(os.path.join(live, "state", name), "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)

        cases = [
            ("proceeds when live", ["--root", live, "--target", "EGFR", "--stage", "final"],
             0, "PREFLIGHT ok"),
            ("stands down on a gate that is not PASS",
             ["--root", live, "--target", "NO_SUCH_TARGET", "--stage", "final"],
             10, "no validation gate file"),
        ]
        halted = os.path.join(tmp, "halted")
        shutil.copytree(live, halted)
        with open(os.path.join(halted, "state", "governor.json"), "w", encoding="utf-8") as fh:
            json.dump({"ceiling": 0, "set_at_utc": now, "basis": "HALTED"}, fh, indent=2)
        cases.append(("stands down when the ceiling is zero",
                      ["--root", halted, "--target", "EGFR", "--stage", "final"],
                      10, "ceiling is not positive"))

        limited = os.path.join(tmp, "limited")
        shutil.copytree(live, limited)
        with open(os.path.join(limited, "state", "authorization.json"), "w", encoding="utf-8") as fh:
            json.dump({"authorized_through_stage": 6,
                       "allow_fold_only_instrument": False}, fh)
        cases.append(("stops beyond the authorized stage",
                      ["--root", limited, "--target", "EGFR", "--stage", "final"],
                      10, "exceeds authorization"))
        cases.append(("continues inside the authorized stage",
                      ["--root", limited, "--target", "EGFR", "--stage", "screen"],
                      0, "PREFLIGHT ok"))

        fold_only = os.path.join(tmp, "fold_only")
        shutil.copytree(live, fold_only)
        gate_path = os.path.join(fold_only, "state", "gates", "EGFR.json")
        with open(gate_path, encoding="utf-8") as fh:
            gate = json.load(fh)
        gate["evidence_level"] = "FOLD_ONLY"
        with open(gate_path, "w", encoding="utf-8") as fh:
            json.dump(gate, fh)
        cases.append(("stops on an unapproved fold-only instrument",
                      ["--root", fold_only, "--target", "EGFR", "--stage", "screen"],
                      10, "outside approved scope"))
        approved_fold_only = os.path.join(tmp, "approved_fold_only")
        shutil.copytree(fold_only, approved_fold_only)
        with open(os.path.join(approved_fold_only, "state", "authorization.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"authorized_through_stage": 10,
                       "allow_fold_only_instrument": True}, fh)
        cases.append(("allows explicitly approved fold-only exploration",
                      ["--root", approved_fold_only, "--target", "EGFR", "--stage", "screen"],
                      0, "PREFLIGHT ok"))
        cases.append(("requires a target for production",
                      ["--root", live, "--stage", "gen_screen"],
                      2, "--target is required"))

        unsupported_gate = os.path.join(tmp, "unsupported_gate")
        shutil.copytree(live, unsupported_gate)
        gate_path = os.path.join(unsupported_gate, "state", "gates", "EGFR.json")
        with open(gate_path, encoding="utf-8") as fh:
            gate = json.load(fh)
        gate["arms"] = {}
        with open(gate_path, "w", encoding="utf-8") as fh:
            json.dump(gate, fh)
        cases.append(("rejects a bare PASS without arm evidence",
                      ["--root", unsupported_gate, "--target", "EGFR", "--stage", "screen"],
                      10, "has no evidence"))

        for label, argv, expected_code, expected in cases:
            proc = run("preflight.py", argv, args.verbose)
            output = proc.stdout + proc.stderr
            if proc.returncode == expected_code and expected in output:
                print("  ok    preflight {}".format(label))
            else:
                print("  FAIL  preflight {}: exit {}, output {!r}"
                      .format(label, proc.returncode, output.strip()[:120]))
                failures.append("preflight did not {}".format(label))

        print("")
        print("corrupted fixture, expecting the validators to fail and say why")
        bad = os.path.join(tmp, "bad_sheet.csv")
        corrupt(SHEET, bad)
        for script in ("check_design_sheet.py", "check_diversity.py"):
            argv = ["--sheet", bad, "--schema", SCHEMA]
            if script == "check_design_sheet.py":
                argv += SCORE_ARGS
            proc = run(script, argv, args.verbose)
            n_errors = proc.stdout.count("ERROR ")
            if proc.returncode == 1 and n_errors:
                print("  ok    {} caught {} error(s)".format(script, n_errors))
            else:
                print("  FAIL  {} exited {} with {} error line(s); a check that "
                      "never fails is broken".format(script, proc.returncode, n_errors))
                failures.append("{} did not reject the corrupted fixture".format(script))

        with open(SHEET, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        rows[0]["final_score"] = "0.99"
        rows[1]["rank_zscore"] = "0.99"
        isolated = os.path.join(tmp, "wrong_summary.csv")
        with open(isolated, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        proc = run("check_design_sheet.py",
                   ["--sheet", isolated, "--schema", SCHEMA] + SCORE_ARGS,
                   args.verbose)
        if (proc.returncode == 1 and "final_score differs" in proc.stdout and
                "rank_zscore differs" in proc.stdout):
            print("  ok    check_design_sheet.py rejects isolated summary tampering")
        else:
            failures.append("summary score arithmetic was not checked")

        print("")
        print("corruptions injected: " + ", ".join(c for c, _ in CORRUPTIONS))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    if failures:
        for f in failures:
            print("FAILED: " + f)
        return 1
    print("all checks behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
