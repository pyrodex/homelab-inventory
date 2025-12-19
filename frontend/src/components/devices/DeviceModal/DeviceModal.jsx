import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { deviceApi, monitorApi, vendorApi, modelApi, locationApi } from '../../../services/api';
import { 
  DEVICE_TYPES, 
  MONITOR_TYPES, 
  NETWORKS, 
  INTERFACE_TYPES, 
  POE_STANDARDS 
} from '../../../constants/deviceTypes';

const FIELD_LABELS = {
  name: 'Device Name',
  device_type: 'Device Type',
  ip_address: 'Address',
  deviceFunction: 'Device Function',
  vendor_id: 'Vendor',
  model_id: 'Model',
  location_id: 'Location',
  serial_number: 'Serial Number',
  networks: 'Networks',
  interface_type: 'Interface Type',
  poe_powered: 'PoE Powered',
  poe_standards: 'PoE Standards',
  monitoring_enabled: 'Monitoring Enabled',
};

const Section = ({ title, description, isOpen, onToggle, children }) => (
  <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 shadow-sm transition-colors">
    <button
      type="button"
      onClick={onToggle}
      className="w-full flex items-center justify-between px-4 md:px-6 py-3 md:py-4 text-left"
      aria-expanded={isOpen}
    >
      <div>
        <p className="text-base md:text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</p>
        {description && <p className="text-sm text-gray-500 dark:text-gray-300 mt-0.5">{description}</p>}
      </div>
      {isOpen ? <ChevronUp size={20} className="text-gray-500 dark:text-gray-300" /> : <ChevronDown size={20} className="text-gray-500 dark:text-gray-300" />}
    </button>
    <div className={`${isOpen ? 'block' : 'hidden'} md:block border-t border-gray-200 dark:border-gray-700`}>
      <div className="p-4 md:p-6">
        {children}
      </div>
    </div>
  </div>
);

