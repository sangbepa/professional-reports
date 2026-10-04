---
name: financial-report-research
description: Design and conduct question-led evidence research for valuation, financial due diligence, ESG, earnings and board reports. Use to substantiate material assumptions, investigate conflicting evidence and identify what a decision-ready report can support.
---

# Research for a specific decision

Start from the decision and the strongest conclusion the engagement seeks to support. Identify what could overturn that conclusion; acquire evidence for competing explanations as well as the preferred one. A source register proves provenance, not the economic adequacy of an assumption.

Use this skill for research design and synthesis. Existing domain skills own calculations, transaction procedures and accounting normalization. For a valuation engagement, hand collection/normalization requests to `valuation-evidence`, assumptions/methods to `valuation-design`, and tests to the appropriate model skill. Consume supplied current records rather than collecting the same documents twice. A narrow request for a filing or a factual extraction does not require a full research engagement.

In an orchestrated engagement this entrypoint supplies purpose policy. For a host-selected task, consult the corresponding method in [report-research-plan](../report-research-plan/SKILL.md), [report-source-assess](../report-source-assess/SKILL.md), [report-evidence-extract](../report-evidence-extract/SKILL.md) or [report-data-reconcile](../report-data-reconcile/SKILL.md), using its accepted input and explicit return artifact. Do not repeat the whole research loop for every leaf operation. A direct narrow request can use the relevant leaf skill without creating a full engagement.

## Select the relevant purpose

Read [the evidence contract](references/evidence-contract.md) and only the matching purpose profile. Combine profiles when the mandate combines decisions, while keeping each conclusion's basis distinct.

| Purpose | Profile | Principal question |
|---|---|---|
| Company/equity valuation | [valuation](references/valuation.md) | Why is the selected earning/reinvestment path and resulting value defensible? |
| Buy-side or vendor FDD | [fdd](references/fdd.md) | Which earnings, working-capital and funding adjustments survive transaction-level testing? |
| ESG disclosure, diligence or readiness | [esg](references/esg.md) | What material exposure or disclosure is supported for the selected framework and boundary? |
| Earnings update | [earnings](references/earnings.md) | What changed versus a valid expectation, and how does it alter estimates or the thesis? |
| Board paper or minutes | [board](references/board.md) | What supports the proposed decision, or what actually occurred at the meeting? |

For sector-dependent economics, read only the relevant lens in [industry lenses](references/industry-lenses.md). These are starting questions, not universal models or fixed peer lists.

## Execute the research

1. Establish purpose, audience, entity/ownership perimeter, dates and information cutoff. Define the intended conclusion strength and proportionate completion criteria before searching.
2. Form material questions and credible alternative explanations. Prioritize by their potential effect on the actual decision. Do not use a universal numeric materiality threshold or a minimum source count.
3. Search for original issuer, regulator, standard-setter, exchange or contractual evidence suited to each question. Record what was sought, found, contradicted or unavailable. Several articles repeating one release are one underlying observation.
4. Freeze useful originals with publication/availability evidence, covered period, retrieval time and locators. Reconcile units, scope, calendar and definitions before combining observations. A later-published fact does not belong in an earlier information set merely because it covers an earlier period.
5. Connect observations to proposed inputs through an explicit calibration or interpretation. A qualitative outlook cannot establish an exact margin, growth rate or investment return. Assess historical regimes, structural changes, contrary evidence, selection bias and shared data dependencies.
6. Return question/evidence records, supported inferences, plausible bounded judgments and unresolved material issues. For a material gap, specify the next useful source or test and the work unit it affects. Writing must not silently substitute confident prose for this work.

Stop when the evidence permits the requested level of judgment, or when further feasible research has diminishing decision value. Disclosed uncertainty can support a bounded judgment when its rationale and consequences are defensible. If the unresolved issue can reverse the conclusion and its implications cannot be bounded, downgrade the conclusion or return that work for research. Record the actual scope; public-data screening is not completed transaction diligence.

Pass the evidence packet and current artifact versions to `financial-report-writing`. Use the engagement's existing lifecycle for hashes, dependencies and reviewer closure. These instructions do not install data access, calculate a valuation or certify source truth by themselves.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### financial-report-research-method

Execute the substantive method in this component against current bound inputs. Capabilities: purpose-led-research, valuation-research, fdd-research, esg-research, earnings-research, board-research.

### financial-report-research-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### financial-report-research-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

