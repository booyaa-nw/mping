"""設定(`mping.ini`)の読み込みと CLI > ini > デフォルト の優先順位解決."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOG_DIR = "./booyaa_log/ping"

# IPヘッダ(20byte, オプション無し) + ICMPヘッダ(8byte) = 28byte
IP_ICMP_HEADER_SIZE = 28

DEFAULT_INI = """\
[ping]
ttl = 128
timeout = 1.0
retry_count = 3
interval = 1.0
size = 60
df = false

[tui]
view_recent = 60
view_success = [green]O
view_fail = [red]X
view_expired = [yellow]▲

[log]
result_directory = ./booyaa_log/ping
ping_success = OK
ping_fail = NG
ping_expired = EXPIRED
"""


@dataclass(frozen=True)
class StyledMark:
    """Rich向けのスタイル指定を含むマーク表記 (`"[green]O"` のような ini 値)."""

    style: str | None
    mark: str

    @classmethod
    def parse(cls, raw: str) -> "StyledMark":
        raw = raw.strip()
        if raw.startswith("[") and "]" in raw:
            style, _, mark = raw[1:].partition("]")
            return cls(style=style or None, mark=mark or "?")
        return cls(style=None, mark=raw or "?")


@dataclass(frozen=True)
class PingSettings:
    """解決済みの設定値一式."""

    ttl: int
    timeout: float
    retry_count: int
    interval: float
    size: int
    df: bool

    view_recent: int
    view_success: StyledMark
    view_fail: StyledMark
    view_expired: StyledMark

    result_directory: Path
    ping_success_label: str
    ping_fail_label: str
    ping_expired_label: str

    @property
    def data_size(self) -> int:
        """ICMPペイロードサイズ (`--size` からIP/ICMPヘッダ分を除いた値)."""
        return self.size - IP_ICMP_HEADER_SIZE


def _load_ini(ini_path: Path | None) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read_string(DEFAULT_INI)
    if ini_path is not None and ini_path.is_file():
        parser.read(ini_path, encoding="utf-8")
    return parser


def load_settings(
    ini_path: Path | None = None,
    *,
    ttl: int | None = None,
    timeout: float | None = None,
    retry_count: int | None = None,
    interval: float | None = None,
    size: int | None = None,
    df: bool | None = None,
    log_dir: str | None = None,
) -> PingSettings:
    """`mping.ini` を読み込み、CLI引数(渡された場合)で上書きして確定させる.

    優先順位: CLI引数 > ini > 組み込みデフォルト。
    """
    parser = _load_ini(ini_path)

    resolved_size = size if size is not None else parser.getint("ping", "size")
    if resolved_size < IP_ICMP_HEADER_SIZE:
        raise ValueError(
            f"--size は{IP_ICMP_HEADER_SIZE}以上を指定してください"
            f"(IPヘッダ20+ICMPヘッダ8): {resolved_size}"
        )

    result_dir = log_dir if log_dir is not None else parser.get("log", "result_directory")

    return PingSettings(
        ttl=ttl if ttl is not None else parser.getint("ping", "ttl"),
        timeout=timeout if timeout is not None else parser.getfloat("ping", "timeout"),
        retry_count=retry_count if retry_count is not None else parser.getint("ping", "retry_count"),
        interval=interval if interval is not None else parser.getfloat("ping", "interval"),
        size=resolved_size,
        df=df if df is not None else parser.getboolean("ping", "df"),
        view_recent=parser.getint("tui", "view_recent"),
        view_success=StyledMark.parse(parser.get("tui", "view_success")),
        view_fail=StyledMark.parse(parser.get("tui", "view_fail")),
        view_expired=StyledMark.parse(parser.get("tui", "view_expired")),
        result_directory=Path(result_dir),
        ping_success_label=parser.get("log", "ping_success"),
        ping_fail_label=parser.get("log", "ping_fail"),
        ping_expired_label=parser.get("log", "ping_expired"),
    )
