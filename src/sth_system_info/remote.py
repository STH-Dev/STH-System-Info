from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
from typing import Any
import json
import shlex

import paramiko


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    if not value or value == "-":
        return None
    return int(value)


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _expand_proxy_command(command: str, hostname: str, port: int) -> str:
    return command.replace("%h", hostname).replace("%p", str(port))


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_status: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CpuThreadGroup:
    socket: int | None
    core: int
    node: int | None
    cpus: tuple[int, ...]

    @property
    def primary_cpu(self) -> int:
        return self.cpus[0]


@dataclass(frozen=True)
class TopologySummary:
    architecture: str
    model_names: tuple[str, ...]
    logical_cpu_count: int | None
    sockets: int | None
    threads_per_core: int | None
    numa_nodes: int | None = None

    @property
    def display_model(self) -> str:
        if not self.model_names:
            return "Unknown CPU"
        return " / ".join(self.model_names)


@dataclass(frozen=True)
class Topology:
    summary: TopologySummary
    groups: tuple[CpuThreadGroup, ...]

    @property
    def physical_core_count(self) -> int:
        return len(self.groups)

    @property
    def logical_cpu_count(self) -> int:
        return sum(len(group.cpus) for group in self.groups)

    @property
    def primary_cpus(self) -> list[int]:
        return [group.primary_cpu for group in self.groups]

    @property
    def logical_cpus(self) -> list[int]:
        cpus: list[int] = []
        for group in self.groups:
            cpus.extend(group.cpus)
        return cpus

    @property
    def sibling_pairs(self) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for group in self.groups:
            if len(group.cpus) >= 2:
                pairs.append((group.cpus[0], group.cpus[1]))
        return pairs

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": asdict(self.summary),
            "physical_core_count": self.physical_core_count,
            "logical_cpu_count": self.logical_cpu_count,
            "primary_cpus": self.primary_cpus,
            "logical_cpus": self.logical_cpus,
            "sibling_pairs": self.sibling_pairs,
            "groups": [asdict(group) for group in self.groups],
        }


def parse_lscpu_summary(text: str) -> TopologySummary:
    values: dict[str, list[str]] = defaultdict(list)
    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value:
            values[key].append(value)

    architecture = values.get("Architecture", ["unknown"])[0]
    model_names = tuple(_unique_in_order(values.get("Model name", [])))
    logical_cpu_count = _parse_optional_int(values.get("CPU(s)", [""])[0]) if values.get("CPU(s)") else None
    sockets = _parse_optional_int(values.get("Socket(s)", [""])[0]) if values.get("Socket(s)") else None
    threads_per_core = (
        _parse_optional_int(values.get("Thread(s) per core", [""])[0])
        if values.get("Thread(s) per core")
        else None
    )
    numa_nodes = _parse_optional_int(values.get("NUMA node(s)", [""])[0]) if values.get("NUMA node(s)") else None
    return TopologySummary(
        architecture=architecture,
        model_names=model_names,
        logical_cpu_count=logical_cpu_count,
        sockets=sockets,
        threads_per_core=threads_per_core,
        numa_nodes=numa_nodes,
    )


def parse_lscpu_topology(summary: TopologySummary, csv_text: str) -> Topology:
    grouped: dict[tuple[int | None, int], list[tuple[int, int | None]]] = defaultdict(list)
    for raw_line in csv_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        columns = [item.strip() for item in line.split(",")]
        if len(columns) < 4:
            continue

        cpu = int(columns[0])
        core = _parse_optional_int(columns[1])
        socket = _parse_optional_int(columns[2])
        node = _parse_optional_int(columns[3])
        online = columns[4].lower() if len(columns) >= 5 else "y"
        if online not in {"y", "yes", "1"}:
            continue

        if summary.threads_per_core == 1:
            grouped[(socket, cpu)].append((cpu, node))
        else:
            grouped[(socket, core if core is not None else cpu)].append((cpu, node))

    groups: list[CpuThreadGroup] = []
    for (socket, core), members in grouped.items():
        cpus = tuple(sorted(cpu for cpu, _ in members))
        node = next((node for _, node in members if node is not None), None)
        groups.append(CpuThreadGroup(socket=socket, core=core, node=node, cpus=cpus))

    groups.sort(key=lambda group: ((group.socket or 0), group.core, group.cpus[0]))
    return Topology(summary=summary, groups=tuple(groups))


class RemoteSession:
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: int = 22,
        proxy_command: str | None = None,
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.proxy_command = proxy_command
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._proxy: paramiko.ProxyCommand | None = None

    def connect(self) -> None:
        connect_kwargs: dict[str, Any] = {
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "look_for_keys": False,
            "allow_agent": False,
            "timeout": 30,
        }
        if self.proxy_command:
            expanded_command = _expand_proxy_command(self.proxy_command, self.hostname, self.port)
            self._proxy = paramiko.ProxyCommand(expanded_command)
            connect_kwargs["sock"] = self._proxy
        try:
            self._client.connect(**connect_kwargs)
        except Exception:
            if self._proxy is not None:
                self._proxy.close()
                self._proxy = None
            raise

    def close(self) -> None:
        self._client.close()
        if self._proxy is not None:
            self._proxy.close()
            self._proxy = None

    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        timeout: int = 1800,
        check: bool = False,
    ) -> CommandResult:
        wrapped = f"bash -lc {shlex.quote(command)}"
        if sudo:
            wrapped = f"sudo -S -p '' {wrapped}"

        stdin, stdout, stderr = self._client.exec_command(
            wrapped,
            timeout=timeout,
            get_pty=sudo,
        )
        if sudo:
            stdin.write(self.password + "\n")
            stdin.flush()

        stdout_text = stdout.read().decode("utf-8", "replace")
        stderr_text = stderr.read().decode("utf-8", "replace")
        exit_status = stdout.channel.recv_exit_status()
        result = CommandResult(command=command, exit_status=exit_status, stdout=stdout_text, stderr=stderr_text)
        if check and exit_status != 0:
            raise RuntimeError(
                f"{self.hostname}: command failed with exit {exit_status}\n"
                f"command: {command}\n"
                f"stdout:\n{stdout_text}\n"
                f"stderr:\n{stderr_text}"
            )
        return result

    def collect_topology(self) -> Topology:
        lscpu_text = self.run("lscpu", check=True).stdout
        lscpu_csv = self.run("lscpu -p=CPU,CORE,SOCKET,NODE,ONLINE", check=True).stdout
        summary = parse_lscpu_summary(lscpu_text)
        return parse_lscpu_topology(summary, lscpu_csv)

    def upload_text(self, destination: str, contents: str) -> None:
        sftp = self._client.open_sftp()
        try:
            with sftp.file(destination, "w") as handle:
                handle.write(contents)
        finally:
            sftp.close()

    def download_text(self, path: str) -> str:
        sftp = self._client.open_sftp()
        try:
            with sftp.file(path, "r") as handle:
                return handle.read().decode("utf-8", "replace")
        finally:
            sftp.close()

    def dump_debug_json(self, topology: Topology) -> str:
        return json.dumps(topology.to_dict(), indent=2)
