from bist_terminal.quality.data_quality import data_quality_score

def test_quality_score_transparent():
    score,parts=data_quality_score({'price_verified':True,'financial_fresh':True,'no_source_conflict':True,'no_missing_periods':False,'corporate_actions_normalized':True})
    assert score==85 and parts['no_missing_periods']==0
