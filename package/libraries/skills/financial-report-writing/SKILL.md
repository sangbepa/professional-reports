---
name: financial-report-writing
description: Turn current research and reviewed analysis into expert-facing valuation, FDD, ESG, earnings or board documents. Build evidence-based arguments, explicit judgments and decision implications; return material research gaps rather than disguise them with confident prose.
---

# Write for the person who must decide

Establish what the reader already knows, what decision the document serves and what conclusion strength the evidence permits. Write the substantive argument before page layout. Clear language is compatible with depth; jargon, length, source counts and decorative charts do not establish professional adequacy.

Read [the argument contract](references/argument-contract.md) and only the relevant purpose profile:

| Purpose | Writing profile |
|---|---|
| Company/equity valuation | [valuation](references/valuation.md) |
| Financial due diligence | [fdd](references/fdd.md) |
| ESG disclosure, diligence or readiness | [esg](references/esg.md) |
| Earnings analysis | [earnings](references/earnings.md) |
| Board decision paper, minutes or sample | [board](references/board.md) |

Use the current evidence packet from `financial-report-research` or equivalent supplied records. Existing domain authors own methods, inputs and financial/technical judgments. Do not change a selected assumption in prose without returning it to the model/analysis owner and invalidating affected work. For a writing-only task, distinguish editorial improvement from unperformed research or calculation.

In an orchestrated engagement this entrypoint supplies writing policy, while [report-findings](../report-findings/SKILL.md), [report-argument](../report-argument/SKILL.md), [report-outline](../report-outline/SKILL.md), [report-section-write](../report-section-write/SKILL.md) and [report-claim-check](../report-claim-check/SKILL.md) own separate artifacts. Read only the current operation and relevant profile. A targeted rewrite need not regenerate unrelated research or a full report plan.

## Build and test the argument

For material conclusions, link the issue, relevant observation, interpretation, competing explanation, quantified implication and judgment. These are argument relationships, not six mandatory headings. A coherent narrative can combine them. Use topic/exhibit titles that express the actual finding and its scope, with nearby dates, units and source locators.

Lead with what the analysis supports and why it matters. Give uncertainty where it changes that conclusion, rather than repeating generic disclaimers. State accepted, rejected and still-open interpretations and their consequences. Keep facts, management statements, forecasts and analyst judgments distinguishable without turning the report into a log of internal labels.

Write for the specified expert reader: emphasize changed economics, disputes, methods, evidence and choices. Explain a technical concept only when it affects a real interpretation or the user requests a learning document. Remove generic aphorisms, obvious formula explanations, unearned certainty and repetitive background. Do not remove evidence or qualifications to sound decisive.

If a material argument cannot be supported, produce a precise research/analysis return and restrict the draft's conclusion to its actual basis. A well-written conditional scenario does not become a defensible valuation range, completed FDD or assurance opinion through style. Bounded judgments remain appropriate when alternatives and consequences justify them for the mandate.

Deliver substantive content plus its claim/evidence/model links and unresolved-work record. The business report should not recount execution steps, formula counts, hash checks or model-tool names unless they affect the reader's decision; retain those in the work specification.

## Composition and review

Preserve user language, structure, selected design and requested format. `valuation-compose` binds valuation content; `report-design` carries a hash-bound existing design reference and a handoff method. The package includes a valuation-only report-outfit build/render adapter at `adapters/valuation/`, with bundled neutral assets and synthetic engineering checks. Use the verified current runtime; this does not provide FDD/ESG/board execution or a professional-content approval. A prior presentation selection does not transfer review to new content, a new genre or changed bytes.

Before publication require a proportionate substantive review of claim support, selected judgments, counterarguments and decision implications against the current artifacts. Content/source/model review and typography/layout review are separate. Existing review roles can perform this work; do not invent an extra reviewer identity. Where independent AI review is required or requested, use the actual available review channel, record requested/observed model settings and scope, and never invent a review result.

Use new artifact versions for substantive changes. Current numerical binding and every final PDF page still require their format-specific checks. This skill improves research-to-writing decisions; it is not a guarantee of partner signoff or a tool that automatically produces validated analysis from a company name.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### financial-report-writing-method

Execute the substantive method in this component against current bound inputs. Capabilities: purpose-led-writing, valuation-writing, fdd-writing, esg-writing, earnings-writing, board-writing.

### financial-report-writing-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### financial-report-writing-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

