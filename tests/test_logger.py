import csv

from common.ping.base import ICMP_TYPE_ECHO_REPLY, PingResult
from mping.logger import ResultLogger
from mping.models import PingOutcome, PingTarget


def _make_logger(tmp_path):
    return ResultLogger(tmp_path / "booyaa_log" / "ping", hostname="nitro5-skull")


def test_filename_matches_hostname_src_dst_convention(tmp_path):
    logger = _make_logger(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", source_address="172.16.201.111")
    result = PingResult(ok=True, rtt=0.03, icmp_type=ICMP_TYPE_ECHO_REPLY, icmp_code=0, reply_from="1.1.1.1")
    logger.log_result(target, result, PingOutcome.SUCCESS)

    expected = tmp_path / "booyaa_log" / "ping" / "nitro5-skull_172.16.201.111_1.1.1.1_log.csv"
    assert expected.exists()


def test_header_written_only_once(tmp_path):
    logger = _make_logger(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", source_address="172.16.201.111")
    result = PingResult(ok=True, rtt=0.03, icmp_type=ICMP_TYPE_ECHO_REPLY, icmp_code=0, reply_from="1.1.1.1")

    logger.log_result(target, result, PingOutcome.SUCCESS)
    logger.log_result(target, result, PingOutcome.SUCCESS)

    path = tmp_path / "booyaa_log" / "ping" / "nitro5-skull_172.16.201.111_1.1.1.1_log.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "start_time,src,dst,result,rtt,type,code,reply_from"
    # ヘッダーは最初の1回だけ。データ行が2行続く。
    assert len(lines) == 3
    assert lines[1].count("start_time") == 0


def test_row_format_matches_expected_columns(tmp_path):
    logger = _make_logger(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", source_address="172.16.201.111")
    result = PingResult(ok=True, rtt=0.037009, icmp_type=0, icmp_code=0, reply_from="1.1.1.1")
    logger.log_result(target, result, PingOutcome.SUCCESS)

    path = tmp_path / "booyaa_log" / "ping" / "nitro5-skull_172.16.201.111_1.1.1.1_log.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, row = rows[0], rows[1]
    assert header == ["start_time", "src", "dst", "result", "rtt", "type", "code", "reply_from"]
    assert row[1:] == ["172.16.201.111", "1.1.1.1", "OK", "0.037009", "0", "0", "1.1.1.1"]


def test_ng_and_expired_labels(tmp_path):
    logger = _make_logger(tmp_path)
    target = PingTarget(destination="1.1.1.1", display_name="1.1.1.1", source_address="172.16.201.111")

    fail_result = PingResult(ok=False, rtt=None, icmp_type=98, icmp_code=0, reply_from=None)
    logger.log_result(target, fail_result, PingOutcome.FAIL)

    expired_result = PingResult(ok=False, rtt=0.5, icmp_type=11, icmp_code=0, reply_from="10.0.0.1")
    logger.log_result(target, expired_result, PingOutcome.EXPIRED)

    path = tmp_path / "booyaa_log" / "ping" / "nitro5-skull_172.16.201.111_1.1.1.1_log.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1][3] == "NG"
    assert rows[1][4] == ""  # timeoutでrtt無し
    assert rows[2][3] == "EXPIRED"


def test_filename_falls_back_to_unknown_when_source_unresolved(tmp_path):
    logger = _make_logger(tmp_path)
    target = PingTarget(destination="8.8.8.8", display_name="8.8.8.8", source_address=None)
    result = PingResult(ok=True, rtt=0.02, icmp_type=0, icmp_code=0, reply_from="8.8.8.8")
    logger.log_result(target, result, PingOutcome.SUCCESS)

    expected = tmp_path / "booyaa_log" / "ping" / "nitro5-skull_unknown_8.8.8.8_log.csv"
    assert expected.exists()
