import asyncio

from mping.models import PingTarget
from mping.runner import PingRunner, RunnerSettings


def test_loop_for_target_keeps_fixed_cadence_even_when_ping_is_slow():
    """1回のping自体がintervalに近い時間かかっても、次の送信までの待ち時間に
    その分が上乗せされない(旧実装では『timeout + interval』に間隔が伸びてしまい、
    タイムアウトする宛先だけ実行ペースが遅れるバグがあった)ことを検証する。
    """
    target = PingTarget(destination="192.0.2.1", display_name="192.0.2.1")
    settings = RunnerSettings(ttl=64, timeout=0.05, interval=0.05, data_size=32, df=False)
    runner = PingRunner([target], settings)

    call_times: list[float] = []

    async def fake_ping_once(tgt):
        call_times.append(asyncio.get_running_loop().time())
        # 実際のping(タイムアウト待ち等)がinterval近くかかることをシミュレート
        await asyncio.sleep(0.045)

    runner._ping_once = fake_ping_once

    async def run_for_a_bit():
        task = asyncio.create_task(runner._loop_for_target(target))
        await asyncio.sleep(0.32)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_for_a_bit())

    # 0.32s / interval(0.05s) ≒ 6〜7回。旧実装のバグ(実質0.095s間隔)なら3〜4回程度しか呼ばれない。
    assert len(call_times) >= 5

    gaps = [b - a for a, b in zip(call_times, call_times[1:])]
    # 各呼び出し間隔がinterval(0.05s)に近いこと(旧実装のtimeout+interval=0.095s相当には
    # ならないこと)を、スケジューリング誤差を許容しつつ確認する。
    assert all(gap < 0.08 for gap in gaps), gaps
