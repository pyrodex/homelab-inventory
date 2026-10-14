# Dark Theme Screenshots

Homelab Inventory 2.1 in the dark theme, using demo data. See also the [light theme gallery](../light/README.md).

## Devices

### Dashboard
Stats, live Prometheus status, tag filter bar, and device cards.

![Dashboard](./dashboard.png)

### Condensed view
One line per device for large inventories.

![Condensed view](./condensed.png)

### Tag filter
Click a tag to filter; several tags must all match.

![Tag filter](./tags.png)

### Advanced search
Filter by type, vendor, model, location, monitoring, PoE, and IP.

![Advanced search](./search.png)

### Add device

![Add device](./add-device.png)

### Edit device

![Edit device](./edit-device.png)

### Relationships and impact
What goes down with the UPS.

![Relationships and impact](./relationships.png)

### Device history
Field-level diffs for one device.

![Device history](./device-history.png)

### Global history
Every change across the inventory.

![Global history](./history.png)

### Other Actions menu

![Other Actions menu](./other-actions.png)

### Discovery
ICMP and reverse DNS across a range, with one-click add.

![Discovery](./discovery.png)

### Bulk operations
JSON/CSV import, export, and bulk delete.

![Bulk operations](./bulk-operations.png)

## IPAM

### Subnet grid
Monitored, unmonitored, seen, DHCP, DNS-only, reserved, and free addresses.

![Subnet grid](./ipam.png)

### Not in inventory and In use
Evidence for each unknown address, and PTR names for inventoried ones.

![Not in inventory and In use](./ipam-unknown.png)

### Add to monitoring
Probe results and pre-selected monitors for an unknown address.

![Add to monitoring](./ipam-add-to-monitoring.png)

### DHCP leases
dnsmasq lease sources, push command, and upload.

![DHCP leases](./ipam-dhcp.png)

## Integrations

### Prometheus service discovery
Live status and a generated scrape_configs block.

![Prometheus service discovery](./prometheus-sd.png)

### Ansible inventory export

![Ansible inventory export](./export-ansible.png)

### NetBox CSV export

![NetBox CSV export](./export-netbox.png)

### Webhooks

![Webhooks](./webhooks.png)

## Administration

### Vendors

![Vendors](./admin-vendors.png)

### Models

![Models](./admin-models.png)

### Locations

![Locations](./admin-locations.png)

### Tags
Rename, merge, or delete tags.

![Tags](./admin-tags.png)

## Mobile

### Dashboard

![Dashboard](./mobile-dashboard.png)

### IPAM

![IPAM](./mobile-ipam.png)
