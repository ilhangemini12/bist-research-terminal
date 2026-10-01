from __future__ import annotations
WEIGHTS={'price_verified':30,'financial_fresh':25,'no_source_conflict':15,'no_missing_periods':15,'corporate_actions_normalized':15}

def data_quality_score(flags:dict[str,bool])->tuple[int,dict[str,int]]:
    parts={k:(w if bool(flags.get(k)) else 0) for k,w in WEIGHTS.items()}
    return sum(parts.values()),parts
