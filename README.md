# mping

複数宛先へ同時に ping を実行し、結果をリアルタイム表示・CSV ログ出力する CLI ツール。

- Windows: `ctypes` + `iphlpapi.dll` (`IcmpSendEcho`) で実装 (実装済み)
- Linux: `icmplib` で実装予定 (今回のリニューアルでは未実装・後日対応)

## 使い方

```
mping 192.168.1.1 192.168.1.2 --ttl 64 --interval 1.0
mping -f targets.txt --size 1500 --df
```

## ログ出力

デフォルトでカレントディレクトリ配下 `./booyaa_log/ping/` に宛先ごとの CSV を出力する
(`--log-dir` または `mping.ini` の `[log] result_directory` で変更可能)。

## 設定ファイル (`mping.ini`)

CLI 引数 > `mping.ini` > 組み込みデフォルト の優先順位で設定を解決する。
組み込みデフォルトの内容は `mping.config.DEFAULT_INI` を参照。

## 画面表示 (履歴列)

履歴は 1 行で表示し、同一結果が連続しても「動いていることが見た目で分かる」よう、
成功/失敗/TTL超過それぞれについて大文字/小文字(または記号の形状)を毎パケット交互に
切り替えて表示する(例: `O/o`, `X/x`, `▲/△`)。

## 開発メモ

CLI引数解析基盤・動作ログ基盤・ping実行エンジンは、mping内で自己完結モジュールとして
実装・pytest・実機確認した上で `tools/common` へ移植済み(2026-09-13)。現在は以下のように
`common` 側のモジュールを利用する。

- `common.cli`(`BaseArgumentParser`/`positive_int`/`non_negative_float`)
- `common.logging`(`build_logger`。ただしmping自身は現時点で未使用)
- `common.ping`(`ping_async`)/`common.ping.base`(`PingResult`等)

移植元だった `_cli_base.py`/`_logging.py`/`ping/` パッケージおよび重複していた
`tests/test_cli_base.py`/`tests/test_ping_base.py` は削除済み。`fire_and_forget.py`の
common化は、mping自身が最終的に `asyncio.TaskGroup` 方式を採用し利用しなくなったため
見送り(必要とするツールが出た時点で改めて検討)。
