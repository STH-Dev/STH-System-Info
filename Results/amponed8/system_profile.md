# System Profile: amponed8

## Identification

| Field | Value |
|---|---|
| Hostname | amponed8 |
| Target hostname | amponed8 |
| Tags | arm64, ampere, single_socket, no_smt |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | Linux amponed8 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 13:53:54 UTC 2025 aarch64 aarch64 aarch64 GNU/Linux |
| Captured at | 2026-04-17T22:03:59.675945+00:00 |

## CPU

| Field | Value |
|---|---|
| Model | Ampere-1a |
| Architecture | aarch64 |
| Vendor | Ampere |
| Sockets | 1 |
| Physical cores | 192 |
| Logical CPUs | 192 |
| Threads per core | 1 |
| NUMA nodes | 1 |
| Base MHz | Unknown |
| Max MHz | 3200.0000 |
| Governor | ondemand |
| L1d cache | 12288 KiB |
| L1i cache | 3072 KiB |
| L2 cache | 393216 KiB |
| L3 cache | Unknown KiB |

## Memory

| Field | Value |
|---|---|
| Total memory | 502.2681541442871 GiB |
| Populated DIMMs / devices | 8 / 8 |
| Memory type | DDR5 |
| Memory speed | 5200 MT/s |

## Storage

| Device | Type | Size | Model |
|---|---|---|---|
| nvme0n1 | disk | 1.8T | WD_BLACK SN850X 2000GB |

## Network

| Description | Product | Logical name | Driver |
|---|---|---|---|
| Ethernet interface | BCM57416 NetXtreme-E Dual-Media 10G RDMA Ethernet Controller | enP1p3s0f0np0 | autonegotiation=on broadcast=yes driver=bnxt_en driverversion=6.8.0-90-generic duplex=full firmware=232.0.155.2/pkg 232.1.132.8 latency=0 link=no multicast=yes port=twisted pair speed=1Gbit/s |
| Ethernet interface | BCM57416 NetXtreme-E Dual-Media 10G RDMA Ethernet Controller | enP1p3s0f1np1 | autonegotiation=on broadcast=yes driver=bnxt_en driverversion=6.8.0-90-generic duplex=full firmware=232.0.155.2/pkg 232.1.132.8 ip=10.11.11.210 latency=0 link=yes multicast=yes port=twisted pair speed=1Gbit/s |
| Ethernet interface | Unknown | enx02210b7f905a | autonegotiation=off broadcast=yes driver=cdc_ether driverversion=6.8.0-90-generic duplex=half firmware=CDC Ethernet Device link=no multicast=yes port=twisted pair |

## Collection

| Status | Count |
|---|---:|
| captured | 25 |

## Artifacts

- Raw outputs are stored under `raw/`.
- Topology artifacts are stored under `topology/`.
