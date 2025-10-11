import React, { useState, useEffect } from 'react';
import { Plus, Server, Activity, Download, Edit2, Trash2, X, Check, Settings, List, Grid, Copy } from 'lucide-react';

const API_URL = '/api';

const DEVICE_TYPES = [
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

const MONITOR_TYPES = [
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

const NETWORKS = ['LAN', 'IoT', 'DMZ', 'GUEST', 'ALL'];

const INTERFACE_TYPES = [
  '10Base-T', '100Base-TX', '1000Base-T (1GbE)', '2.5GBase-T (2.5GbE)',
  '5GBase-T (5GbE)', '10GBase-T (10GbE)', 'SFP (1GbE)', 'SFP+ (10GbE)',
  '25G SFP28', '40G QSFP+', '50G SFP56', '100G QSFP28', '100G QSFP56',
  '200G QSFP56-DD', '400G QSFP-DD', 'Wi-Fi 4 (802.11n)', 'Wi-Fi 5 (802.11ac)',
  'Wi-Fi 6 (802.11ax)', 'Wi-Fi 6E (6GHz)', 'Wi-Fi 7 (802.11be)', 'Other'
];

const POE_STANDARDS = [
  'PoE (802.3af)',
  'PoE+ (802.3at)',
  'PoE++ (802.3bt Type 3)',
  'PoE+++ (802.3bt Type 4)',
  'Passive PoE',
  'Other'
];

export default function App() {
  const [devices, setDevices] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedType, setSelectedType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [cloningDevice, setCloningDevice] = useState(null);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('full');

  useEffect(() => {
    fetchDevices();
    fetchStats();
  }, [selectedType]);

  const fetchDevices = async () => {
    try {
      const url = selectedType === 'all' ? `${API_URL}/devices` : `${API_URL}/devices?type=${selectedType}`;
      const res = await fetch(url);
      const data = await res.json();
      setDevices(data);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const handleExportPrometheus = async (mode = 'download') => {
    try {
      const url = mode === 'download' ? `${API_URL}/prometheus/export?mode=download` : `${API_URL}/prometheus/export?mode=write`;
      const res = await fetch(url);
      if (mode === 'write') {
        const data = await res.json();
        alert(`Success! ${data.message}`);
      } else {
        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = 'prometheus_targets.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
      }
    } catch (err) {
      console.error('Failed to export:', err);
      alert('Failed to export configuration');
    }
  };

  const toggleMonitoring = async (device) => {
    try {
      await fetch(`${API_URL}/devices/${device.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...device, monitoring_enabled: !device.monitoring_enabled })
      });
      fetchDevices();
      fetchStats();
    } catch (err) {
      console.error('Failed to toggle monitoring:', err);
    }
  };

  const deleteDevice = async (id) => {
    if (!window.confirm('Are you sure you want to delete this device?')) return;
    try {
      await fetch(`${API_URL}/devices/${id}`, { method: 'DELETE' });
      fetchDevices();
      fetchStats();
    } catch (err) {
      console.error('Failed to delete device:', err);
    }
  };

  const handleClone = (device) => {
    const clonedDevice = {
      ...device,
      name: '',
      ip_address: '',
      location_id: '',
      id: null
    };
    setCloningDevice(clonedDevice);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Homelab Inventory</h1>
              <p className="text-gray-600 mt-1">Manage your infrastructure monitoring</p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowAdminModal(true)} className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700">
                <Settings size={20} />Admin
              </button>
              <button onClick={() => handleExportPrometheus('write')} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                <Check size={20} />Write Prometheus Files
              </button>
              <button onClick={() => handleExportPrometheus('download')} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Download size={20} />Download Config
              </button>
              <button onClick={() => setShowAddModal(true)} className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700">
                <Plus size={20} />Add Device
              </button>
            </div>
          </div>
        </div>
      </div>

      {stats && (
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div><p className="text-gray-600 text-sm">Total Devices</p><p className="text-3xl font-bold text-gray-900">{stats.total_devices}</p></div>
                <Server className="text-blue-600" size={40} />
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div><p className="text-gray-600 text-sm">Monitoring Enabled</p><p className="text-3xl font-bold text-green-600">{stats.enabled_devices}</p></div>
                <Activity className="text-green-600" size={40} />
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div><p className="text-gray-600 text-sm">Monitoring Disabled</p><p className="text-3xl font-bold text-red-600">{stats.disabled_devices}</p></div>
                <X className="text-red-600" size={40} />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-end justify-between gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Device Type</label>
              <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)} className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                <option value="all">All Devices</option>
                {DEVICE_TYPES.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}
              </select>
            </div>
            <div className="flex-1 max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">Search Devices</label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name, IP, function, vendor, model..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setViewMode('full')} className={`p-2 rounded-lg ${viewMode === 'full' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`} title="Full View"><Grid size={20} /></button>
              <button onClick={() => setViewMode('condensed')} className={`p-2 rounded-lg ${viewMode === 'condensed' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`} title="Condensed View"><List size={20} /></button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-4 pb-8">
        {loading ? (
          <div className="text-center py-12"><p className="text-gray-600">Loading devices...</p></div>
        ) : devices.length === 0 ? (
          <div className="bg-white p-12 rounded-lg shadow text-center">
            <Server className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-gray-600">No devices found. Add your first device to get started.</p>
          </div>
        ) : (
          <DeviceList 
            devices={devices} 
            searchTerm={searchTerm} 
            viewMode={viewMode} 
            onToggleMonitoring={toggleMonitoring} 
            onEdit={setEditingDevice} 
            onClone={handleClone} 
            onDelete={deleteDevice} 
            onClearSearch={() => setSearchTerm('')} 
          />
        )}
      </div>

      {(showAddModal || editingDevice || cloningDevice) && <DeviceModal device={editingDevice || cloningDevice} onClose={() => { setShowAddModal(false); setEditingDevice(null); setCloningDevice(null); }} onSave={() => { fetchDevices(); fetchStats(); setShowAddModal(false); setEditingDevice(null); setCloningDevice(null); }} />}
      {showAdminModal && <AdminModal onClose={() => setShowAdminModal(false)} />}
    </div>
  );
}

function DeviceList({ devices, searchTerm, viewMode, onToggleMonitoring, onEdit, onClone, onDelete, onClearSearch }) {
  const filteredDevices = devices.filter(device => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      device.name?.toLowerCase().includes(search) ||
      device.ip_address?.toLowerCase().includes(search) ||
      device.function?.toLowerCase().includes(search) ||
      device.vendor_name?.toLowerCase().includes(search) ||
      device.model_name?.toLowerCase().includes(search) ||
      device.location_name?.toLowerCase().includes(search) ||
      device.serial_number?.toLowerCase().includes(search) ||
      device.networks?.toLowerCase().includes(search) ||
      device.interface_type?.toLowerCase().includes(search) ||
      device.poe_standards?.toLowerCase().includes(search) ||
      DEVICE_TYPES.find(t => t.value === device.device_type)?.label.toLowerCase().includes(search) ||
      device.monitors?.some(m => m.monitor_type.toLowerCase().includes(search))
    );
  });

  if (filteredDevices.length === 0) {
    return (
      <div className="bg-white p-12 rounded-lg shadow text-center">
        <Server className="mx-auto text-gray-400 mb-4" size={48} />
        <p className="text-gray-600">No devices match your search criteria.</p>
        <button onClick={onClearSearch} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Clear Search
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {searchTerm && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
          Found {filteredDevices.length} device{filteredDevices.length !== 1 ? 's' : ''} matching "{searchTerm}"
        </div>
      )}
      {filteredDevices.map(device => (
        <DeviceCard 
          key={device.id} 
          device={device} 
          viewMode={viewMode} 
          onToggleMonitoring={onToggleMonitoring} 
          onEdit={onEdit} 
          onClone={onClone} 
          onDelete={onDelete} 
        />
      ))}
    </div>
  );
}

function DeviceCard({ device, viewMode, onToggleMonitoring, onEdit, onClone, onDelete }) {
  if (viewMode === 'condensed') {
    return (
      <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4 flex-1">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-gray-900 truncate">{device.name}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${device.monitoring_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                  {device.monitoring_enabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                <span>{DEVICE_TYPES.find(t => t.value === device.device_type)?.label || device.device_type}</span>
                {device.ip_address && <span>{device.ip_address}</span>}
                {device.location_name && <span>📍 {device.location_name}</span>}
                {device.monitors && device.monitors.length > 0 && <span className="text-blue-600">{device.monitors.length} monitor{device.monitors.length !== 1 ? 's' : ''}</span>}
              </div>
            </div>
          </div>
          <div className="flex gap-2 ml-4">
            <button onClick={() => onToggleMonitoring(device)} className={`p-2 rounded-lg ${device.monitoring_enabled ? 'bg-red-100 text-red-600 hover:bg-red-200' : 'bg-green-100 text-green-600 hover:bg-green-200'}`}>
              {device.monitoring_enabled ? <X size={18} /> : <Check size={18} />}
            </button>
            <button onClick={() => onClone(device)} className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200" title="Clone Device"><Copy size={18} /></button>
            <button onClick={() => onEdit(device)} className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200"><Edit2 size={18} /></button>
            <button onClick={() => onDelete(device.id)} className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"><Trash2 size={18} /></button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <h3 className="text-xl font-bold text-gray-900">{device.name}</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${device.monitoring_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
              {device.monitoring_enabled ? 'Monitoring Active' : 'Monitoring Disabled'}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><p className="text-gray-600">Type</p><p className="font-medium text-gray-900">{DEVICE_TYPES.find(t => t.value === device.device_type)?.label || device.device_type}</p></div>
            {device.ip_address && <div><p className="text-gray-600">Address</p><p className="font-medium text-gray-900">{device.ip_address}</p></div>}
            {device.function && <div><p className="text-gray-600">Function</p><p className="font-medium text-gray-900">{device.function}</p></div>}
            {device.networks && <div><p className="text-gray-600">Networks</p><p className="font-medium text-gray-900">{device.networks}</p></div>}
            {device.vendor_name && <div><p className="text-gray-600">Vendor</p><p className="font-medium text-gray-900">{device.vendor_name}</p></div>}
            {device.model_name && <div><p className="text-gray-600">Model</p><p className="font-medium text-gray-900">{device.model_name}</p></div>}
            {device.location_name && <div><p className="text-gray-600">Location</p><p className="font-medium text-gray-900">{device.location_name}</p></div>}
            {device.interface_type && <div><p className="text-gray-600">Interface</p><p className="font-medium text-gray-900">{device.interface_type}</p></div>}
            {device.poe_powered && <div><p className="text-gray-600">PoE Powered</p><p className="font-medium text-green-600">Yes</p></div>}
            {device.poe_standards && <div><p className="text-gray-600">PoE Standards</p><p className="font-medium text-purple-600">{device.poe_standards}</p></div>}
          </div>
          {device.monitors && device.monitors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Monitors:</p>
              <div className="flex flex-wrap gap-2">
                {device.monitors.map(monitor => (
                  <span key={monitor.id} className={`px-3 py-1 rounded-full text-xs ${monitor.enabled ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}>
                    {monitor.monitor_type}{monitor.port && `:${monitor.port}`}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-2 ml-4">
          <button onClick={() => onToggleMonitoring(device)} className={`p-2 rounded-lg ${device.monitoring_enabled ? 'bg-red-100 text-red-600 hover:bg-red-200' : 'bg-green-100 text-green-600 hover:bg-green-200'}`}>
            {device.monitoring_enabled ? <X size={20} /> : <Check size={20} />}
          </button>
          <button onClick={() => onClone(device)} className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200" title="Clone Device"><Copy size={20} /></button>
          <button onClick={() => onEdit(device)} className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200"><Edit2 size={20} /></button>
          <button onClick={() => onDelete(device.id)} className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"><Trash2 size={20} /></button>
        </div>
      </div>
    </div>
  );
}

function DeviceModal({ device, onClose, onSave }) {
  const [formData, setFormData] = useState(device || {
    name: '', device_type: 'linux_server_physical', ip_address: '', function: '',
    vendor_id: '', model_id: '', location_id: '', serial_number: '', networks: 'LAN',
    interface_type: '', poe_powered: false, poe_standards: '', monitoring_enabled: true
  });

  const [monitors, setMonitors] = useState(
    device?.monitors 
      ? device.id 
        ? device.monitors
        : device.monitors.map(m => ({ ...m, id: null }))
      : []
  );
  const [newMonitor, setNewMonitor] = useState({ monitor_type: 'node_exporter', port: 9100, enabled: true });
  const [vendors, setVendors] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedNetworks, setSelectedNetworks] = useState(device?.networks ? device.networks.split(',') : ['LAN']);
  const [selectedInterfaces, setSelectedInterfaces] = useState(device?.interface_type ? device.interface_type.split(',') : []);
  const [selectedPoeStandards, setSelectedPoeStandards] = useState(device?.poe_standards ? device.poe_standards.split(',') : []);

  useEffect(() => { fetchVendors(); fetchLocations(); }, []);
  useEffect(() => { if (formData.vendor_id) fetchModels(formData.vendor_id); else setModels([]); }, [formData.vendor_id]);

  const fetchVendors = async () => { try { const res = await fetch(`${API_URL}/vendors`); const data = await res.json(); setVendors(data); } catch (err) { console.error(err); } };
  const fetchModels = async (vendorId) => { try { const res = await fetch(`${API_URL}/models?vendor_id=${vendorId}`); const data = await res.json(); setModels(data); } catch (err) { console.error(err); } };
  const fetchLocations = async () => { try { const res = await fetch(`${API_URL}/locations`); const data = await res.json(); setLocations(data); } catch (err) { console.error(err); } };

  const handleNetworkToggle = (network) => {
    if (network === 'ALL') { setSelectedNetworks(['ALL']); }
    else { let newSelection = selectedNetworks.filter(n => n !== 'ALL'); if (newSelection.includes(network)) { newSelection = newSelection.filter(n => n !== network); } else { newSelection.push(network); } if (newSelection.length === 0) { newSelection = ['LAN']; } setSelectedNetworks(newSelection); }
  };

  const handleInterfaceToggle = (interfaceType) => {
    let newSelection = [...selectedInterfaces];
    if (newSelection.includes(interfaceType)) { newSelection = newSelection.filter(i => i !== interfaceType); } else { newSelection.push(interfaceType); }
    setSelectedInterfaces(newSelection);
  };

  const handlePoeStandardToggle = (poeStandard) => {
    let newSelection = [...selectedPoeStandards];
    if (newSelection.includes(poeStandard)) { newSelection = newSelection.filter(p => p !== poeStandard); } else { newSelection.push(poeStandard); }
    setSelectedPoeStandards(newSelection);
  };

  const handleSave = async () => {
    const missingFields = [];
    
    if (!formData.name?.trim()) missingFields.push('Device Name');
    if (!formData.ip_address?.trim()) missingFields.push('Address');
    if (!formData.device_type) missingFields.push('Device Type');
    if (!formData.function?.trim()) missingFields.push('Function');
    if (!formData.vendor_id) missingFields.push('Vendor');
    if (!formData.model_id) missingFields.push('Model');
    if (!formData.location_id) missingFields.push('Location');
    if (!formData.serial_number?.trim()) missingFields.push('Serial Number');
    
    if (missingFields.length > 0) { 
      alert(`The following required fields are missing:\n\n${missingFields.join('\n')}`); 
      return; 
    }
    
    try {
      const saveData = { 
        ...formData, 
        networks: selectedNetworks.join(','), 
        interface_type: selectedInterfaces.join(','), 
        poe_standards: selectedPoeStandards.join(','),
        vendor_id: formData.vendor_id || null, 
        model_id: formData.model_id || null, 
        location_id: formData.location_id || null 
      };
      
      const isEdit = device && device.id;
      const method = isEdit ? 'PUT' : 'POST';
      const url = isEdit ? `${API_URL}/devices/${device.id}` : `${API_URL}/devices`;
      
      const res = await fetch(url, { 
        method, 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(saveData) 
      });
      const savedDevice = await res.json();
      
      if (isEdit) {
        const originalMonitorIds = (device.monitors || [])
          .filter(m => m.id)
          .map(m => m.id);
        
        const currentMonitorIds = monitors
          .filter(m => m.id)
          .map(m => m.id);
        
        const monitorsToDelete = originalMonitorIds.filter(
          id => !currentMonitorIds.includes(id)
        );
        
        for (const monitorId of monitorsToDelete) {
          await fetch(`${API_URL}/monitors/${monitorId}`, { 
            method: 'DELETE' 
          });
        }
      }
      
      for (const monitor of monitors) { 
        if (!monitor.id) { 
          await fetch(`${API_URL}/devices/${savedDevice.id}/monitors`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(monitor) 
          }); 
        } 
      }
      
      onSave();
    } catch (err) { 
      console.error(err); 
      alert('Failed to save device'); 
    }
  };

  const addMonitor = () => {
    const existingMonitor = monitors.find(m => m.monitor_type === newMonitor.monitor_type);
    if (existingMonitor) { alert(`A ${MONITOR_TYPES.find(t => t.value === newMonitor.monitor_type)?.label || newMonitor.monitor_type} monitor is already added to this device.`); return; }
    setMonitors([...monitors, { ...newMonitor, id: null }]);
    setNewMonitor({ monitor_type: 'node_exporter', port: 9100, enabled: true });
  };

  const removeMonitor = (index) => { setMonitors(monitors.filter((_, i) => i !== index)); };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">{device && device.id ? 'Edit Device' : device ? 'Clone Device' : 'Add New Device'}</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Device Name *</label><input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Device Type *</label><select value={formData.device_type} onChange={(e) => setFormData({ ...formData, device_type: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required>{DEVICE_TYPES.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}</select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Address *</label><input type="text" value={formData.ip_address} onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })} placeholder="192.168.1.10, example.com, or 192.168.1.10:9100" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Function *</label><input type="text" value={formData.function} onChange={(e) => setFormData({ ...formData, function: e.target.value })} placeholder="e.g., Web Server, Storage" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Vendor *</label><select value={formData.vendor_id} onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value, model_id: '' })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required><option value="">Select Vendor...</option>{vendors.map(vendor => <option key={vendor.id} value={vendor.id}>{vendor.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Model *</label><select value={formData.model_id} onChange={(e) => setFormData({ ...formData, model_id: e.target.value })} disabled={!formData.vendor_id} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100" required><option value="">Select Model...</option>{models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Location *</label><select value={formData.location_id} onChange={(e) => setFormData({ ...formData, location_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required><option value="">Select Location...</option>{locations.map(location => <option key={location.id} value={location.id}>{location.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Serial Number *</label><input type="text" value={formData.serial_number} onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required /></div>
            <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">Networks</label><div className="flex flex-wrap gap-2">{NETWORKS.map(network => <button key={network} type="button" onClick={() => handleNetworkToggle(network)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selectedNetworks.includes(network) ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>{network}</button>)}</div><p className="text-xs text-gray-500 mt-1">Select ALL to override other selections</p></div>
            <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">Interface Types</label><div className="flex flex-wrap gap-2">{INTERFACE_TYPES.map(iface => <button key={iface} type="button" onClick={() => handleInterfaceToggle(iface)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selectedInterfaces.includes(iface) ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>{iface}</button>)}</div><p className="text-xs text-gray-500 mt-1">Select multiple interface types if applicable</p></div>
            <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">PoE Standards</label><div className="flex flex-wrap gap-2">{POE_STANDARDS.map(poe => <button key={poe} type="button" onClick={() => handlePoeStandardToggle(poe)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selectedPoeStandards.includes(poe) ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>{poe}</button>)}</div><p className="text-xs text-gray-500 mt-1">Select applicable PoE standards for this device</p></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-3">Options</label><div className="space-y-2"><label className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"><input type="checkbox" checked={formData.poe_powered} onChange={(e) => setFormData({ ...formData, poe_powered: e.target.checked })} className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500" /><span className="text-sm font-medium text-gray-700">PoE Powered</span></label><label className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"><input type="checkbox" checked={formData.monitoring_enabled} onChange={(e) => setFormData({ ...formData, monitoring_enabled: e.target.checked })} className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500" /><span className="text-sm font-medium text-gray-700">Monitoring Enabled</span></label></div></div>
          </div>
          <div className="border-t pt-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Monitors</h3>
            {monitors.length > 0 && (
              <div className="space-y-2 mb-4">
                {monitors.map((monitor, index) => (
                  <div key={index} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                    <span className="flex-1 text-sm">{MONITOR_TYPES.find(m => m.value === monitor.monitor_type)?.label || monitor.monitor_type}{monitor.port && ` (Port: ${monitor.port})`}</span>
                    <button type="button" onClick={() => removeMonitor(index)} className="p-1 text-red-600 hover:bg-red-100 rounded"><X size={16} /></button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <select value={newMonitor.monitor_type} onChange={(e) => { const type = MONITOR_TYPES.find(m => m.value === e.target.value); setNewMonitor({ ...newMonitor, monitor_type: e.target.value, port: type?.defaultPort || null }); }} className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">{MONITOR_TYPES.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}</select>
              <input type="number" value={newMonitor.port || ''} onChange={(e) => setNewMonitor({ ...newMonitor, port: e.target.value ? parseInt(e.target.value) : null })} placeholder="Port" className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
              <button type="button" onClick={addMonitor} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Add</button>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-6 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">Cancel</button>
            <button type="button" onClick={handleSave} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">{device && device.id ? 'Update Device' : device ? 'Clone Device' : 'Create Device'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AdminModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('vendors');
  const [vendors, setVendors] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [newVendorName, setNewVendorName] = useState('');
  const [newModelName, setNewModelName] = useState('');
  const [newLocationName, setNewLocationName] = useState('');
  const [selectedVendorForModel, setSelectedVendorForModel] = useState('');
  const [editingVendor, setEditingVendor] = useState(null);
  const [editingModel, setEditingModel] = useState(null);
  const [editingLocation, setEditingLocation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => { setLoading(true); await Promise.all([fetchVendors(), fetchModels(), fetchLocations()]); setLoading(false); };
  const fetchVendors = async () => { try { const res = await fetch(`${API_URL}/vendors`); const data = await res.json(); setVendors(data); } catch (err) { console.error(err); } };
  const fetchModels = async () => { 
    try { 
      const res = await fetch(`${API_URL}/models`); 
      const data = await res.json(); 
      const sortedData = data.sort((a, b) => {
        const vendorCompare = (a.vendor_name || '').localeCompare(b.vendor_name || '');
        if (vendorCompare !== 0) return vendorCompare;
        return (a.name || '').localeCompare(b.name || '');
      });
      setModels(sortedData); 
    } catch (err) { 
      console.error(err); 
    } 
  };
  const fetchLocations = async () => { try { const res = await fetch(`${API_URL}/locations`); const data = await res.json(); setLocations(data); } catch (err) { console.error(err); } };

  const addVendor = async () => {
    if (!newVendorName.trim()) return;
    try {
      const res = await fetch(`${API_URL}/vendors`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newVendorName.trim() }) });
      if (res.ok) { setNewVendorName(''); fetchVendors(); } else { const err = await res.json(); alert(err.error || 'Failed to add vendor'); }
    } catch (err) { console.error(err); alert('Failed to add vendor'); }
  };

  const updateVendor = async (id, name) => {
    try {
      const res = await fetch(`${API_URL}/vendors/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
      if (res.ok) { setEditingVendor(null); fetchVendors(); } else { const err = await res.json(); alert(err.error || 'Failed to update vendor'); }
    } catch (err) { console.error(err); }
  };

  const deleteVendor = async (id) => {
    if (!window.confirm('Are you sure you want to delete this vendor?')) return;
    try {
      const res = await fetch(`${API_URL}/vendors/${id}`, { method: 'DELETE' });
      if (res.ok) { fetchVendors(); fetchModels(); } else { const err = await res.json(); alert(err.error || 'Failed to delete vendor'); }
    } catch (err) { console.error(err); }
  };

  const addModel = async () => {
    if (!newModelName.trim() || !selectedVendorForModel) return;
    try {
      const res = await fetch(`${API_URL}/models`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newModelName.trim(), vendor_id: parseInt(selectedVendorForModel) }) });
      if (res.ok) { setNewModelName(''); setSelectedVendorForModel(''); fetchModels(); } else { const err = await res.json(); alert(err.error || 'Failed to add model'); }
    } catch (err) { console.error(err); alert('Failed to add model'); }
  };

  const updateModel = async (id, name, vendorId) => {
    try {
      const res = await fetch(`${API_URL}/models/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, vendor_id: vendorId }) });
      if (res.ok) { setEditingModel(null); fetchModels(); } else { const err = await res.json(); alert(err.error || 'Failed to update model'); }
    } catch (err) { console.error(err); }
  };

  const deleteModel = async (id) => {
    if (!window.confirm('Are you sure you want to delete this model?')) return;
    try {
      const res = await fetch(`${API_URL}/models/${id}`, { method: 'DELETE' });
      if (res.ok) { fetchModels(); } else { const err = await res.json(); alert(err.error || 'Failed to delete model'); }
    } catch (err) { console.error(err); }
  };

  const addLocation = async () => {
    if (!newLocationName.trim()) return;
    try {
      const res = await fetch(`${API_URL}/locations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newLocationName.trim() }) });
      if (res.ok) { setNewLocationName(''); fetchLocations(); } else { const err = await res.json(); alert(err.error || 'Failed to add location'); }
    } catch (err) { console.error(err); alert('Failed to add location'); }
  };

  const updateLocation = async (id, name) => {
    try {
      const res = await fetch(`${API_URL}/locations/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
      if (res.ok) { setEditingLocation(null); fetchLocations(); } else { const err = await res.json(); alert(err.error || 'Failed to update location'); }
    } catch (err) { console.error(err); }
  };

  const deleteLocation = async (id) => {
    if (!window.confirm('Are you sure you want to delete this location?')) return;
    try {
      const res = await fetch(`${API_URL}/locations/${id}`, { method: 'DELETE' });
      if (res.ok) { fetchLocations(); } else { const err = await res.json(); alert(err.error || 'Failed to delete location'); }
    } catch (err) { console.error(err); }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">Administration</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X size={24} />
            </button>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => setActiveTab('vendors')} className={`px-4 py-2 rounded-lg font-medium ${activeTab === 'vendors' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
              Vendors
            </button>
            <button onClick={() => setActiveTab('models')} className={`px-4 py-2 rounded-lg font-medium ${activeTab === 'models' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
              Models
            </button>
            <button onClick={() => setActiveTab('locations')} className={`px-4 py-2 rounded-lg font-medium ${activeTab === 'locations' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
              Locations
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-600">Loading...</p>
            </div>
          ) : activeTab === 'vendors' ? (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Add New Vendor</h3>
                <div className="flex gap-2">
                  <input type="text" value={newVendorName} onChange={(e) => setNewVendorName(e.target.value)} placeholder="Vendor name" className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" onKeyPress={(e) => e.key === 'Enter' && addVendor()} />
                  <button onClick={addVendor} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                    Add
                  </button>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">Existing Vendors ({vendors.length})</h3>
                <div className="space-y-2">
                  {vendors.map(vendor => (
                    <div key={vendor.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      {editingVendor === vendor.id ? (
                        <input type="text" defaultValue={vendor.name} onBlur={(e) => updateVendor(vendor.id, e.target.value)} onKeyPress={(e) => { if (e.key === 'Enter') { updateVendor(vendor.id, e.target.value); } }} className="flex-1 px-3 py-1 border border-gray-300 rounded" autoFocus />
                      ) : (
                        <div className="flex-1">
                          <span className="font-medium">{vendor.name}</span>
                          <span className="text-sm text-gray-500 ml-2">({vendor.model_count} models, {vendor.device_count} devices)</span>
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button onClick={() => setEditingVendor(vendor.id)} className="p-1 text-blue-600 hover:bg-blue-100 rounded">
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => deleteVendor(vendor.id)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {vendors.length === 0 && (
                    <p className="text-gray-500 text-center py-4">No vendors yet. Add your first vendor above.</p>
                  )}
                </div>
              </div>
            </div>
          ) : activeTab === 'models' ? (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Add New Model</h3>
                {vendors.length === 0 ? (
                  <p className="text-amber-600 bg-amber-50 p-3 rounded-lg">
                    Please add at least one vendor first before adding models.
                  </p>
                ) : (
                  <div className="flex gap-2">
                    <select value={selectedVendorForModel} onChange={(e) => setSelectedVendorForModel(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                      <option value="">Select Vendor...</option>
                      {vendors.map(vendor => (
                        <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                      ))}
                    </select>
                    <input type="text" value={newModelName} onChange={(e) => setNewModelName(e.target.value)} placeholder="Model name" className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" onKeyPress={(e) => e.key === 'Enter' && addModel()} />
                    <button onClick={addModel} disabled={!selectedVendorForModel} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400">
                      Add
                    </button>
                  </div>
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">Existing Models ({models.length})</h3>
                <div className="space-y-2">
                  {models.map(model => (
                    <div key={model.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      {editingModel === model.id ? (
                        <div className="flex-1 flex gap-2">
                          <select defaultValue={model.vendor_id} onBlur={(e) => updateModel(model.id, model.name, e.target.value)} className="px-3 py-1 border border-gray-300 rounded">
                            {vendors.map(vendor => (
                              <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                            ))}
                          </select>
                          <input type="text" defaultValue={model.name} onBlur={(e) => updateModel(model.id, e.target.value, model.vendor_id)} onKeyPress={(e) => { if (e.key === 'Enter') { updateModel(model.id, e.target.value, model.vendor_id); } }} className="flex-1 px-3 py-1 border border-gray-300 rounded" autoFocus />
                        </div>
                      ) : (
                        <div className="flex-1">
                          <span className="font-medium">{model.vendor_name}</span>
                          <span className="text-gray-400 mx-2">→</span>
                          <span className="font-medium">{model.name}</span>
                          <span className="text-sm text-gray-500 ml-2">({model.device_count} devices)</span>
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button onClick={() => setEditingModel(model.id)} className="p-1 text-blue-600 hover:bg-blue-100 rounded">
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => deleteModel(model.id)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {models.length === 0 && (
                    <p className="text-gray-500 text-center py-4">No models yet. Add your first model above.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Add New Location</h3>
                <div className="flex gap-2">
                  <input type="text" value={newLocationName} onChange={(e) => setNewLocationName(e.target.value)} placeholder="Location name (e.g., Data Center, Office, Rack 1)" className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" onKeyPress={(e) => e.key === 'Enter' && addLocation()} />
                  <button onClick={addLocation} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                    Add
                  </button>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">Existing Locations ({locations.length})</h3>
                <div className="space-y-2">
                  {locations.map(location => (
                    <div key={location.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      {editingLocation === location.id ? (
                        <input type="text" defaultValue={location.name} onBlur={(e) => updateLocation(location.id, e.target.value)} onKeyPress={(e) => { if (e.key === 'Enter') { updateLocation(location.id, e.target.value); } }} className="flex-1 px-3 py-1 border border-gray-300 rounded" autoFocus />
                      ) : (
                        <div className="flex-1">
                          <span className="font-medium">{location.name}</span>
                          <span className="text-sm text-gray-500 ml-2">({location.device_count} devices)</span>
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button onClick={() => setEditingLocation(location.id)} className="p-1 text-blue-600 hover:bg-blue-100 rounded">
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => deleteLocation(location.id)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {locations.length === 0 && (
                    <p className="text-gray-500 text-center py-4">No locations yet. Add your first location above.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
