# Responsible use

De novo protein binder design is dual-use. The same protocol that produces a
therapeutic candidate against a receptor ectodomain can, in principle, be
pointed at something that should not be bound. This file states what this
repository is for, what it is not for, and what the skill does about it.

## In scope

- Miniprotein binders against protein targets for research, diagnostics and
  therapeutic discovery, validated by in vitro binding measurement.
- Structure and complex prediction with calibrated confidence.
- Protein engineering: stability, expression, solubility, enzyme activity and
  specificity, interface redesign.
- Method development, benchmarking and teaching on any of the above.

## Out of scope

The skill declines and says so plainly when a request involves:

- Select agents, controlled toxins, or their functional components.
- Enhancing the transmissibility, virulence, host range or immune evasion of a
  pathogen.
- Designing molecules whose intended function is to harm a person, a population,
  livestock or a crop.
- Circumventing a biosecurity screening step, including sequence screening at a
  synthesis provider.

This is not a judgement about the sensitivity of a research area. Work on
pathogen proteins for vaccines, diagnostics and antivirals is ordinary, valuable
science and is in scope; the line is drawn at enhancement and at intended harm.

## Obligations that come with the tools, not with this file

- **Synthesis screening.** Order through providers that screen sequences.
  Do not ask a provider to skip screening, and do not split an order to evade it.
- **Institutional review.** Your biosafety committee, export-control office and
  IRB rules apply to what you make, regardless of what a design pipeline
  produced.
- **Method licences.** Every model this protocol orchestrates carries its own
  licence and its own permitted uses. Confirm each one for your regime; see
  `binder-design-campaign/references/tool-catalog.md` §5.
- **Data provenance.** Structures, sequences and datasets carry their own terms.

## What the skill does

- The scope boundary is stated in `SKILL.md` §2 rule 8, so it is in context at
  every invocation rather than in a file the agent might not read.
- The gate model puts a human in front of the target list (G0), the target
  dossier (G1) and the epitope (G2). A request that should not proceed reaches a
  person before compute is spent.
- Every campaign leaves an auditable record: what was designed, against what
  epitope, with which methods, by whose decision, with the deviations logged.

## Reporting

If you find that this skill produces or facilitates something in the out-of-scope
list, open an issue describing the behaviour — not the harmful output itself —
or contact the maintainers privately.
