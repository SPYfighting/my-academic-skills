# Repository conventions

This file governs changes to the repository. To use a skill, read its own `SKILL.md`; its domain rules apply to that workflow.

## Find a skill

| Request | Entry point |
|---|---|
| Protein binder design, structure prediction, or protein engineering | `binder-design-campaign/SKILL.md` |
| Editable scientific diagrams, raster reconstruction, or local Illustrator drawing | `scientific-illustrator-local/SKILL.md` |
| Editable scientific figures drawn in PowerPoint or PPTX | `scientific-ppt-drawing/SKILL.md` |

## Layout and writing

- One skill per top-level directory, with matching directory name and `name` frontmatter. `SKILL.md` must also include a useful `description`.
- Each skill is self-contained. Keep runtime instructions, scripts, fixtures, licenses, and required references inside it. Resolve paths relative to the skill root unless a link explicitly says otherwise.
- Keep entry points concise. Put conditional detail in `references/`, `workflows/`, or other directories only when needed, with a clear pointer explaining when to read it.
- Write skill instructions in English. Preserve the language of user-provided content such as figure labels. Use ASCII for diagnostic messages and UTF-8 for content files.
- Prefer standard-library helpers. When a skill requires third-party packages or a native application, declare them in that skill, pin dependencies where appropriate, and make installation an explicit step.
- Repository documentation covers discovery, installation, contribution, and attribution. Detailed scientific methods, application-specific limits, and review gates belong to their skill.

For substantial edits to agent-facing prose, use `writing-for-agents` when available. Keep one authoritative explanation of each rule and preserve source attribution. Changes to binder protocol prose must be reflected in its `docs/source-mapping.md`.

## Add or change a skill

1. Create or update the self-contained skill directory. Preserve existing behavior outside the requested scope.
2. Provide `scripts/selfcheck.py` for automated validation. It should exercise representative valid input and reject meaningful invalid input, without opening native applications or making network requests. State what remains untested.
3. Add or update one concise row in each README and the routing table above. Record version changes in `CHANGELOG.md` and `CITATION.cff`; a new skill is a minor repository release.
4. Run `python check.py` with the required per-skill dependencies available. All selected skills must pass; an absent self-check is not a pass.
5. Review the complete diff, then commit only the affected skill and related repository files. Publish through normal commits on the intended branch, preserving existing history.

Keep line endings LF, as specified by `.gitattributes`. Exclude credentials, private inputs, runtime environments, downloaded binaries, local work, and generated outputs. Preserve licenses and attribution at their point of use and in the repository notice index.
