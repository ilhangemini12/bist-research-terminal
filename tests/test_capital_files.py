from bist_terminal.storage.capital_files import capital_parquet_files, capital_shard_path


def test_capital_shard_path_and_discovery(tmp_path):
    d=tmp_path/"data"/"parquet"/"capital"; d.mkdir(parents=True)
    (d/"capital_050_099.parquet").write_bytes(b"b")
    (d/"capital_000_049.parquet").write_bytes(b"a")
    assert capital_shard_path(tmp_path,0,50).name=="capital_000_049.parquet"
    assert [p.name for p in capital_parquet_files(tmp_path)]==[
        "capital_000_049.parquet","capital_050_099.parquet"
    ]
