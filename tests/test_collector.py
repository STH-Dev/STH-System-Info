from pathlib import Path
import json

from sth_system_info.collector import _build_summary, _render_system_profile, CommandCapture
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
                "Handle 0x0000, DMI type 16, 23 bytes",
                "Physical Memory Array",
                "\tLocation: System Board Or Motherboard",
                "\tUse: System Memory",
                "\tMaximum Capacity: 512 GB",
                "\tNumber Of Devices: 4",
                "",
                "Handle 0x0001, DMI type 17, 92 bytes",
                "Memory Device",
                "\tSize: 64 GB",
                "\tForm Factor: DIMM",
                "\tLocator: CPU0_DIMM_A1",
                "\tBank Locator: P0 CHANNEL A DIMM 0",
                "\tType: DDR5",
                "\tType Detail: Registered (Buffered)",
                "\tSpeed: 6400 MT/s",
                "\tConfigured Memory Speed: 5600 MT/s",
                "\tManufacturer: Example Memory",
                "\tPart Number: EX-6400-64G",
                "\tRank: 2",
                "\tConfigured Voltage: 1.1 V",
                "",
                "Handle 0x0002, DMI type 17, 92 bytes",
                "Memory Device",
                "\tSize: 64 GB",
                "\tForm Factor: DIMM",
                "\tLocator: CPU0_DIMM_B1",
                "\tBank Locator: P0 CHANNEL B DIMM 0",
                "\tType: DDR5",
                "\tType Detail: Registered (Buffered)",
                "\tSpeed: 6400 MT/s",
                "\tConfigured Memory Speed: 5600 MT/s",
                "\tManufacturer: Example Memory",
                "\tPart Number: EX-6400-64G",
                "\tRank: 2",
                "\tConfigured Voltage: 1.1 V",
                "",
                "Handle 0x0003, DMI type 17, 92 bytes",
                "Memory Device",
                "\tSize: No Module Installed",
                "\tLocator: CPU0_DIMM_C1",
                "\tBank Locator: P0 CHANNEL C DIMM 0",
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
    assert summary["memory"]["memory_types"] == ["DDR5"]
    assert summary["memory"]["type_details"] == ["Registered (Buffered)"]
    assert summary["memory"]["total_gib"] == 64.0
    assert summary["memory"]["installed_gib"] == 128.0
    assert summary["memory"]["array_device_count"] == 4
    assert summary["memory"]["slot_count"] == 3
    assert summary["memory"]["populated_count"] == 2
    assert summary["memory"]["filled_channel_count"] == 2
    assert summary["memory"]["configured_memory_speed"] == "5600 MT/s"
    assert summary["memory"]["rated_memory_speed"] == "6400 MT/s"
    assert summary["memory"]["capacity_layout"] == ["2 x 64 GB"]
    assert summary["memory"]["part_numbers"] == ["EX-6400-64G"]
    assert summary["memory"]["devices"][0]["channel_label"] == "Channel A"
    assert summary["memory"]["devices"][0]["manufacturer"] == "Example Memory"
    assert summary["network"]["interfaces"][0]["product"] == "Example NIC"

    profile = _render_system_profile(summary)
    assert "| Filled memory channels (best-effort) | 2 |" in profile
    assert "| Current configured speed(s) | 5600 MT/s |" in profile
    assert "| Rated DIMM speed(s) | 6400 MT/s |" in profile
    assert "| CPU0_DIMM_A1 | P0 CHANNEL A DIMM 0 | Channel A | 64 GB |" in profile
