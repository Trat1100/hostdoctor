from __future__ import annotations


def parse_meminfo(text: str) -> tuple[int, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                values[parts[0][:-1]] = int(parts[1]) * 1024
            except ValueError:
                continue
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    if total <= 0 or available < 0:
        raise ValueError("meminfo does not include usable memory counters")
    return total, min(available, total)


def parse_loadavg(text: str) -> tuple[float, float, float]:
    parts = text.split()
    if len(parts) < 3:
        raise ValueError("loadavg does not include three averages")
    try:
        values = tuple(float(item) for item in parts[:3])
    except ValueError:
        raise ValueError("loadavg contains an invalid number") from None
    if any(value < 0 for value in values):
        raise ValueError("loadavg values cannot be negative")
    return values


def count_listening_sockets(text: str) -> int:
    # Only the number of lines is kept. Local addresses and process data are discarded.
    return sum(1 for line in text.splitlines() if line.strip())


def count_failed_units(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())