function DeviceModal({ device, onClose, onSave, onError, fromDiscovery = false }) {
  const normalizeDevice = (deviceData) => ({
    name: deviceData?.name || '', 
    device_type: deviceData?.device_type || 'linux_server_physical', 
    ip_address: deviceData?.ip_address || '', 
    deviceFunction: deviceData?.deviceFunction ?? deviceData?.function ?? '',
    vendor_id: deviceData?.vendor_id ?? '', 
    model_id: deviceData?.model_id ?? '', 
    location_id: deviceData?.location_id ?? '', 
    serial_number: deviceData?.serial_number || '', 
    networks: deviceData?.networks || 'LAN',
    interface_type: deviceData?.interface_type || '', 
    poe_powered: deviceData?.poe_powered ?? false, 
    poe_standards: deviceData?.poe_standards || '', 
    monitoring_enabled: deviceData?.monitoring_enabled ?? true
  });

  const [formData, setFormData] = useState(() => normalizeDevice(device));

  const [monitors, setMonitors] = useState(
    device?.monitors 
      ? device.id 
        ? device.monitors
        : device.monitors.map(m => ({ ...m, id: null }))
      : []
  );
  
  const [newMonitor, setNewMonitor] = useState({ 
    monitor_type: 'node_exporter', 
    port: 9100, 
    enabled: true 
  });
  const [historyEntries, setHistoryEntries] = useState([]);
  const [historyMeta, setHistoryMeta] = useState({ total: 0, limit: 50, offset: 0 });
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  
  const [vendors, setVendors] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedNetworks, setSelectedNetworks] = useState(
    device?.networks ? device.networks.split(',') : ['LAN']
  );
  const [selectedInterfaces, setSelectedInterfaces] = useState(
    device?.interface_type ? device.interface_type.split(',') : []
  );
  const [selectedPoeStandards, setSelectedPoeStandards] = useState(
    device?.poe_standards ? device.poe_standards.split(',') : []
  );
  const [sectionOpen, setSectionOpen] = useState({
    basics: true,
    networking: true,
    monitors: true,
    history: !!device?.id,
  });

  useEffect(() => { 
    loadInitialData(); 
  }, []);
  
  useEffect(() => { 
    if (formData.vendor_id) {
      loadModels(formData.vendor_id);
    } else {
      setModels([]);
    }
  }, [formData.vendor_id]);

  useEffect(() => {
    if (device?.id) {
      loadHistory();
    } else {
      setHistoryEntries([]);
      setHistoryMeta({ total: 0, limit: 50, offset: 0 });
    }
  }, [device?.id]);

  const loadInitialData = async () => {
    try {
      await Promise.all([
        loadVendors(),
        loadLocations()
      ]);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  const toggleSection = (key) => {
    setSectionOpen(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const loadVendors = async () => {
    try {
      const data = await vendorApi.getAll();
      setVendors(data);
    } catch (err) {
      console.error('Failed to load vendors:', err);
    }
  };

  const loadModels = async (vendorId) => {
    try {
      const data = await modelApi.getAll(vendorId);
      setModels(data);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadLocations = async () => {
    try {
      const data = await locationApi.getAll();
      setLocations(data);
    } catch (err) {
      console.error('Failed to load locations:', err);
    }
  };

  const loadHistory = async (offset = 0) => {
    if (!device?.id) return;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const payload = await deviceApi.getHistory(device.id, { limit: historyMeta.limit, offset });
      setHistoryEntries(payload.items || []);
      setHistoryMeta({
        total: payload.total ?? payload.items?.length ?? 0,
        limit: payload.limit ?? historyMeta.limit,
        offset: payload.offset ?? offset,
      });
    } catch (err) {
      console.error('Failed to load history:', err);
      setHistoryError(err.message || 'Failed to load history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleNetworkToggle = (network) => {
    if (network === 'ALL') {
      setSelectedNetworks(['ALL']);
    } else {
      let newSelection = selectedNetworks.filter(n => n !== 'ALL');
      
      if (newSelection.includes(network)) {
        newSelection = newSelection.filter(n => n !== network);
      } else {
        newSelection.push(network);
      }
      
      if (newSelection.length === 0) {
        newSelection = ['LAN'];
      }
      
      setSelectedNetworks(newSelection);
    }
  };

  const handleInterfaceToggle = (interfaceType) => {
    let newSelection = [...selectedInterfaces];
    
    if (newSelection.includes(interfaceType)) {
      newSelection = newSelection.filter(i => i !== interfaceType);
    } else {
      newSelection.push(interfaceType);
    }
    
    setSelectedInterfaces(newSelection);
  };

  const handlePoeStandardToggle = (poeStandard) => {
    let newSelection = [...selectedPoeStandards];
    
    if (newSelection.includes(poeStandard)) {
      newSelection = newSelection.filter(p => p !== poeStandard);
    } else {
      newSelection.push(poeStandard);
    }
    
    setSelectedPoeStandards(newSelection);
  };

  const isValidIPv4 = (value) => {
    // Strict IPv4 (no ports)
    const ipv4Segment = '(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)';
    const ipv4Regex = new RegExp(`^(${ipv4Segment}\\.){3}${ipv4Segment}$`);
    return ipv4Regex.test(value.trim());
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (value === '') return 'Empty';
    return value;
  };

  const getFieldLabel = (field) => FIELD_LABELS[field] || field.replace(/_/g, ' ');

  const getDisplayChange = (entry, field, change) => {
    const displayChange = entry.display_diff?.[field];
    return {
      old: displayChange?.old_label ?? displayChange?.old ?? change?.old,
      new: displayChange?.new_label ?? displayChange?.new ?? change?.new,
    };
  };

  const validateForm = () => {
    const missingFields = [];
    
    if (!formData.name?.trim()) missingFields.push('Device Name');
    if (!formData.ip_address?.trim()) missingFields.push('Address');
    if (!formData.device_type) missingFields.push('Device Type');
    if (!formData.deviceFunction?.trim()) missingFields.push('Device Function');
    
    // When coming from discovery, allow users to add quickly without vendor/model/location/serial.
    if (!fromDiscovery) {
      if (!formData.vendor_id) missingFields.push('Vendor');
      if (!formData.model_id) missingFields.push('Model');
      if (!formData.location_id) missingFields.push('Location');
      if (!formData.serial_number?.trim()) missingFields.push('Serial Number');
    }
    
    if (missingFields.length > 0) {
      onError(`The following required fields are missing:\n\n${missingFields.join('\n')}`);
      return false;
    }

    if (formData.ip_address) {
      const value = formData.ip_address.trim();
      if (value.includes(':')) {
        onError('Ports are configured per monitor. Omit the port from the address.');
        return false;
      }
      const looksIPv4 = /^[0-9.]+$/.test(value);
      if (looksIPv4 && !isValidIPv4(value)) {
        onError('Address must be a valid IPv4 or a domain (no ports).');
        return false;
      }
    }
    
    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    
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
      const savedDevice = isEdit 
        ? await deviceApi.update(device.id, saveData)
        : await deviceApi.create(saveData);
      
      // Handle monitor updates for existing devices
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
        
        // Delete removed monitors
        for (const monitorId of monitorsToDelete) {
          await monitorApi.delete(monitorId);
        }
      }
      
      // Add new monitors
      for (const monitor of monitors) { 
        if (!monitor.id) { 
          await monitorApi.create(savedDevice.id, monitor);
        } 
      }
      
      onSave();
    } catch (err) { 
      console.error('Failed to save device:', err);
      onError(err.message || 'Failed to save device');
    }
  };

  // NEW CODE - Allows duplicates
  const addMonitor = () => {
  // Allow multiple monitors of the same type
    setMonitors([...monitors, { ...newMonitor, id: null }]);
    setNewMonitor({ monitor_type: 'node_exporter', port: 9100, enabled: true });
  };
  const removeMonitor = (index) => {
    setMonitors(monitors.filter((_, i) => i !== index));
  };

  const modalTitle = device && device.id ? 'Edit Device' : device ? 'Clone Device' : 'Add New Device';
  const saveButtonText = device && device.id ? 'Update Device' : device ? 'Clone Device' : 'Create Device';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-0 md:p-4 z-50">
      <div className="bg-white dark:bg-gray-900 rounded-none md:rounded-lg max-w-4xl w-full h-full md:h-auto max-h-[100vh] md:max-h-[90vh] overflow-y-auto modal-content transition-colors">
        <div className="sticky top-0 bg-white dark:bg-gray-900 z-10 p-4 md:p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">{modalTitle}</h2>
          <button
            onClick={onClose}
            className="p-2 -mr-2 text-gray-400 hover:text-gray-600 active:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100 dark:active:text-white transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Close modal"
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="p-4 md:p-6 space-y-4 md:space-y-6">
          <Section
            title="Basics"
            description="Required fields to identify the device."
            isOpen={sectionOpen.basics}
            onToggle={() => toggleSection('basics')}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Device Name *
                </label>
                <input 
                  type="text" 
                  value={formData.name} 
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base" 
                  required 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Device Type *
                </label>
                <select 
                  value={formData.device_type} 
                  onChange={(e) => setFormData({ ...formData, device_type: e.target.value })} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation" 
                  required
                >
                  {DEVICE_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="inline-flex items-center gap-2">
                    <span>Address *</span>
                    <span className="relative inline-flex items-center group cursor-pointer text-gray-400 hover:text-gray-600" aria-label="Address help">
                      <Info size={16} />
                      <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-2 w-56 -translate-x-1/2 rounded-md bg-gray-900 px-3 py-2 text-xs text-white opacity-0 transition duration-150 group-hover:opacity-100 group-hover:translate-y-0 translate-y-1 shadow-lg">
                        IPv4 is validated. Domains are allowed. Ports belong in monitor settings.
                      </span>
                    </span>
                  </span>
                </label>
                <input 
                  type="text" 
                  value={formData.ip_address} 
                  onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })} 
                  placeholder="192.168.1.10 or example.com" 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base" 
                  required 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Device Function *
                </label>
                <input 
                  type="text" 
                  value={formData.deviceFunction} 
                  onChange={(e) => setFormData({ ...formData, deviceFunction: e.target.value })} 
                  placeholder="Provide device function..." 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base" 
                  required 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Vendor *
                </label>
                <select 
                  value={formData.vendor_id} 
                  onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value, model_id: '' })} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation" 
                  required
                >
                  <option value="">Select Vendor...</option>
                  {vendors.map(vendor => (
                    <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model *
                </label>
                <select 
                  value={formData.model_id} 
                  onChange={(e) => setFormData({ ...formData, model_id: e.target.value })} 
                  disabled={!formData.vendor_id} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-base touch-manipulation" 
                  required
                >
                  <option value="">Select Model...</option>
                  {models.map(model => (
                    <option key={model.id} value={model.id}>{model.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location *
                </label>
                <select 
                  value={formData.location_id} 
                  onChange={(e) => setFormData({ ...formData, location_id: e.target.value })} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation" 
                  required
                >
                  <option value="">Select Location...</option>
                  {locations.map(location => (
                    <option key={location.id} value={location.id}>{location.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Serial Number *
                </label>
                <input 
                  type="text" 
                  value={formData.serial_number} 
                  onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })} 
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base" 
                  required 
                />
              </div>
            </div>
          </Section>

          <Section
            title="Networking & Power"
            description="Interfaces, networks, PoE, and monitoring defaults."
            isOpen={sectionOpen.networking}
            onToggle={() => toggleSection('networking')}
          >
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  Networks
                </label>
                <div className="flex flex-wrap gap-2">
                  {NETWORKS.map(network => (
                    <button 
                      key={network} 
                      type="button" 
                      onClick={() => handleNetworkToggle(network)} 
                      className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
                        selectedNetworks.includes(network) 
                          ? 'bg-blue-600 text-white active:bg-blue-700 border border-blue-700 dark:border-blue-500' 
                          : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-200 active:bg-gray-300 dark:active:bg-gray-700 border border-gray-300 dark:border-gray-700'
                      }`}
                    >
                      {network}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-300 mt-1">Select ALL to override other selections</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  Interface Types
                </label>
                <div className="flex flex-wrap gap-2">
                  {INTERFACE_TYPES.map(iface => (
                    <button 
                      key={iface} 
                      type="button" 
                      onClick={() => handleInterfaceToggle(iface)} 
                      className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
                        selectedInterfaces.includes(iface) 
                          ? 'bg-purple-600 text-white active:bg-purple-700 border border-purple-700 dark:border-purple-500' 
                          : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-200 active:bg-gray-300 dark:active:bg-gray-700 border border-gray-300 dark:border-gray-700'
                      }`}
                    >
                      {iface}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-300 mt-1">Select multiple interface types if applicable</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  PoE Standards
                </label>
                <div className="flex flex-wrap gap-2">
                  {POE_STANDARDS.map(poe => (
                    <button 
                      key={poe} 
                      type="button" 
                      onClick={() => handlePoeStandardToggle(poe)} 
                      className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
                        selectedPoeStandards.includes(poe) 
                          ? 'bg-amber-600 text-white active:bg-amber-700 border border-amber-700 dark:border-amber-500' 
                          : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-200 active:bg-gray-300 dark:active:bg-gray-700 border border-gray-300 dark:border-gray-700'
                      }`}
                    >
                      {poe}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-300 mt-1">Select applicable PoE standards for this device</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="flex items-center gap-2 p-3 active:bg-gray-50 dark:active:bg-gray-800 rounded cursor-pointer touch-manipulation min-h-[44px] border border-gray-200 dark:border-gray-700">
                  <input 
                    type="checkbox" 
                    checked={formData.poe_powered} 
                    onChange={(e) => setFormData({ ...formData, poe_powered: e.target.checked })} 
                    className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 touch-manipulation" 
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-200">PoE Powered</span>
                </label>
                <label className="flex items-center gap-2 p-3 active:bg-gray-50 dark:active:bg-gray-800 rounded cursor-pointer touch-manipulation min-h-[44px] border border-gray-200 dark:border-gray-700">
                  <input 
                    type="checkbox" 
                    checked={formData.monitoring_enabled} 
                    onChange={(e) => setFormData({ ...formData, monitoring_enabled: e.target.checked })} 
                    className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 touch-manipulation" 
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Monitoring Enabled</span>
                </label>
              </div>
            </div>
          </Section>

          <Section
            title="Monitors"
            description="Add or remove monitors and ports."
            isOpen={sectionOpen.monitors}
            onToggle={() => toggleSection('monitors')}
          >
            <div className="space-y-4">
              {monitors.length > 0 && (
                <div className="space-y-2">
                  {monitors.map((monitor, index) => (
                  <div key={index} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <span className="flex-1 text-sm text-gray-900 dark:text-gray-100">
                        {MONITOR_TYPES.find(m => m.value === monitor.monitor_type)?.label || monitor.monitor_type}
                        {monitor.port && ` (Port: ${monitor.port})`}
                      </span>
                      <button 
                        type="button" 
                        onClick={() => removeMonitor(index)} 
                      className="p-1 text-red-600 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                        aria-label="Remove monitor"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="flex flex-col md:flex-row gap-2">
                <select 
                  value={newMonitor.monitor_type} 
                  onChange={(e) => { 
                    const type = MONITOR_TYPES.find(m => m.value === e.target.value); 
                    setNewMonitor({ 
                      ...newMonitor, 
                      monitor_type: e.target.value, 
                      port: type?.defaultPort || null 
                    }); 
                  }} 
                  className="flex-1 px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                >
                  {MONITOR_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
                <input 
                  type="number" 
                  value={newMonitor.port || ''} 
                  onChange={(e) => setNewMonitor({ ...newMonitor, port: e.target.value ? parseInt(e.target.value) : null })} 
                  placeholder="Port" 
                  className="w-full md:w-24 px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100" 
                />
                <button 
                  type="button" 
                  onClick={addMonitor} 
                  className="px-4 py-2.5 bg-blue-600 text-white rounded-lg active:bg-blue-700 transition-colors touch-manipulation min-h-[44px]"
                >
                  Add
                </button>
              </div>
            </div>
          </Section>

          {device?.id && (
            <Section
              title="History"
              description="Track changes made to this device."
              isOpen={sectionOpen.history}
              onToggle={() => toggleSection('history')}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    Showing {historyEntries.length} of {historyMeta.total} change{historyMeta.total === 1 ? '' : 's'}
                  </p>
                  <button
                    type="button"
                    onClick={() => loadHistory(historyMeta.offset)}
                    className="px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg active:bg-gray-300 dark:active:bg-gray-600 transition-colors touch-manipulation min-h-[38px]"
                  >
                    Refresh
                  </button>
                </div>

                {historyError && (
                  <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg p-3">
                    {historyError}
                  </div>
                )}

                {historyLoading ? (
                  <div className="space-y-2">
                    {[1,2,3].map(key => (
                      <div key={key} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : historyEntries.length === 0 ? (
                  <p className="text-sm text-gray-600 dark:text-gray-300">No history yet.</p>
                ) : (
                  <div className="space-y-3">
                    {historyEntries.map(entry => (
                      <div key={entry.id} className="border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{entry.summary || 'Change recorded'}</p>
                            <p className="text-xs text-gray-500">{new Date(entry.created_at).toLocaleString()}</p>
                          </div>
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 capitalize">
                            {entry.change_type.replace('_', ' ')}
                          </span>
                        </div>
                        {((entry.diff && Object.keys(entry.diff).length > 0) || (entry.display_diff && Object.keys(entry.display_diff).length > 0)) ? (
                          <div className="mt-3 space-y-2">
                            {Object.entries(entry.diff || entry.display_diff || {}).map(([field, change]) => {
                              const displayChange = getDisplayChange(entry, field, change);
                              return (
                                <div key={field} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                                  <span className="text-sm text-gray-700 dark:text-gray-300">{getFieldLabel(field)}</span>
                                  <div className="text-sm text-gray-900 dark:text-gray-100 sm:text-right">
                                    <span className="text-xs text-gray-500 dark:text-gray-400 pr-1">from</span>
                                    {formatValue(displayChange.old)}
                                    <span className="text-xs text-gray-500 dark:text-gray-400 px-1">to</span>
                                    {formatValue(displayChange.new)}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">No field changes recorded.</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Section>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col-reverse md:flex-row md:justify-end gap-3 pt-4 md:pt-6 border-t border-gray-200 dark:border-gray-700 sticky bottom-0 bg-white dark:bg-gray-900 pb-4 md:pb-0 -mx-4 md:mx-0 px-4 md:px-0">
            <button 
              type="button" 
              onClick={onClose} 
              className="w-full md:w-auto px-4 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg active:bg-gray-50 dark:active:bg-gray-800 transition-colors touch-manipulation min-h-[44px]"
            >
              Cancel
            </button>
            <button 
              type="button" 
              onClick={handleSave} 
              className="w-full md:w-auto px-4 py-2.5 bg-green-600 text-white rounded-lg active:bg-green-700 transition-colors touch-manipulation min-h-[44px]"
            >
              {saveButtonText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DeviceModal;
