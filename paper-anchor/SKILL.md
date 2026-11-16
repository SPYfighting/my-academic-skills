---
name: paper-anchor
description: "Organize paper-driven research around the thesis, claims, and evidence in PAPER.md. Load when project rules enable paper-anchor, the user names it, or the user asks to use a PAPER.md with its dashboard marker. Use for research design, analysis, exploration, evidence review, and research handoffs."
license: MIT
metadata:
  version: "0.3.1"
---

# Paper Anchor

`PAPER.md` holds the current paper design and evidence index. The thesis defines the research question, results `R1` and onward state the claims to test, and evidence IDs such as `R1.E1` connect those claims to reviewable work. Keep detailed methods, data, and run records at their existing locations and link to them.

## Start work

1. Read the dashboard, research handoff, and relevant claims. Follow links to the underlying task, run, or artifact as needed. If `PAPER.md` is missing, continue independent authorized work. When the user requests initialization, run `python <checker> PAPER.md --init` and use the research question they provide.
2. State the main claim or evidence ID, the question, and the expected output. For a read-only review, trace the claim to original artifacts and report findings in the requested deliverable.
3. Continue the existing evidence item when it covers the task. Add an item under a confirmed claim when an authorized control, replication, or analysis is needed. Before formal analysis, record what would support or weaken the claim, including the relevant metrics and controls. Link the full design from the task or methods record.
4. Authorized literature checks, quality control, and small pilots can proceed before an evidence ID exists. State the specific uncertainty and record findings in the research, task, or run record. Link reviewable findings to an existing item or propose a change. Ask the researcher to decide when scope, risk, resources, or authority materially change, and continue independent authorized work.

## Research decisions

The researcher confirms the thesis, creation or removal of claims, claim titles and wording, final verdicts, proposal acceptance, and closure of open questions. Offer concrete proposals with evidence IDs. Record explicit user instructions when implementing a decision.

Maintain evidence items, output links, and next steps within the authorized scope. A planned result can move into progress as work starts. When setting evidence aside, keep its ID and record the reason. Use the paper handoff for the next scientific step and any separate project handoff for active jobs, permissions, blockers, and recovery.

## Record evidence

Use the six columns in [the template](templates/PAPER.md), in order: evidence ID, planned work, analysis status, evidential interpretation, one-line result, and artifacts. The bundled template uses Chinese field labels. Keep the labels and status vocabulary used by the template.

| Field | How to fill it |
|---|---|
| Analysis status | Use the template's planned, in progress, blocked, completed, technical failure, or set-aside status. |
| Evidential interpretation | For completed work, use 支持 (supports), 部分支持 (partly supports), 不支持 (does not support), 无法判定 (inconclusive), or 未判读 (awaiting interpretation). For other statuses, use `—`. |
| Result | Summarize the comparison, observed effect, and essential conditions. Explain blockers, technical failures, and set-aside items. Record the recovery point when work is incomplete. |
| Artifact | Link every completed result to a reviewable file or external source. Prefer local paths relative to `PAPER.md`. Link inputs, versions, reproduction steps, and full results from the artifact. Verify external references separately. |

A valid negative result is a completed analysis with an interpretation of 不支持. Use 部分支持 when the result supports only part of the claim, and 无法判定 when valid outputs leave the claim unresolved. Use the technical failure status when execution or quality control invalidates the analysis and keep its diagnostic record. The dashboard measures progress. The final verdict depends on the scope, strength, and consistency of the evidence.

## Update and hand off

1. For material research changes, update the affected items, artifact links, and next steps. Record proposals or open questions that require a researcher decision.
2. Update the research handoff and append a dated changelog entry with the actor, affected IDs, change, and reason. For parallel work, assign one person or agent to merge updates into the current copy of `PAPER.md`.
3. Run `python <checker> PAPER.md --fix-dashboard`, resolve errors introduced by the change, and report meaningful warnings. If the checker is unavailable and a handoff is necessary, sync the dashboard manually and mark it as pending verification.
4. Report evidence produced, progress, unfinished items, and decisions. Keep read-only reviews and unrelated maintenance in their own deliverables.

`<checker>` is [`scripts/check_paper.py`](scripts/check_paper.py) relative to this skill directory. See the [usage guide](README.md) for project setup, legacy files, and automated checks.
