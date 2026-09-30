#!/usr/bin/env python3
"""Validate a design sheet against the frozen schema.

Turns the sheet-writer invariants from references/deliverables-spec.md into a
runnable check. Standard library only, so it runs anywhere the campaign runs.

    python check_design_sheet.py --sheet design_sheet.csv \
        --schema sheet_schema.json --policy scoring_policy.yaml \
        --normalization score_normalization.json

Exit code 0 when there are no errors, 1 otherwise. Warnings never fail the run;
they are things a human should look at.
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required; install binder-design-campaign/requirements.txt") from exc

NULL_STRINGS = {"", "na", "n/a", "none", "null", "pending", "nan"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append((where, msg))

    def warn(self, where, msg):
        self.warnings.append((where, msg))

    def emit(self):
        for where, msg in self.warnings:
            print("WARN  {}: {}".format(where, msg))
        for where, msg in self.errors:
            print("ERROR {}: {}".format(where, msg))
        print("")
        print("{} error(s), {} warning(s)".format(len(self.errors), len(self.warnings)))
        return 1 if self.errors else 0


def is_null(value):
    return value is None or str(value).strip().lower() in NULL_STRINGS


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_bool(value):
    v = str(value).strip().lower()
    if v in ("true", "1", "yes", "y", "t", "pass"):
        return True
    if v in ("false", "0", "no", "n", "f", "fail"):
        return False
    return None


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


ARM_PREFIXES = ("ipsae_", "sc_dockq_", "n_seeds_", "predicted_structure_path_",
                "ipsae_offtarget_", "selectivity_delta_")


def arm_of(name, arms):
    """The ranking arm a column belongs to, or None if it is not per-arm.

    Arm names come from the schema's ranking_arms, never from a hardcoded list,
    so a campaign that renamed or substituted an arm is checked against its own
    instrument rather than against the default one.
    """
    for prefix in ARM_PREFIXES:
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            return suffix if suffix in arms else "__unknown__"
    return None


def expected_columns(schema):
    """Schema columns, keeping only the per-arm columns for live ranking arms."""
    arms = schema.get("ranking_arms", [])
    cols = []
    for col in schema["columns"]:
        arm = arm_of(col["name"], arms)
        if arm is None or arm in arms:
            cols.append(col)
    return cols


def check_columns(rows, cols, schema, rep):
    if not rows:
        rep.error("sheet", "no data rows")
        return
    present = set(rows[0].keys())
    for col in cols:
        if col["name"] not in present:
            rep.error("columns", "missing required column '{}'".format(col["name"]))
    known = {c["name"] for c in schema["columns"]}
    known |= {c["name"] for c in schema.get("counter_screen_columns", [])}
    known |= {c["name"] for c in schema.get("oligomeric_target_columns", [])}
    for name in sorted(present - known):
        rep.warn("columns", "unrecognised column '{}' (not in the frozen schema)".format(name))


def check_cells(rows, cols, schema, rep):
    enums = schema.get("enums", {})
    mandatory = set(schema.get("mandatory_nonnull", []))
    sentinel_cfg = schema.get("sentinel_check", {})
    sentinels = set(sentinel_cfg.get("values", []))
    sentinel_severity = sentinel_cfg.get("severity", "warn")

    by_name = {c["name"]: c for c in cols}

    for idx, row in enumerate(rows, start=2):  # header is line 1
        rid = row.get("design_id") or "line {}".format(idx)
        where = "row {}".format(rid)

        for name in mandatory:
            if name not in row:
                continue
            if is_null(row[name]):
                rep.error(where, "mandatory_nonnull column '{}' is null".format(name))

        for name, col in by_name.items():
            if name not in row:
                continue
            raw = row[name]
            if is_null(raw):
                if not col.get("nullable") and name not in mandatory:
                    rep.warn(where, "column '{}' is null".format(name))
                continue

            dtype = col.get("dtype")
            value = None
            if dtype == "float":
                value = parse_float(raw)
                if value is None:
                    rep.error(where, "column '{}' is not a float: {!r}".format(name, raw))
                    continue
                if math.isnan(value):
                    continue
            elif dtype == "int":
                value = parse_int(raw)
                if value is None:
                    rep.error(where, "column '{}' is not an int: {!r}".format(name, raw))
                    continue
            elif dtype == "bool":
                if parse_bool(raw) is None:
                    rep.error(where, "column '{}' is not a boolean: {!r}".format(name, raw))
                    continue
            elif dtype == "enum":
                allowed = enums.get(col.get("enum"), [])
                if str(raw) not in allowed:
                    rep.error(where, "column '{}' value {!r} is not in the frozen enum".format(name, raw))
                    continue
            elif dtype == "str":
                regex = col.get("regex")
                if regex:
                    import re
                    if not re.match(regex, str(raw)):
                        rep.error(where, "column '{}' fails pattern {}".format(name, regex))

            if value is not None:
                if "min" in col and value < col["min"]:
                    rep.error(where, "column '{}' = {} is below min {}".format(name, value, col["min"]))
                if "max" in col and value > col["max"]:
                    rep.error(where, "column '{}' = {} is above max {}".format(name, value, col["max"]))

            if col.get("score") and sentinels:
                fv = parse_float(raw)
                if fv is not None and fv in sentinels:
                    msg = "score column '{}' holds the sentinel-like value {}; a missing score must be NaN".format(name, fv)
                    (rep.error if sentinel_severity == "error" else rep.warn)(where, msg)


def check_missing_metrics(rows, cols, schema, rep):
    """Every NaN carries a reason, and every reason names a real NaN.

    NaN alone says a number is absent. It does not say whether the arm was
    never dispatched, errored, cannot represent this system, or scored the
    wrong molecule - and those four call for four different responses in the
    next round.
    """
    cfg = schema.get("missing_metrics_check")
    if not cfg:
        return
    column = cfg.get("column", "missing_metrics")
    allowed = set(schema.get("enums", {}).get(cfg.get("enum", ""), []))
    severity = cfg.get("severity", "error")
    report = rep.error if severity == "error" else rep.warn
    score_cols = [c["name"] for c in cols if c.get("score")]

    for row in rows:
        if column not in row:
            return  # column absent entirely; check_columns already said so
        where = "row {}".format(row.get("design_id"))

        declared = {}
        raw = (row.get(column) or "").strip()
        if raw:
            for item in raw.split(";"):
                item = item.strip()
                if not item:
                    continue
                if "=" not in item:
                    report(where, "{} entry {!r} is not metric=REASON".format(column, item))
                    continue
                metric, reason = (part.strip() for part in item.split("=", 1))
                if allowed and reason not in allowed:
                    report(where, "{} reason {!r} is not in the frozen enum".format(column, reason))
                if metric not in row:
                    report(where, "{} names {!r}, which is not a column".format(column, metric))
                    continue
                declared[metric] = reason

        actually_missing = set()
        for name in score_cols:
            if name not in row:
                continue
            value = parse_float(row[name])
            if is_null(row[name]) or (value is not None and math.isnan(value)):
                actually_missing.add(name)

        for metric in sorted(set(declared) - actually_missing):
            report(where, "{} claims {!r} is missing, but it carries a value"
                   .format(column, metric))
        for metric in sorted(actually_missing - set(declared)):
            report(where, "{} is NaN with no reason in {}; record NOT_RUN, FAILED, "
                          "UNSUPPORTED or CONSTRUCT_FAIL".format(metric, column))


def check_uniqueness(rows, rep):
    seen = {}
    for row in rows:
        did = row.get("design_id")
        if did in seen:
            rep.error("design_id", "duplicate design_id {!r}".format(did))
        seen[did] = True


def check_per_target(rows, schema, rep):
    n_expected = schema.get("designs_per_target")
    tier = schema.get("final_seed_tier", 5)
    caps = schema.get("selection_caps", {})
    min_dist = caps.get("min_levenshtein_between_rows", 6)

    by_target = defaultdict(list)
    for row in rows:
        by_target[row.get("target")].append(row)

    for target, trows in sorted(by_target.items()):
        where = "target {}".format(target)

        if n_expected and len(trows) != n_expected:
            rep.warn(where, "{} rows, schema expects {} (shipping fewer is allowed "
                            "only when stated in the sheet and the report)"
                     .format(len(trows), n_expected))

        ranks = [parse_int(r.get("rank")) for r in trows]
        good_ranks = sorted(r for r in ranks if r is not None)
        if len(good_ranks) != len(ranks):
            rep.error(where, "at least one row has an unparseable rank")
        elif good_ranks != list(range(1, len(trows) + 1)):
            rep.error(where, "ranks are not a contiguous 1..N block: {}".format(good_ranks))

        ordered = sorted(trows, key=lambda r: parse_int(r.get("rank")) or 0)
        prev_key = None
        for row in ordered:
            n_seeds = parse_int(row.get("n_seeds")) or 0
            full = 1 if n_seeds >= tier else 0
            pose = 1 if parse_bool(row.get("pose_PASS")) else 0
            z = parse_float(row.get("rank_zscore"))
            if z is None or math.isnan(z):
                rep.error("row {}".format(row.get("design_id")), "rank_zscore is not a usable number")
                continue
            key = (full, pose, z)
            if prev_key is not None and key > prev_key:
                rep.error(where, "row {} violates the rank order key "
                                 "(full_seeds, pose_PASS, rank_zscore) = {} follows {}"
                          .format(row.get("design_id"), key, prev_key))
            prev_key = key

        seqs = [(r.get("design_id"), (r.get("sequence") or "").strip().upper()) for r in trows]
        seen = {}
        for did, seq in seqs:
            if seq in seen:
                rep.error(where, "rows {} and {} ship an identical sequence".format(seen[seq], did))
            seen[seq] = did
        for i in range(len(seqs)):
            for j in range(i + 1, len(seqs)):
                d = levenshtein(seqs[i][1], seqs[j][1])
                if 0 < d < min_dist:
                    rep.error(where, "rows {} and {} are {} edits apart (minimum is {})"
                              .format(seqs[i][0], seqs[j][0], d, min_dist))

        below = [r for r in trows if (parse_int(r.get("n_seeds")) or 0) < tier]
        if below:
            rep.warn(where, "{} row(s) below the final seed tier of {}; each must be "
                            "disclosed with its actual n_seeds and a logged top-up attempt"
                     .format(len(below), tier))

        for row in trows:
            if is_null(row.get("pose_dockq")):
                rep.error("row {}".format(row.get("design_id")),
                          "pose_dockq is null; it is never relaxed and the row is not rank-eligible")
            fv = parse_float(row.get("final_score"))
            if fv is None or math.isnan(fv):
                rep.error("row {}".format(row.get("design_id")),
                          "final_score is null or NaN; it is never relaxed")


def check_scoring(rows, schema, policy, normalization, rep):
    """Recompute the summary columns from the frozen raw terms and pool stats."""
    if not isinstance(policy, dict) or not policy.get("frozen_at_utc"):
        rep.error("policy", "scoring policy has no frozen_at_utc")
        return
    if not isinstance(normalization, dict) or not normalization.get("pool_id"):
        rep.error("normalization", "full scored-pool identity is missing")
        return
    arms = schema.get("ranking_arms", [])
    policy_arms = [arm.get("name") for arm in policy.get("arms", [])]
    if not arms or arms != policy_arms:
        rep.error("policy", "ranking_arms differ from the frozen scoring policy")
        return
    terms = policy.get("terms", [])
    if (not terms or any(term.get("weight", 0) <= 0 or
                         term.get("per_arm") is not True or
                         not term.get("column_prefix") for term in terms)):
        rep.error("policy", "scoring terms or weights are invalid")
        return
    counter = policy.get("counter_screen", {})
    targets = normalization.get("targets", {})
    for row in rows:
        target = row.get("target")
        where = "row {}".format(row.get("design_id"))
        stats = targets.get(target, {}).get("terms", {})
        values = []
        weighted_z = []
        for arm in arms:
            for term in terms:
                name = "{}_{}".format(term.get("column_prefix", term["metric"]), arm)
                val = parse_float(row.get(name))
                if val is None or not math.isfinite(val):
                    rep.error(where, "ranking term {} is absent or non-finite".format(name))
                    continue
                values.append(val)
                summary = stats.get(name, {})
                mu = summary.get("mean")
                sd = summary.get("sd")
                if (not isinstance(mu, (int, float)) or
                        not isinstance(sd, (int, float)) or
                        not math.isfinite(mu) or not math.isfinite(sd) or sd <= 0):
                    rep.error(where, "{} has no valid full-pool normalization".format(name))
                    continue
                weighted_z.append(((val - mu) / sd, term["weight"]))
            if counter.get("enabled"):
                on = parse_float(row.get("ipsae_{}".format(arm)))
                off = parse_float(row.get("ipsae_offtarget_{}".format(arm)))
                delta = parse_float(row.get("selectivity_delta_{}".format(arm)))
                if any(v is None or not math.isfinite(v) for v in (on, off, delta)):
                    rep.error(where, "counter-screen values for {} are incomplete".format(arm))
                    continue
                if not math.isclose(delta, on - off, abs_tol=1e-5):
                    rep.error(where, "selectivity_delta_{} does not equal on minus off".format(arm))
                name = "selectivity_delta_{}".format(arm)
                values.append(delta)
                summary = stats.get(name, {})
                mu, sd = summary.get("mean"), summary.get("sd")
                if (not isinstance(mu, (int, float)) or
                        not isinstance(sd, (int, float)) or
                        not math.isfinite(mu) or not math.isfinite(sd) or sd <= 0):
                    rep.error(where, "{} has no valid full-pool normalization".format(name))
                else:
                    weighted_z.append(((delta - mu) / sd, counter["term_weight"]))
        expected_count = len(arms) * (len(terms) + bool(counter.get("enabled")))
        if len(values) != expected_count or len(weighted_z) != expected_count:
            continue
        expected_final = sum(values) / len(values)
        recorded_final = parse_float(row.get("final_score"))
        if (recorded_final is None or not math.isfinite(recorded_final) or
                not math.isclose(recorded_final, expected_final, abs_tol=1e-5)):
            rep.error(where, "final_score differs from frozen raw-term mean {:.6f}"
                      .format(expected_final))
        expected_z = sum(z * weight for z, weight in weighted_z) / sum(
            weight for _, weight in weighted_z)
        recorded_z = parse_float(row.get("rank_zscore"))
        if (recorded_z is None or not math.isfinite(recorded_z) or
                not math.isclose(recorded_z, expected_z, abs_tol=1e-4)):
            rep.error(where, "rank_zscore differs from frozen weighted z-score {:.6f}"
                      .format(expected_z))
        pose_terms = [parse_float(row.get("sc_dockq_{}".format(arm))) for arm in arms]
        if all(value is not None and math.isfinite(value) for value in pose_terms):
            expected_pose = min(pose_terms)
            recorded_pose = parse_float(row.get("pose_dockq"))
            if (recorded_pose is None or not math.isfinite(recorded_pose) or
                    not math.isclose(recorded_pose, expected_pose, abs_tol=1e-5)):
                rep.error(where, "pose_dockq differs from minimum arm sc_dockq {:.6f}"
                          .format(expected_pose))
            threshold = schema.get("pose_dockq_threshold")
            if isinstance(threshold, (int, float)):
                expected_pass = expected_pose >= threshold
                if parse_bool(row.get("pose_PASS")) is not expected_pass:
                    rep.error(where, "pose_PASS disagrees with frozen pose threshold")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", required=True, help="design sheet CSV")
    ap.add_argument("--schema", required=True, help="frozen sheet_schema.json")
    ap.add_argument("--policy", required=True, help="frozen scoring_policy.yaml")
    ap.add_argument("--normalization", required=True,
                    help="full scored-pool means and standard deviations")
    args = ap.parse_args()

    with open(args.schema, encoding="utf-8") as fh:
        schema = json.load(fh)
    with open(args.sheet, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    with open(args.policy, encoding="utf-8") as fh:
        policy = yaml.safe_load(fh)
    with open(args.normalization, encoding="utf-8") as fh:
        normalization = json.load(fh)

    rep = Report()
    cols = expected_columns(schema)

    check_columns(rows, cols, schema, rep)
    if rows:
        check_cells(rows, cols, schema, rep)
        check_missing_metrics(rows, cols, schema, rep)
        check_uniqueness(rows, rep)
        check_per_target(rows, schema, rep)
        check_scoring(rows, schema, policy, normalization, rep)

    print("checked {} row(s) from {}".format(len(rows), args.sheet))
    sys.exit(rep.emit())


if __name__ == "__main__":
    main()
