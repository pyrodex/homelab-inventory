export const DEVICE_TYPES = [
  { value: 'linux_server_physical', label: 'Linux Server (Physical)' },
  { value: 'linux_server_virtual', label: 'Linux Server (Virtual)' },
  { value: 'freebsd_server', label: 'FreeBSD Server' },
  { value: 'network_switch', label: 'Network Switch' },
  { value: 'wireless_ap', label: 'Wireless Access Point' },
  { value: 'icmp_only', label: 'ICMP Only Device' },
  { value: 'ip_camera', label: 'IP Camera' },
  { value: 'video_streamer', label: 'Video Streamer' },
  { value: 'iot_device', label: 'IoT Device' },
  { value: 'url', label: 'URL' },
  { value: 'dns_record', label: 'DNS Record' },
  { value: 'ipmi_console', label: 'IPMI Console' },
  { value: 'ups_nut', label: 'UPS (NUT)' }
];

export const MONITOR_TYPES = [
  { value: 'node_exporter', label: 'Node Exporter', defaultPort: 9100 },
  { value: 'smartprom', label: 'SmartProm', defaultPort: 9902 },
  { value: 'snmp', label: 'SNMP', defaultPort: 161 },
  { value: 'icmp', label: 'ICMP', defaultPort: null },
  { value: 'http', label: 'HTTP', defaultPort: 80 },
  { value: 'https', label: 'HTTPS', defaultPort: 443 },
  { value: 'dns', label: 'DNS', defaultPort: 53 },
  { value: 'ipmi', label: 'IPMI', defaultPort: 623 },
  { value: 'nut', label: 'NUT', defaultPort: 3493 },
  { value: 'docker', label: 'Docker', defaultPort: 8090 }
];

export const NETWORKS = ['LAN', 'IoT', 'DMZ', 'GUEST', 'ALL'];

export const INTERFACE_TYPES = [
  '10Base-T', '100Base-TX', '1000Base-T (1GbE)', '2.5GBase-T (2.5GbE)',
  '5GBase-T (5GbE)', '10GBase-T (10GbE)', 'SFP (1GbE)', 'SFP+ (10GbE)',
  '25G SFP28', '40G QSFP+', '50G SFP56', '100G QSFP28', '100G QSFP56',
  '200G QSFP56-DD', '400G QSFP-DD', 'Wi-Fi 4 (802.11n)', 'Wi-Fi 5 (802.11ac)',
  'Wi-Fi 6 (802.11ax)', 'Wi-Fi 6E (6GHz)', 'Wi-Fi 7 (802.11be)', 'Other'
];

export const POE_STANDARDS = [
  'PoE (802.3af)',
  'PoE+ (802.3at)',
  'PoE++ (802.3bt Type 3)',
  'PoE+++ (802.3bt Type 4)',
  'Passive PoE',
  'Other'
];
