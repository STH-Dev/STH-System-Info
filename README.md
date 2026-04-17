# STH System Info

`sth-system-info` collects a reusable, SPEC-style machine inventory from remote Linux
systems over SSH. It keeps raw command outputs, generates a normalized summary JSON,
renders a Markdown system profile, and captures `lstopo` topology artifacts.

## What It Produces

Each collection writes a host directory containing:

- `manifest.json`
- `summary.json`
- `system_profile.md`
- `topology/lstopo.xml`
- `topology/lstopo.txt`
- `topology/lstopo.svg` when available
- `raw/` command outputs such as:
  - `lscpu.txt`
  - `lscpu-topology.csv`
  - `cpuinfo.txt`
  - `meminfo.txt`
  - `numactl.txt`
  - `lsblk.json`
  - `df.txt`
  - `ipaddr.txt`
  - `lspci.txt`
  - `lspci_verbose.txt`
  - `lshw_network.txt`
  - `dmi_system.txt`
  - `dmi_baseboard.txt`
  - `dmi_processor.txt`
  - `dmi_memory.txt`
  - `uname.txt`
  - `os-release.txt`
  - `cmdline.txt`
  - `cpu_governor.txt`
  - `transparent_hugepage.txt`

## Quick Start

```bash
cd /Users/patrickkennedy/Desktop/AgentC/sth-system-info
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Run a collection against a configured host:

```bash
export STH_SYSTEM_INFO_SSH_PASSWORD=sthuser
sth-system-info collect \
  --config hosts/sth-lab.toml \
  --host thor \
  --output-root runs
```

Or write directly to a fixed directory:

```bash
sth-system-info collect \
  --config hosts/sth-lab.toml \
  --host thor \
  --output-dir /tmp/thor-system-info
```

## Notes

- SSH and sudo use the same password by default.
- Commands that require privilege are treated as optional. The collection does not
  fail if one of them is unavailable.
- The current implementation is Linux-focused and intended for benchmark-lab hosts.
