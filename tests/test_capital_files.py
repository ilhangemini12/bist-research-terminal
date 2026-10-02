from bist_terminal.storage.capital_files import capital_parquet_files, capital_shard_path, load_capital_records
import pandas as pd


def test_capital_shard_path_and_discovery(tmp_path):
    d=tmp_path/"data"/"parquet"/"capital"; d.mkdir(parents=True)
    (d/"capital_050_099.parquet").write_bytes(b"b")
    (d/"capital_000_049.parquet").write_bytes(b"a")
    assert capital_shard_path(tmp_path,0,50).name=="capital_000_049.parquet"
    assert [p.name for p in capital_parquet_files(tmp_path)]==[
        "capital_000_049.parquet","capital_050_099.parquet"
    ]


def test_load_capital_records_accepts_only_explicit_total_share_count(tmp_path):
    d=tmp_path/"data"/"parquet"/"capital"; d.mkdir(parents=True)
    pd.DataFrame([
        {
            "ticker":"THYAO","total_shares":1380000000.0,
            "method":"EXPLICIT_TOTAL_SHARE_COUNT","source_url":"https://kap.example/thy",
            "mkk_member_oid":"1","company_title":"THY","retrieved_at":"2026-10-02T00:00:00Z",
        },
        {
            "ticker":"BAD","total_shares":999.0,
            "method":"SHARE_GROUP_NOMINAL_RATIO","source_url":"https://kap.example/bad",
            "mkk_member_oid":"2","company_title":"BAD","retrieved_at":"2026-10-02T00:00:00Z",
        },
    ]).to_parquet(d/"capital_000_001.parquet",index=False)
    rows=load_capital_records(tmp_path)
    assert set(rows)=={"THYAO"}
    assert rows["THYAO"]["total_shares"]==1380000000.0
    assert rows["THYAO"]["method"]=="EXPLICIT_TOTAL_SHARE_COUNT"
