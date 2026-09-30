# Compute backends

The scientific layer never talks to a scheduler. It talks to four verbs. This
keeps the protocol portable across a university Slurm cluster, a single
workstation, and a metered cloud account, and it means a site with a different
scheduler writes one adapter instead of editing the protocol.

```
submit(job_spec) -> job_id
poll(job_id)     -> {pending | running | success | failed | timeout | cancelled}
harvest(job_id)  -> local out/ directory
append_ledger(row)
```

---

## 1. Job spec

```yaml
job_id:          <campaign-unique, deterministic from stage+target+shard>
campaign:        <campaign id>
target:          <target name, or null for campaign-wide jobs>
stage:           setup | bringup | generate | gen_screen | screen | intermediate | final | optimize | audit
method:          <token from method_vocab.json, or null>
command:         <argv list — no shell string interpolation of secrets>
environment:     <container image digest, conda env name + lockfile hash, or module list>
resources:
  gpus:          1
  gpu_type:      <e.g. A100-80GB>
  cpus:          8
  mem_gb:        64
  walltime_s:    <min(ceil(2.0 * benchmarked_p90_s), site_cap)>
inputs:          [<pinned artifact paths>]
outputs_dir:     out/
seeds:           [<distinct integers>]
depends_on:      [<job_id>, ...]
```

Rules that hold on every backend:

- **`walltime_s = min(ceil(2.0 * benchmarked_p90_s), site_cap)`.** A method
  whose benchmarked p90 exceeds half the site cap is made to fit by lowering
  its per-job batch size, not by raising the walltime.
- **Every job writes to `out/`.** End every job command with
  `mkdir -p out && cp -r <results> out/`, or write directly under `out/`.
- **A "success" job whose harvested output file count is 2 or fewer** — only
  stdout and stderr — **is a canary failure, not a success.** Investigate and
  relaunch.
- **A non-zero exit code with the declared output present is a HARVEST case,
  not a re-run case.** Ingest the on-disk results into the ledger before any
  retry decision.
- **Idempotent on `(job_id, stage)`.** A re-run must not double-count.
- **No secrets in command strings.** Credentials and tokens reach jobs through
  the scheduler's secret or environment mechanism only — never interpolated
  into an argv, a script body, a log line, a ledger row or a message. A
  suspected leak stops dispatch from the affected identity until it is rotated.

---

## 2. Slurm adapter (first-class)

`submit` writes an sbatch script from a frozen template and returns the Slurm
job ID. `poll` reads `sacct`. `harvest` reads from the shared filesystem — no
copy step is needed when `out/` already lives on shared storage.

Template shape:

```bash
#!/bin/bash
#SBATCH --job-name=<campaign>-<stage>-<target>-<shard>
#SBATCH --partition=<from G0>
#SBATCH --gres=gpu:<gpu_type>:<n>
#SBATCH --cpus-per-task=<cpus>
#SBATCH --mem=<mem_gb>G
#SBATCH --time=<walltime as HH:MM:SS>
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --requeue

set -euo pipefail
# 1. dead-man switch: never treat stand-down as permission to work
# PREFLIGHT_SCRIPT, CAMPAIGN_ROOT, STAGE and optional TARGET come from the
# frozen submission configuration, not from a retyped per-job command.
preflight_args=(--root "$CAMPAIGN_ROOT" --stage "$STAGE")
if [[ -n "${TARGET:-}" ]]; then preflight_args+=(--target "$TARGET"); fi
if python "$PREFLIGHT_SCRIPT" "${preflight_args[@]}"; then
    :
else
    preflight_status=$?
    if [[ "$preflight_status" -eq 10 ]]; then
        echo "Campaign job stood down before model work" >&2
        exit 0
    fi
    exit "$preflight_status"
fi
# 2. environment (module load / conda activate / apptainer exec)
# 3. work
# 4. mkdir -p out && cp -r <results> out/
```

Slurm-specific notes:

- **Job arrays** are the right unit for a generation or scoring wave: one array
  per (target, method, stage), one task per shard. `--array=0-999%<N>` gives a
  per-wave concurrency cap without any external governor.
- **Concurrency control** is `%N` on the array plus the partition's own limits.
  Record the effective cap in the ledger so throughput numbers are interpretable
  later.
- **Dependencies**: `--dependency=afterok:<jobid>` expresses the
  generate-then-score chain. Prefer coupling generation and screening in one job
  (§5) over a dependency chain, so a survivor set is never left unscored.
