from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Defaults:
    username: str
    port: int


@dataclass(frozen=True)
class HostConfig:
    name: str
    hostname: str
    display_name: str | None
    proxy_command: str | None
    username: str
    port: int
    tags: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    defaults: Defaults
    hosts: tuple[HostConfig, ...]

    def require_host(self, name: str) -> HostConfig:
        by_name = {host.name: host for host in self.hosts}
        if name not in by_name:
            available = ", ".join(sorted(by_name))
            raise ValueError(f"Unknown host '{name}'. Available hosts: {available}")
        return by_name[name]


def load_config(path: Path) -> AppConfig:
    data = tomllib.loads(path.read_text())
    defaults_raw = data.get("defaults", {})
    defaults = Defaults(
        username=str(defaults_raw.get("username", "sthuser")),
        port=int(defaults_raw.get("port", 22)),
    )

    hosts: list[HostConfig] = []
    for item in data.get("hosts", []):
        hosts.append(
            HostConfig(
                name=str(item["name"]),
                hostname=str(item.get("hostname", item["name"])),
                display_name=(
                    str(item["display_name"])
                    if item.get("display_name") is not None
                    else None
                ),
                proxy_command=(
                    str(item["proxy_command"])
                    if item.get("proxy_command") is not None
                    else None
                ),
                username=str(item.get("username", defaults.username)),
                port=int(item.get("port", defaults.port)),
                tags=tuple(str(tag) for tag in item.get("tags", [])),
                enabled=bool(item.get("enabled", True)),
            )
        )

    if not hosts:
        raise ValueError(f"No hosts configured in {path}")

    return AppConfig(defaults=defaults, hosts=tuple(hosts))
