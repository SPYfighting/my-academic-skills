# Minimal campaign fixture

A deliberately tiny campaign laid out the way a real one is, so the scripts in
`skills/binder-design-campaign/scripts/` have something to run against and so
you can see the file shapes before building your own.

Two targets, six ranked rows each. The sequences are random and the numbers are
synthetic. **Nothing here is scientific data** — it exists to exercise the
checks.

```
design_sheet.csv          12 rows, 2 targets, schema-conforming; its
                          missing_metrics column is empty because nothing is
                          missing, which is the normal case
sheet_schema.json         the frozen schema, with designs_per_target=6 and
                          final_seed_tier=3 so the fixture stays small
scoreboard.csv            derived from the sheet and the ledger
wallclock_hours.json      scheduler accounting, which the sheet cannot supply
ledger/demo-worker.jsonl  four job rows, one writer
ledger/rejects/*.jsonl    five rejected designs, by gate and reason code
state/governor.json       concurrency ceiling, read by preflight.py
state/heartbeat.json      orchestrator liveness, read by preflight.py
state/gates/*.json        the G3 validation gate files, both PASS
```

## Running against it

From the repository root:

```bash
python check.py
```

That runs every script on this fixture, then on a corrupted copy of it, and
asserts that the validators reject the corrupted one and say why. A check that
never fails is broken (`skills/binder-design-campaign/references/failure-modes.md`
§4), so both halves have to pass.

To drive one script by hand, read `check.py` for its arguments.

## A note on the timestamps

`state/governor.json` and `state/heartbeat.json` carry the moment the fixture was
committed, so `preflight.py` will stand down against them once they age past its
staleness limits — 25 minutes for the governor, 30 for the heartbeat. That is
the intended behaviour: a governor no live process refreshes is a dead governor.
`check.py` writes fresh copies into a temporary directory before testing the
proceed path, which is why it does not mutate anything here.

## Building your own

Copy `sheet_schema.json` as a starting point. Before the first production job,
set `ranking_arms` to the arms validated at G3, set `designs_per_target` and
`final_seed_tier` to the campaign's values, and replace the `structure_method`
and `seq_method` enums with the roster's tokens. Then freeze it — the schema is
not edited again once production scoring begins.
