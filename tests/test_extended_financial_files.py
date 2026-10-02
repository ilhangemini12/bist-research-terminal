from bist_terminal.storage.extended_financial_files import extended_metric_files, extended_metric_shard_path


def test_extended_metric_paths_are_period_immutable(tmp_path):
    d=tmp_path/"data"/"parquet"/"extended_financials"
    d.mkdir(parents=True)
    (d/"extended_financials_2025_4.parquet").write_bytes(b"x")
    (d/"extended_financials_2025_2.parquet").write_bytes(b"y")
    assert [p.name for p in extended_metric_files(tmp_path)]==[
        "extended_financials_2025_2.parquet",
        "extended_financials_2025_4.parquet",
    ]
    assert extended_metric_shard_path(tmp_path,2026,2).name=="extended_financials_2026_2.parquet"
