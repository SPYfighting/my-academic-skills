---
name: paper-anchor
description: "Use PAPER.md as the entry point for a paper's design, evidence, active tasks, and results. Use by default for paper-related work in projects whose rules adopt paper-anchor, or when the user asks to use it."
license: MIT
metadata:
  version: "0.4.1"
---

# Paper Anchor

## Open the paper record

Use this workflow for paper-related work when project rules adopt paper-anchor or the user requests it. In an adopting project it is the default. Read the relevant claims in the root `PAPER.md` if it exists. When the project first needs its paper design recorded, create `PAPER.md` directly from [the Markdown template](templates/PAPER.md). Start from available plans and evidence, mark proposed wording as a draft, and leave unknowns explicit. Read-only work uses any existing record as context and reports findings in the requested deliverable.

Use `PAPER.md` as the project overview for claims, evidence, active research, and the next steps. Update it in place and preserve evidence IDs and recorded decisions. The [fictional example](examples/PAPER.example.md) shows the links for an active analysis.

## Plan and carry out research

1. Identify the paper question and relevant claim or evidence gap. Use stable IDs such as `R1` for claims and `R1.E1` for evidence. An authorized exploration can start with a specific uncertainty and acquire an evidence ID later.
2. For formal work, record the comparison, readout, controls, and what would support or weaken the claim. Keep details in project records. In the evidence row, link the Task from Planned work and link available interim or final results, figures, or tables from Artifacts. Use paths relative to `PAPER.md` for project files. When an active exploration has no evidence ID yet, link its Task and available outputs under Paper design. Move those links to the evidence row once it has an ID.
3. When a status, result, or file path materially changes, verify the source record and update `PAPER.md` during the same work. Update the relevant status, interpretation, short result, links, and next step. Verify links still resolve after moving or renaming files. A completed negative analysis is still complete. Use inconclusive when valid evidence leaves the claim unresolved. Record technical failure with its reason and available diagnostic record.
4. Record a proposed change with its evidence and rationale under Decisions when researcher input is needed. Verify updated IDs and links before finishing.

The researcher confirms the thesis, claim changes, and final verdicts. The agent can draft proposals and maintain evidence within the authorized scope.
