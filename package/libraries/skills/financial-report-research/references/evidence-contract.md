# Evidence that can carry a conclusion

Use this contract for material assertions and selected assumptions; do not create a card for every sentence. Field names can follow the engagement's existing schema. Preserve these meanings and links, rather than imposing a second database or lifecycle.

## Engagement and question records

Record `purpose`, `reader`, `decision`, `entity/perimeter`, `valuation_or_reporting_date`, `information_cutoff`, `language`, and requested conclusion strength. Add jurisdiction, framework, version and applicability evidence where the task depends on them. A standard's issuance or effective date alone does not establish its legal applicability to this entity.

For each material question record:

- `question_id`, the question, decision consequence and materiality rationale;
- competing hypotheses, including a credible adverse explanation;
- evidence/test needed to discriminate between them;
- searches/requests actually executed, their results and remaining gaps;
- a proportionate stopping condition and downstream work units.

Do not invent failed searches, private requests or management interviews. Unavailable access is different from evidence of absence.

## Source, observation and interpretation

Keep three linked layers:

1. **Source:** ID, original URL/file, issuer/author, document version, availability/publication evidence, period, retrieval time, actual content hash and precise page/note/row locator. Confirm that the frozen content, not just its landing-page date, belongs to the information set.
2. **Observation:** exact relevant fact or reported statement, definition, entity/business scope, unit/currency, period and normalization. Distinguish an issuer assertion from independent verification. Preserve reconciliation differences instead of choosing the convenient number.
3. **Interpretation:** what the observation supports, what it does not establish, why it bears on the question, and credible contrary evidence. Several consistent facts can support a judgment without proving a forecast with certainty.

Use explicit classifications such as `reported_actual`, `management_guidance`, `market_observation`, `third_party_estimate`, `analyst_judgment` and `unresolved`. Do not relabel an assumption as an actual because a formula uses it.

## Material assumption or claim record

Include the candidate and selected value/range, unit, horizon, source/observation IDs, model result/input path when relevant, calibration method, alternatives, rationale, contrary evidence, and uncertainty. Explain *why this alternative is selected* and how a different defensible choice affects the decision.

Acceptable calibration may be an operating-driver build, a regime-aware history, a reconciled management plan, a suitable market benchmark or another purpose-appropriate method. Do not treat a historical average, peer median or management target as automatically maintainable. Document overlapping evidence and model dependencies when calling an analysis a cross-check.

Possible dispositions:

| Disposition | Meaning |
|---|---|
| `supported_observation` | The source establishes the specific fact within its stated scope. |
| `reasoned_judgment` | Evidence, alternatives and quantified implications support an analyst selection; it remains a judgment. |
| `bounded_scenario_only` | Useful conditional calculation, without adequate basis to adopt it as the selected value or recommendation. |
| `research_required` | A material missing or conflicting fact prevents the intended conclusion. |

`reasoned_judgment` is not a guarantee of realized returns. `bounded_scenario_only` is not failure when scenarios are the actual mandate, but it does not satisfy a request for a defensible valuation conclusion by changing the label.

## Return work precisely

A research return identifies the affected claim/assumption, missing discriminating evidence, feasible next inquiry, responsible capability, priority, interim conclusion restriction and sensitivity/consequence where available. Request more user data only when genuinely necessary; continue independent research within the authorized scope.

The lifecycle records observable work, decision rationale and artifact changes. It does not require private chain-of-thought. A mechanical validator can test dates, links, hashes and schema; independent substantive review must judge whether the evidence actually supports the claim.