- **Cancellation discipline**: `scancel` only job IDs recorded in this
  campaign's own job-metadata ledger. Never `scancel -u $USER` — a shared
  account will have other people's work on it.
- **Filesystem**: campaign state on shared storage; scratch on node-local disk
  where the site provides it, with results copied to `out/` before the job ends.
  Torch extension caches and JIT caches go on **persistent shared** storage so
  every job after the first skips the compile.
- **Quota is a hard constraint**, and this protocol discards nothing. Estimate
  storage at G0 and re-check at G4.

---

## 3. Local adapter

`submit` runs the command as a subprocess with a concurrency semaphore sized to
the GPU count. `poll` checks the process. `harvest` is a no-op beyond confirming
`out/`.

Use with the `explore` preset. The protocol is unchanged; only the wall-clock
and the achievable design counts differ. Say so in the deliverables.

---

## 4. Metered cloud adapter

Per-second billing changes the failure modes: an orphaned container bills
silently, and an ungated dispatch storm is not recoverable. The source campaign
handled this with a governor; the portable core of that design:

- **A single campaign-wide concurrency ceiling**, published to one file, with a
  small set of authorised writers. Per-track caps are an advisory subdivision
  of the one ceiling, never additive to it.
- **A fail-closed submit gate.** Every dispatch path — every SDK call, every
  retry path, every canary — calls the gate immediately before **each single**
  dispatch. One approval authorises exactly one container start, never a batch,
  never a loop. Any exception inside the gate returns *refuse*.
- **A staleness dead-man switch.** If the ceiling file is missing or has not
  been refreshed within a couple of cycles, treat the ceiling as zero. A
  governor that no live process refreshes is a dead governor.
- **Metered spend is canonical.** The provider's metered figure, scoped to your
  own account or app, is the only basis for **raising** a ceiling or lifting a
  throttle. A rate-card reconstruction may **pause** dispatch but never release
  one, and it is reported as `UNCALIBRATED`. Expect metered to exceed rate-card:
  providers bill total container lifetime, including idle and failed containers,
  plus CPU and memory adders.
- **Terminate in the same cycle you harvest.** Wrap any directly created
  sandbox in `try/finally` with termination in the `finally`. A harvested
  container is never left to idle to its timeout.
- **Reap only on evidence.** A container may be terminated only when its job ID
  carries a terminal status in the job ledger, or it has produced no output and
  no heartbeat for more than twice its benchmarked wall-clock. "Looks idle" is
  not grounds. Every terminate is scoped to this campaign's own job IDs.
- **A hard per-container wall-clock cap** that the provider enforces, so
  per-container spend is bounded even when every control loop is dead.

**Ask at G0 whether the budget is a ceiling or an allocation** that expires if
unused, because grant and cloud-credit budgets genuinely differ here. Either
way, the objective is information per unit cost, not a spend figure: compute
left over because a target saturated is a result, not a failure.

So the campaign needs somewhere to stop, and the stopping rules are cheap:

- **Early stop** — a target whose best score has not improved across a full
  generate-and-score round is a candidate for closing, not for another round at
  the same settings.
- **Successive halving** — give every method a minimum exploration budget, then
  concentrate on what is working rather than continuing all arms at equal rate.
- **Diminishing returns** — when a round's improvement is small against its
  cost, say so and move the compute to a target that is still moving.

Under-pace is a signal to check whether the plan was too conservative, and it
is reported. It is not, on its own, a reason to add work.

---

## 5. The submit gate

One function, called before every dispatch, on every backend. The repository
currently supplies `scripts/preflight.py` as an **in-job** guard; a production
backend must implement and test the submit-time gate described here before
dispatching paid or shared jobs. It refuses when
any of these holds:

| Condition | Reason token |
|---|---|
| the campaign is halted | `HALTED` |
| `state/authorization.json` is missing or the stage exceeds its approved limit | `OUTSIDE_AUTHORIZATION` |
| the target's `state/gates/<target>.json` is absent or not `PASS`, and `stage` is a scoring stage | `VALIDATION_GATE` |
| a fold-only G3 gate is not explicitly allowed in the approved plan | `UNAPPROVED_FOLD_ONLY` |
| the concurrency ceiling is zero, missing, or stale | `STALE_OR_MISSING_GOVERNOR` |
| live jobs are at or above the ceiling minus a headroom margin | `AT_CEILING` (retry with jittered backoff) |
| on metered backends, spend pace exceeds the band and the job is long | `OVER_PACE` |
| generation has outrun scoring on this target | `GEN_BACKLOG_CAP` |
| anything raised inside the gate | `GATE_ERROR` |

