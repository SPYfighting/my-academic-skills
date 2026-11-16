# Paper Anchor

Use `PAPER.md` to connect a paper's research question and claims to evidence, results, and the next scientific step. [SKILL.md](SKILL.md) gives agents the workflow, the [template](templates/PAPER.md) is ready to use, and the [fictional example](examples/PAPER.example.md) shows completed, pending, and non-supporting evidence.

When a project's rules adopt paper-anchor, the agent uses it by default for paper-related work. It creates `PAPER.md` directly from the template when the project first needs to record its design. Continue existing records in place and preserve their evidence IDs and links. The researcher confirms the thesis, claims, and final verdicts.

Daily use needs only Markdown. For maintainers, `python check.py paper-anchor` from the collection root runs the offline fixture checks. It verifies the bundled files and linked example artifacts. Project routing in a particular agent and scientific interpretation are outside those checks.

MIT license. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
