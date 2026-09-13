"""rich を用いた画面表示 (Option B: 1行 + 大文字/小文字・形状の交互表示)."""

from __future__ import annotations

from rich.live import Live
from rich.table import Table
from rich.text import Text

from mping.config import PingSettings, StyledMark
from mping.models import PingOutcome, PingTarget

_ALT_MARK = {
    PingOutcome.SUCCESS: "o",
    PingOutcome.FAIL: "x",
    PingOutcome.EXPIRED: "△",
}


def _mark_for(outcome: PingOutcome, blink: bool, settings: PingSettings) -> tuple[str, str | None]:
    """(表示文字, style) を返す。blink=Trueの回は基本マークの別形態(交互表示)を使う."""
    styled: StyledMark
    if outcome is PingOutcome.SUCCESS:
        styled = settings.view_success
    elif outcome is PingOutcome.EXPIRED:
        styled = settings.view_expired
    else:
        styled = settings.view_fail

    mark = _ALT_MARK[outcome] if blink else styled.mark
    return mark, styled.style


def render_history(target: PingTarget, settings: PingSettings) -> Text:
    """1宛先分の履歴を、案Bの交互表示でレンダリングする."""
    text = Text()
    for entry in target.history:
        mark, style = _mark_for(entry.outcome, entry.blink, settings)
        text.append(mark, style=style)
    return text


def _format_rtt(target: PingTarget) -> str:
    """直近パケットのRTTを表示用に整形する(タイムアウト時は '-')."""
    if target.last_rtt is None:
        return "-"
    return f"{target.last_rtt * 1000:.1f} ms"


def _destination_cell(target: PingTarget) -> str | Text:
    """Destinationセルを描画する.

    FQDN指定の場合(`display_name`がユーザー入力のFQDNで、`destination`が
    解決後のIPv4アドレスまたは解決失敗を表す`None`)、1行目にFQDN、2行目に
    `(解決後IPアドレス)`または`(unknown)`(解決失敗、赤字)を表示する。
    IPアドレスをそのまま指定した場合(`display_name == destination`)は
    従来通り1行のみ表示する。
    """
    if target.display_name == target.destination:
        return target.display_name

    text = Text(target.display_name)
    text.append("\n")
    if target.destination is None:
        text.append("(unknown)", style="red")
    else:
        text.append(f"({target.destination})")
    return text


def _ok_ng_cell(target: PingTarget) -> Text:
    """OK/NGを1列にまとめて表示する(OK: 緑、NG: 赤、`OK/NG`形式)."""
    text = Text()
    text.append(str(target.success_count), style="green")
    text.append("/")
    text.append(str(target.fail_count + target.expired_count), style="red")
    return text


def build_table(targets: list[PingTarget], settings: PingSettings) -> Table:
    """宛先一覧テーブルを構築する.

    列: 宛先アドレス / 送信元アドレス / OK・NG(1列) / RTT(直近パケット) / 履歴
    (期限切れ(ICMP type==11)はNGに含めてカウントしつつ、履歴では▲/△の
    マークで区別して表示する)
    """
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Destination")
    table.add_column("Source")
    table.add_column("OK/NG", justify="right")
    table.add_column("RTT", justify="right")
    table.add_column("History", overflow="fold")

    for target in targets:
        table.add_row(
            _destination_cell(target),
            target.source_address or "-",
            _ok_ng_cell(target),
            _format_rtt(target),
            render_history(target, settings),
        )
    return table


class ScreenView:
    """`rich.live.Live` によるリアルタイム表示.

    `screen=False, transient=False` により、実行完了後も最後の描画内容が
    画面に残ったままになる(要件: 「実行完了後画面がクリアされないこと」)。
    """

    def __init__(
        self,
        targets: list[PingTarget],
        settings: PingSettings,
        *,
        refresh_per_second: float = 4.0,
    ) -> None:
        self._targets = targets
        self._settings = settings
        self._live = Live(
            build_table(self._targets, self._settings),
            screen=False,
            transient=False,
            refresh_per_second=refresh_per_second,
        )

    def __enter__(self) -> "ScreenView":
        self._live.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._live.__exit__(*exc_info)

    def refresh(self) -> None:
        self._live.update(build_table(self._targets, self._settings))
