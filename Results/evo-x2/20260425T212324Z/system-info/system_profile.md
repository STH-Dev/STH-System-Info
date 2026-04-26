# System Profile: evo-x2

## Identification

| Field | Value |
|---|---|
| Hostname | evo-x2 |
| Target hostname | evo-x2 |
| Tags | x86_64 |
| OS | Ubuntu 26.04 LTS |
| Kernel | Linux evo-x2 7.0.0-14-generic #14-Ubuntu SMP PREEMPT_DYNAMIC Mon Apr 13 11:09:53 UTC 2026 x86_64 GNU/Linux |
| Captured at | 2026-04-25T21:26:36.798767+00:00 |

## CPU

| Field | Value |
|---|---|
| Model | AMD RYZEN AI MAX+ 395 w/ Radeon 8060S |
| Architecture | x86_64 |
| Vendor | AuthenticAMD |
| Sockets | 1 |
| Physical cores | 16 |
| Logical CPUs | 32 |
| Threads per core | 2 |
| NUMA nodes | 1 |
| Base MHz | Unknown |
| Max MHz | 5187.5000 |
| Governor | powersave |
| L1d cache | 768 KiB |
| L1i cache | 512 KiB |
| L2 cache | 16384 KiB |
| L3 cache | 65536 KiB |

## Memory

| Field | Value |
|---|---|
| Total memory | 122.7 GiB |
| Installed memory from DMI | 128.0 GiB |
| Populated DIMMs / devices | 8 / 8 |
| Filled memory channels (best-effort) | 8 |
| Channel inference source(s) | bank_locator:channel |
| Memory device slots in array | 8 |
| Maximum array capacity | 64 GB |
| DIMM capacities | 8 x 16 GB |
| DIMM type(s) | LPDDR5 |
| DIMM detail(s) | Synchronous Unbuffered (Unregistered) |
| Form factor(s) | Other |
| Current configured speed(s) | 8000 MT/s |
| Rated DIMM speed(s) | 8532 MT/s |
| Manufacturer(s) | Micron Technology |
| Part number(s) | MT62F4G32D8DV-023 WT |

### DIMM Inventory

| Locator | Bank | Channel | Size | Type | Running | Rated | Manufacturer | Part Number | Rank |
|---|---|---|---|---|---|---|---|---|---|
| DIMM 0 | P0 CHANNEL A | Channel A | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL B | Channel B | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL C | Channel C | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL D | Channel D | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL E | Channel E | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL F | Channel F | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL G | Channel G | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |
| DIMM 0 | P0 CHANNEL H | Channel H | 16 GB | LPDDR5 / Synchronous Unbuffered (Unregistered) | 8000 MT/s | 8532 MT/s | Micron Technology | MT62F4G32D8DV-023 WT | 2 |

## Storage

| Device | Type | Size | Model |
|---|---|---|---|
| sda | disk | 0B | Flash Drive |
| nvme0n1 | disk | 1.9T | ADATA LEGEND 900 |

## Network

| Description | Product | Logical name | Driver |
|---|---|---|---|
| Ethernet interface | RTL8125 2.5GbE Controller | eno1 | autonegotiation=on broadcast=yes driver=r8169 driverversion=7.0.0-14-generic duplex=full firmware=rtl8125b-2_0.0.2 07/13/20 ip=10.11.11.154 latency=0 link=yes multicast=yes port=twisted pair speed=100Mbit/s |
| Ethernet interface | MT7925 (RZ717) Wi-Fi 7 160MHz | wlp195s0 | broadcast=yes driver=mt7925e driverversion=7.0.0-14-generic firmware=____000000-20260106153120 ip=10.11.11.247 latency=0 link=yes multicast=yes |

## Collection

| Status | Count |
|---|---:|
| captured | 22 |
| skipped | 3 |

## Artifacts

- Raw outputs are stored under `raw/`.
- Topology artifacts are stored under `topology/`.
