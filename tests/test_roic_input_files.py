from bist_terminal.storage.roic_input_files import roic_input_files, roic_input_shard_path


def test_roic_input_shard_path_is_deterministic(tmp_path):
    p=roic_input_shard_path(tmp_path,2026,2)
    assert p.name=="roic_inputs_2026_2.parquet"


def test_roic_input_files_are_sorted(tmp_path):
    d=tmp_path/"data"/"parquet"/"roic_inputs"
    d.mkdir(parents=True)
    (d/"roic_inputs_2026_2.parquet").write_bytes(b"x")
    (d/"roic_inputs_2025_4.parquet").write_bytes(b"x")
    assert [p.name for p in roic_input_files(tmp_path)]==[
        "roic_inputs_2025_4.parquet",
        "roic_inputs_2026_2.parquet",
    ]
