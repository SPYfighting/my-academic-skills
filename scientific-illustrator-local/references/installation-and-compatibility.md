# Installation and compatibility

## Agent discovery

Use this complete directory as a project-local skill. No source changes are needed for different agents, and an agent can also read `SKILL.md` directly from the repository.

| Agent | Project directory | Invocation |
|---|---|---|
| Codex | `<project>/.agents/skills/scientific-illustrator-local/` | `$scientific-illustrator-local` or an explicit workflow request |
| Claude Code | `<project>/.claude/skills/scientific-illustrator-local/` | `/scientific-illustrator-local` |
| OpenCode | `<project>/.opencode/skills/scientific-illustrator-local/` | Load the named skill; project `.agents/skills` and `.claude/skills` are also supported |

Choose one discovery location per agent to avoid duplicate skill entries. If Codex and Claude Code use separate project copies, keep their versions consistent. Scripts do not modify agent settings, add hooks/MCP servers, or register global skills.

Conventions checked on 2026-09-08: [Codex](https://developers.openai.com/codex/skills), [Claude Code](https://code.claude.com/docs/en/skills), [OpenCode](https://opencode.ai/docs/skills/). Image understanding, sandbox access, and native-application permission depend on the agent environment. A compatible skill format is not proof that every model has completed the drawing workflow.

## Prepare dependencies once

Use existing CPython 3.11, 3.12, or 3.13. From this skill directory:

```text
python -X utf8 scripts/setup_environment.py --with-vtracer
```

If Windows `python` points to an older interpreter, use `py -3.12` or a verified absolute path. Setup creates this directory's `.venv` and installs the pinned `requirements.lock` packages. The explicit `--with-vtracer` option downloads official VTracer 1.0.0-alpha.4 into `bin/` and verifies its pinned SHA256. It does not install a global skill or write into Adobe's Scripts directory. Environments and executables are not included in the source package.

Omit `--with-vtracer` if a suitable executable is already installed. Lookup supports PATH or the absolute `SCIENTIFIC_VECTOR_VTRACER` environment variable. The installer refuses to replace an existing VTracer file. For offline Python installation, use `--offline-wheelhouse <wheel-directory>` and omit the VTracer download option. Normal drawing does not download dependencies.

```text
python -X utf8 scripts/setup_environment.py --check
```

`--check` inspects the existing skill environment without installing anything. The shared application entry point is `scripts/figure_cli.py` on both operating systems.

## Automated package check

```text
python scripts/selfcheck.py
```

The standard-library launcher uses this skill's `.venv`, an explicit `SCIENTIFIC_ILLUSTRATOR_PYTHON` path, or the current compatible interpreter. It exercises valid and invalid SVG/jobs, live-text preparation, background cleanup, and local contour tracing. It does not access Illustrator, install dependencies, or use the network. Optional Node/PowerShell syntax checks are reported separately. A passing package check does not establish native application compatibility.

## Native compatibility

| Environment | Implementation | Evidence |
|---|---|---|
| Windows, Illustrator 27.2.0 | Native paths, live text, separate text layer, AI save, PNG export, resume | Tested on hardware, including a paper-figure reconstruction accepted visually by the user |
| Windows, other Illustrator versions | Discover registered COM versions and test required capabilities | Not tested version by version |
| macOS, Intel or Apple silicon | Discover running bundle, use AppleScript with the shared JSX; pinned VTracer assets for both architectures | Adapter contract checks; no macOS hardware result yet |
| Linux | SVG preparation, text cleanup, tracing, QA | No native Illustrator connection |

`illustrator-doctor` reports the actual version, active document, artboard coordinates, and required capabilities. Hardware validation establishes a version's working scope; the adapter does not claim universal compatibility.

Adobe documented an Illustrator 25.1 AppleScript `do javascript` regression and its fix in 25.2. Update affected installations rather than promising to bypass an application defect. [Adobe version note](https://blog.developer.adobe.com/en/publish/2021/01/an-illustrator-25-1-update-for-plugin-developers)

On macOS, the first connection may require the user to grant Automation permission to the terminal or agent in system settings. The adapter selects an already-running bundle by its actual path and does not launch another version.

## Validate a different machine

After the user opens Illustrator, run with this skill's Python:

```text
<python> -X utf8 scripts/figure_cli.py illustrator-doctor
<python> -X utf8 scripts/figure_cli.py native-test --create-document --out-dir <new-absolute-test-directory>
```

The disposable test document remains open; user documents are not closed. Inspect `native-audit.json`, AI, and PNG: five live labels, correct regular/bold faces, no duplicated objects after replay, and an unchanged corner sentinel. Keep the system/version and evidence in the user's project, outside the skill source package.
