"""ugk/rpc.py — Zero-dep JSON-RPC 2.0 surface (Phase 4 thin adapter, Grundnorm 444).

Exposes the governance kernel over HTTP+JSON using only Python stdlib
(http.server, socketserver, json, threading).

Methods:
  ugk.govern(intent, subject, authority, op, nonce) → verdict
  ugk.status()                                       → kernel snapshot
  ugk.verify()                                       → chain integrity result
  ugk.attest()                                       → 3+1 hash attestation

Replay protection: every ugk.govern call must include a unique `nonce` string.
The server rejects requests with a previously seen nonce (replay=True response).

DKN envelope: govern responses carry `dimension_id` in the authority field.

Phase 4 constraint: NO governance logic here.  All receipts, hashes, and gate
evaluation happen inside GovernanceKernel.execute().  This module parses JSON,
delegates, and serializes.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional


# ---------------------------------------------------------------------------
# JSON-RPC request / response helpers
# ---------------------------------------------------------------------------

def _ok(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str, data: Any = None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


# JSON-RPC 2.0 error codes
_PARSE_ERROR      = -32700
_INVALID_REQUEST  = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS   = -32602
_INTERNAL_ERROR   = -32603
_REPLAY_DETECTED  = -32000   # application-defined


# ---------------------------------------------------------------------------
# UGKRPCServer — in-process JSON-RPC handler (no networking required for tests)
# ---------------------------------------------------------------------------

class UGKRPCServer:
    """JSON-RPC 2.0 handler.  Testable without starting an HTTP server.

    Usage (in-process):
        server = UGKRPCServer(kernel)
        response = server.handle_request('{"jsonrpc":"2.0","method":"ugk.status","params":{},"id":1}')
        result = json.loads(response)

    Usage (HTTP):
        http_server = server.start(host="127.0.0.1", port=7734)  # returns HTTPServer
        http_server.serve_forever()
    """

    def __init__(self, kernel=None, authority: str = "rpc"):
        from ugk.kernel import GovernanceKernel
        self._kernel    = kernel if kernel is not None else GovernanceKernel(authority=authority)
        self._authority = authority
        self._seen_nonces: set[str] = set()   # replay protection (in-memory, session-scoped)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public: handle a raw JSON-RPC 2.0 request string
    # ------------------------------------------------------------------

    def handle_request(self, raw: str) -> str:
        """Parse a JSON-RPC 2.0 request string and return a JSON response string."""
        try:
            req = json.loads(raw)
        except Exception:
            return json.dumps(_err(None, _PARSE_ERROR, "Parse error"))

        req_id  = req.get("id")
        method  = req.get("method", "")
        params  = req.get("params", {})

        if not isinstance(method, str):
            return json.dumps(_err(req_id, _INVALID_REQUEST, "Invalid method"))

        handler = {
            "ugk.govern": self._handle_govern,
            "ugk.status": self._handle_status,
            "ugk.verify": self._handle_verify,
            "ugk.attest": self._handle_attest,
        }.get(method)

        if handler is None:
            return json.dumps(_err(req_id, _METHOD_NOT_FOUND,
                                   f"Method not found: {method!r}"))

        try:
            result = handler(params)
            return json.dumps(_ok(req_id, result))
        except Exception as e:
            return json.dumps(_err(req_id, _INTERNAL_ERROR,
                                   "Internal error", str(e)))

    # ------------------------------------------------------------------
    # Method handlers — all delegate to kernel; no governance logic here
    # ------------------------------------------------------------------

    def _handle_govern(self, params: dict) -> dict:
        from ugk.kernel import (
            GateRefusal, GovernanceNotFounded, UndeclaredOp, KernelInternalOp,
        )
        intent    = params.get("intent", "observe")
        subject   = params.get("subject", "")
        authority = params.get("authority", self._authority)
        op        = params.get("op", "crp_evidence")
        nonce     = params.get("nonce", "")

        # Replay protection
        with self._lock:
            if nonce in self._seen_nonces:
                return {"admitted": False, "error": "replay_detected",
                        "nonce": nonce}
            self._seen_nonces.add(nonce)

        # DKN envelope: append dimension_id to authority
        snap = self._kernel.snapshot_fast()
        dim_id = snap.get("dimension_id", "")
        if dim_id:
            authority = f"{authority}@{dim_id[:16]}"

        try:
            self._kernel.execute(
                op=op, authority=authority,
                parameters={"intent": intent, "subject": subject,
                            "nonce": nonce},
            )
            snap_after = self._kernel.snapshot_fast()
            return {
                "admitted":    True,
                "op":          op,
                "stream_hash": snap_after["stream_hash"],
                "dimension_id": dim_id,
            }
        except GateRefusal as e:
            return {"admitted": False, "reason": str(e)}
        except GovernanceNotFounded as e:
            return {"admitted": False, "error": "governance_not_founded", "detail": str(e)}
        except UndeclaredOp as e:
            return {"admitted": False, "error": "undeclared_op", "detail": str(e)}
        except KernelInternalOp as e:
            return {"admitted": False, "error": "kernel_internal_op", "detail": str(e)}

    def _handle_status(self, params: dict) -> dict:
        snap = self._kernel.snapshot_fast()
        return {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v
                for k, v in snap.items()}

    def _handle_verify(self, params: dict) -> dict:
        ok = self._kernel.store.verify_stream_hash()
        return {
            "chain_intact":  ok,
            "receipt_count": self._kernel.store.receipt_count(),
            "stream_hash":   self._kernel.store.stream_hash(),
        }

    def _handle_attest(self, params: dict) -> dict:
        snap = self._kernel.snapshot()
        return {
            "stream_hash":         snap["stream_hash"],
            "hash_verified":       snap["hash_verified"],
            "law_hash":            snap.get("law_hash", ""),
            "csh_finality_hash":   snap.get("csh_finality_hash", ""),
            "csh_quorum_achieved": snap.get("csh_quorum_achieved", False),
            "mosaic_root":         snap.get("mosaic_root", ""),
            "dimension_id":        snap.get("dimension_id", ""),
        }

    # ------------------------------------------------------------------
    # HTTP server (optional — not needed for gate tests)
    # ------------------------------------------------------------------

    def start(self, host: str = "127.0.0.1", port: int = 7734) -> HTTPServer:
        """Start an HTTP server and return it.  Call serve_forever() or
        serve in a thread.  The caller is responsible for shutdown."""
        rpc_server = self  # capture for handler closure

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body   = self.rfile.read(length).decode("utf-8", errors="replace")
                resp   = rpc_server.handle_request(body)
                resp_b = resp.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp_b)))
                self.end_headers()
                self.wfile.write(resp_b)

            def log_message(self, fmt, *args):
                pass  # suppress default HTTP logging

        server = HTTPServer((host, port), _Handler)
        return server


__all__ = ["UGKRPCServer"]
