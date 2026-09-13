"""mping CLIエントリポイント."""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import sys
from pathlib import Path

from common.cli import BaseArgumentParser, non_negative_float, positive_int
from common.ping.base import PingResult
from mping.config import load_settings
from mping.destinations import resolve_destinations
from mping.logger import ResultLogger
from mping.models import PingOutcome, PingTarget
from mping.runner import PingRunner, RunnerSettings
from mping.ui import ScreenView

try:
    from common.iptools.host.resolve import is_resolve
    from common.iptools.host.routing import get_my_hostname, get_src_addr
except ImportError:  # common未導入環境でも単体で動作できるようにする
    get_src_addr = None
    get_my_hostname = None
    is_resolve = None


def _resolve_hostname() -> str:
    """ログファイル名に使う実行PC名を取得する(`common.iptools`優先、無ければ標準ライブラリ)."""
    if get_my_hostname is not None:
        result = get_my_hostname()
        if result.ok:
            return result.value
    import socket

    return socket.gethostname()


def _is_ipv4_literal(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def _resolve_target_ip(dest: str) -> str | None:
    """ping送信先IPv4アドレスを確定する.

    `common.ping`(Windows実装: `ws2_32.inet_addr`)はドット付き10進表記の
    IPv4アドレスしか解釈できずDNS解決を行わないため、FQDN指定はここで
    事前にIPv4アドレスへ解決しておく必要がある(解決しないままpingへ渡すと
    `inet_addr`が解釈に失敗し、実際には一切ネットワークに出ないまま
    即座に失敗を繰り返してしまう)。解決できない場合はNoneを返す。
    """
    if _is_ipv4_literal(dest):
        return dest
    if is_resolve is None:
        return None
    result = is_resolve(dest)
    if not result.ok or not result.value.resolvable:
        return None
    for addr in result.value.addresses:
        if _is_ipv4_literal(addr):
            return addr
    # IPv6アドレスしか得られなかった場合(AAAAのみ等)。
    # Windows実装(ctypes+iphlpapi.dll, IPv4のみ)は現状IPv6未対応のため解決失敗として扱う。
    return None


def build_parser() -> BaseArgumentParser:
    parser = BaseArgumentParser(
        prog="mping",
        description="複数宛先へ同時にpingを実行し、結果をリアルタイム表示・CSVログ出力します。",
    )
    parser.add_argument("targets", nargs="*", help="ping対象の宛先(IPアドレス/FQDN)。複数指定可")
    parser.add_argument("-f", "--file", dest="list_file", help="宛先一覧を記載したファイルのパス(1行1宛先)")
    parser.add_argument("--ttl", type=positive_int, default=None, help="TTL (デフォルト: 128 または ini設定)")
    parser.add_argument("--timeout", type=non_negative_float, default=None, help="タイムアウト秒 (デフォルト: 1.0)")
    parser.add_argument("--interval", type=non_negative_float, default=None, help="送信間隔秒 (デフォルト: 1.0)")
    parser.add_argument(
        "--size",
        type=positive_int,
        default=None,
        help="IPパケット全体サイズ(IPヘッダ20+ICMPヘッダ8を含む)。デフォルト60。MTU試験用",
    )
    parser.add_argument("--df", action="store_true", default=None, help="Don't Fragment (フラグメント禁止)")
    parser.add_argument(
        "--log-dir", dest="log_dir", default=None, help="ログ出力先ディレクトリ(デフォルト: ./booyaa_log/ping/)"
    )
    parser.add_argument("--ini", dest="ini_path", default="mping.ini", help="設定ファイルパス(デフォルト: ./mping.ini)")
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    settings = load_settings(
        ini_path=Path(args.ini_path) if args.ini_path else None,
        ttl=args.ttl,
        timeout=args.timeout,
        interval=args.interval,
        size=args.size,
        df=args.df,
        log_dir=args.log_dir,
    )

    destinations = resolve_destinations(args.targets, args.list_file)
    if not destinations:
        print("宛先が指定されていません。", file=sys.stderr)
        return 1

    # `targets`は画面表示対象の全宛先(解決失敗も含む)、`pingable_targets`は
    # 実際にpingを送信する対象(IPv4解決に成功したもの)。名前解決に失敗した
    # FQDNも一覧からは除外せず、Destination列に"(unknown)"(赤字)として
    # 表示し続ける(ping自体は実行しない)。
    targets: list[PingTarget] = []
    pingable_targets: list[PingTarget] = []
    for dest in destinations:
        resolved_ip = _resolve_target_ip(dest)

        source_address = None
        if resolved_ip is not None and get_src_addr is not None:
            result = get_src_addr(resolved_ip)
            if result.ok:
                source_address = result.value

        target = PingTarget(
            destination=resolved_ip,
            display_name=dest,  # 画面にはユーザー指定の表記(FQDN等)をそのまま表示
            source_address=source_address,
            history_size=settings.view_recent,
        )
        targets.append(target)
        if resolved_ip is not None:
            pingable_targets.append(target)
        else:
            print(
                f"警告: 宛先 {dest!r} をIPv4アドレスに解決できないため、一覧には表示しますがpingは実行しません。",
                file=sys.stderr,
            )

    if not pingable_targets:
        print("解決できるIPv4宛先がありませんでした。", file=sys.stderr)
        return 1

    logger = ResultLogger(
        settings.result_directory,
        hostname=_resolve_hostname(),
        success_label=settings.ping_success_label,
        fail_label=settings.ping_fail_label,
        expired_label=settings.ping_expired_label,
    )

    with ScreenView(targets, settings) as view:

        def on_result(target: PingTarget, result: PingResult, outcome: PingOutcome) -> None:
            logger.log_result(target, result, outcome)
            view.refresh()

        runner = PingRunner(
            pingable_targets,
            RunnerSettings(
                ttl=settings.ttl,
                timeout=settings.timeout,
                interval=settings.interval,
                data_size=settings.data_size,
                df=settings.df,
            ),
            on_result=on_result,
        )

        try:
            await runner.run()
        except* (KeyboardInterrupt, asyncio.CancelledError):
            # Ctrl+Cによる終了は、オリジナル実装同様「正常終了扱いでログ出力先を
            # 表示する」UXを維持するため、ここで握りつぶす。
            # (asyncio.TaskGroupは子タスクの例外を必ず ExceptionGroup /
            #  BaseExceptionGroup に包んで再送出するため、素の except では
            #  なく except* (PEP 654) でグループの中身ごとに振り分ける)
            pass
        except* Exception:
            # Ctrl+C以外の例外は握りつぶさず、原因調査のためtracebackを表示する。
            # (以前の実装は BaseException を無条件に握りつぶしており、
            #  ctypes呼び出しの不具合等が無言で消えてしまっていた)
            import traceback

            traceback.print_exc()

    print(f"ping log directory is {settings.result_directory.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
