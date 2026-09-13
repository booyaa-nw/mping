from pathlib import Path

import pytest

from mping.config import load_settings


def test_defaults_when_no_ini_and_no_cli_overrides(tmp_path):
    settings = load_settings(ini_path=tmp_path / "does_not_exist.ini")
    assert settings.ttl == 128
    assert settings.timeout == 1.0
    assert settings.interval == 1.0
    assert settings.size == 60
    assert settings.df is False
    assert settings.result_directory == Path("./booyaa_log/ping")
    assert settings.data_size == 32  # 60 - 28


def test_cli_overrides_take_precedence_over_ini_and_defaults(tmp_path):
    ini_path = tmp_path / "mping.ini"
    ini_path.write_text(
        "[ping]\nttl = 64\ntimeout = 2.0\nretry_count = 5\ninterval = 0.5\nsize = 100\ndf = true\n"
        "[tui]\nview_recent = 40\nview_success = [green]O\nview_fail = [red]X\nview_expired = [yellow]▲\n"
        "[log]\nresult_directory = ./custom_log\nping_success = OK\nping_fail = NG\nping_expired = TTL\n",
        encoding="utf-8",
    )

    settings = load_settings(ini_path=ini_path, ttl=32, size=1500)
    # CLIで指定したものはCLI優先
    assert settings.ttl == 32
    assert settings.size == 1500
    # CLI未指定はiniの値が使われる
    assert settings.timeout == 2.0
    assert settings.df is True
    assert settings.result_directory == Path("./custom_log")


def test_size_below_header_size_raises(tmp_path):
    with pytest.raises(ValueError):
        load_settings(ini_path=tmp_path / "no.ini", size=10)


def test_styled_mark_parses_style_and_plain_mark():
    from mping.config import StyledMark

    styled = StyledMark.parse("[green]O")
    assert styled.style == "green"
    assert styled.mark == "O"

    plain = StyledMark.parse("X")
    assert plain.style is None
    assert plain.mark == "X"
