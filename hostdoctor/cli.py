from __future__ import annotations

import argparse
import sys

from .collect import collect_report
from .report import apply_thresholds, render_json, render_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hostdoctor", description="Read-only, privacy-conscious Linux diagnostics.")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect a one-time host status snapshot")
    collect.add_argument("--format", choices=("text", "json"), default="text")
    collect.add_argument("--disk-warn-below", type=float, default=10.0)
    collect.add_argument("--memory-warn-below", type=float, default=10.0)
    collect.add_argument("--inode-warn-below", type=float, default=10.0)
    collect.add_argument("--fail-on", choices=("warning", "never"), default="never")
    args = parser.parse_args(argv)

    thresholds = (args.disk_warn_below, args.memory_warn_below, args.inode_warn_below)
    if any(value < 0 or value > 100 for value in thresholds):
        parser.error("thresholds must be between 0 and 100")
    try:
        report = apply_thresholds(
            collect_report(),
            disk_warn_below=args.disk_warn_below,
            memory_warn_below=args.memory_warn_below,
            inode_warn_below=args.inode_warn_below,
        )
    except RuntimeError as exc:
        print(f"hostdoctor: {exc}", file=sys.stderr)
        return 2

    print(render_json(report) if args.format == "json" else render_text(report))
    return 1 if args.fail_on == "warning" and report["summary"]["warning"] else 0
