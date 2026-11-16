# Paper Anchor

Paper Anchor connects a paper's thesis and claims to planned evidence, observed results, and reviewable artifacts. `PAPER.md` also contains a generated dashboard, research handoff, proposals, open questions, and an append-only changelog.

The [example](examples/PAPER.example.md) uses a fictional remote-sensing study. For R4, one of two active analyses is complete and one completed result does not support the current claim. The dashboard displays both facts. Researcher decisions, such as revising a claim or accepting its final verdict, remain explicit.

## Set up a project

1. Copy the full skill directory into your project's skill directory or give the agent the path to [SKILL.md](SKILL.md). See the collection's [installation guide](https://github.com/SPYfighting/my-academic-skills/blob/main/docs/installation.md).
2. Add the [activation snippet](bootstrap/snippet.md) to the project rules. You can also request the named skill explicitly.
3. From the research project root, use Python 3.8 or later to initialize `PAPER.md`:

   ```bash
   python /path/to/paper-anchor/scripts/check_paper.py PAPER.md --init
   ```

   The bundled template and example use Chinese field labels. After confirming the thesis, claims, and planned evidence, run the same command with `--fix-dashboard`.

The optional `bash ./install.sh` command installs user-level copies for local agents that discover `~/.agents/skills` or `~/.claude/skills`. For project-local discovery, follow the usual installation for your agent.

## Check a paper

| Option | Behavior |
|---|---|
| No option | Check the document, dashboard consistency, and local artifacts |
| `--fix-dashboard` | Regenerate the dashboard block and check the file |
| `--staged` | Check the Git index version of the document and resolve local artifacts in the worktree |
| `--strict` | Treat warnings as failures |
| `--quiet` | Suppress individual warnings |

The check validates file structure, dates, IDs, statuses, interpretation, and local artifact paths. It reports external links as unverified. Use version history to audit edits to earlier changelog entries. Scientific interpretation and external source verification require review of the underlying evidence.

Legacy five-column tables are supported. A legacy completed row is completed and awaiting interpretation. A legacy non-supporting row is completed with a non-supporting interpretation. Run `--fix-dashboard` to refresh the old dashboard. To migrate a table to six columns, add the separate interpretation column and preserve the original IDs, results, and links.

### Optional Git hook

Run `bash ./install.sh --hook "/path/to/project"` to install the hook. It checks the staged `PAPER.md` and skips projects without one in the index. It looks for a project-local or user-level copy of the checker and reports when the checker or Python is unavailable. If the project already has a hook or a custom `core.hooksPath`, merge [the hook](hooks/pre-commit) into the project's existing setup.

## Validation

Run `python scripts/selfcheck.py` from the skill directory. The offline self-check exercises the bundled template and example, legacy compatibility, dashboard regeneration, artifact validation, and the staged-read interface. The tests use synthetic evidence, with the Git substitution limited to the staged-read unit test. Native agent discovery, remote artifact accessibility, and scientific conclusions require separate validation.

MIT license. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
