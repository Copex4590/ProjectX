"""Chromium DevTools Protocol client — real network *responses*, not DOM guesses."""

from __future__ import annotations

import json

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket

from camera_hunter.app.webengine_setup import debugging_port
from camera_hunter.engine.classifier import ObservedRequest, should_emit_cdp_response
from camera_hunter.engine.hls_capture import (
    canonical_request_headers,
    cookie_header_from_associated,
    cookie_names_from_header,
)
from camera_hunter.engine.hls_diag import diag

_ATTACH_TYPES = {"page", "iframe", "other", "webview"}


class CdpNetworkMonitor(QObject):
    """Stay attached across navigation, redirects, ads, iframes and popups."""

    response_captured = Signal(object)  # ObservedRequest
    attached_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sockets: dict[str, QWebSocket] = {}
        self._browser_ws: QWebSocket | None = None
        self._browser_ws_url = ""
        self._sessions: set[str] = set()
        self._cmd_id = 0
        self._attached = False
        self._nam = QNetworkAccessManager(self)
        self._pending_reply = None
        self._pending_kind = ""
        self._extra_ct: dict[str, str] = {}
        self._req_gen: dict[str, int] = {}
        self._req_meta: dict[str, dict] = {}
        self._listing_capture = False
        self._generation = 0
        self._poll = QTimer(self)
        self._poll.setInterval(400)
        self._poll.timeout.connect(self._try_attach)

    @property
    def is_attached(self) -> bool:
        return bool(self._sessions) or bool(self._sockets)

    def start(self) -> None:
        if not self._poll.isActive():
            self._poll.start()
        self._try_attach()

    def set_listing_capture(self, enabled: bool) -> None:
        """Listing pages: forward only camera-thumbnail images, not the full network dump."""
        self._listing_capture = bool(enabled)

    def set_generation(self, generation: int) -> None:
        self._generation = int(generation)

    def prepare_for_navigation(self) -> None:
        """Keep Network domain enabled on every attached target after a nav."""
        self.start()
        if self._browser_ws is not None:
            self._send(self._browser_ws, "Target.setAutoAttach", {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            })
            for sid in list(self._sessions):
                self._enable_network(self._browser_ws, sid)
        for ws in list(self._sockets.values()):
            self._enable_network(ws, None)

    def _next_id(self) -> int:
        self._cmd_id += 1
        return self._cmd_id

    def _try_attach(self) -> None:
        if self._pending_reply is not None:
            return
        port = debugging_port()
        if not port:
            return
        if self._browser_ws is None:
            kind, path = "version", "/json/version"
        else:
            kind, path = "list", "/json/list"
        req = QNetworkRequest(QUrl(f"http://127.0.0.1:{port}{path}"))
        reply = self._nam.get(req)
        self._pending_reply = reply
        self._pending_kind = kind
        reply.finished.connect(self._on_json_reply)

    def _on_json_reply(self) -> None:
        reply = self._pending_reply
        kind = self._pending_kind
        self._pending_reply = None
        self._pending_kind = ""
        if reply is None:
            return
        try:
            body = bytes(reply.readAll()).decode("utf-8", errors="replace")
            data = json.loads(body) if body.strip() else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        finally:
            reply.deleteLater()
        if kind == "version" and isinstance(data, dict):
            ws_url = str(data.get("webSocketDebuggerUrl") or "")
            if ws_url and ws_url != self._browser_ws_url:
                self._connect_browser(ws_url)
            return
        if kind != "list" or not isinstance(data, list):
            return
        for target in data:
            if not isinstance(target, dict):
                continue
            ttype = str(target.get("type") or "")
            if ttype not in _ATTACH_TYPES:
                continue
            # Browser auto-attach already owns page targets.
            if ttype == "page" and self._sessions:
                continue
            ws_url = str(target.get("webSocketDebuggerUrl") or "")
            if not ws_url or ws_url in self._sockets:
                continue
            self._connect_page(ws_url)

    def _connect_browser(self, ws_url: str) -> None:
        if self._browser_ws is not None:
            try:
                self._browser_ws.close()
            except Exception:
                pass
            self._browser_ws.deleteLater()
            self._browser_ws = None
        self._browser_ws_url = ws_url
        ws = QWebSocket()
        self._browser_ws = ws
        ws.textMessageReceived.connect(self._on_message)
        ws.connected.connect(self._on_browser_connected)
        ws.disconnected.connect(self._on_browser_disconnected)
        ws.open(QUrl(ws_url))

    def _on_browser_connected(self) -> None:
        ws = self._browser_ws
        if ws is None:
            return
        self._mark_attached()
        self._send(ws, "Target.setDiscoverTargets", {"discover": True})
        self._send(ws, "Target.setAutoAttach", {
            "autoAttach": True,
            "waitForDebuggerOnStart": False,
            "flatten": True,
        })

    def _on_browser_disconnected(self) -> None:
        if self._browser_ws is not None:
            self._browser_ws.deleteLater()
        self._browser_ws = None
        self._browser_ws_url = ""
        self._sessions.clear()
        if not self._sockets and self._attached:
            self._attached = False
            self.attached_changed.emit(False)

    def _connect_page(self, ws_url: str) -> None:
        ws = QWebSocket()
        self._sockets[ws_url] = ws
        ws.textMessageReceived.connect(self._on_message)
        ws.connected.connect(lambda u=ws_url: self._on_page_connected(u))
        ws.disconnected.connect(lambda u=ws_url: self._on_page_disconnected(u))
        ws.open(QUrl(ws_url))

    def _on_page_connected(self, ws_url: str) -> None:
        ws = self._sockets.get(ws_url)
        if ws is None:
            return
        self._mark_attached()
        self._enable_network(ws, None)

    def _on_page_disconnected(self, ws_url: str) -> None:
        ws = self._sockets.pop(ws_url, None)
        if ws is not None:
            ws.deleteLater()
        if not self._sockets and self._browser_ws is None and self._attached:
            self._attached = False
            self.attached_changed.emit(False)

    def _mark_attached(self) -> None:
        was = self._attached
        self._attached = True
        if not was:
            self.attached_changed.emit(True)

    def _enable_network(self, ws: QWebSocket, session_id: str | None) -> None:
        self._send(ws, "Network.enable", session_id=session_id)
        self._send(ws, "Network.setCacheDisabled", {"cacheDisabled": True}, session_id=session_id)
        self._send(ws, "Page.enable", session_id=session_id)

    def _send(
        self,
        ws: QWebSocket,
        method: str,
        params: dict | None = None,
        session_id: str | None = None,
    ) -> None:
        payload: dict = {"id": self._next_id(), "method": method}
        if params:
            payload["params"] = params
        if session_id:
            payload["sessionId"] = session_id
        ws.sendTextMessage(json.dumps(payload))

    def _on_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        method = msg.get("method")
        params = msg.get("params") or {}
        session_id = msg.get("sessionId")
        if method == "Target.attachedToTarget":
            self._on_attached_to_target(params)
        elif method == "Target.targetCreated":
            self._on_target_created(params)
        elif method == "Target.detachedFromTarget":
            sid = str(params.get("sessionId") or "")
            self._sessions.discard(sid)
        elif method == "Network.requestWillBeSent":
            self._handle_request(params)
        elif method == "Network.requestWillBeSentExtraInfo":
            self._handle_request_extra(params)
        elif method == "Network.responseReceived":
            self._handle_response(params)
        elif method == "Network.responseReceivedExtraInfo":
            self._handle_extra_info(params)
        _ = session_id

    def _on_attached_to_target(self, params: dict) -> None:
        session_id = str(params.get("sessionId") or "")
        info = params.get("targetInfo") or {}
        ttype = str(info.get("type") or "")
        if not session_id:
            return
        self._sessions.add(session_id)
        self._mark_attached()
        diag(
            "cdp_target_attached",
            target_type=ttype,
            url=str(info.get("url") or ""),
            sessions=len(self._sessions),
            generation=self._generation,
            listing_capture=self._listing_capture,
        )
        ws = self._browser_ws
        if ws is None:
            return
        if ttype in _ATTACH_TYPES or not ttype:
            self._enable_network(ws, session_id)
        if params.get("waitingForDebugger"):
            self._send(ws, "Runtime.runIfWaitingForDebugger", session_id=session_id)

    def _on_target_created(self, params: dict) -> None:
        info = params.get("targetInfo") or {}
        ttype = str(info.get("type") or "")
        target_id = str(info.get("targetId") or "")
        ws = self._browser_ws
        if ws is None or not target_id or ttype not in _ATTACH_TYPES:
            return
        diag(
            "cdp_target_created",
            target_type=ttype,
            url=str(info.get("url") or ""),
            generation=self._generation,
            listing_capture=self._listing_capture,
        )
        self._send(ws, "Target.attachToTarget", {"targetId": target_id, "flatten": True})

    def _content_type_from_headers(self, headers: object) -> str:
        if not isinstance(headers, dict):
            return ""
        for key, value in headers.items():
            if str(key).lower() == "content-type":
                return str(value)
        return ""

    def _remember_request_generation(self, request_id: str) -> None:
        if not request_id:
            return
        if len(self._req_gen) > 2000:
            self._req_gen.clear()
            self._req_meta.clear()
        self._req_gen[request_id] = self._generation

    def _store_request_meta(self, request_id: str, url: str, params: dict, request: dict) -> dict:
        headers = canonical_request_headers(request.get("headers") or {})
        document_url = str(params.get("documentURL") or "")
        meta = self._req_meta.get(request_id) or {}
        if headers:
            merged = dict(meta.get("headers") or {})
            merged.update(headers)
            meta["headers"] = merged
        if document_url:
            meta["document_url"] = document_url
        meta["url"] = url
        self._req_meta[request_id] = meta
        return meta

    def _emit_hls_request(self, url: str, request_id: str, resource_type: str, meta: dict) -> None:
        headers = dict(meta.get("headers") or {})
        document_url = str(meta.get("document_url") or "")
        diag(
            "cdp_hls_request",
            url=url,
            header_keys=sorted(headers),
            has_cookie="Cookie" in headers,
            cookie_names=cookie_names_from_header(headers.get("Cookie")),
            referer=headers.get("Referer"),
            origin=headers.get("Origin"),
            user_agent=headers.get("User-Agent"),
            document_url=document_url,
            generation=self._req_gen.get(request_id, self._generation),
        )
        self.response_captured.emit(
            ObservedRequest(
                url=url,
                mime_type=None,
                resource_type=resource_type,
                source="NETWORK REQUEST",
                session_id=self._req_gen.get(request_id, self._generation),
                request_headers=headers or None,
                document_url=document_url or None,
            )
        )

    def _handle_request(self, params: dict) -> None:
        request = params.get("request") or {}
        url = str(request.get("url") or "")
        request_id = str(params.get("requestId") or "")
        self._remember_request_generation(request_id)
        if not url:
            return
        lower = url.lower()
        is_stream = ".m3u8" in lower or "mpegurl" in lower or ".mpd" in lower
        if is_stream:
            self._store_request_meta(request_id, url, params, request)
        if self._listing_capture:
            return
        if not is_stream:
            return
        meta = self._req_meta.get(request_id) or {}
        self._emit_hls_request(url, request_id, str(params.get("type") or ""), meta)

    def _handle_request_extra(self, params: dict) -> None:
        request_id = str(params.get("requestId") or "")
        if not request_id:
            return
        meta = self._req_meta.get(request_id)
        extra_headers = canonical_request_headers(params.get("headers") or {})
        associated = cookie_header_from_associated(params.get("associatedCookies") or [])
        if associated and "Cookie" not in extra_headers:
            extra_headers["Cookie"] = associated
        if meta is None:
            if not extra_headers:
                return
            meta = {"headers": extra_headers}
            self._req_meta[request_id] = meta
        elif extra_headers:
            merged = dict(meta.get("headers") or {})
            merged.update(extra_headers)
            meta["headers"] = merged
        url = str(meta.get("url") or "")
        lower = url.lower()
        if self._listing_capture or not url:
            return
        if ".m3u8" not in lower and "mpegurl" not in lower and ".mpd" not in lower:
            return
        if extra_headers.get("Cookie") or associated:
            self._emit_hls_request(url, request_id, "XHR", meta)

    def _handle_extra_info(self, params: dict) -> None:
        request_id = str(params.get("requestId") or "")
        content_type = self._content_type_from_headers(params.get("headers") or {})
        if request_id and content_type:
            if len(self._extra_ct) > 800:
                self._extra_ct.clear()
            self._extra_ct[request_id] = content_type

    def _handle_response(self, params: dict) -> None:
        response = params.get("response") or {}
        url = str(response.get("url") or "")
        if not url:
            return
        request_id = str(params.get("requestId") or "")
        content_type = self._content_type_from_headers(response.get("headers") or {})
        if not content_type and request_id:
            content_type = self._extra_ct.pop(request_id, "")
        mime = (content_type.split(";")[0].strip() if content_type else "") or str(
            response.get("mimeType") or ""
        )
        resource_type = str(params.get("type") or "")
        gen = self._req_gen.pop(request_id, self._generation) if request_id else self._generation
        if gen != self._generation:
            return
        if not should_emit_cdp_response(
            listing_capture=self._listing_capture,
            url=url,
            mime_type=mime,
            resource_type=resource_type,
        ):
            return
        meta = self._req_meta.pop(request_id, {}) if request_id else {}
        self.response_captured.emit(
            ObservedRequest(
                url=url,
                mime_type=mime or None,
                resource_type=resource_type,
                source="NETWORK RESPONSE",
                session_id=gen,
                request_headers=(meta or {}).get("headers"),
                document_url=(meta or {}).get("document_url"),
            )
        )
