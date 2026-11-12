from toolserver.host_guard import check_host, guard_request


def test_default_accepts_localhost_on_listen_port():
    assert check_host("localhost:8080", port=8080) == (200, "ok")


def test_foreign_host_is_rejected():
    status, reason = check_host("attacker.test:8080", port=8080)
    assert status != 200
    assert reason


def test_guard_request_reads_host_header():
    assert guard_request({"Host": "localhost:8080"}, port=8080) == (200, "ok")
