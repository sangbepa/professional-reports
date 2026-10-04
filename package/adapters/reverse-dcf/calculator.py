"""Read-only original workbook AST + independent Decimal forward check."""
import sys,json,hashlib,importlib.util,time,datetime,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pr.reverse_dcf import solve
from pr.util import digest,write_json
OUT=Path(__file__).resolve().parent
BOOK=Path(__file__).resolve().parent/'cases/hyundai-2026-09-22/original/Hyundai-Motor-DCF-2026-09-22.xlsx'
AUDIT=Path(__file__).resolve().parent/'cases/hyundai-2026-09-22/original/audit-2026-09-23-calculation-check.py'

def main():
    start=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    freeze=OUT/'frozen';freeze.mkdir(exist_ok=True)
    for p in [BOOK,AUDIT]:
        dst=freeze/p.name
        if dst.exists() and digest(dst)!=digest(p):raise ValueError('Frozen input changed')
        if not dst.exists():shutil.copyfile(p,dst)
    spec=importlib.util.spec_from_file_location('original_audit',freeze/AUDIT.name)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.BOOK=freeze/BOOK.name
    if digest(mod.BOOK)!=mod.EXPECTED_HASH:raise ValueError('Original audited workbook hash mismatch')
    cells,meta=mod.load_xml()
    asts={k:mod.Parser(c['formula'],k[0]).parse() for k,c in cells.items() if c['formula'] is not None}
    def forward(g):
        overrides={('DCF',col+'47'):g for col in 'DEFGHIJ'}
        return mod.Engine(cells,asts,overrides)
    target=float(cells['DCF','D36']['value'])
    base=mod.Engine(cells,asts);base_decimal=mod.independent(cells)
    result=solve(lambda g:forward(g).cell('DCF','D126'),target,-.3,.3)
    if result['status']!='solved':raise ValueError('No unique sampled root: '+result['status'])
    growth=result['roots'][0];engine=forward(growth)
    overrides={('DCF',col+'47'):growth for col in 'DEFGHIJ'}
    independent=mod.independent(cells,overrides=overrides)
    px=engine.cell('DCF','D126');other=float(independent['price'])
    def literal(addr):return float(cells['DCF',addr]['value'])
    issued=sum(literal('D'+str(r)) for r in range(235,239))
    treasury=sum(literal('E'+str(r)) for r in range(235,239))
    shares=issued-treasury
    finance=(literal('D202')-literal('D203'))*literal('D82')
    associates=(literal('D215')-literal('D216'))*literal('D87')
    nfa=sum(literal('D'+str(r)) for r in [204,205,206])-sum(literal('D'+str(r)) for r in [207,208,209,210])
    finance_nfa=literal('D211')+literal('D212')-literal('D213')-literal('D214')
    bridge=nfa-finance_nfa+finance+associates-literal('D35')
    ev=float(independent['operating_ev']);equity=ev+bridge
    checks={
      'base_ast_vs_decimal':abs(base.cell('DCF','D126')-float(base_decimal['price']))<1e-5,
      'roundtrip_within_0_1_percent':abs(px/target-1)<=.001,
      'independent_decimal_within_0_1_percent':abs(other/target-1)<=.001,
      'ast_vs_decimal':abs(px-other)<1e-5,
      'bridge_independent_sum':abs(bridge-float(independent['nonoperating_bridge']))<1e-9,
      'ev_to_parent_equity':abs(engine.cell('DCF','D124')-equity)<1e-8,
      'issued_minus_treasury':abs(engine.cell('DCF','D125')-shares)<1e-9,
      'nci_subtracted_once':abs((ev+bridge+literal('D35'))-equity-literal('D35'))<1e-9,
      'finance_value_fixed':abs(float(independent['finance_nav']*independent['pb'])-finance)<1e-9,
      'wacc_fixed':independent['wacc']==base_decimal['wacc'],
      'original_book_unchanged':digest(BOOK)==mod.EXPECTED_HASH,
    }
    no_nci_overrides=dict(overrides,**{})
    no_nci_overrides[('DCF','D35')]=0
    no_nci_px=mod.Engine(cells,asts,no_nci_overrides).cell('DCF','D126')
    checks['nci_omission_increases_equity_exactly_once']=abs((no_nci_px-px)-literal('D35')*1e6/shares)<1e-5
    history={str(y):literal(col+'20') for y,col in zip([2023,2024,2025],'DEF')}
    result.update(target_price=target,price_status='Frozen model input, historical close not independently confirmed; external sources conflict',
      cutoff='2026-09-22',forecast_years=list(range(2027,2034)),variable='Uniform annual nonfinancial automobile+other revenue growth; DCF!D47:J47',
      growth=growth,forward_price=px,independent_price=other,roundtrip_relative_error=abs(px/target-1),
      checks=checks,calculation_pass=all(checks.values()),
      base_price=base.cell('DCF','D126'),wacc=float(independent['wacc']),terminal_growth=float(independent['terminal_g']),
      bridge_trillion_krw=dict(nonfinancial_nfa=nfa-finance_nfa,finance_equity=finance,associates=associates,nci_deduction=literal('D35'),total=bridge,industrial_ev=ev,parent_equity=equity),
      shares_million=dict(issued=issued,treasury=treasury,outstanding=shares),
      forecast=mod.plain(independent['forecast']),historical_consolidated_revenue_trillion=history,
      original_model_sha256=digest(BOOK),audit_sha256=digest(AUDIT),solver_sha256=digest(ROOT/'pr/reverse_dcf.py'),
      limitations=['Equal economic rights across common/preferred shares; target is common-price input',
       'Manufacturing scope includes automobile and other businesses, not a separately disclosed manufacturing-only model',
       'NCI book amount held fixed, not economically revalued','Shares as of 2026 Q2, later corporate actions not reconciled',
       'Lease and consolidation methodology warnings preserved','No new Excel save/reopen or live market certification'],
      execution=dict(started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),calculation_seconds=time.monotonic()-start))
    write_json(OUT/'result.json',result)
    print(json.dumps({k:result[k] for k in ['growth','forward_price','roundtrip_relative_error','calculation_pass','execution']}))
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
