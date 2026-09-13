"""ping 結果のCSVログ出力(現行実装踏襲).

ファイル名: `<実行PC名>_<送信元アドレス>_<宛先>_log.csv`
(例: `nitro5-skull_172.16.201.111_1.1.1.1_log.csv`)

CSV列: `start_time,src,dst,result,rtt,type,code,reply_from`
ヘッダーはファイル新規作成時の最初の1行のみ書き込み、既存ファイルへの追記時は
ヘッダーをスキップする(現行実装踏襲)。
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from common.ping.base import PingResult
from mping.models import PingOutcome, PingTarget

_CSV_HEADER = ["start_time", "src", "dst", "result", "rtt", "type", "code", "reply_from"]


def _sanitize(value: str) -> str:
    """ファイル名に使えない文字(IPv6の`:`等)を安全な文字に置き換える."""
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


class ResultLogger:
    """宛先ごとに1つのCSVファイルへ結果を追記するロガー.

    ログディレクトリはカレントディレクトリからの相対パス(デフォルト
    `./booyaa_log/ping/`)を前提とする。ディレクトリが存在しない場合は
    `mkdir(parents=True, exist_ok=True)` で作成する(旧実装で未作成時に
    エラーになっていた点の修正)。
    """

    def __init__(
        self,
        result_directory: Path,
        *,
        hostname: str,
        success_label: str = "OK",
        fail_label: str = "NG",
        expired_label: str = "EXPIRED",
    ) -> None:
        self._directory = result_directory
        self._hostname = hostname
        self._success_label = success_label
        self._fail_label = fail_label
        self._expired_label = expired_label
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, target: PingTarget) -> Path:
        src = _sanitize(target.source_address or "unknown")
        dst = _sanitize(target.destination)
        return self._directory / f"{self._hostname}_{src}_{dst}_log.csv"

    def _label_for(self, outcome: PingOutcome) -> str:
        return {
            PingOutcome.SUCCESS: self._success_label,
            PingOutcome.FAIL: self._fail_label,
            PingOutcome.EXPIRED: self._expired_label,
        }[outcome]

    def log_result(self, target: PingTarget, result: PingResult, outcome: PingOutcome) -> None:
        """1回分の ping 結果をCSVに追記する."""
        path = self._path_for(target)
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(_CSV_HEADER)
            rtt_str = "" if result.rtt is None else f"{result.rtt:.6f}"
            writer.writerow(
                [
                    datetime.now().isoformat(sep=" ", timespec="microseconds"),
                    target.source_address or "",
                    target.destination,
                    self._label_for(outcome),
                    rtt_str,
                    "" if result.icmp_type is None else result.icmp_type,
                    "" if result.icmp_code is None else result.icmp_code,
                    result.reply_from or "",
                ]
            )
