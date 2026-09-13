"""宛先リストの解決.

CLI位置引数と `-f/--file` によるリストファイルから宛先一覧を確定する。
重複は最初の出現順を維持したまま排除する。

注記: `-f` の意味づけ(リストファイル)はオリジナル実装(`multi_ping.py`)を踏襲した
想定で設計しているが、旧実装の当該箇所は本セッションでは再確認できていないため、
実装後に旧CLIの `-l/-f` オプションの厳密な挙動と突き合わせて確認すること。
"""

from __future__ import annotations

from pathlib import Path


def _split_item(item: str) -> list[str]:
    """1つの引数(または1行)を`,`区切りで複数宛先に分割する.

    オリジナル実装(`multi_ping.py`)踏襲で、CLI位置引数・リストファイルの各行とも
    `mping 1.1.1.1,8.8.8.8` のようにカンマ区切りで複数宛先をまとめて指定できる。
    前後の空白は除去し、連続カンマ・末尾カンマ等による空要素は無視する。
    """
    return [part.strip() for part in item.split(",") if part.strip()]


def _read_list_file(path: Path) -> list[str]:
    """1行1宛先(または`,`区切りで複数宛先)のリストファイルを読み込む.

    空行と `#` で始まるコメント行は無視する。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        result.extend(_split_item(stripped))
    return result


def resolve_destinations(
    targets: list[str] | None,
    list_file: str | None,
) -> list[str]:
    """位置引数とリストファイルから宛先一覧を確定する(重複は最初の出現順を維持して排除).

    位置引数・リストファイルの各行とも、`,`区切りで複数宛先をまとめて指定できる
    (例: `mping 1.1.1.1,8.8.8.8,google.co.jp`)。
    """
    raw: list[str] = []
    if targets:
        for item in targets:
            raw.extend(_split_item(item))
    if list_file:
        raw.extend(_read_list_file(Path(list_file)))

    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
