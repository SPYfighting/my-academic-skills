# Design rationale

Why this repository is shaped the way it is. Read `source-mapping.md` for the
line-by-line correspondence with the original prompt; this file explains the
major decisions behind that mapping.

---

## 1. Evidence checkpoints exist because the failures were silent

The source campaign was a deliberate autonomy experiment: one written protocol,
no human input on any design decision, 48 hours. It worked — 27% of 1,320
synthesised designs bound, 49% among the top-ranked design per target. That is
the correct experiment to run once.

The same data reveal a limit: three targets produced almost nothing, and the
in silico scores that drove the whole pipeline **gave little warning**. Designs against
maltose-binding protein, which yielded 0 of 90, scored about as well as designs
against VEGF-A, which yielded many. A campaign needs explicit evidence at the
consequential choices: construct, epitope and whether the scoring instrument
has demonstrated discriminating power on this target.

Those are checkpoints G1, G2 and G3. An agent may make the scientific choice
within a user-approved plan, but must record the alternatives and evidence.
A non-specialist's approval does not turn an unsupported choice into a
validated one.

The user reviews the scope once and chooses an execution limit. Later review
stops are optional within that limit; a change in goal, cost or external action
returns to the user. This supports both an autonomous run through delivery and
a campaign reviewed stage by stage.

## 2. Length was a structural problem, not a verbosity problem

The source prompt is 16,281 words of unbroken prose with no headings. It reads
as a contract for one run rather than a manual to be consulted, which is exactly
what it was.

Three things reduce it without losing content:

**Remove what cannot travel.** Roughly a third of the prompt specifies one
company's internal stack: a per-second cloud billing governor with its own
arithmetic, a submit-gate module with a described implementation, Slack
threading invariants, a Google Drive single-writer rule, orchestrator sleep bans
and heartbeat protocols. None of it runs on a university cluster. What survives
is the set of *ideas* those mechanisms encoded — fail-closed submission,
metered spend as the only basis for raising a limit, evidence-based container
reaping, generation never outrunning scoring — expressed against a four-verb
backend contract that a Slurm adapter satisfies in about thirty lines of sbatch.

**Turn mechanical rules into code.** The prompt states its sheet-writer
invariants in prose: null policies, rank ordering keys, selection caps,
relaxation ladders, write-time gate recomputation. A few hundred words each, and
an agent reading them still has to implement the check correctly under time
pressure. As Python, they are shorter, they run, and — importantly — they fail
on bad input, which prose cannot. `scripts/` is where most of the compression
came from.

**Load the rest on demand.** Nothing about the compute governor is relevant
while choosing an epitope. `SKILL.md` is the spine and an index; `references/`
holds the detail with a stated trigger for reading each file.

The result is 250 lines in the always-loaded file, with the substance intact and
addressable.

## 3. The backend is a contract because environments differ more than science does

The scientific layer — dossier, epitope, instrument, gates, deliverables — is
the same whether the jobs run on four A100s in a shared queue or on 300 rented
H100s. The submission layer is entirely different.

So the protocol calls four verbs (`submit`, `poll`, `harvest`,
`append_ledger`) and never names a scheduler. Slurm is the first-class adapter
because that is where most academic GPU time is; a local adapter covers a
workstation; a metered-cloud adapter carries the source campaign's governor
ideas for anyone billing per second. A site with LSF, PBS or Kubernetes writes
one adapter and changes nothing above it.

One piece of the cloud machinery was worth keeping everywhere:
`binder-design-campaign/scripts/preflight.py`, the in-job dead-man switch. It costs under a second at
job start and is the only control that still binds when every orchestrating
process is dead — which, on a queue with a day of pending jobs, is a situation
that actually happens.

## 4. Generalisation goes sideways, not outward

The requirement was for the skill to extend "to related protein design,
structure prediction, and broader bioinformatics work". Extending outward — one
skill that tries to cover everything computational in biology — produces a
document with no shared discipline, because a single-cell pipeline and a binder
campaign have almost nothing in common beyond running on a cluster.

Extending sideways works better. Binder design, structure prediction and general
protein design differ in **what they generate and how they discriminate**, and
agree on everything else: target dossiers, frozen constructs, validated
instruments, transductive z-scores, provenance keys, nothing-discarded storage,
derived deliverables, adversarial review. So `workflows/` holds three thin files
that state their deltas, and `references/` holds the shared core once.

The delta that matters is at G3. Binder design has useful within-target in
silico filters, but their score does not reliably predict whether an unfamiliar
target will yield a hit. Structure prediction has no design pool to separate, so its G3
becomes held-out recapitulation. General protein design usually has a *weak*
discriminator, and its G3 measures how weak — because a campaign that ranks on
an unvalidated score should be sized by experimental throughput, not by in
silico filtering. Saying that plainly is more useful than pretending the binder
workflow generalises unchanged.

---

## 5. The protocol ends at the design sheet

A reviewer suggested closing the loop: read the assay results back in, classify
the experimental failures, and let them steer the next round. It is the right
shape for a research programme and the wrong shape for this skill, for a
practical reason rather than a principled one.

Assay results arrive weeks or months later, from someone else, in a format
nobody has seen yet - a CRO report, a folder of sensorgrams, a spreadsheet with
its own conventions. Building an ingestion path now means guessing that format,
and a guessed schema is worse than no schema: it looks authoritative and it is
wrong. The work it would pull in - curve fitting, replicate handling, assay QC,
plate controls - is a different skill with different failure modes.

So the boundary is drawn at the handoff, and it is drawn in both directions.
The protocol does not fetch or interpret experimental data, and the failure
vocabulary contains no assay outcomes, because a code the campaign can never
write is noise in an enum whose whole point is aggregation. Earlier results do
reach the campaign, but as **operator input at G0** in the operator's own
words, where they inform the epitope, the difficulty prior and the negative
objectives - and where nobody mistakes them for something the protocol
measured.

What stays on the dry side is the part that keeps the claims honest: the G0
separation of the experimental endpoint from the computable proxy, and the
`predicted` / `inferred` / `measured` labelling in the report. Those exist
precisely because the protocol will never see the measurement.

---

## What this repository does not claim

It has not been run end to end on a real campaign. The scripts are exercised
against a fixture, both on clean and corrupted input; the protocol is adapted
from a published one that was. Those are different kinds of evidence and the
distinction is worth keeping: what is validated here is that the checks catch
what they claim to catch, not that a campaign run under this skill reproduces
the published hit rate.
