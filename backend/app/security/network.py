from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass
import ipaddress
import os
import re
import secrets
from threading import Lock
import time
from typing import Mapping
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.websockets import WebSocketDisconnect


MIB = 1024 * 1024
MAX_JSON_BYTES = 16 * MIB
MAX_WAV_BYTES = 10 * MIB
MAX_BUNDLE_BYTES = 50 * MIB
MULTIPART_OVERHEAD_BYTES = 128 * 1024
MAX_WEBSOCKET_BYTES = 64 * 1024
DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_HOSTS = ("localhost", "127.0.0.1", "::1")


def is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as exc:
        raise ValueError("ARGUS_ALLOWED_ORIGINS must contain valid exact HTTP(S) origins") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or "*" in value or any(character.isspace() for character in value)):
        raise ValueError("ARGUS_ALLOWED_ORIGINS must contain exact HTTP(S) origins without paths or wildcards")
    return value.rstrip("/")


def _host(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", value):
            raise ValueError("ARGUS_ALLOWED_HOSTS must contain literal hostnames/IPs without ports or wildcards")
    return value


@dataclass(frozen=True)
class SecuritySettings:
    network_mode: str = "local"
    token: str | None = None
    allowed_origins: tuple[str, ...] = DEFAULT_ORIGINS
    allowed_hosts: tuple[str, ...] = DEFAULT_HOSTS
    max_concurrent_work: int = 4
    max_websocket_connections: int = 16
    max_work_requests_per_minute: int = 60
    max_websocket_messages_per_minute: int = 120

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> SecuritySettings:
        environment = os.environ if environment is None else environment
        mode = environment.get("ARGUS_NETWORK_MODE", "local").strip().lower()
        if mode not in {"local", "lan"}:
            raise ValueError("ARGUS_NETWORK_MODE must be local or lan")
        bind_host = environment.get("ARGUS_BIND_HOST", "127.0.0.1").strip()
        if mode == "local" and not is_loopback_host(bind_host):
            raise ValueError("A non-loopback ARGUS_BIND_HOST requires ARGUS_NETWORK_MODE=lan")
        token = environment.get("ARGUS_API_TOKEN", "").strip() or None
        if token is not None and not re.fullmatch(r"[A-Za-z0-9._~-]{32,256}", token):
            raise ValueError("ARGUS_API_TOKEN must be 32 to 256 URL-safe characters")
        origin_text = environment.get("ARGUS_ALLOWED_ORIGINS", "").strip()
        host_text = environment.get("ARGUS_ALLOWED_HOSTS", "").strip()
        if mode == "lan" and (not token or not origin_text or not host_text):
            raise ValueError("LAN mode requires ARGUS_API_TOKEN, ARGUS_ALLOWED_ORIGINS and ARGUS_ALLOWED_HOSTS")
        origins = tuple(dict.fromkeys((*DEFAULT_ORIGINS, *(_origin(item.strip()) for item in origin_text.split(",") if item.strip()))))
        if mode == "local" and any(not is_loopback_host(urlsplit(item).hostname or "") for item in origins):
            raise ValueError("Non-loopback origins require ARGUS_NETWORK_MODE=lan")
        hosts = tuple(dict.fromkeys((*DEFAULT_HOSTS, *(_host(item) for item in host_text.split(",") if item.strip()))))
        return cls(network_mode=mode, token=token, allowed_origins=origins, allowed_hosts=hosts)

    @property
    def authentication_required(self) -> bool:
        return self.token is not None


class NetworkSecurityMiddleware:
    """Reject untrusted requests before routing, parsing or physical execution.

    Limits are per process. This instrument intentionally runs one ASGI worker;
    multi-worker/public deployment requires a shared limiter and TLS termination.
    """

    def __init__(self, app: ASGIApp, settings: SecuritySettings) -> None:
        self.app = app
        self.settings = settings
        self._lock = Lock()
        self._active_work = 0
        self._active_sockets = 0
        self._work_rates: OrderedDict[str, deque[float]] = OrderedDict()

    def _host_allowed(self, scope: Scope) -> bool:
        values = [value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"host"]
        if len(values) != 1:
            return False
        try:
            parsed = urlsplit("//" + values[0])
            parsed.port
            if (parsed.username is not None or parsed.password is not None or parsed.path
                    or parsed.query or parsed.fragment or any(character.isspace() for character in values[0])):
                return False
            return _host(parsed.hostname or "") in self.settings.allowed_hosts
        except ValueError:
            return False

    def _origin_allowed(self, scope: Scope) -> bool:
        origins = [value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"origin"]
        return not origins or (len(origins) == 1 and origins[0] in self.settings.allowed_origins)

    def _local_peer_allowed(self, scope: Scope) -> bool:
        if self.settings.network_mode != "local":
            return True
        client = scope.get("client")
        if not client:
            return True
        try:
            return ipaddress.ip_address(client[0]).is_loopback
        except ValueError:
            # ASGI in-process clients may use a synthetic peer name. Uvicorn
            # always supplies a numeric peer IP, with proxy headers disabled.
            return True

    def _authenticated(self, scope: Scope) -> bool:
        if self.settings.token is None:
            return True
        headers = [value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"authorization"]
        candidate = headers[0][7:] if len(headers) == 1 and headers[0].startswith("Bearer ") else ""
        if scope["type"] == "websocket" and not candidate:
            candidates = [item.removeprefix("argus-token.") for item in scope.get("subprotocols", []) if item.startswith("argus-token.")]
            candidate = candidates[0] if len(candidates) == 1 and "argus" in scope.get("subprotocols", []) else ""
        return secrets.compare_digest(candidate.encode("utf-8"), self.settings.token.encode("utf-8"))

    @staticmethod
    def _body_limit(path: str) -> int:
        if path == "/api/import":
            return MAX_BUNDLE_BYTES + MULTIPART_OVERHEAD_BYTES
        if path.startswith("/sessions/") and path.endswith("/experiments/upload"):
            return MAX_WAV_BYTES + MULTIPART_OVERHEAD_BYTES
        return MAX_JSON_BYTES

    @staticmethod
    def _work_request(scope: Scope) -> bool:
        # Emergency stop must remain available while measurements/jobs are busy.
        return (scope.get("method") in {"POST", "PUT", "PATCH", "DELETE"}
                and not scope["path"].endswith("/emergency-stop"))

    def _reserve_work(self, scope: Scope) -> bool:
        now = time.monotonic()
        peer = str((scope.get("client") or ("unknown", 0))[0])
        with self._lock:
            if self._active_work >= self.settings.max_concurrent_work:
                return False
            history = self._work_rates.setdefault(peer, deque())
            self._work_rates.move_to_end(peer)
            while history and history[0] <= now - 60:
                history.popleft()
            if len(history) >= self.settings.max_work_requests_per_minute:
                return False
            history.append(now)
            while len(self._work_rates) > 256:
                self._work_rates.popitem(last=False)
            self._active_work += 1
            return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        if not self._host_allowed(scope):
            await self._reject(scope, receive, send, 400, "Untrusted Host header")
            return
        if not self._local_peer_allowed(scope) or not self._origin_allowed(scope):
            await self._reject(scope, receive, send, 403, "Network peer or Origin is not allowed")
            return
        is_preflight = scope["type"] == "http" and scope.get("method") == "OPTIONS" and any(name == b"access-control-request-method" for name, _ in scope.get("headers", []))
        public_health = scope["type"] == "http" and scope["path"] == "/health" and scope.get("method") in {"GET", "HEAD"}
        if not (is_preflight or public_health) and not self._authenticated(scope):
            await self._reject(scope, receive, send, 401, "A valid ARGUS bearer token is required")
            return
        if scope["type"] == "websocket":
            await self._websocket(scope, receive, send)
            return
        work = self._work_request(scope)
        if work and not self._reserve_work(scope):
            await self._reject(scope, receive, send, 429, "Work capacity exceeded; retry later")
            return
        try:
            await self._http(scope, receive, send)
        finally:
            if work:
                with self._lock:
                    self._active_work -= 1

    async def _http(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = self._body_limit(scope["path"])
        lengths = [value for name, value in scope.get("headers", []) if name == b"content-length"]
        if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
            await self._reject(scope, receive, send, 400, "Invalid Content-Length")
            return
        if lengths and (len(lengths[0]) > 20 or int(lengths[0]) > limit):
            await self._reject(scope, receive, send, 413, "Request body exceeds the configured size limit")
            return
        # Buffer bounded chunks before multipart/JSON parsing. This also handles
        # chunked bodies and prevents oversized uploads filling temporary disk.
        chunks: deque[Message] = deque()
        total = 0
        deadline = time.monotonic() + 60
        while True:
            if time.monotonic() >= deadline:
                await self._reject(scope, receive, send, 408, "Request body timed out")
                return
            try:
                message = await asyncio.wait_for(receive(), timeout=max(0.01, min(10, deadline - time.monotonic())))
            except TimeoutError:
                await self._reject(scope, receive, send, 408, "Request body timed out")
                return
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > limit:
                await self._reject(scope, receive, send, 413, "Request body exceeds the configured size limit")
                return
            if message.get("body") or not message.get("more_body", False):
                chunks.append(message)
            if len(chunks) > 8192:
                await self._reject(scope, receive, send, 413, "Request body is excessively fragmented")
                return
            if not message.get("more_body", False):
                break

        async def buffered_receive() -> Message:
            return chunks.popleft() if chunks else await receive()

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = {**message, "headers": [*message.get("headers", []), (b"x-content-type-options", b"nosniff"), (b"cache-control", b"no-store")]}
            await send(message)

        await self.app(scope, buffered_receive, secure_send)

    async def _websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        with self._lock:
            full = self._active_sockets >= self.settings.max_websocket_connections
            if not full:
                self._active_sockets += 1
        if full:
            await send({"type": "websocket.close", "code": 4429, "reason": "Connection capacity exceeded"})
            return
        history: deque[float] = deque()

        async def bounded_receive() -> Message:
            try:
                message = await asyncio.wait_for(receive(), timeout=60)
            except TimeoutError:
                await send({"type": "websocket.close", "code": 4408, "reason": "Connection idle timeout"})
                raise WebSocketDisconnect(4408)
            if message["type"] == "websocket.receive":
                size = len(message.get("bytes") or b"") + len((message.get("text") or "").encode("utf-8"))
                if size > MAX_WEBSOCKET_BYTES:
                    await send({"type": "websocket.close", "code": 1009, "reason": "Message exceeds 64 KiB"})
                    raise WebSocketDisconnect(1009)
                now = time.monotonic()
                while history and history[0] <= now - 60:
                    history.popleft()
                if len(history) >= self.settings.max_websocket_messages_per_minute:
                    await send({"type": "websocket.close", "code": 4429, "reason": "Message rate exceeded"})
                    raise WebSocketDisconnect(4429)
                history.append(now)
            return message

        async def authenticated_send(message: Message) -> None:
            if message["type"] == "websocket.accept" and "argus" in scope.get("subprotocols", []):
                message = {**message, "subprotocol": "argus"}
            await send(message)

        try:
            await self.app(scope, bounded_receive, authenticated_send)
        finally:
            with self._lock:
                self._active_sockets -= 1

    async def _reject(self, scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4401 if status == 401 else 4403, "reason": detail})
            return
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        origin = next((value.decode("latin-1") for name, value in scope.get("headers", []) if name == b"origin"), None)
        if origin in self.settings.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
        if status == 401:
            headers["WWW-Authenticate"] = "Bearer"
        if status == 429:
            headers["Retry-After"] = "60"
        await JSONResponse({"detail": detail}, status_code=status, headers=headers)(scope, receive, send)
