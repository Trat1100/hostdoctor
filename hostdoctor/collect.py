from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from .parsers import count_failed_units, count_listening_sockets, parse_loadavg, parse_meminfo


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return None


def _run(command: list[str], *, timeout: float = 2.0) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def _statvfs(path: Path):
    if not hasattr(os, "statvfs"):
        raise OSError("inode counters are unavailable on this platform")
    return os.statvfs(path)


def collect_report(
    *,
    proc_root: Path = Path("/proc"),
    root_path: Path = Path("/"),
    os_name: str | None = None,
    command_runner: Callable[[list[str]], tuple[int, str]] = _run,
    disk_usage: Callable = shutil.disk_usage,
    statvfs: Callable = _statvfs,
    cpu_count: Callable[[], int | None] = os.cpu_count,
) -> dict:
    detected_os = platform.system() if os_name is None else os_name
    if detected_os != "Linux":
        raise RuntimeError("HostDoctor supports Linux only")

    checks = []

    meminfo_text = _read(proc_root / "meminfo")
    if meminfo_text is None:
        checks.append({"id": "memory", "status": "unknown", "summary": "memory counters unavailable"})
    else:
        try:
            total, available = parse_meminfo(meminfo_text)
            pct = round(available * 100 / total, 1)
            checks.append(
                {
                    "id": "memory",
                    "status": "ok",
                    "summary": f"{pct:.1f}% available",
                    "available_percent": pct,
                    "available_bytes": available,
                    "total_bytes": total,
                }
            )
        except ValueError:
            checks.append({"id": "memory", "status": "unknown", "summary": "memory counters unavailable"})

    load_text = _read(proc_root / "loadavg")
    try:
        loads = parse_loadavg(load_text or "")
        cores = max(1, cpu_count() or 1)
        checks.append(
            {
                "id": "load_average",
                "status": "ok",
                "summary": f"{loads[0]:.2f} / {loads[1]:.2f} / {loads[2]:.2f} across {cores} CPU(s)",
                "values": list(loads),
                "cpu_count": cores,
            }
        )
    except ValueError:
        checks.append({"id": "load_average", "status": "unknown", "summary": "load averages unavailable"})

    try:
        disk = disk_usage(root_path)
        disk_pct = round((disk.free / disk.total) * 100, 1) if disk.total else None
        if disk_pct is None:
            raise ValueError
        checks.append(
            {
                "id": "root_filesystem",
                "status": "ok",
                "summary": f"{disk_pct:.1f}% free",
                "free_percent": disk_pct,
                "free_bytes": disk.free,
                "total_bytes": disk.total,
            }
        )
    except (OSError, ValueError, ZeroDivisionError):
        checks.append({"id": "root_filesystem", "status": "unknown", "summary": "root filesystem counters unavailable"})

    try:
        stats = statvfs(root_path)
        total_inodes = stats.f_files
        free_inodes = stats.f_favail
        inode_pct = round(free_inodes * 100 / total_inodes, 1) if total_inodes else None
        if inode_pct is None:
            raise ValueError
        checks.append(
            {
                "id": "root_inodes",
                "status": "ok",
                "summary": f"{inode_pct:.1f}% free",
                "free_percent": inode_pct,
                "free_count": free_inodes,
                "total_count": total_inodes,
            }
        )
    except (OSError, ValueError, ZeroDivisionError, AttributeError):
        checks.append({"id": "root_inodes", "status": "unknown", "summary": "inode counters unavailable"})

    socket_status, socket_output = command_runner(["ss", "-H", "-lntu"])
    if socket_status == 0:
        count = count_listening_sockets(socket_output)
        checks.append(
            {
                "id": "listening_sockets",
                "status": "ok",
                "summary": f"{count} TCP/UDP listening socket(s); addresses omitted",
                "count": count,
            }
        )
    else:
        checks.append({"id": "listening_sockets", "status": "unknown", "summary": "ss unavailable or permission denied"})

    service_status, service_output = command_runner(
        ["systemctl", "list-units", "--failed", "--type=service", "--no-legend", "--plain", "--no-pager"]
    )
    if service_status == 0:
        failed = count_failed_units(service_output)
        checks.append(
            {
                "id": "systemd_services",
                "status": "ok" if failed == 0 else "warning",
                "summary": f"{failed} failed service unit(s); names omitted",
                "failed_count": failed,
            }
        )
    else:
        checks.append({"id": "systemd_services", "status": "unknown", "summary": "systemd query unavailable"})

    return {"tool": "hostdoctor", "version": "0.1.0", "platform": "linux", "checks": checks}
