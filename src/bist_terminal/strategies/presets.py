from __future__ import annotations
import yaml
from bist_terminal.strategies.expression import compile_expression

def load_presets(path='config/presets.yaml'):
    with open(path,encoding='utf-8') as f: return yaml.safe_load(f)['presets']

def explain_match(row:dict,expr:str)->dict:
    fn=compile_expression(expr); return {'matched':fn(row),'formula':expr,'inputs':{k:row.get(k) for k in sorted(fn.required_fields)}}
