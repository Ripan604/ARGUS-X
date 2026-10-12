from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from threading import RLock
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app.main import create_app
from backend.app.core.config import ArgusConfig
from backend.app.models.domain import Experiment
from backend.app.safety.constraints import NoGoRegion
from backend.app.security import NetworkSecurityMiddleware, SecuritySettings
from backend.app.security import network
from backend.run_backend import server_configuration


TOKEN = "test-token-" + "a" * 40
LAN_ORIGIN = "http://192.168.1.5:5173"


@pytest.fixture
def local_app(tmp_path):
    return create_app(tmp_path / "local-security.db", security_settings=SecuritySettings())


@pytest.fixture
def lan_app(tmp_path):
    settings = SecuritySettings.from_environment({
        "ARGUS_NETWORK_MODE": "lan", "ARGUS_BIND_HOST": "0.0.0.0",
        "ARGUS_API_TOKEN": TOKEN, "ARGUS_ALLOWED_ORIGINS": LAN_ORIGIN,
        "ARGUS_ALLOWED_HOSTS": "192.168.1.5",
    })
    return create_app(tmp_path / "lan-security.db", security_settings=settings)


def test_local_demo_remains_usable_and_health_declares_security(local_app):
    with TestClient(local_app, base_url="http://localhost") as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["network_mode"] == "local"
        assert response.json()["authentication_required"] is False
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/materials").status_code == 200


