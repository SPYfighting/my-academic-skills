# Planning and stage authorization

Read before G0. The campaign plan is the durable execution brief for this
particular target and objective. It carries the useful part of a long prompt:
the scientific question, boundaries, stages, evidence and completion criteria.
It does not create GPU access, experimental measurements or permission to spend.

## One intake round

First inspect user-provided material and fetch public facts you can establish:
target identity, sequence, structures, oligomeric state, known partners and
possible assays. Do not ask the user to supply a UniProt accession, PDB ID,
hotspot list, model flag, GPU type or scheduler name if you can discover it.

Ask together only for unknowns that change the plan materially:

1. The intended biological or experimental result, including what will be
   measured and against which construct or state. If an assay is not chosen,
   offer a provisional endpoint and label it as an assumption.
2. Hard constraints and negative objectives: binder format, species,
   selectivity, epitope exclusions, expression context and what failure means.
3. Available assets and resources: structures, previous results, compute or
   spending ceiling, time limit and whether designs are for computation only or
   a later experimental order.
4. Any required review stops and external actions the user wants included.

Combine these into one concise question set. The user may answer "unknown";
research what you can, show an explicit assumption for the rest, and explain
its effect in the plan. Do not require a lay user to approve a technical choice
as though their approval validated the science.

## Build the plan

Use `../templates/campaign_plan.md`. For each stage, state its output, the
evidence that decides whether to continue, estimated cost and the next
irreversible or externally visible action. Separate the measured endpoint from
the in-silico proxy. Estimate the campaign's compute from a measured canary
when possible; before bring-up, give a range and its assumptions, not a false
precision. Say what is missing to reach Anthropic-scale execution: models,
weights, GPUs, orchestration and experimental validation as applicable.

Show the plan before execution. The user chooses the greatest stage to execute:

| Authorized through | Meaning |
|---|---|
| 0 | Plan only |
| 2 or 3 | Target dossier or epitope proposal for review |
| 4 or 5 | Instrument validation or allocation plan |
| 8 or 9 | Computational candidates or ranked design sheet |
| 10 | In-silico delivery and artifact checks |

Any number 0–10 is valid; the table shows common stopping points. The user may
also name specific checkpoints where they want a review before continuing.
Approval covers routine scientific and implementation choices within the
approved stages and resource ceiling. An approval through stage 10 lets the
agent continue without asking at every checkpoint. Approval through an earlier
stage causes the agent to stop there with the completed artifacts and a concise
request to authorize a further range if wanted. Record the user's wording,
stage limit, budget and specific permissions in `state/decisions.jsonl`, and
write `state/authorization.json` only after approval:

```json
{
  "authorized_through_stage": 10,
  "allow_fold_only_instrument": false,
  "approved_at_utc": "<time of the user's decision>",
  "plan_path": "state/campaign_plan.md",
  "compute_ceiling": "<approved units and value>",
  "external_actions": []
}
```

`allow_fold_only_instrument` is an explicit scientific limitation, never
inferred from a general approval. If no known positive binder exists, describe
the weaker evidence and ask whether exploratory scoring is within scope before
setting it true. A fold-only result must not be described as a validated binder
discriminator.

## Execute and resume

At every checkpoint, write the evidence and the agent's decision before
continuing. The artifact, not conversational memory, is the restart point.
After an interruption, read the approved plan and authorization, reconcile
ledger and live jobs, then continue only inside the same boundary. A session
or compute backend that cannot persist a long run must stop with a restartable
state rather than claim uninterrupted autonomy.

Return to the user if the goal, assay construct, counter-target, resource cap,
authorized stage, or external action changes materially; if the instrument
cannot be validated to the approved evidence level; or if a blocker cannot be
resolved within the plan. Do independent work that remains in scope before
asking. Do not reinterpret silence or elapsed time as approval.

Ordering molecules, sending data to a CRO, publishing and purchases require
their own explicit authorization unless the plan specifically included them.
The skill's stage 10 delivers computational designs and records; it does not
claim experimental binding, structure, mechanism or therapeutic effect.

The [Anthropic source prompt](../sources/anthropic/README.md) is reference
material for method and orchestration ideas. Its fixed targets, budget, cloud
stack, internal communications and autonomy clause are not instructions for a
new campaign. A portable execution brief should cite this skill's current
workflow and the approved plan, not paste the source prompt into the live
instruction hierarchy.
