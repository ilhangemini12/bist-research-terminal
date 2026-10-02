"""Probe recent SPK special-disclosure metadata schema only."""
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bist_terminal.providers.spk import SPKRegistryProvider

def main():
    end=date.today()
    start=end-timedelta(days=7)
    p=SPKRegistryProvider(timeout=30)
    topics=p.disclosure_topics()
    rows=p.special_disclosures(dateBegin=start.isoformat(), dateEnd=end.isoformat())
    print("SPK_DISCLOSURE_TOPICS_TYPE",type(topics).__name__)
    print("SPK_DISCLOSURE_TOPICS",json.dumps(topics,ensure_ascii=False)[:4000])
    print("SPK_DISCLOSURES_TYPE",type(rows).__name__)
    if isinstance(rows,list):
        print("SPK_DISCLOSURES_COUNT",len(rows))
        for i,row in enumerate(rows[:8]):
            print(f"SPK_DISCLOSURE_{i}_KEYS",sorted(row.keys()) if isinstance(row,dict) else type(row).__name__)
            print(f"SPK_DISCLOSURE_{i}",json.dumps(row,ensure_ascii=False)[:5000])
    else:
        print("SPK_DISCLOSURES_SAMPLE",json.dumps(rows,ensure_ascii=False)[:5000])

if __name__=="__main__":
    main()