@pytest.mark.parametrize("path,method", [
    ("/sessions", "GET"), ("/sessions", "POST"), ("/devices", "GET"),
    ("/devices/connect", "POST"), ("/api/research/jobs", "POST"),
    ("/api/import", "POST"), ("/api/export/arbitrary", "GET"), ("/docs", "GET"),
])
def test_lan_private_routes_require_authentication_before_validation(lan_app, path, method):
    with TestClient(lan_app, base_url="http://localhost") as client:
        response = client.request(method, path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert client.get("/health").json()["authentication_required"] is True


def test_bearer_token_valid_wrong_non_ascii_and_duplicate(lan_app):
    with TestClient(lan_app, base_url="http://localhost") as client:
        assert client.get("/api/materials", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
        assert client.get("/api/materials", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/api/materials", headers=[(b"Authorization", b"Bearer \xff")]).status_code == 401
        assert client.get("/api/materials", headers=[("Authorization", f"Bearer {TOKEN}"), ("Authorization", f"Bearer {TOKEN}")]).status_code == 401


@pytest.mark.parametrize("origin", ["https://evil.example", "http://192.168.1.66:5173", "null", "http://localhost:9999"])
def test_untrusted_origin_cannot_read_or_mutate_local_instrument(local_app, origin):
    with TestClient(local_app, base_url="http://localhost") as client:
        assert client.get("/api/materials", headers={"Origin": origin}).status_code == 403
        response = client.post("/devices/connect", headers={"Origin": origin}, json={"device": "microphone"})
        assert response.status_code == 403
        assert local_app.state.devices["microphone"].connected is False


def test_exact_cors_preflight_and_readable_authentication_errors(lan_app):
    with TestClient(lan_app, base_url="http://localhost") as client:
        response = client.options("/api/materials", headers={"Origin": LAN_ORIGIN, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == LAN_ORIGIN
        denied = client.get("/api/materials", headers={"Origin": LAN_ORIGIN})
        assert denied.status_code == 401
        assert denied.headers["access-control-allow-origin"] == LAN_ORIGIN
        assert "access-control-allow-credentials" not in denied.headers
        assert client.options("/api/materials", headers={"Origin": "http://192.168.1.66:5173", "Access-Control-Request-Method": "GET"}).status_code == 403


@pytest.mark.parametrize("host", ["evil.example:8000", "localhost.evil.example", "localhost@evil.example", "localhost:invalid", "localhost?query", "localhost#fragment"])
def test_host_header_rebinding_is_rejected(local_app, host):
    with TestClient(local_app, base_url="http://localhost") as client:
        assert client.get("/health", headers={"Host": host}).status_code == 400


def test_ipv6_loopback_host_is_accepted(local_app):
    with TestClient(local_app, base_url="http://localhost") as client:
        assert client.get("/health", headers={"Host": "[::1]"}).status_code == 200


@pytest.mark.parametrize("environment", [
    {"ARGUS_BIND_HOST": "0.0.0.0"}, {"ARGUS_NETWORK_MODE": "public"},
    {"ARGUS_NETWORK_MODE": "lan"}, {"ARGUS_API_TOKEN": "short"},
    {"ARGUS_ALLOWED_ORIGINS": "http://192.168.1.1:5173"},
    {"ARGUS_ALLOWED_ORIGINS": "http://localhost:5173/path"},
    {"ARGUS_ALLOWED_HOSTS": "*"}, {"ARGUS_ALLOWED_HOSTS": "localhost:8000"},
])
def test_insecure_network_configuration_fails_closed(environment):
    with pytest.raises(ValueError):
        SecuritySettings.from_environment(environment)


def test_backend_transport_defaults_are_loopback_and_bound(monkeypatch):
    for key in ("ARGUS_NETWORK_MODE", "ARGUS_BIND_HOST", "ARGUS_API_TOKEN", "ARGUS_ALLOWED_ORIGINS", "ARGUS_ALLOWED_HOSTS", "ARGUS_API_PORT"):
        monkeypatch.delenv(key, raising=False)
    configuration = server_configuration()
    assert configuration["host"] == "127.0.0.1"
    assert configuration["proxy_headers"] is False
    assert configuration["ws_max_size"] == 64 * 1024
    assert configuration["ws_max_queue"] == 8
    monkeypatch.setenv("ARGUS_BIND_HOST", "0.0.0.0")
    with pytest.raises(ValueError, match="requires"):
        server_configuration()


def test_lan_websocket_token_subprotocol_authentication(lan_app):
    with TestClient(lan_app, base_url="http://localhost") as client:
        for path in ("/ws/probe/edge-test", "/ws/session/nonexistent"):
            with pytest.raises(WebSocketDisconnect) as denied:
                with client.websocket_connect("ws://localhost" + path):
                    pass
            assert denied.value.code == 4401
        with client.websocket_connect("ws://localhost/ws/probe/edge-test", subprotocols=["argus", f"argus-token.{TOKEN}"], headers={"Origin": LAN_ORIGIN}) as socket:
            assert socket.accepted_subprotocol == "argus"
            socket.send_json({"type": "hello", "node_type": "edge_laptop"})
            assert socket.receive_json()["type"] == "ack"
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect(f"ws://localhost/ws/probe/edge-test?token={TOKEN}"):
                pass
        assert denied.value.code == 4401


def test_websocket_origin_is_checked_even_with_valid_token(lan_app):
    with TestClient(lan_app, base_url="http://localhost") as client:
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect("ws://localhost/ws/probe/edge-test", subprotocols=["argus", f"argus-token.{TOKEN}"], headers={"Origin": "https://evil.example"}):
                pass
        assert denied.value.code == 4403


def test_websocket_frame_is_bounded_before_json_parsing(local_app):
    with TestClient(local_app, base_url="http://localhost") as client:
        with client.websocket_connect("ws://localhost/ws/probe/oversize-node") as socket:
            socket.send_text("x" * (network.MAX_WEBSOCKET_BYTES + 1))
            with pytest.raises(WebSocketDisconnect) as oversized:
                socket.receive_json()
            assert oversized.value.code == 1009
        assert local_app.state.repository.list_probe_nodes() == []


def test_malformed_binary_and_nested_websocket_messages_do_not_crash_connection(local_app):
    with TestClient(local_app, base_url="http://localhost") as client:
        with client.websocket_connect("ws://localhost/ws/probe/robust-node") as socket:
            socket.send_bytes(b"binary frame")
            assert socket.receive_json()["type"] == "error"
            socket.send_text("not JSON")
            assert socket.receive_json()["type"] == "error"
            socket.send_text("[" * 1500 + "0" + "]" * 1500)
            assert socket.receive_json()["type"] == "error"
            socket.send_json({"type": "heartbeat"})
            assert socket.receive_json()["type"] == "ack"


def test_websocket_connections_and_messages_are_bounded(tmp_path):
    settings = replace(SecuritySettings(), max_websocket_connections=1, max_websocket_messages_per_minute=2)
    app = create_app(tmp_path / "sockets.db", security_settings=settings)
    with TestClient(app, base_url="http://localhost") as client:
        with client.websocket_connect("ws://localhost/ws/probe/first-node") as first:
            with pytest.raises(WebSocketDisconnect) as full:
                with client.websocket_connect("ws://localhost/ws/probe/second-node"):
                    pass
            assert full.value.code == 4429
            for _ in range(2):
                first.send_json({"type": "heartbeat"})
                assert first.receive_json()["type"] == "ack"
            first.send_json({"type": "heartbeat"})
            with pytest.raises(WebSocketDisconnect) as limited:
                first.receive_json()
            assert limited.value.code == 4429
        with client.websocket_connect("ws://localhost/ws/probe/third-node") as recovered:
            recovered.send_json({"type": "heartbeat"})
            assert recovered.receive_json()["type"] == "ack"


def test_declared_and_actual_request_size_are_bounded(local_app, monkeypatch):
    monkeypatch.setattr(network, "MAX_JSON_BYTES", 256)
    with TestClient(local_app, base_url="http://localhost") as client:
        declared = client.post("/sessions", content=b"{}", headers={"Content-Length": "257", "Content-Type": "application/json"})
        assert declared.status_code == 413
        actual = client.post("/sessions", content=json.dumps({"padding": "a" * 300}), headers={"Content-Length": "1", "Content-Type": "application/json"})
        assert actual.status_code == 413
        assert local_app.state.repository.list_sessions() == []
        assert client.post("/sessions", content=b"{}", headers={"Content-Length": "-1"}).status_code == 400
        assert client.post("/sessions", content=b"{}", headers={"Content-Length": "9" * 5000}).status_code == 413


@pytest.mark.parametrize("path", ["/sessions", "/api/research/jobs"])
@pytest.mark.parametrize("limit", [-1, 0, 201, 2_147_483_647])
def test_list_limits_cannot_disable_database_result_bounds(local_app, path, limit):
    with TestClient(local_app, base_url="http://localhost") as client:
        assert client.get(path, params={"limit": limit}).status_code == 422


def test_serial_connection_only_accepts_discovered_ports(local_app, monkeypatch):
    device = local_app.state.devices["serial_probe"]
    monkeypatch.setattr(device, "available_ports", lambda: [{"port": "COM4"}])
    calls = []
    monkeypatch.setattr(device, "connect", lambda **kwargs: calls.append(kwargs) or {"connected": True})
    with TestClient(local_app, base_url="http://localhost") as client:
        assert client.post("/devices/connect", json={"device": "serial_probe", "port": "C:/private.txt"}).status_code == 422
        assert calls == []
        assert client.post("/devices/connect", json={"device": "serial_probe", "port": "COM4"}).status_code == 200
        assert calls[0]["port"] == "COM4"


@pytest.mark.parametrize("unsafe_state", ["emergency_stop", "amplitude", "no_go"])
def test_physical_execution_is_gated_before_device_acquisition(local_app, monkeypatch, unsafe_state):
    experiment = Experiment(0.1, 0.1, 0.9, 0.9, 1200, 3000, 0.9 if unsafe_state == "amplitude" else 0.3, 0.12, "chirp")
    runtime = SimpleNamespace(
        lock=RLock(), emergency_stop={"latched": unsafe_state == "emergency_stop"},
        no_go_regions=[NoGoRegion(0.0, 0.0, 0.2, 0.2)] if unsafe_state == "no_go" else [],
        unavailable_action_keys=set(), engine=SimpleNamespace(config=ArgusConfig(),
            current_recommendation=SimpleNamespace(selected=SimpleNamespace(experiment=experiment))),
    )
    monkeypatch.setattr(local_app.state.manager, "get", lambda session_id: runtime)
    device = local_app.state.devices["serial_probe"]
    device.connected = True
    acquisitions = []
    monkeypatch.setattr(device, "acquire", lambda *args: acquisitions.append(args))
    with TestClient(local_app, base_url="http://localhost") as client:
        response = client.post("/sessions/safe-test/experiments/device", json={"device": "serial_probe"})
        assert response.status_code == (409 if unsafe_state == "emergency_stop" else 422)
        assert acquisitions == []


def test_work_rate_limit_preserves_emergency_stop_access(tmp_path):
    settings = replace(SecuritySettings(), max_work_requests_per_minute=1)
    app = create_app(tmp_path / "rate.db", security_settings=settings)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.post("/api/probe/register", json={"node_id": "node-test", "node_type": "phone"}).status_code == 201
        blocked = client.post("/api/probe/register", json={"node_id": "node-other", "node_type": "phone"})
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == "60"
        # The route runs (404 for this missing session) instead of being throttled.
        assert client.post("/api/sessions/missing/emergency-stop", json={"reason": "operator stop"}).status_code == 404
        assert client.get("/health").status_code == 200


def _scope(path="/sessions", peer="127.0.0.1"):
    return {"type": "http", "http_version": "1.1", "method": "POST", "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": b"", "headers": [(b"host", b"localhost")],
            "server": ("localhost", 8000), "client": (peer, 12345)}


def test_chunked_body_is_limited_before_handler_and_parsing(monkeypatch):
    monkeypatch.setattr(network, "MAX_JSON_BYTES", 8)

    async def exercise():
        calls = []
        outgoing = []
        chunks = iter([{"type": "http.request", "body": b"12345", "more_body": True},
                       {"type": "http.request", "body": b"67890", "more_body": True}])

        async def handler(*args):
            calls.append(True)

        async def receive():
            return next(chunks)

        async def send(message):
            outgoing.append(message)

        await NetworkSecurityMiddleware(handler, SecuritySettings())(_scope(), receive, send)
        assert calls == []
        assert outgoing[0]["status"] == 413

    asyncio.run(exercise())


def test_local_mode_denies_non_loopback_peer_even_with_local_host_header():
    async def exercise():
        outgoing = []

        async def handler(*args):
            pytest.fail("A remote peer must not reach the local API")

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            outgoing.append(message)

        await NetworkSecurityMiddleware(handler, SecuritySettings())(_scope(peer="192.168.1.5"), receive, send)
        assert outgoing[0]["status"] == 403

    asyncio.run(exercise())


def test_concurrent_work_limit_releases_capacity_and_bypasses_emergency_stop():
    async def exercise():
        started = asyncio.Event()
        release = asyncio.Event()
        statuses = []

        async def handler(scope, receive, send):
            if scope["path"] == "/hold":
                started.set()
                await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                statuses.append(message["status"])

        middleware = NetworkSecurityMiddleware(handler, replace(SecuritySettings(), max_concurrent_work=1))
        first = asyncio.create_task(middleware(_scope("/hold"), receive, send))
        await started.wait()
        await middleware(_scope("/work"), receive, send)
        assert statuses == [429]
        await middleware(_scope("/api/sessions/example/emergency-stop"), receive, send)
        assert statuses == [429, 200]
        release.set()
        await first
        await middleware(_scope("/work"), receive, send)
        assert statuses == [429, 200, 200, 200]

    asyncio.run(exercise())
