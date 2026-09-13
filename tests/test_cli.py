import mping.cli as cli_module


def test_is_ipv4_literal_true_for_dotted_quad():
    assert cli_module._is_ipv4_literal("1.1.1.1") is True


def test_is_ipv4_literal_false_for_fqdn():
    assert cli_module._is_ipv4_literal("google.co.jp") is False


def test_is_ipv4_literal_false_for_ipv6():
    assert cli_module._is_ipv4_literal("::1") is False


def test_resolve_target_ip_returns_literal_as_is():
    assert cli_module._resolve_target_ip("8.8.8.8") == "8.8.8.8"


def test_resolve_target_ip_picks_ipv4_when_mixed_with_ipv6(monkeypatch):
    # FQDNのgetaddrinfoがIPv6/IPv4混在で返ってきても、Windows実装(IPv4のみ対応)向けに
    # IPv4アドレスを選ぶことを確認する。
    class FakeCheck:
        resolvable = True
        addresses = ("2001:db8::1", "93.184.216.34")

    class FakeResult:
        ok = True
        value = FakeCheck()

    monkeypatch.setattr(cli_module, "is_resolve", lambda fqdn: FakeResult())
    assert cli_module._resolve_target_ip("example.com") == "93.184.216.34"


def test_resolve_target_ip_none_when_unresolvable(monkeypatch):
    class FakeCheck:
        resolvable = False
        addresses = ()

    class FakeResult:
        ok = True
        value = FakeCheck()

    monkeypatch.setattr(cli_module, "is_resolve", lambda fqdn: FakeResult())
    assert cli_module._resolve_target_ip("no-such-host.invalid") is None


def test_resolve_target_ip_none_when_only_ipv6_available(monkeypatch):
    # IPv6アドレスしか得られない場合、Windows実装(iphlpapi/IPv4のみ)では
    # pingできないため、解決失敗として扱う。
    class FakeCheck:
        resolvable = True
        addresses = ("2001:db8::1",)

    class FakeResult:
        ok = True
        value = FakeCheck()

    monkeypatch.setattr(cli_module, "is_resolve", lambda fqdn: FakeResult())
    assert cli_module._resolve_target_ip("ipv6-only.example") is None


def test_resolve_target_ip_none_when_is_resolve_unavailable(monkeypatch):
    monkeypatch.setattr(cli_module, "is_resolve", None)
    assert cli_module._resolve_target_ip("example.com") is None
