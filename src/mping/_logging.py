"""アプリケーションログの共通基盤.

ping の実行結果CSV出力 (`mping.logger.ResultLogger`) とは別に、ツール自体の
動作ログ (エラー・警告など) を出力するための最小限のロガー設定ヘルパー。
将来 `common.logging` への移植を想定した自己完結モジュール。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def build_logger(
    name: str,
    *,
    log_dir: Path | None = None,
    level: int = logging.INFO,
    filename: str = "app.log",
) -> logging.Logger:
    """名前付きロガーを構築する.

    `log_dir` を指定した場合はファイル出力ハンドラを追加する(ディレクトリが
    存在しない場合は作成する)。標準エラー出力へのハンドラは常に追加する。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        # 二重登録防止 (再呼び出し時)
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
