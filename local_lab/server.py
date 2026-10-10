"""Standalone local TCP/UDP lab server. Defaults to loopback only."""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .protocol import DEFAULT_MAX_TRANSFER_BYTES, ProtocolError, recv_frame, sanitize_filename, send_frame
except ImportError:  # script execution from local_lab/
    from protocol import DEFAULT_MAX_TRANSFER_BYTES, ProtocolError, recv_frame, sanitize_filename, send_frame


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def handle_tcp_connection(conn: socket.socket, receive_dir: Path, max_bytes: int) -> dict:
    conn.settimeout(15)
    header, payload = recv_frame(conn, max_bytes)
    kind = header.get("kind")
    if kind == "message":
        response = {"ok": True, "message": "message received", "bytes": len(payload)}
    elif kind == "file":
        name = sanitize_filename(header.get("filename"))
        declared_size = header.get("file_size")
        if not isinstance(declared_size, int) or declared_size != len(payload) or declared_size > max_bytes:
            raise ProtocolError("file size does not match payload or exceeds limit")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != header.get("sha256"):
            raise ProtocolError("SHA-256 verification failed")
        receive_dir.mkdir(parents=True, exist_ok=True)
        destination = receive_dir / name
        # Avoid overwriting existing received files.
        if destination.exists():
            destination = receive_dir / f"{destination.stem}_{int(time.time() * 1000)}{destination.suffix}"
        destination.write_bytes(payload)
        response = {"ok": True, "message": "file received and verified", "bytes": len(payload), "sha256": digest, "saved_as": destination.name}
    else:
        raise ProtocolError("unsupported request kind")
    send_frame(conn, response)
    return response


def tcp_worker(listener: socket.socket, receive_dir: Path, max_bytes: int, stop: threading.Event) -> None:
    listener.settimeout(1)
    while not stop.is_set():
        try:
            conn, address = listener.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        start = time.perf_counter()
        try:
            with conn:
                result = handle_tcp_connection(conn, receive_dir, max_bytes)
            print(json.dumps({"time": utc_now(), "protocol": "TCP", "peer": str(address), "duration_s": time.perf_counter() - start, **result}), flush=True)
        except Exception as exc:
            print(json.dumps({"time": utc_now(), "protocol": "TCP", "peer": str(address), "error": str(exc)}), flush=True)


def udp_worker(sock: socket.socket, stop: threading.Event) -> None:
    sock.settimeout(1)
    while not stop.is_set():
        try:
            data, address = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError:
            break
        received_at = time.time()
        try:
            packet = json.loads(data.decode("utf-8"))
            sequence = packet["sequence"]
            if not isinstance(sequence, int) or sequence < 0:
                raise ValueError("sequence must be a non-negative integer")
            print(json.dumps({"time": utc_now(), "protocol": "UDP", "peer": str(address), "sequence": sequence, "sent_timestamp": packet.get("sent_timestamp"), "received_timestamp": received_at}), flush=True)
            # An application-level echo lets the client estimate RTT and detect missing acknowledgements.
            sock.sendto(json.dumps({"sequence": sequence, "server_timestamp": received_at}).encode("utf-8"), address)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(json.dumps({"time": utc_now(), "protocol": "UDP", "peer": str(address), "error": str(exc)}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; loopback is the safe default")
    parser.add_argument("--tcp-port", type=int, default=5050)
    parser.add_argument("--udp-port", type=int, default=5051)
    parser.add_argument("--receive-dir", default="received_files")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_TRANSFER_BYTES)
    args = parser.parse_args()
    if not 1 <= args.tcp_port <= 65535 or not 1 <= args.udp_port <= 65535 or args.max_bytes <= 0:
        parser.error("ports must be 1..65535 and max-bytes must be positive")
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: LAN binding requested. Use only a trusted private network; firewall only these ports and stop the server after the lab.", flush=True)
    receive_dir = Path(args.receive_dir).resolve()
    stop = threading.Event()
    tcp = socket.socket(socket.AF_INET6 if ":" in args.host else socket.AF_INET, socket.SOCK_STREAM)
    udp = socket.socket(socket.AF_INET6 if ":" in args.host else socket.AF_INET, socket.SOCK_DGRAM)
    try:
        tcp.bind((args.host, args.tcp_port)); tcp.listen(8)
        udp.bind((args.host, args.udp_port))
    except OSError:
        tcp.close(); udp.close()
        raise
    print(f"TCP listening on {args.host}:{args.tcp_port}; UDP listening on {args.host}:{args.udp_port}; files go to {receive_dir}", flush=True)
    threads = [threading.Thread(target=tcp_worker, args=(tcp, receive_dir, args.max_bytes, stop), daemon=True), threading.Thread(target=udp_worker, args=(udp, stop), daemon=True)]
    for thread in threads: thread.start()
    try:
        while True: time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping server…", flush=True)
    finally:
        stop.set(); tcp.close(); udp.close()
        for thread in threads: thread.join(timeout=2)


if __name__ == "__main__":
    main()
