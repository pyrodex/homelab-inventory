# Ansible dynamic inventory

Homelab Inventory can act as an Ansible inventory source.

```bash
# Download the inventory script from your instance (no dependencies beyond Python 3)
curl -o homelab_inventory.py http://homelab-inventory:5000/api/export/ansible/script
chmod +x homelab_inventory.py

export HOMELAB_INVENTORY_URL=http://homelab-inventory:5000
ansible-inventory -i homelab_inventory.py --graph
ansible -i homelab_inventory.py 'tag_proxmox:&monitoring_enabled' -m ping
```

The script's source lives at [`backend/scripts/ansible_inventory.py`](../../backend/scripts/ansible_inventory.py).
Prefer a static file? `curl -o inventory.yml "http://homelab-inventory:5000/api/export/ansible?format=yaml"`.

| Variable | Purpose |
|---|---|
| `HOMELAB_INVENTORY_URL` | Base URL of the app (required) |
| `HOMELAB_INVENTORY_FILTER` | Query string to narrow hosts, e.g. `tag=prod&monitoring_enabled=true` |
| `HOMELAB_INVENTORY_TOKEN` | Bearer token, if the app sits behind auth |
| `HOMELAB_INVENTORY_TIMEOUT` | Request timeout in seconds (default 10) |
| `HOMELAB_INVENTORY_INSECURE` | `1` to skip TLS verification |

## Groups

| Group | Members |
|---|---|
| `type_<device_type>` | e.g. `type_linux_server_physical` |
| `location_<location>` | e.g. `location_basement_rack` |
| `vendor_<vendor>` | e.g. `vendor_supermicro` |
| `tag_<tag>` | e.g. `tag_prod`, `tag_k8s_node` (`-` and `.` become `_`) |
| `network_<network>` | from the device's Networks field, e.g. `network_iot` |
| `runs_on_<host>` | VMs/containers running on that host |
| `monitoring_enabled` / `monitoring_disabled` | by the monitoring toggle |

URL and DNS-record entries are excluded unless `include_all_types=true` is in the filter.

## Host variables

`ansible_host` (IP or hostname, port stripped) plus `homelab_id`, `homelab_name`, `homelab_type`,
`homelab_function`, `homelab_vendor`, `homelab_model`, `homelab_location`, `homelab_serial`,
`homelab_networks`, `homelab_tags`, `homelab_runs_on`, `homelab_monitoring_enabled`,
`homelab_monitors`, `homelab_subnet`, `homelab_vlan`.

Inventory hostnames are the device name when it's a clean token (`[A-Za-z0-9._-]`), otherwise a slug;
duplicate names get `-<id>`. Names are computed across the whole inventory, so filtering never renames a host.
