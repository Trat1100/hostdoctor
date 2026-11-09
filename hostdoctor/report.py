from __future__ import annotations

import json


def apply_thresholds(
    report: dict,
    *,
    disk_warn_below: float = 10.0,
    memory_warn_below: float = 10.0,
    inode_warn_below: float = 10.0,
) -> dict:
    checks = []
    for original in report["checks"]:
        check = dict(original)
        check_id = check["id"]
        value = None
        threshold = None
        if check_id == "root_filesystem":
            value, threshold = check.get("free_percent"), disk_warn_below
        elif check_id == "root_inodes":
            value, threshold = check.get("free_percent"), inode_warn_below
        elif check_id == "memory":
            value, threshold = check.get("available_percent"), memory_warn_below
        if value is not None and value < threshold:
            check["status"] = "warning"
            check["summary"] += f" (below {threshold:.1f}% threshold)"
        checks.append(check)
    counts = {state: sum(1 for check in checks if check["status"] == state) for state in ("ok", "warning", "unknown")}
    return {**report, "checks": checks, "summary": counts}


def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def render_text(report: dict) -> str:
    lines = ["HostDoctor snapshot"]
    for check in report["checks"]:
        lines.append(f"- {check['id'].replace('_', ' ').title()}: {check['summary']} ({check['status']})")
    counts = report["summary"]
    lines.append(f"Summary: {counts['ok']} ok, {counts['warning']} warning, {counts['unknown']} unknown")
    return "\n".join(lines)
