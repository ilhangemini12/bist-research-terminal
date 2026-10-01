from bist_terminal.financials.quarterly import standalone_quarters, ttm_from_quarters


def rec(year,period,revenue,net_income,assets):
    return {
        'report_period':f'{year}-12-31',
        'payload':{
            'status':'PARSED_HIGH_CONFIDENCE',
            'archive_year':year,
            'archive_period':str(period),
            'statement_scope':'Konsolide',
            'facts':{
                'revenue':revenue,
                'gross_profit':revenue/2,
                'operating_profit':revenue/4,
                'net_income':net_income,
                'cash_from_operations':net_income*2,
                'assets':assets,
                'equity':assets/2,
                'cash':10,
                'current_assets':20,
                'current_liabilities':10,
                'inventories':5,
            },
        },
    }


def test_standalone_quarters_difference_cumulative_flows():
    rows=[
        rec(2025,1,100,10,1000),
        rec(2025,2,250,30,1100),
        rec(2025,3,430,55,1200),
        rec(2025,4,700,90,1300),
    ]
    q=standalone_quarters(rows)
    assert [x['facts']['revenue'] for x in q]==[100,150,180,270]
    assert [x['facts']['net_income'] for x in q]==[10,20,25,35]
    assert [x['facts']['assets'] for x in q]==[1000,1100,1200,1300]


def test_ttm_requires_four_contiguous_quarters_and_sums_flows():
    q=standalone_quarters([
        rec(2025,1,100,10,1000),
        rec(2025,2,250,30,1100),
        rec(2025,3,430,55,1200),
        rec(2025,4,700,90,1300),
    ])
    t=ttm_from_quarters(q)
    assert t['revenue']==700
    assert t['net_income']==90
    assert t['assets']==1300
    assert t['quarters_used']==['2025Q1','2025Q2','2025Q3','2025Q4']


def test_missing_previous_period_does_not_infer_flow():
    q=standalone_quarters([rec(2025,2,250,30,1100)])
    assert q[0]['flow_basis']=='MISSING_PREVIOUS_PERIOD'
    assert q[0]['facts']['revenue'] is None
    assert q[0]['facts']['assets']==1100
