from pathlib import Path
import json

from sth_system_info.collector import _build_summary, CommandCapture
from sth_system_info.config import HostConfig


def test_build_summary_parses_core_fields(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    topo = tmp_path / "topology"
    raw.mkdir()
    topo.mkdir()

    (raw / "lscpu.txt").write_text(
        "\n".join(
            [
                "Architecture:        x86_64",
                "CPU(s):              8",
                "Vendor ID:           GenuineIntel",
                "Model name:          Example CPU",
                "Socket(s):           1",
                "Thread(s) per core:  2",
                "NUMA node(s):        1",
                "L1d cache:           48 KiB (4 instances)",
                "L1i cache:           64 KiB (4 instances)",
                "L2 cache:            2 MiB (4 instances)",
                "L3 cache:            36 MiB (1 instance)",
                "CPU max MHz:         4000.0000",
            ]
        )
    )
    (raw / "lscpu-topology.csv").write_text(
        "\n".join(
            [
                "# comment",
                "0,0,0,0,Y",
                "1,1,0,0,Y",
                "2,2,0,0,Y",
                "3,3,0,0,Y",
                "4,0,0,0,Y",
                "5,1,0,0,Y",
                "6,2,0,0,Y",
                "7,3,0,0,Y",
            ]
        )
    )
    (raw / "cpuinfo.txt").write_text("flags\t: aes avx avx2\n")
    (raw / "meminfo.txt").write_text("MemTotal:       67108864 kB\n")
    (raw / "os-release.txt").write_text('PRETTY_NAME="Ubuntu 24.04.4 LTS"\nVERSION="24.04.4 LTS"\n')
    (raw / "uname.txt").write_text("Linux example 6.8.0 x86_64\n")
    (raw / "cmdline.txt").write_text("quiet splash\n")
    (raw / "cpu_governor.txt").write_text("performance\n")
    (raw / "transparent_hugepage.txt").write_text("[always] madvise never\n")
    (raw / "lsblk.json").write_text(json.dumps({"blockdevices": [{"name": "nvme0n1", "type": "disk", "size": "894.3G"}]}))
    (raw / "dmi_memory.txt").write_text(
        "\n".join(
            [
                "Handle 0x0001, DMI type 17, 92 bytes",
                "Memory Device",
                "\tSize: 64 GB",
                "\tType: DDR5",
                "\tConfigured Memory Speed: 5600 MT/s",
            ]
        )
    )
    (raw / "dmi_system.txt").write_text(
        "\n".join(
            [
                "Handle 0x0002, DMI type 1, 27 bytes",
                "System Information",
                "\tManufacturer: NVIDIA",
                "\tProduct Name: Example System",
            ]
        )
    )
    (raw / "lshw_network.txt").write_text(
        "\n".join(
            [
                "  *-network",
                "       description: Ethernet interface",
                "       product: Example NIC",
                "       logical name: eth0",
                "       configuration: driver=r8169 ip=10.0.0.1",
            ]
        )
    )

    captures = [
        CommandCapture(
            command_id="lscpu",
            command="lscpu",
            sudo=False,
            optional=False,
            timeout=300,
            status="captured",
            exit_status=0,
            stdout_path="raw/lscpu.txt",
            stderr_path=None,
            error=None,
        )
    ]
    host = HostConfig(
        name="example",
        hostname="example",
        display_name=None,
        proxy_command=None,
        username="tester",
        port=22,
        tags=("x86_64",),
        enabled=True,
    )

    summary = _build_summary(host=host, captures=captures, output_dir=tmp_path)
    assert summary["cpu"]["display_model"] == "Example CPU"
    assert summary["cpu"]["physical_cores"] == 4
    assert summary["cpu"]["logical_cores"] == 8
    assert summary["cpu"]["l3_cache_kib"] == 36864
    assert summary["memory"]["memory_type"] == "DDR5"
    assert summary["memory"]["total_gib"] == 64.0
    assert summary["network"]["interfaces"][0]["product"] == "Example NIC"
