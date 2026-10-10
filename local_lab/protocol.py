"""Length-prefixed, bounded TCP message framing helpers."""
from __future__ import annotations

import hashlib
import json
import re
import socket
import struct
from typing import Any

MAX_HEADER_BYTES = 16 * 1024
DEFAULT_MAX_TRANSFER_BYTES = 10 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class ProtocolError(Exception):
    """Raised for malformed or unsafe wire data."""


def recv_exact(sock: socket.socket, size: int) -> bytes:
    if size < 0:
        raise ProtocolError("negative read size")
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before the complete frame arrived")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(sock: socket.socket, header: dict[str, Any], payload: bytes = b"") -> None:
    data = dict(header)
    data["payload_size"] = len(payload)
    encoded = json.dumps(data, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_HEADER_BYTES:
        raise ProtocolError("header is too large")
    sock.sendall(struct.pack("!I", len(encoded)) + encoded + payload)


def recv_frame(sock: socket.socket, max_payload_bytes: int = DEFAULT_MAX_TRANSFER_BYTES) -> tuple[dict[str, Any], bytes]:
    header_size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 1 <= header_size <= MAX_HEADER_BYTES:
        raise ProtocolError("invalid header length")
    try:
        header = json.loads(recv_exact(sock, header_size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid JSON header") from exc
    if not isinstance(header, dict):
        raise ProtocolError("header must be a JSON object")
    size = header.get("payload_size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > max_payload_bytes:
        raise ProtocolError("payload size is invalid or exceeds the configured limit")
    return header, recv_exact(sock, size)


def sanitize_filename(name: str) -> str:
    """Return a safe basename, rejecting empty, traversal-like, or unusable names."""
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ProtocolError("filename is empty or invalid")
    # Reject paths rather than silently accepting their final component.
    if "/" in name or "\\" in name or ".." in name:
        raise ProtocolError("path separators and traversal names are not allowed")
    cleaned = _SAFE_NAME.sub("_", name).strip("._")
    if not cleaned or len(cleaned) > 128:
        raise ProtocolError("filename is not usable")
    return cleaned


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
