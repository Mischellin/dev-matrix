from gateway import create_app

SIGN = {"document_id": "doc-1", "signer": "alice"}


def signing_paths(app):
    return [path for _, path in app.routes() if path.startswith("/signing")]


def test_disabled_by_default_returns_404():
    app = create_app({})
    assert app.handle("POST", "/signing/sign", SIGN).status == 404
    assert app.handle("GET", "/signing/signatures/sig-1").status == 404
    assert app.handle("POST", "/signing/verify", {"signature_id": "sig-1"}).status == 404


def test_disabled_hides_routes_and_description():
    app = create_app({"SIGNING_ENABLED": "0"})
    assert signing_paths(app) == []
    assert not [p for p in app.describe()["paths"] if p.startswith("/signing")]


def test_enabled_lists_routes_and_description():
    app = create_app({"SIGNING_ENABLED": "true"})
    assert ("POST", "/signing/sign") in app.routes()
    assert ("POST", "/signing/verify") in app.routes()
    assert ("GET", "/signing/signatures/{signature_id}") in app.routes()
    assert app.describe()["paths"]["/signing/sign"] == ["post"]
    assert app.handle("POST", "/signing/sign", SIGN).status == 201


def test_truthy_values_enable():
    for value in ["1", "true", "TRUE", "Yes", "on", "ON", " on "]:
        app = create_app({"SIGNING_ENABLED": value})
        assert app.handle("POST", "/signing/sign", SIGN).status == 201, value


def test_invalid_or_falsy_values_disable():
    for value in ["0", "false", "no", "off", "", "enabled", "2", "truee", "y"]:
        app = create_app({"SIGNING_ENABLED": value})
        assert app.handle("POST", "/signing/sign", SIGN).status == 404, value
        assert signing_paths(app) == [], value


def test_two_apps_with_different_envs_coexist():
    on = create_app({"SIGNING_ENABLED": "1"})
    off = create_app({"SIGNING_ENABLED": "0"})
    assert on.handle("POST", "/signing/sign", SIGN).status == 201
    assert off.handle("POST", "/signing/sign", SIGN).status == 404
    assert signing_paths(on) and not signing_paths(off)


def test_flag_evaluated_at_construction_only():
    env = {"SIGNING_ENABLED": "0"}
    app = create_app(env)
    env["SIGNING_ENABLED"] = "1"
    assert app.handle("POST", "/signing/sign", SIGN).status == 404
    env2 = {"SIGNING_ENABLED": "1"}
    app2 = create_app(env2)
    env2["SIGNING_ENABLED"] = "0"
    assert app2.handle("POST", "/signing/sign", SIGN).status == 201


def test_default_env_is_process_environment_at_construction(monkeypatch):
    monkeypatch.setenv("SIGNING_ENABLED", "0")
    off = create_app()
    monkeypatch.setenv("SIGNING_ENABLED", "yes")
    on = create_app()
    assert off.handle("POST", "/signing/sign", SIGN).status == 404
    assert on.handle("POST", "/signing/sign", SIGN).status == 201


def test_other_routes_unaffected():
    for flag in ["0", "1"]:
        app = create_app({"SIGNING_ENABLED": flag})
        assert app.handle("GET", "/health").body == {"status": "ok"}
        assert app.handle("GET", "/version").status == 200
        assert app.handle("POST", "/health").status == 405
        assert app.handle("GET", "/nope").status == 404
        assert ("GET", "/health") in app.routes()
        assert "/version" in app.describe()["paths"]


def test_sign_validation_status_codes():
    app = create_app({"SIGNING_ENABLED": "1"})
    assert app.handle("POST", "/signing/sign", None).status == 400
    assert app.handle("POST", "/signing/sign", ["x"]).status == 400
    for bad in (
        {},
        {"document_id": "d"},
        {"signer": "a"},
        {"document_id": "", "signer": "a"},
        {"document_id": "d", "signer": "  "},
        {"document_id": 5, "signer": "a"},
    ):
        assert app.handle("POST", "/signing/sign", bad).status == 422, bad


def test_sign_and_fetch_signature():
    app = create_app({"SIGNING_ENABLED": "on"})
    created = app.handle("POST", "/signing/sign", SIGN)
    assert created.status == 201
    sig_id = created.body["signature_id"]
    fetched = app.handle("GET", f"/signing/signatures/{sig_id}")
    assert fetched.status == 200
    assert fetched.body["document_id"] == "doc-1"
    assert fetched.body["signer"] == "alice"
    assert app.handle("GET", "/signing/signatures/missing").status == 404


def test_verify_status_codes():
    app = create_app({"SIGNING_ENABLED": "1"})
    sig_id = app.handle("POST", "/signing/sign", SIGN).body["signature_id"]
    ok = app.handle("POST", "/signing/verify", {"signature_id": sig_id})
    assert ok.status == 200 and ok.body["valid"] is True
    assert app.handle("POST", "/signing/verify", {"signature_id": "nope"}).status == 404
    assert app.handle("POST", "/signing/verify", {}).status == 422
    assert app.handle("POST", "/signing/verify", None).status == 400


def test_signature_state_is_per_app():
    a = create_app({"SIGNING_ENABLED": "1"})
    b = create_app({"SIGNING_ENABLED": "1"})
    sig_id = a.handle("POST", "/signing/sign", SIGN).body["signature_id"]
    assert b.handle("GET", f"/signing/signatures/{sig_id}").status == 404
