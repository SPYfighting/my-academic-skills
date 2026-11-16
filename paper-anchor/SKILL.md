---
name: paper-anchor
description: "Organize research around a paper's claims and evidence. Use by default for paper-related work in projects whose rules adopt paper-anchor, or when the user asks to use it. Create or maintain PAPER.md when the project's paper design needs a durable record."
license: MIT
metadata:
  version: "0.4.0"
---

# Paper Anchor

## Open the paper record

Use this workflow for paper-related work when project rules adopt paper-anchor or the user requests it. In an adopting project it is the default. Read the relevant claims in the root `PAPER.md` if it exists. When the project first needs its paper design recorded, create `PAPER.md` directly from [the Markdown template](templates/PAPER.md). Start from available plans and evidence, mark proposed wording as a draft, and leave unknowns explicit. Read-only work uses any existing record as context and reports findings in the requested deliverable.

Update existing records in place. Keep their evidence IDs, source links, and recorded decisions. The [fictional example](examples/PAPER.example.md) shows how to link results to claims.

## Plan and carry out research

1. Identify the paper question and relevant claim or evidence gap. Use stable IDs such as `R1` for claims and `R1.E1` for evidence. An authorized exploration can start with a specific uncertainty and acquire an evidence ID later.
2. For formal work, record the comparison, readout, controls, and what would support or weaken the claim. Keep methods, execution plans, data, logs, and full results in project records and link to them.
3. Update the relevant evidence row with analysis status, interpretation, a short result, and a reviewable artifact link. A completed negative analysis is still complete. Use inconclusive when valid evidence leaves the claim unresolved. Record technical failure as an analysis status, with the reason and the associated diagnostic record when available.
4. Update the claim's next scientific step. Record a proposed change with its evidence and rationale under Decisions when researcher input is needed. Verify updated IDs and links before finishing.

The researcher confirms the thesis, claim changes, and final verdicts. The agent can draft proposals and maintain evidence within the authorized scope.