**Fail-closed on every path.** A delayed dispatch costs seconds; an ungated
dispatch storm can cost a quota or a budget irrecoverably.

Run the in-job guard with explicit `--root`, `--stage` and, for a target
production stage, `--target`. Exit 0 means proceed; exit 10 means stand down;
exit 2 means configuration error. The submit-time gate also needs live-job,
spend and backlog checks that the in-job guard alone cannot supply. Do not
describe the four-verb interface or the Slurm sketch as a finished adapter.

`GEN_BACKLOG_CAP` deserves its own note: **generation must not outrun
scoring**, because a generated design that is never scored is wasted compute.
The source rule, portable as written: refuse a generation-stage dispatch when
`generated[target] >= 200` and `generated[target] > 2 * max(scored[target], 50)`.

The **coupled `gen_screen` job** is the structural fix that makes the cap rarely
bind: one job generates backbones and sequences, applies the novelty, liability,
monomer-foldability and structural-plausibility filters in-job, writes the
survivors and the `n_generated` ledger row, then screen-scores every survivor on
all ranking arms and appends the `n_scored` row. Where one environment cannot
carry both stacks, chain the screen as an immediately dispatched job on the same
survivors — a queued-but-undrained scoring arm is a logged deviation.

---

## 6. Ledger

One append per job completion. **One subfile per writer** —
`ledger/<writer_id>.jsonl` — never a single shared file: concurrent appends on
a network filesystem are not atomic and silently clobber.

```json
{"ts_utc": "...", "job_id": "...", "target": "...", "stage": "gen_screen",
 "structure_method": "...", "n_generated": 512, "n_scored": 512,
 "gpu_seconds": 4210, "writer_id": "..."}
```

Plus one job-metadata append at **dispatch** time, on every dispatch path:

```json
{"job_id": "...", "campaign": "...", "target": "...", "stage": "...",
 "submitted_at_utc": "...", "gpu_type": "...", "writer_id": "..."}
```

A dispatch path that cannot write this row does not dispatch.

Campaign totals reported anywhere are exactly the sums over this tree, computed
at report time. Never a count of files, never a number carried in memory. An
aggregation that returns empty after a completed wave is a fail-loud condition,
not a zero.

Never move or rewrite a shared directory while jobs write into it. Route every
append to a shared file through its owning writer after a fresh re-mount — an
append against a stale filesystem snapshot clobbers.

---

## 7. Monitoring

- Check liveness **and progress** every few minutes on any fleet or
  long-running job. Alive but producing nothing is a failure in progress: fix
  and relaunch.
- Every batch job reports **commanded versus delivered** item counts. A
  shortfall above ~10% is a warning in the manifest even on a clean exit.
- Where the runtime supports it, keep one monitor per ~10 live jobs, and scale
  monitors down as jobs complete.
- Gate completion on explicit markers and output counts, not on exit codes.

---

## 8. Restart

Keep **zero load-bearing state in memory**. The ledger, the active-job table,
the per-target progress tracker and the gate files live on durable storage and
are written on every update. After any gap, before issuing new work:

1. Write a fresh heartbeat and clear any halt flag you own.
2. Restart any standing monitor that has gone stale.
3. Re-load the durable ledgers.
4. Reconcile against **live scheduler state** — `squeue`/`sacct`, the process
   table, or the provider's list call — and write the result to a file.
5. Read that reconciliation before dispatching anything.

Reconcile only against state **you** created. A shared cluster account, a shared
storage volume and a shared cloud workspace all carry other people's work; a
blanket cancel or a blanket cleanup is destructive to it.

---

## 9. Naming and isolation

Every campaign-created directory, volume, job name and ledger carries a
campaign-unique prefix — a date alone is not unique enough on a shared account.
Reusable across campaigns as infrastructure: prebuilt environments and model
weight caches, re-validated per the roster criteria. Created fresh per campaign:
ledgers, novelty databases, design outputs, gate files and progress notes.

Any deletion on shared campaign storage requires a verified archive first. If
the archive step fails or times out, halt and escalate rather than proceeding.
