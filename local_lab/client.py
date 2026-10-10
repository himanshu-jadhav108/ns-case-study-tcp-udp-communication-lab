"""Command-line client for TCP messages/files and UDP notification batches."""
from __future__ import annotations

import argparse
import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .metrics import append_csv, throughput_bytes_per_second, udp_sequence_metrics
    from .protocol import DEFAULT_MAX_TRANSFER_BYTES, ProtocolError, recv_frame, send_frame, sha256_bytes
except ImportError:  # script execution from local_lab/
    from metrics import append_csv, throughput_bytes_per_second, udp_sequence_metrics
    from protocol import DEFAULT_MAX_TRANSFER_BYTES, ProtocolError, recv_frame, send_frame, sha256_bytes


def send_tcp(host: str, port: int, kind: str, message: str | None, file_path: str | None, timeout: float, max_bytes: int) -> dict:
    payload = b""
    header = {"kind": kind}
    if kind == "message":
        payload = (message or "").encode("utf-8")
        if len(payload) > max_bytes: raise ProtocolError("message exceeds configured limit")
    else:
        path = Path(file_path or "")
        payload = path.read_bytes()
        if len(payload) > max_bytes: raise ProtocolError("file exceeds configured limit")
        header.update(filename=path.name, file_size=len(payload), sha256=sha256_bytes(payload))
    start = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        send_frame(sock, header, payload)
        response, _ = recv_frame(sock, 16 * 1024)
    elapsed = time.perf_counter() - start
    response.update({"duration_s": elapsed, "throughput_bytes_s": throughput_bytes_per_second(int(response.get("bytes", 0)), elapsed), "mode": "local_measured", "protocol": "TCP"})
    return response


def send_udp(host: str, port: int, count: int, interval: float, timeout: float, csv_path: str) -> dict:
    if count < 1 or count > 10000 or interval < 0: raise ValueError("count must be 1..10000 and interval must be non-negative")
    received: dict[int, float] = {}
    sent_at: dict[int, float] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.02)
        start = time.perf_counter()
        for sequence in range(count):
            timestamp = time.time()
            sent_at[sequence] = time.perf_counter()
            packet = {"sequence": sequence, "sent_timestamp": timestamp, "message": "lab notification"}
            sock.sendto(json.dumps(packet).encode("utf-8"), (host, port))
            if interval: time.sleep(interval)
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline and len(received) < count:
            try:
                data, _ = sock.recvfrom(2048)
                ack = json.loads(data.decode("utf-8"))
                seq = ack.get("sequence")
                if seq in sent_at and seq not in received: received[seq] = (time.perf_counter() - sent_at[seq]) * 1000
            except socket.timeout:
                continue
        elapsed = time.perf_counter() - start
    metrics = udp_sequence_metrics(range(count), received.keys())
    avg_rtt = sum(received.values()) / len(received) if received else None
    row = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode": "local_measured", "protocol": "UDP", "event": "notification_batch", "sent": count, "received": metrics["received"], "loss_count": metrics["lost"], "rtt_ms": "" if avg_rtt is None else round(avg_rtt, 3), "duration_s": round(elapsed, 6), "success": metrics["received"] == count, "details": "Missing echo ACK can mean request or return-path loss; RTT is measured, not one-way delay."}
    append_csv(csv_path, row)
    return {**metrics, "average_rtt_ms": avg_rtt, "duration_s": elapsed, "mode": "local_measured", "protocol": "UDP"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--tcp-port", type=int, default=5050)
    parser.add_argument("--udp-port", type=int, default=5051)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_TRANSFER_BYTES)
    parser.add_argument("--csv", default="local_observations.csv")
    sub = parser.add_subparsers(dest="command", required=True)
    message = sub.add_parser("message"); message.add_argument("text")
    file_cmd = sub.add_parser("file"); file_cmd.add_argument("path")
    udp = sub.add_parser("udp"); udp.add_argument("--count", type=int, default=20); udp.add_argument("--interval", type=float, default=0.02)
    args = parser.parse_args()
    try:
        if args.command == "message":
            result = send_tcp(args.host, args.tcp_port, "message", args.text, None, args.timeout, args.max_bytes)
        elif args.command == "file":
            result = send_tcp(args.host, args.tcp_port, "file", None, args.path, args.timeout, args.max_bytes)
        else:
            result = send_udp(args.host, args.udp_port, args.count, args.interval, args.timeout, args.csv)
        print(json.dumps(result, indent=2))
        if args.command != "udp":
            append_csv(args.csv, {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode": "local_measured", "protocol": "TCP", "event": args.command, "duration_s": result["duration_s"], "bytes": result["bytes"], "throughput_bytes_s": result["throughput_bytes_s"], "success": result["ok"], "details": result.get("message", "")})
    except (OSError, ValueError, ProtocolError) as exc:
        print(json.dumps({"mode": "local_measured", "error": str(exc)}))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
