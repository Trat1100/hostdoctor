from pathlib import Path
from types import SimpleNamespace

from hostdoctor.collect import collect_report
from hostdoctor.report import apply_thresholds, render_json, render_text


def test_collects_synthetic_linux_snapshot_without_retaining_network_or_unit_names(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "meminfo").write_text("MemTotal: 1000 kB\nMemAvailable: 200 kB\n")
    (proc / "loadavg").write_text("0.20 0.30 0.40 1/2 98765\n")
    commands = []

    def run(args):
        commands.append(args)
        if args[0] == "ss":
            return 0, "tcp LISTEN 0 1 192.0.2.10:443 0.0.0.0:*\n"
        return 0, "private-unit.service loaded failed failed description\n"

    report = collect_report(
        proc_root=proc,
        root_path=Path("/"),
        os_name="Linux",
        command_runner=run,
        disk_usage=lambda _path: SimpleNamespace(total=100, used=90, free=10),
        statvfs=lambda _path: SimpleNamespace(f_files=100, f_favail=5),
        cpu_count=lambda: 2,
    )
    report = apply_thresholds(report, disk_warn_below=15, memory_warn_below=25, inode_warn_below=10)
    output = render_text(report) + render_json(report)
    assert report["summary"] == {"ok": 2, "warning": 4, "unknown": 0}
    assert "192.0.2.10" not in output
    assert "private-unit" not in output
    assert "98765" not in output
    assert [command[0] for command in commands] == ["ss", "systemctl"]
    assert "journalctl" not in output


def test_unavailable_probes_are_unknown_not_healthy(tmp_path):
    proc = tmp_path / "empty-proc"
    proc.mkdir()
    report = collect_report(
        proc_root=proc,
        os_name="Linux",
        command_runner=lambda _args: (127, ""),
        disk_usage=lambda _path: (_ for _ in ()).throw(OSError()),
        statvfs=lambda _path: (_ for _ in ()).throw(OSError()),
    )
    assert {check["status"] for check in report["checks"]} == {"unknown"}


def test_non_linux_platform_is_rejected():
    try:
        collect_report(os_name="Windows")
    except RuntimeError as exc:
        assert "Linux only" in str(exc)
    else:
        raise AssertionError("non-Linux host should be rejected")
