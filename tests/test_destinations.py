from mping.destinations import resolve_destinations


def test_resolve_from_cli_targets_only():
    result = resolve_destinations(["1.1.1.1", "8.8.8.8"], None)
    assert result == ["1.1.1.1", "8.8.8.8"]


def test_resolve_dedups_preserving_first_occurrence_order():
    result = resolve_destinations(["1.1.1.1", "8.8.8.8", "1.1.1.1"], None)
    assert result == ["1.1.1.1", "8.8.8.8"]


def test_resolve_from_list_file(tmp_path):
    list_file = tmp_path / "targets.txt"
    list_file.write_text("192.168.1.1\n# comment\n\n192.168.1.2\n", encoding="utf-8")
    result = resolve_destinations(None, str(list_file))
    assert result == ["192.168.1.1", "192.168.1.2"]


def test_resolve_combines_cli_and_file_dedup(tmp_path):
    list_file = tmp_path / "targets.txt"
    list_file.write_text("192.168.1.1\n", encoding="utf-8")
    result = resolve_destinations(["192.168.1.1", "10.0.0.1"], str(list_file))
    assert result == ["192.168.1.1", "10.0.0.1"]


def test_resolve_with_nothing_returns_empty_list():
    assert resolve_destinations(None, None) == []
    assert resolve_destinations([], None) == []


def test_resolve_splits_comma_separated_cli_arg():
    # `mping 1.1.1.1,8.8.8.8,google.co.jp` のように1つの引数にまとめて指定するケース
    # (オリジナル実装踏襲)。
    result = resolve_destinations(["1.1.1.1,192.0.2.1,1.0.0.1,8.8.8.8,8.8.4.4,google.co.jp"], None)
    assert result == ["1.1.1.1", "192.0.2.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "google.co.jp"]


def test_resolve_splits_comma_separated_ignores_surrounding_whitespace_and_empty_parts():
    result = resolve_destinations(["1.1.1.1, 8.8.8.8 ,,9.9.9.9,"], None)
    assert result == ["1.1.1.1", "8.8.8.8", "9.9.9.9"]


def test_resolve_splits_comma_across_multiple_cli_args():
    result = resolve_destinations(["1.1.1.1,8.8.8.8", "9.9.9.9"], None)
    assert result == ["1.1.1.1", "8.8.8.8", "9.9.9.9"]


def test_resolve_dedups_across_comma_split_values():
    result = resolve_destinations(["1.1.1.1,8.8.8.8,1.1.1.1"], None)
    assert result == ["1.1.1.1", "8.8.8.8"]


def test_resolve_splits_comma_separated_list_file_lines(tmp_path):
    list_file = tmp_path / "targets.txt"
    list_file.write_text("192.168.1.1,192.168.1.2\n# comment\n\n10.0.0.1\n", encoding="utf-8")
    result = resolve_destinations(None, str(list_file))
    assert result == ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
