from bist_terminal.storage.financial_files import financial_parquet_files, financial_shard_path


def test_financial_files_include_base_then_sorted_shards(tmp_path):
    d=tmp_path/"data"/"parquet"
    s=d/"financials"
    s.mkdir(parents=True)
    (d/"financials.parquet").write_bytes(b"base")
    (s/"financials_2024_4_000_322.parquet").write_bytes(b"b")
    (s/"financials_2024_3_000_322.parquet").write_bytes(b"a")
    assert [p.name for p in financial_parquet_files(tmp_path)] == [
        "financials.parquet",
        "financials_2024_3_000_322.parquet",
        "financials_2024_4_000_322.parquet",
    ]


def test_financial_shard_path_is_deterministic(tmp_path):
    p=financial_shard_path(tmp_path,2025,3,0,323)
    assert p.name=="financials_2025_3_000_322.parquet"
