from gateway import create_app


def test_health_and_version():
    app = create_app({})
    assert app.handle("GET", "/health").status == 200
    assert app.handle("GET", "/version").body == {"version": "1.0"}


def test_unknown_path_and_wrong_method():
    app = create_app({})
    assert app.handle("GET", "/nope").status == 404
    assert app.handle("POST", "/health").status == 405


def test_sign_and_fetch_roundtrip():
    app = create_app({"SIGNING_ENABLED": "1"})
    created = app.handle("POST", "/signing/sign", {"document_id": "d1", "signer": "alice"})
    assert created.status < 300
    sig_id = created.body["signature_id"]
    fetched = app.handle("GET", f"/signing/signatures/{sig_id}")
    assert fetched.status == 200
    assert fetched.body["document_id"] == "d1"
