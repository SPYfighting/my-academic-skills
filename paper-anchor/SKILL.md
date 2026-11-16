---
name: paper-anchor
description: "Use PAPER.md as the entry point for a paper's design, evidence, active tasks, and results. Use by default for paper-related work in projects whose rules adopt paper-anchor, or when the user asks to use it."
license: MIT
metadata:
  version: "0.4.2"
---

# Paper Anchor

## Open the paper record

Use this workflow for paper-related work when project rules adopt paper-anchor or the user requests it. In an adopting project it is the default. Read the relevant claims in the root `PAPER.md` if it exists. When the project first needs its paper design recorded, create `PAPER.md` directly from [the Markdown template](templates/PAPER.md). Start from available plans and evidence, mark proposed wording as a draft, and leave unknowns explicit. Read-only work uses any existing record as context and reports findings in the requested deliverable.

Use `PAPER.md` as the project overview for claims, evidence, active research, and the next steps. Update it in place and preserve evidence IDs and recorded decisions. The [fictional example](examples/PAPER.example.md) shows the links for an active analysis.

Reuse the project-local skill copy. Update it when the user asks to sync, keeping the existing `PAPER.md`, evidence IDs, and links.

## Plan and carry out research

1. Identify the paper question and relevant claim or evidence gap. Use stable IDs such as `R1` for claims and `R1.E1` for evidence. An authorized exploration can start with a specific uncertainty and acquire an evidence ID later.
2. For formal work, record the comparison, readout, controls, and what would support or weaken the claim. Keep details in project records. In the evidence row, link the Task from Planned work and link available interim or final results, figures, or tables from Artifacts. Use paths relative to `PAPER.md` for project files. When an active exploration has no evidence ID yet, link its Task and available outputs under Paper design. Move those links to the evidence row once it has an ID.
3. When a status, result, or file path materially changes, verify the source record and update `PAPER.md` during the same work. Update the relevant status, interpretation, short result, links, and next step. Verify links after moving or renaming files.
4. Record a proposed change with its evidence and rationale under Decisions when researcher input is needed. Verify updated IDs and links before finishing.

The researcher confirms the thesis, claim changes, and final verdicts. The agent can draft proposals and maintain evidence within the authorized scope.

## Maintain evidence across tasks

- **Complete the required work.** When several Tasks contribute to one evidence item, mark it complete once its agreed analyses and required controls meet the Task acceptance criteria. While a required control is pending, link interim artifacts and record the analysis as in progress or blocked. A valid negative result counts as complete. Use inconclusive when valid results leave the claim unresolved. Record technical failure with its reason and available diagnostic record.
- **Resolve conflicting records.** Match the Task and its input or run version to the actual logs and artifacts. Use the verified records to establish progress and the Task criteria to judge completion. When a record is confirmed wrong, correct the Task within scope before updating `PAPER.md`. If the conflict remains unresolved, note what needs checking and preserve existing results and the researcher's verdict.
- **Keep evidence history.** Give an independent follow-up control its own evidence ID and cross-reference the original when the original analysis remains valid. When an error invalidates the original analysis and requires a rerun, reuse its ID, update its status, and preserve the superseded artifacts with the reason.
- **Assign writeback.** In serial work, the executor writes back verified changes. For parallel work, the initiating agent coordinates and merges updates into `PAPER.md`. Each executor updates their own Task and reports the evidence ID, verified status, result, and links. On a change of coordinator, record pending IDs and links in the project's existing handoff.
