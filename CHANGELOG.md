# Changelog

All notable changes to Homelab Inventory. Versions follow [Semantic Versioning](https://semver.org/).
Releases before 2.0 are listed on the [GitHub releases page](https://github.com/pyrodex/homelab-inventory/releases).

## [Unreleased]

### Added
- **Reverse DNS in IPAM.** Ping sweeps look up the PTR record for every address, not just ones that answer.
  - Addresses whose only evidence is a PTR record get a new **rose** "Reverse DNS only" state. By default they're kept
    out of free and next-free; set `IPAM_PTR_BLOCKS_FREE=false` to allow them.
  - Any address with a PTR record gets a corner marker in the grid.
  - PTR names show in tooltips, address details and the **In use** list, which flags inventoried devices with **no PTR**.
  - New summary counts: `dns_only` and `with_ptr`.
- `IPAM_SWEEP_PTR` (default on) to limit PTR lookups to addresses that answer.

### Changed
- PTR lookups now separate "no record" from resolver errors, so a DNS outage during a sweep never erases names already
  recorded.
- `ipam.address_discovered` still fires only for addresses seen on the network. A PTR record alone doesn't count; an
  address known only from DNS fires when it first answers.

## [2.0.0] - 2026-10-13

The inventory now understands your network, not just your device list: which IPs are really free, what depends on what,
and what Prometheus says is up. It can also feed Ansible, NetBox and webhooks directly.

Upgrading from 1.x is drop-in (migrations run automatically), but read
[Upgrading to 2.0](README.md#upgrading-to-20) first, mainly for the new Prometheus target labels.

### Added

**IPAM** (#17, #22)
- CIDR subnets (IPv4/IPv6) with name, VLAN, gateway, location, and reserved ranges (DHCP pools, VIPs).
- Color-coded address grid, utilization, free ranges, **next free IP**, and one-click "add device here".
- Flags duplicate IP assignments and devices whose IP isn't inside any subnet.
- Scheduled per-subnet **ping sweeps** (IPv4, bounded size) and **Scan now**.
- **dnsmasq DHCP lease import**: watched files (`DNSMASQ_LEASES_PATH`), `curl` push, or upload. Per-source snapshots
  and automatic expiry.
- Addresses that answer pings or hold a lease but aren't inventoried are shown as "not in inventory" and are never
  offered as free.

**Prometheus** (#18)
- HTTP service discovery at `/api/prometheus/sd` (optional bearer token), plus a generated `scrape_configs` snippet
  with blackbox/SNMP relabeling.
- Live **Up / Down / Degraded / Not scraped** status on every device from `PROMETHEUS_URL`, using `probe_success` over
  `up`. Matches by device id, then device name, then instance, so hand-written jobs still match.

**Tags & relationships** (#19)
- Free-form tags with autocomplete, click-to-filter, and Admin rename/merge/delete. Tags work in search, bulk CSV/JSON,
  history and Prometheus labels.
- Typed relationships: *runs on* (VM → host), *connected to* (→ switch, with port), *powered by* (→ UPS/PDU, with outlet).
  Loops are rejected.
- **Impact analysis**: everything that goes down with a device, shown as a dependency tree.

**Exports** (#20)
- **Ansible dynamic inventory** (`/api/export/ansible`, a stdlib-only script, or static YAML). Groups by type,
  location, vendor, tag, network and host, with `homelab_*` host variables. Hostnames stay stable regardless of filters.
- **NetBox CSV** bulk-import bundle in dependency order, matching NetBox 4.7's import formats.

**Webhooks** (#23)
- JSON POST on `device.created`, `device.updated`, `device.deleted`, `device.relationship_changed`, and
  `ipam.address_discovered` (a new address not in inventory).
- Optional HMAC-SHA256 signature (`X-Hub-Signature-256`), retries on 5xx/timeouts, redirects refused, and a
  per-webhook delivery log with a test button.
- Events fire only after the change commits.

### Changed
- Prometheus targets gain the labels `inventory_device_id`, `inventory_group` (SD only), `tags` and `runs_on`.
- Discovery probes run in parallel.
- Device history records tag and relationship changes.
- The backend runs in-process background workers (sweep scheduler, lease watcher, webhook dispatcher). Disable them
  with `IPAM_BACKGROUND_WORKERS=false`.

### Fixed
- Ping timeout passed in milliseconds to Linux iputils, which expects seconds; unreachable hosts no longer hang
  until the subprocess timeout.
- Prometheus export no longer fails on devices without an IP.
- Bulk JSON import no longer crashes on rows that aren't objects.
- Backend tests ran against the real `DATABASE_PATH` and wiped it at teardown. They now use a temporary database.
- Stale `test_api.py` assertions updated for the `{success, data}` response format; the full suite (105 tests) passes.

### Upgrade notes
- Four additive migrations run on first start. Back up first.
- The new target labels start new Prometheus time series for exported targets; see the README for how to drop them.
- The app still has no built-in authentication; keep it behind your reverse proxy's auth.

[Unreleased]: https://github.com/pyrodex/homelab-inventory/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/pyrodex/homelab-inventory/compare/v1.7.3...v2.0.0
