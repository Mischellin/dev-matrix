import pytest
from toolserver.host_guard import check_host, guard_request

ALLOWED = ["tools.example.test", "*.apps.example.test", "[::1]:8080", "api.example.test:8443"]


def test_exact_host_any_port_case_insensitive():
    assert check_host("tools.example.test", ["Tools.Example.TEST"])[0] == 200
    assert check_host("TOOLS.example.test:9000", ALLOWED)[0] == 200


def test_pattern_port_must_match():
    assert check_host("api.example.test:8443", ALLOWED)[0] == 200
    assert check_host("api.example.test:8444", ALLOWED)[0] == 421
    assert check_host("api.example.test", ALLOWED)[0] == 421


def test_wildcard_subdomains():
    assert check_host("a.apps.example.test", ALLOWED)[0] == 200
    assert check_host("a.b.apps.example.test:81", ALLOWED)[0] == 200
    assert check_host("apps.example.test", ALLOWED)[0] == 421
    assert check_host("evil-apps.example.test", ALLOWED)[0] == 421
    assert check_host("a.apps.example.test.evil.test", ALLOWED)[0] == 421


def test_wildcard_with_port():
    pats = ["*.example.test:8443"]
    assert check_host("x.example.test:8443", pats)[0] == 200
    assert check_host("x.example.test:80", pats)[0] == 421


def test_default_port_normalisation():
    assert check_host("tools.example.test", ["tools.example.test:80"])[0] == 200
    assert check_host("tools.example.test:80", ["tools.example.test:80"])[0] == 200
    assert check_host("tools.example.test", ["tools.example.test:443"], default_port=443)[0] == 200
    assert check_host("tools.example.test", ["tools.example.test:443"])[0] == 421


def test_ipv6_literals():
    assert check_host("[::1]:8080", ALLOWED)[0] == 200
    assert check_host("[0:0:0:0:0:0:0:1]:8080", ALLOWED)[0] == 200
    assert check_host("[::1]:9090", ALLOWED)[0] == 421
    assert check_host("[::2]:8080", ALLOWED)[0] == 421
    assert check_host("::1", ALLOWED)[0] == 400
    assert check_host("[::1", ALLOWED)[0] == 400


def test_missing_or_blank_host_is_400():
    for value in (None, "", "   "):
        status, reason = check_host(value, ALLOWED)
        assert status == 400
        assert reason


def test_malformed_host_is_400():
    for value in [
        "user@tools.example.test",
        "tools.example.test/path",
        "tools.example.test?x=1",
        "tools.example.test#frag",
        "tools.example.test:",
        "tools.example.test:http",
        "tools.example.test:70000",
        "tools .example.test",
    ]:
        assert check_host(value, ["tools.example.test"])[0] == 400


def test_rebinding_hosts_rejected_with_421():
    for value in ("tools.example.test.evil.test", "evil.test", "10.0.0.5:8080"):
        assert check_host(value, ALLOWED)[0] == 421


def test_nonempty_allow_list_replaces_loopback_default():
    assert check_host("localhost:8080", ["tools.example.test"], port=8080)[0] == 421
    assert check_host("localhost:8080", port=8080)[0] == 200


def test_empty_allow_list_loopback_variants():
    assert check_host("127.0.0.1:8080", port=8080)[0] == 200
    assert check_host("[::1]:8080", port=8080)[0] == 200
    assert check_host("LOCALHOST:8080", port=8080)[0] == 200
    assert check_host("localhost:9999", port=8080)[0] == 421
    assert check_host("evil.test:8080", port=8080)[0] == 421


def test_guard_request_and_invalid_pattern():
    assert guard_request({"HOST": "tools.example.test"}, ALLOWED)[0] == 200
    assert guard_request({"host": "evil.test"}, ALLOWED)[0] == 421
    assert guard_request({"Accept": "*/*"}, ALLOWED)[0] == 400
    with pytest.raises(ValueError):
        check_host("tools.example.test", ["bad host!"])
