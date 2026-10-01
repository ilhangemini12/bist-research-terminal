from pathlib import Path

from bist_terminal.storage.history_files import history_parquet_files, history_shard_path


def test_history_files_include_base_then_sorted_shards(tmp_path):
    root=tmp_path
    d=root/"data"/"parquet"
    h=d/"history"
    h.mkdir(parents=True)
    (d/"daily_ohlcv.parquet").write_bytes(b"base")
    (h/"daily_ohlcv_155_204.parquet").write_bytes(b"b")
    (h/"daily_ohlcv_105_154.parquet").write_bytes(b"a")
    assert [p.name for p in history_parquet_files(root,"daily_ohlcv")] == [
        "daily_ohlcv.parquet",
        "daily_ohlcv_105_154.parquet",
        "daily_ohlcv_155_204.parquet",
    ]


def test_history_shard_path_is_bounded_and_deterministic(tmp_path):
    p=history_shard_path(tmp_path,"corporate_actions",105,50)
    assert p.name == "corporate_actions_105_154.parquet"
