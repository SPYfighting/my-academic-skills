# Paper Anchor

Use `PAPER.md` as the paper project's overview. Follow relative links from each evidence row to its Task, available results, and figures or tables. [SKILL.md](SKILL.md) gives agents the workflow, and the [template](templates/PAPER.md) is ready to use. The [fictional example](examples/PAPER.example.md) shows an active Task with interim results and a comparison table.

When a project's rules adopt paper-anchor, the agent uses it by default for paper-related work. It creates `PAPER.md` directly from the template when the project first needs to record its design. The agent updates the overview in the same work that changes an evidence status, result, or file path. Evidence IDs stay stable. The researcher confirms the thesis, claims, and final verdicts.

Daily use needs only Markdown. For maintainers, `python check.py paper-anchor` from the collection root runs the offline fixture checks. It verifies the bundled files and linked example artifacts. Project routing in a particular agent and scientific interpretation are outside those checks.

MIT license. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
