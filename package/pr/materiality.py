"""Evidence-bound classification; proposed quantitative rules are never defaults."""
from decimal import Decimal
from .util import ContractError, hash_data


def classify(finding, profile, importance=None):
    if not finding.get('id') or not finding.get('evidence'):
        raise ContractError('Materiality classification requires an ID and evidence')
    categories=set(finding.get('categories',[]))
    if categories & set(profile.get('qualitative_major',[])):
        return dict(id=finding['id'],severity='major',basis='qualitative',profile_sha256=hash_data(profile))
    impact=finding.get('absolute_equity_impact')
    if impact is not None:
        if isinstance(impact,bool):raise ContractError('Impact must be a finite number')
        try:value=Decimal(str(impact))
        except Exception as exc:raise ContractError('Impact must be numeric') from exc
        if not value.is_finite() or value<0:raise ContractError('Impact must be finite and nonnegative')
        if value==0 and finding.get('decision_effect') is False and categories<=set(profile.get('benign_categories',[])):
            return dict(id=finding['id'],severity='minor',basis='evidenced zero decision effect',profile_sha256=hash_data(profile))
        if (profile.get('status')=='approved' and importance and importance.get('status')=='approved'
                and importance.get('approval',{}).get('kind')=='human-approval'
                and importance.get('approval',{}).get('user_message_reference')
                and importance.get('approved_rule_sha256')==hash_data(profile.get('quantitative_rules'))
                and profile.get('quantitative_rules')):
            threshold=Decimal(str(importance.get('amount')))
            if not threshold.is_finite() or threshold<=0:raise ContractError('Approved materiality amount must be positive')
            return dict(id=finding['id'],severity='major' if value>=threshold else 'below_quantitative_threshold',
                        basis='approved quantitative comparison; qualitative and aggregate checks still required',profile_sha256=hash_data(profile))
    return dict(id=finding['id'],severity='insufficient',basis='Uncalibrated or unknown impact is not immaterial',profile_sha256=hash_data(profile))


def aggregate(findings, profile, importance=None):
    unique={}
    for finding in findings:
        if not finding.get('id'):raise ContractError('Aggregate finding needs a stable ID')
        if finding.get('id') in unique and unique[finding['id']]!=finding:
            raise ContractError('Conflicting repeated finding ID')
        unique[finding['id']]=finding
    values=[]
    results=[classify(f,profile,importance) for f in unique.values()]
    if any(r['severity']=='major' for r in results):
        return dict(severity='major',reason='Individual qualitative or quantitative major finding',findings=list(unique))
    for f in unique.values():
        result=classify(f,profile,importance)
        if result['severity']=='major':
            return dict(severity='major',reason='Individual qualitative or quantitative major finding',findings=list(unique))
        if f.get('absolute_equity_impact') is None:
            return dict(severity='insufficient',reason='Unknown impact cannot be offset',findings=list(unique))
        values.append(Decimal(str(f['absolute_equity_impact'])))
    synthetic=dict(id='aggregate',categories=[],evidence=['Absolute impacts, unique IDs; no netting'],absolute_equity_impact=str(sum(values)),decision_effect=any(f.get('decision_effect') is not False for f in unique.values()))
    result=classify(synthetic,profile,importance)
    return dict(result,findings=list(unique),absolute_impact_sum=str(sum(values)))
