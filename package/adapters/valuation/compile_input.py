"""Expand explicitly chosen provenance bases into canonical valuation inputs.

No methods, financial numbers, source judgments or review approvals are inferred.
Analysts provide a compact input tree and shared full provenance bases; code
assembles repetitive metadata and validates the same existing input contract.
"""
import argparse,copy,json
from pathlib import Path
try:from .schema_tools import validate_schema
except ImportError:from schema_tools import validate_schema

META={'kind','source','as_of','unit','rationale'}
def compile_input(compact):
 if not isinstance(compact,dict) or set(compact)!={'bases','input'}:raise ValueError('Explicit bases and input tree required')
 bases=compact['bases']
 if not isinstance(bases,dict):raise ValueError('Provenance registry required')
 for name,basis in bases.items():
  if not isinstance(basis,dict) or set(basis)!=META:raise ValueError('Complete provenance without review override required: '+name)
 def expand(value):
  if isinstance(value,list):return [expand(x) for x in value]
  if not isinstance(value,dict):return value
  if '$basis' in value:
   if set(value)!={'$basis','value'} or value['$basis'] not in bases:raise ValueError('Known exact provenance basis and explicit value required')
   result=copy.deepcopy(bases[value['$basis']]);result['value']=value['value']
   result['review']={'status':'unreviewed','reviewer':'','reference':''}
   return result
  if {'value','source','kind'}.issubset(value):raise ValueError('Typed atoms must use a registered basis; embedded review declarations refused')
  return {k:expand(v) for k,v in value.items()}
 result=expand(compact['input']);validate_schema(result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('compact',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 data=compile_input(json.loads(a.compact.read_text()))
 with a.out.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({'status':'schema_valid','out':str(a.out),'financial_review':'not_performed'}))
