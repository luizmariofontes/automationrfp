from app.shared.health import get_checkers


def test_liveness(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["env"] == "test"


def test_liveness_alias_na_api(client):
    assert client.get("/api/v1/health").status_code == 200


def test_request_id_e_devolvido(client):
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_readiness_ok(app, client):
    app.dependency_overrides[get_checkers] = lambda: {
        "postgres": lambda s: None,
        "redis": lambda s: None,
    }
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}


def test_readiness_com_dependencia_fora(app, client):
    def falha(_settings):
        raise ConnectionError("sem banco")

    app.dependency_overrides[get_checkers] = lambda: {"postgres": falha, "redis": lambda s: None}
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"] == {"postgres": "falha", "redis": "ok"}
