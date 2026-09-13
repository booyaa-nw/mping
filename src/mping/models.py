"""宛先ごとの ping 実行状態を保持するデータモデル.

案B(1行 + 大文字/小文字・形状の交互表示)による「動いているかどうかが見た目で
わかる」履歴表示を実現するためのロジックをここに集約する。マークの文字・色は
`mping.config`/`mping.ui` 側の関心事とし、ここでは結果種別と交互表示状態のみを
保持する(表示ロジックとモデルを分離するため)。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class PingOutcome(Enum):
    """1パケットの結果種別."""

    SUCCESS = "success"
    FAIL = "fail"
    EXPIRED = "expired"  # ICMP type==11 (TTL Exceeded) の実応答あり


@dataclass(frozen=True)
class HistoryEntry:
    """履歴1件分。案B(大文字/小文字・形状の交互表示)の状態を保持する."""

    outcome: PingOutcome
    blink: bool  # True/Falseの交互でマークの表示形態を切り替える


@dataclass
class PingTarget:
    """1つの宛先に対する ping 実行状態.

    `destination`はping送信先IPv4アドレス。FQDN指定で名前解決に失敗した場合は
    `None`となり、その宛先は一覧には表示されるがpingは実行されない
    (`display_name`のみで元の入力(FQDN等)を保持する)。
    """

    destination: str | None
    display_name: str
    source_address: str | None = None
    history_size: int = 60

    success_count: int = 0
    fail_count: int = 0
    expired_count: int = 0
    last_rtt: float | None = None

    history: deque[HistoryEntry] = field(default_factory=lambda: deque(maxlen=60))
    _blink: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if self.history.maxlen != self.history_size:
            self.history = deque(self.history, maxlen=self.history_size)

    def _record(self, outcome: PingOutcome, rtt: float | None) -> None:
        entry = HistoryEntry(outcome=outcome, blink=self._blink)
        self._blink = not self._blink
        self.history.append(entry)
        self.last_rtt = rtt
        if outcome is PingOutcome.SUCCESS:
            self.success_count += 1
        elif outcome is PingOutcome.EXPIRED:
            self.expired_count += 1
        else:
            self.fail_count += 1

    def record_success(self, rtt: float | None) -> None:
        """成功パケットを記録する."""
        self._record(PingOutcome.SUCCESS, rtt)

    def record_expired(self, rtt: float | None) -> None:
        """ICMP type==11 (TTL Exceeded) の実応答を記録する.

        オリジナル実装(`multi_ping.py`)の `elif ping_reply['type'] == 11` 分岐に
        対応する。タイムアウトや他の失敗とは区別してカウントする。
        """
        self._record(PingOutcome.EXPIRED, rtt)

    def record_fail(self, rtt: float | None = None) -> None:
        """タイムアウト、またはその他の失敗を記録する."""
        self._record(PingOutcome.FAIL, rtt)

    @property
    def total_count(self) -> int:
        return self.success_count + self.fail_count + self.expired_count
