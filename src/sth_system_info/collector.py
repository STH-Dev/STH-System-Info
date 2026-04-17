from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import json
import os
import re
import shlex

from .config import HostConfig
from .remote import RemoteSession, Topology, parse_lscpu_summary, parse_lscpu_topology
from . import __version__


DEFAULT_PASSWORD_ENVS = ("STH_SYSTEM_INFO_SSH_PASSWORD", "STH_LATENCY_SSH_PASSWORD")


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    command: str
    relpath: str
    sudo: bool = False
    optional: bool = False
    timeout: int = 300


@dataclass(frozen=True)
class CommandCapture:
    command_id: str
    command: str
    sudo: bool
    optional: bool
    timeout: int
    status: str
    exit_status: int | None
    stdout_path: str | None
    stderr_path: str | None
    error: str | None


@dataclass(frozen=True)
class CollectionArtifacts:
    output_dir: Path
    manifest_path: Path
    summary_path: Path
    profile_path: Path
    captures: list[CommandCapture]


def _timestamped_output_dir(root: Path, host_name: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = root / host_name / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _ensure_output_dir(output_dir: Path | None, output_root: Path, host_name: str) -> Path:
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    return _timestamped_output_dir(output_root, host_name)


def _write_text(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def _command_specs() -> list[CommandSpec]:
    return [
        CommandSpec("uname", "uname -a", "raw/uname.txt"),
        CommandSpec("os_release", "cat /etc/os-release", "raw/os-release.txt"),
        CommandSpec("lscpu", "lscpu", "raw/lscpu.txt"),
        CommandSpec("lscpu_topology", "lscpu -p=CPU,CORE,SOCKET,NODE,ONLINE", "raw/lscpu-topology.csv"),
        CommandSpec("lscpu_cache", "lscpu -C", "raw/lscpu-cache.txt", optional=True),
        CommandSpec("cpuinfo", "cat /proc/cpuinfo", "raw/cpuinfo.txt"),
        CommandSpec("meminfo", "cat /proc/meminfo", "raw/meminfo.txt"),
        CommandSpec("numactl", "numactl --hardware", "raw/numactl.txt"),
        CommandSpec(
            "lsblk",
            "lsblk --json -o NAME,MODEL,SIZE,TYPE,TRAN,VENDOR,MOUNTPOINT",
            "raw/lsblk.json",
        ),
        CommandSpec("df", "df -T", "raw/df.txt"),
        CommandSpec("ipaddr", "ip addr", "raw/ipaddr.txt"),
        CommandSpec("iproute", "ip route", "raw/iproute.txt"),
        CommandSpec("lspci", "lspci", "raw/lspci.txt", optional=True),
        CommandSpec("lspci_verbose", "lspci -vvv", "raw/lspci_verbose.txt", sudo=True, optional=True, timeout=900),
        CommandSpec("lshw_network", "lshw -C network", "raw/lshw_network.txt", sudo=True, optional=True, timeout=900),
        CommandSpec("dmi_system", "dmidecode -t system", "raw/dmi_system.txt", sudo=True, optional=True),
        CommandSpec("dmi_baseboard", "dmidecode -t baseboard", "raw/dmi_baseboard.txt", sudo=True, optional=True),
        CommandSpec("dmi_processor", "dmidecode -t processor", "raw/dmi_processor.txt", sudo=True, optional=True),
        CommandSpec("dmi_memory", "dmidecode -t memory", "raw/dmi_memory.txt", sudo=True, optional=True, timeout=900),
        CommandSpec("cmdline", "cat /proc/cmdline", "raw/cmdline.txt"),
        CommandSpec(
            "cpu_governor",
            "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
            "raw/cpu_governor.txt",
            optional=True,
        ),
        CommandSpec(
            "transparent_hugepage",
            "cat /sys/kernel/mm/transparent_hugepage/enabled",
            "raw/transparent_hugepage.txt",
            optional=True,
        ),
        CommandSpec("lstopo_text", "lstopo --of console", "topology/lstopo.txt", optional=True, timeout=900),
        CommandSpec("lstopo_xml", "lstopo --of xml", "topology/lstopo.xml", optional=True, timeout=900),
        CommandSpec("lstopo_svg", "lstopo --of svg", "topology/lstopo.svg", optional=True, timeout=900),
    ]


def _parse_os_release(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"')
    return result


def _parse_meminfo_total_gib(text: str) -> float | None:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB$", text, flags=re.MULTILINE)
    if not match:
        return None
    kib = int(match.group(1))
    return kib / (1024 * 1024)


def _parse_size_to_kib(value: str | None) -> int | None:
    if not value:
        return None
    token = value.strip()
    token = re.sub(r"\s*\([^)]*\)\s*$", "", token)
    token = token.replace("iB", "B").replace(" ", "")
    match = re.match(r"^([0-9.]+)([KMGTP]?B?)$", token, flags=re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).upper()
    factors = {
        "": 1 / 1024,
        "B": 1 / 1024,
        "K": 1,
        "KB": 1,
        "M": 1024,
        "MB": 1024,
        "G": 1024 * 1024,
        "GB": 1024 * 1024,
        "T": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024,
    }
    factor = factors.get(unit)
    if factor is None:
        return None
    return int(amount * factor)


def _lscpu_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _first_present(values: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        if key in values and values[key]:
            return values[key]
    return None


def _parse_lshw_network(text: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("  *-network"):
            if current:
                devices.append(current)
            current = {}
            continue
        if current is None:
            continue
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = value.strip()
    if current:
        devices.append(current)
    return devices


def _parse_dmidecode_sections(text: str, section_name: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_section = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("Handle "):
            if current:
                blocks.append(current)
            current = None
            in_section = False
            continue
        if line.strip() == section_name:
            current = {}
            in_section = True
            continue
        if not in_section or current is None:
            continue
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def _memory_summary_from_dmi(text: str) -> dict[str, Any]:
    devices = _parse_dmidecode_sections(text, "Memory Device")
    populated: list[dict[str, str]] = []
    for device in devices:
        size = device.get("Size", "")
        if size and size not in {"No Module Installed", "Unknown"}:
            populated.append(device)
    speeds = [device.get("Configured Memory Speed") or device.get("Speed") for device in populated]
    speeds = [speed for speed in speeds if speed and speed not in {"Unknown", "0 MT/s"}]
    types = [device.get("Type") for device in populated if device.get("Type") and device.get("Type") != "Unknown"]
    return {
        "devices": populated,
        "slot_count": len(devices),
        "populated_count": len(populated),
        "memory_type": types[0] if types else None,
        "memory_speed": speeds[0] if speeds else None,
    }


def _status_counts(captures: list[CommandCapture]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for capture in captures:
        counts[capture.status] = counts.get(capture.status, 0) + 1
    return counts


def _render_system_profile(summary: dict[str, Any]) -> str:
    host = summary["host"]
    cpu = summary["cpu"]
    memory = summary["memory"]
    storage = summary["storage"]
    software = summary["software"]
    network = summary["network"]
    collection = summary["collection"]

    lines = [
        f"# System Profile: {host['name']}",
        "",
        "## Identification",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Hostname | {host['name']} |",
        f"| Target hostname | {host['hostname']} |",
        f"| Tags | {', '.join(host['tags']) if host['tags'] else '—'} |",
        f"| OS | {software.get('pretty_name') or software.get('os_release', 'Unknown')} |",
        f"| Kernel | {software.get('kernel', 'Unknown')} |",
        f"| Captured at | {summary['captured_at']} |",
        "",
        "## CPU",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | {cpu.get('display_model') or 'Unknown'} |",
        f"| Architecture | {cpu.get('architecture') or 'Unknown'} |",
        f"| Vendor | {cpu.get('vendor') or 'Unknown'} |",
        f"| Sockets | {cpu.get('sockets') or 'Unknown'} |",
        f"| Physical cores | {cpu.get('physical_cores') or 'Unknown'} |",
        f"| Logical CPUs | {cpu.get('logical_cores') or 'Unknown'} |",
        f"| Threads per core | {cpu.get('threads_per_core') or 'Unknown'} |",
        f"| NUMA nodes | {cpu.get('numa_nodes') or 'Unknown'} |",
        f"| Base MHz | {cpu.get('base_mhz') or 'Unknown'} |",
        f"| Max MHz | {cpu.get('max_mhz') or 'Unknown'} |",
        f"| Governor | {cpu.get('governor') or 'Unknown'} |",
        f"| L1d cache | {cpu.get('l1d_cache_kib') or 'Unknown'} KiB |",
        f"| L1i cache | {cpu.get('l1i_cache_kib') or 'Unknown'} KiB |",
        f"| L2 cache | {cpu.get('l2_cache_kib') or 'Unknown'} KiB |",
        f"| L3 cache | {cpu.get('l3_cache_kib') or 'Unknown'} KiB |",
        "",
        "## Memory",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Total memory | {memory.get('total_gib') or 'Unknown'} GiB |",
        f"| Populated DIMMs / devices | {memory.get('populated_count') or 0} / {memory.get('slot_count') or 0} |",
        f"| Memory type | {memory.get('memory_type') or 'Unknown'} |",
        f"| Memory speed | {memory.get('memory_speed') or 'Unknown'} |",
        "",
        "## Storage",
        "",
        "| Device | Type | Size | Model |",
        "|---|---|---|---|",
    ]

    for device in storage.get("devices", []):
        if device.get("type") == "disk":
            lines.append(
                f"| {device.get('name', 'Unknown')} | {device.get('type', 'Unknown')} | "
                f"{device.get('size', 'Unknown')} | {device.get('model', 'Unknown')} |"
            )
    if lines[-1] == "|---|---|---|---|":
        lines.append("| — | — | — | — |")

    lines.extend(
        [
            "",
            "## Network",
            "",
            "| Description | Product | Logical name | Driver |",
            "|---|---|---|---|",
        ]
    )
    for device in network.get("interfaces", []):
        lines.append(
            f"| {device.get('description', 'Unknown')} | {device.get('product', 'Unknown')} | "
            f"{device.get('logical name', 'Unknown')} | {device.get('configuration', 'Unknown')} |"
        )
    if lines[-1] == "|---|---|---|---|":
        lines.append("| — | — | — | — |")

    lines.extend(
        [
            "",
            "## Collection",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]
    )
    for status, count in sorted(collection["status_counts"].items()):
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Raw outputs are stored under `raw/`.",
            "- Topology artifacts are stored under `topology/`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_summary(
    *,
    host: HostConfig,
    captures: list[CommandCapture],
    output_dir: Path,
) -> dict[str, Any]:
    def read_text(relpath: str) -> str:
        path = output_dir / relpath
        if not path.exists():
            return ""
        return path.read_text()

    lscpu_text = read_text("raw/lscpu.txt")
    lscpu_values = _lscpu_values(lscpu_text)
    topology = None
    lscpu_topology_csv = read_text("raw/lscpu-topology.csv")
    if lscpu_text and lscpu_topology_csv:
        summary = parse_lscpu_summary(lscpu_text)
        topology = parse_lscpu_topology(summary, lscpu_topology_csv)
    os_release = _parse_os_release(read_text("raw/os-release.txt"))
    meminfo_text = read_text("raw/meminfo.txt")
    lsblk_text = read_text("raw/lsblk.json")
    lsblk = json.loads(lsblk_text) if lsblk_text else {"blockdevices": []}
    dmi_memory = _memory_summary_from_dmi(read_text("raw/dmi_memory.txt"))
    dmi_system = _parse_dmidecode_sections(read_text("raw/dmi_system.txt"), "System Information")
    lshw_network = _parse_lshw_network(read_text("raw/lshw_network.txt"))
    cpuinfo_text = read_text("raw/cpuinfo.txt")
    cpu_flags_match = re.search(r"^(?:flags|Features)\s*:\s*(.+)$", cpuinfo_text, flags=re.MULTILINE)
    cpu_flags = cpu_flags_match.group(1).split() if cpu_flags_match else []
    socket_count = None
    if topology is not None:
        sockets = {group.socket for group in topology.groups if group.socket is not None}
        socket_count = topology.summary.sockets or (len(sockets) if sockets else None)

    summary = {
        "schema_version": "1.0.0",
        "collector_version": __version__,
        "captured_at": datetime.now(UTC).isoformat(),
        "host": {
            "name": host.name,
            "hostname": host.hostname,
            "display_name": host.display_name,
            "username": host.username,
            "port": host.port,
            "tags": list(host.tags),
        },
        "cpu": {
            "architecture": _first_present(lscpu_values, ["Architecture"]),
            "vendor": _first_present(lscpu_values, ["Vendor ID"]),
            "display_model": (topology.summary.display_model if topology else _first_present(lscpu_values, ["Model name"])),
            "model_names": list(topology.summary.model_names) if topology else [],
            "sockets": socket_count,
            "physical_cores": topology.physical_core_count if topology else None,
            "logical_cores": topology.logical_cpu_count if topology else None,
            "threads_per_core": topology.summary.threads_per_core if topology else None,
            "numa_nodes": topology.summary.numa_nodes if topology else None,
            "base_mhz": _first_present(lscpu_values, ["CPU MHz"]),
            "max_mhz": _first_present(lscpu_values, ["CPU max MHz"]),
            "governor": read_text("raw/cpu_governor.txt").strip() or None,
            "l1d_cache_kib": _parse_size_to_kib(_first_present(lscpu_values, ["L1d cache"])),
            "l1i_cache_kib": _parse_size_to_kib(_first_present(lscpu_values, ["L1i cache"])),
            "l2_cache_kib": _parse_size_to_kib(_first_present(lscpu_values, ["L2 cache"])),
            "l3_cache_kib": _parse_size_to_kib(_first_present(lscpu_values, ["L3 cache"])),
            "flags_count": len(cpu_flags),
            "topology": topology.to_dict() if topology else None,
        },
        "memory": {
            "total_gib": _parse_meminfo_total_gib(meminfo_text),
            "slot_count": dmi_memory["slot_count"],
            "populated_count": dmi_memory["populated_count"],
            "memory_type": dmi_memory["memory_type"],
            "memory_speed": dmi_memory["memory_speed"],
            "devices": dmi_memory["devices"],
        },
        "storage": {
            "devices": lsblk.get("blockdevices", []),
        },
        "network": {
            "interfaces": lshw_network,
        },
        "software": {
            "pretty_name": os_release.get("PRETTY_NAME"),
            "os_release": os_release.get("VERSION"),
            "kernel": read_text("raw/uname.txt").strip(),
            "kernel_cmdline": read_text("raw/cmdline.txt").strip(),
            "transparent_hugepage": read_text("raw/transparent_hugepage.txt").strip() or None,
            "system_dmi": dmi_system[0] if dmi_system else None,
        },
        "topology_artifacts": {
            "text": "topology/lstopo.txt" if (output_dir / "topology/lstopo.txt").exists() else None,
            "xml": "topology/lstopo.xml" if (output_dir / "topology/lstopo.xml").exists() else None,
            "svg": "topology/lstopo.svg" if (output_dir / "topology/lstopo.svg").exists() else None,
        },
        "collection": {
            "command_count": len(captures),
            "status_counts": _status_counts(captures),
            "commands": [asdict(capture) for capture in captures],
        },
    }
    return summary


def resolve_password(explicit_password: str | None, password_env: str | None) -> str:
    if explicit_password:
        return explicit_password
    if password_env:
        value = os.environ.get(password_env)
        if value:
            return value
        raise ValueError(f"Environment variable {password_env} is not set")
    for env_name in DEFAULT_PASSWORD_ENVS:
        value = os.environ.get(env_name)
        if value:
            return value
    raise ValueError(
        "No SSH password provided. Use --password, --password-env, or set one of: "
        + ", ".join(DEFAULT_PASSWORD_ENVS)
    )


def collect_host(
    *,
    host: HostConfig,
    password: str,
    output_root: Path,
    output_dir: Path | None = None,
) -> CollectionArtifacts:
    final_output_dir = _ensure_output_dir(output_dir, output_root, host.name)
    (final_output_dir / "raw").mkdir(parents=True, exist_ok=True)
    (final_output_dir / "topology").mkdir(parents=True, exist_ok=True)

    captures: list[CommandCapture] = []
    session = RemoteSession(
        hostname=host.hostname,
        username=host.username,
        password=password,
        port=host.port,
        proxy_command=host.proxy_command,
    )
    session.connect()
    try:
        for spec in _command_specs():
            result = session.run(spec.command, sudo=spec.sudo, timeout=spec.timeout, check=False)
            stdout_path = None
            stderr_path = None
            status = "captured" if result.exit_status == 0 else ("skipped" if spec.optional else "failed")
            error = None if result.exit_status == 0 else f"command exited with status {result.exit_status}"

            target_path = final_output_dir / spec.relpath
            if result.stdout:
                _write_text(target_path, result.stdout)
                stdout_path = spec.relpath
            elif result.exit_status == 0:
                _write_text(target_path, "")
                stdout_path = spec.relpath

            if result.stderr:
                stderr_relpath = spec.relpath + ".stderr.txt"
                _write_text(final_output_dir / stderr_relpath, result.stderr)
                stderr_path = stderr_relpath

            captures.append(
                CommandCapture(
                    command_id=spec.command_id,
                    command=spec.command,
                    sudo=spec.sudo,
                    optional=spec.optional,
                    timeout=spec.timeout,
                    status=status,
                    exit_status=result.exit_status,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    error=error,
                )
            )

        summary = _build_summary(host=host, captures=captures, output_dir=final_output_dir)
        summary_path = final_output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))

        profile_path = final_output_dir / "system_profile.md"
        profile_path.write_text(_render_system_profile(summary))

        manifest = {
            "schema_version": "1.0.0",
            "collector_version": __version__,
            "captured_at": summary["captured_at"],
            "host": summary["host"],
            "summary_path": "summary.json",
            "system_profile_path": "system_profile.md",
            "captures": [asdict(capture) for capture in captures],
        }
        manifest_path = final_output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return CollectionArtifacts(
            output_dir=final_output_dir,
            manifest_path=manifest_path,
            summary_path=summary_path,
            profile_path=profile_path,
            captures=captures,
        )
    finally:
        session.close()
