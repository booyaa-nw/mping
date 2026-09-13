"""複数宛先への並列 ping 実行 (asyncio.TaskGroup ベース)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from common.ping import ping_async
from common.ping.base import ICMP_TYPE_TTL_EXCEEDED, PingResult
from mping.models import PingOutcome, PingTarget

OnResultHook = Callable[[PingTarget, PingResult, PingOutcome], "Awaitable[None] | None"]


@dataclass
class RunnerSettings:
    ttl: int
    timeout: float
    interval: float
    data_size: int
    df: bool


class PingRunner:
    """`asyncio.TaskGroup` で全宛先を並列に周期実行するランナー.

    旧実装の「スレッド + fire_and_forget + (実質未使用の) Lock」に代えて、
    単一イベントループ上の協調スケジューリングにより、明示的なロックなしで
    共有状態(`PingTarget`)への書き込みを安全に行う。
    """

    def __init__(
        self,
        targets: list[PingTarget],
        settings: RunnerSettings,
        on_result: OnResultHook | None = None,
    ) -> None:
        self._targets = targets
        self._settings = settings
        self._on_result = on_result

    async def run(self) -> None:
        """外部からキャンセルされるまで、全宛先への周期実行を継続する."""
        async with asyncio.TaskGroup() as tg:
            for target in self._targets:
                tg.create_task(self._loop_for_target(target))

    async def _loop_for_target(self, target: PingTarget) -> None:
        """一定周期(`interval`)でpingを送信し続ける.

        `await ping_once(); await asyncio.sleep(interval)` という単純な実装だと、
        1回のping自体にかかった時間(タイムアウトで`timeout`秒ブロックする場合等)の
        「後に」さらに`interval`秒待つことになり、タイムアウトする宛先だけ実行間隔が
        `timeout + interval`秒に伸びてしまう(成功する宛先との間で送信ペースがずれる
        不具合があった)。`loop.time()`基準の絶対時刻でスケジュールし、次回発火時刻
        から起算することで、宛先ごとのRTT/タイムアウトの長さに関わらず一定周期を保つ。
        """
        loop = asyncio.get_running_loop()
        next_at = loop.time()
        while True:
            await self._ping_once(target)
            next_at += self._settings.interval
            delay = next_at - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                # 1回のping自体がinterval以上かかった場合、遅れを引きずらないよう
                # 次回の基準時刻を現在時刻にリセットする(すぐ次を送信する)。
                next_at = loop.time()

    async def _ping_once(self, target: PingTarget) -> None:
        result = await ping_async(
            target.destination,
            ttl=self._settings.ttl,
            timeout=self._settings.timeout,
            data_size=self._settings.data_size,
            df=self._settings.df,
        )

        if result.ok:
            outcome = PingOutcome.SUCCESS
            target.record_success(result.rtt)
        elif result.icmp_type == ICMP_TYPE_TTL_EXCEEDED:
            # オリジナル実装 (`multi_ping.py`) の
            # `elif ping_reply['type'] == 11: ... view_expired` に対応。
            # 実際にICMP TTL Exceeded応答を受信した場合のみ「期限切れ」として扱い、
            # 単純なタイムアウトやその他のエラーは通常の失敗としてカウントする。
            outcome = PingOutcome.EXPIRED
            target.record_expired(result.rtt)
        else:
            outcome = PingOutcome.FAIL
            target.record_fail(result.rtt)

        if self._on_result is not None:
            maybe_awaitable = self._on_result(target, result, outcome)
            if maybe_awaitable is not None:
                await maybe_awaitable
