from mping.config import load_settings
from mping.models import PingTarget
from mping.ui import _destination_cell, _ok_ng_cell, build_table, render_history


def _settings(tmp_path):
    return load_settings(ini_path=tmp_path / "no.ini")


def test_render_history_alternates_case_for_repeated_success(tmp_path):
    settings = _settings(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_success(0.01)
    target.record_success(0.01)
    target.record_success(0.01)
    text = render_history(target, settings)
    assert text.plain == "OoO"


def test_render_history_alternates_shape_for_expired(tmp_path):
    settings = _settings(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_expired(0.2)
    target.record_expired(0.2)
    text = render_history(target, settings)
    assert text.plain == "▲△"


def test_build_table_has_expected_columns(tmp_path):
    settings = _settings(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", source_address="10.0.0.1")
    target.record_success(0.01)
    table = build_table([target], settings)
    headers = [col.header for col in table.columns]
    assert headers == ["Destination", "Source", "OK/NG", "RTT", "History"]


def test_build_table_folds_expired_into_ng_and_shows_latest_rtt(tmp_path):
    settings = _settings(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_fail()
    target.record_expired(0.123)
    table = build_table([target], settings)
    ok_ng_cell = list(table.columns[2].cells)[0]
    rtt_cell = list(table.columns[3].cells)[0]
    assert ok_ng_cell.plain == "0/2"  # success(0) / fail(1)+expired(1)
    assert rtt_cell == "123.0 ms"


def test_ok_ng_cell_colors_success_green_and_failure_red():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    target.record_success(0.01)
    target.record_success(0.01)
    target.record_fail()
    text = _ok_ng_cell(target)
    assert text.plain == "2/1"
    spans = {(s.start, s.end): s.style for s in text.spans}
    assert spans[(0, 1)] == "green"
    assert spans[(2, 3)] == "red"


def test_destination_cell_is_plain_string_for_ip_literal():
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1")
    cell = _destination_cell(target)
    assert cell == "1.1.1.1"


def test_destination_cell_shows_resolved_ip_for_fqdn():
    target = PingTarget(destination="142.251.23.94", display_name="google.co.jp")
    cell = _destination_cell(target)
    assert cell.plain == "google.co.jp\n(142.251.23.94)"


def test_destination_cell_shows_unknown_in_red_when_unresolved():
    target = PingTarget(destination=None, display_name="hogehoge")
    cell = _destination_cell(target)
    assert cell.plain == "hogehoge\n(unknown)"
    unknown_start = len("hogehoge\n")
    spans = {(s.start, s.end): s.style for s in cell.spans}
    assert spans[(unknown_start, len(cell.plain))] == "red"
