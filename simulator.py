"""Pure, seeded network-condition simulator used by the cloud dashboard."""
from __future__ import annotations

import random


def simulate_network(*, packet_count: int, packet_bytes: int, base_delay_ms: float, loss_probability: float, bandwidth_kbps: float, seed: int = 7) -> list[dict]:
    if not isinstance(packet_count, int) or packet_count < 1 or packet_count > 5000:
        raise ValueError("packet_count must be between 1 and 5000")
    if packet_bytes < 1 or packet_bytes > 65507:
        raise ValueError("packet_bytes must be between 1 and 65507")
    if base_delay_ms < 0 or base_delay_ms > 5000:
        raise ValueError("base_delay_ms must be between 0 and 5000")
    if not 0 <= loss_probability <= 1:
        raise ValueError("loss_probability must be between 0 and 1")
    if bandwidth_kbps <= 0:
        raise ValueError("bandwidth_kbps must be positive")
    rng = random.Random(seed)
    transmission_ms = packet_bytes * 8 / (bandwidth_kbps * 1000) * 1000
    observations = []
    elapsed_ms = 0.0
    for sequence in range(packet_count):
        elapsed_ms += transmission_ms
        delay_ms = base_delay_ms + rng.uniform(0, max(1.0, base_delay_ms * 0.15))
        delivered = rng.random() >= loss_probability
        observations.append({"sequence": sequence, "delay_ms": round(delay_ms, 3), "delivered": delivered, "elapsed_ms": round(elapsed_ms + delay_ms, 3), "bytes": packet_bytes if delivered else 0, "mode": "simulated"})
    return observations


def summarize(observations: list[dict], bandwidth_kbps: float) -> dict:
    count = len(observations)
    received = sum(1 for row in observations if row["delivered"])
    success_bytes = sum(row["bytes"] for row in observations)
    loss_count = count - received
    duration_s = max((row["elapsed_ms"] for row in observations), default=0) / 1000
    delays = [row["delay_ms"] for row in observations if row["delivered"]]
    return {"sent": count, "received": received, "loss_count": loss_count, "loss_percent": (loss_count / count * 100 if count else 0), "reliability_percent": (received / count * 100 if count else 0), "avg_delay_ms": (sum(delays) / len(delays) if delays else None), "throughput_bytes_s": (success_bytes / duration_s if duration_s else 0), "duration_s": duration_s, "bandwidth_cap_kbps": bandwidth_kbps, "mode": "simulated"}
