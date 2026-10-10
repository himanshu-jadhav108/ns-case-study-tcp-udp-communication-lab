"""Metrics and CSV logging shared by local lab clients."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

CSV_FIELDS = ["timestamp_utc", "mode", "protocol", "event", "sequence", "sent", "received", "loss_count", "rtt_ms", "duration_s", "bytes", "throughput_bytes_s", "success", "details"]


def udp_sequence_metrics(sent_sequences: Iterable[int], received_sequences: Iterable[int]) -> dict[str, float | int]:
    sent = set(sent_sequences)
    received = set(received_sequences)
    missing = sent - received
    extra = received - sent
    count = len(sent)
    return {"sent": count, "received": len(sent & received), "lost": len(missing), "unexpected": len(extra), "loss_percent": (100.0 * len(missing) / count if count else 0.0)}


def throughput_bytes_per_second(byte_count: int, elapsed_seconds: float) -> float:
    if byte_count < 0 or elapsed_seconds < 0:
        raise ValueError("byte count and elapsed time must be non-negative")
    if elapsed_seconds == 0:
        return 0.0 if byte_count == 0 else math.inf
    return byte_count / elapsed_seconds


def append_csv(path: str | Path, row: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    exists = target.exists() and target.stat().st_size > 0
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})
