from __future__ import annotations
import json, pathlib, datetime

def write_latest(payload:dict,path='dashboard/data/latest.json'):
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True)
    payload=dict(payload); payload.setdefault('generated_at',datetime.datetime.now(datetime.timezone.utc).isoformat())
    pathlib.Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
