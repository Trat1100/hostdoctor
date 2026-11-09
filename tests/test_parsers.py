import pytest

from hostdoctor.parsers import count_failed_units, count_listening_sockets, parse_loadavg, parse_meminfo


def test_meminfo_uses_available_memory_not_free_only():
    total, available = parse_meminfo("MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 600 kB\n")
    assert total == 1_024_000
    assert available == 614_400


def test_proc_parsers_reject_malformed_values():
    with pytest.raises(ValueError):
        parse_meminfo("MemFree: 2 kB")
    with pytest.raises(ValueError):
        parse_loadavg("broken")


def test_socket_and_failed_unit_parsers_keep_only_counts():
    sockets = "tcp LISTEN 0 128 10.0.0.4:443 0.0.0.0:*\nudp UNCONN 0 0 10.0.0.4:53 0.0.0.0:*\n"
    units = "private-service-name.service loaded failed failed Demo\n"
    assert count_listening_sockets(sockets) == 2
    assert count_failed_units(units) == 1
