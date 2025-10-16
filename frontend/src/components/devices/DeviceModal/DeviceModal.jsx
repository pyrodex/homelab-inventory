import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { deviceApi, monitorApi, vendorApi, modelApi, locationApi } from '../../../services/api';
import { 
  DEVICE_TYPES, 
  MONITOR_TYPES, 
  NETWORKS, 
  INTERFACE_TYPES, 
  POE_STANDARDS 
} from '../../../constants/deviceTypes';

function DeviceModal({ device, onClose, onSave, onError }) {
  const [formData, setFormData] = useState(device || {
    name: '', 
    device_type: 'linux_server_physical', 
    ip_address: '', 
    function: '',
    vendor_id: '', 
    model_id: '', 
    location_id: '', 
    serial_number: '', 
    networks: 'LAN',
    interface_type: '', 
    poe_powered: false, 
    poe_standards: '', 
    monitoring_enabled: true
  });

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

  const validateForm = () => {
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
      onError(`The following required fields are missing:\n\n${missingFields.join('\n')}`);
      return false;
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

  const addMonitor = () => {
    const existingMonitor = monitors.find(m => m.monitor_type === newMonitor.monitor_type);
    
    if (existingMonitor) {
      const monitorLabel = MONITOR_TYPES.find(t => t.value === newMonitor.monitor_type)?.label || newMonitor.monitor_type;
      onError(`A ${monitorLabel} monitor is already added to this device.`);
      return;
    }
    
    setMonitors([...monitors, { ...newMonitor, id: null }]);
    setNewMonitor({ monitor_type: 'node_exporter', port: 9100, enabled: true });
  };

  const removeMonitor = (index) => {
    setMonitors(monitors.filter((_, i) => i !== index));
  };

  const modalTitle = device && device.id ? 'Edit Device' : device ? 'Clone Device' : 'Add New Device';
  const saveButtonText = device && device.id ? 'Update Device' : device ? 'Clone Device' : 'Create Device';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">{modalTitle}</h2>
        </div>
        
        <div className="p-6">
          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device Name *
              </label>
              <input 
                type="text" 
                value={formData.name} 
                onChange={(e) => setFormData({ ...formData, name: e.target.value })} 
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                required
              >
                {DEVICE_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Address *
              </label>
              <input 
                type="text" 
                value={formData.ip_address} 
                onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })} 
                placeholder="192.168.1.10, example.com, or 192.168.1.10:9100" 
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                required 
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Function *
              </label>
              <input 
                type="text" 
                value={formData.function} 
                onChange={(e) => setFormData({ ...formData, function: e.target.value })} 
                placeholder="e.g., Web Server, Storage" 
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed" 
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                required 
              />
            </div>
            
            {/* Networks */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Networks
              </label>
              <div className="flex flex-wrap gap-2">
                {NETWORKS.map(network => (
                  <button 
                    key={network} 
                    type="button" 
                    onClick={() => handleNetworkToggle(network)} 
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedNetworks.includes(network) 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {network}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Select ALL to override other selections</p>
            </div>
            
            {/* Interface Types */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Interface Types
              </label>
              <div className="flex flex-wrap gap-2">
                {INTERFACE_TYPES.map(iface => (
                  <button 
                    key={iface} 
                    type="button" 
                    onClick={() => handleInterfaceToggle(iface)} 
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedInterfaces.includes(iface) 
                        ? 'bg-purple-600 text-white' 
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {iface}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Select multiple interface types if applicable</p>
            </div>
            
            {/* PoE Standards */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                PoE Standards
              </label>
              <div className="flex flex-wrap gap-2">
                {POE_STANDARDS.map(poe => (
                  <button 
                    key={poe} 
                    type="button" 
                    onClick={() => handlePoeStandardToggle(poe)} 
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedPoeStandards.includes(poe) 
                        ? 'bg-amber-600 text-white' 
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {poe}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Select applicable PoE standards for this device</p>
            </div>
            
            {/* Options */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Options
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={formData.poe_powered} 
                    onChange={(e) => setFormData({ ...formData, poe_powered: e.target.checked })} 
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500" 
                  />
                  <span className="text-sm font-medium text-gray-700">PoE Powered</span>
                </label>
                <label className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={formData.monitoring_enabled} 
                    onChange={(e) => setFormData({ ...formData, monitoring_enabled: e.target.checked })} 
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500" 
                  />
                  <span className="text-sm font-medium text-gray-700">Monitoring Enabled</span>
                </label>
              </div>
            </div>
          </div>
          
          {/* Monitors Section */}
          <div className="border-t pt-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Monitors</h3>
            
            {monitors.length > 0 && (
              <div className="space-y-2 mb-4">
                {monitors.map((monitor, index) => (
                  <div key={index} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                    <span className="flex-1 text-sm">
                      {MONITOR_TYPES.find(m => m.value === monitor.monitor_type)?.label || monitor.monitor_type}
                      {monitor.port && ` (Port: ${monitor.port})`}
                    </span>
                    <button 
                      type="button" 
                      onClick={() => removeMonitor(index)} 
                      className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                      aria-label="Remove monitor"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex gap-2">
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
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
              />
              <button 
                type="button" 
                onClick={addMonitor} 
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add
              </button>
            </div>
          </div>
          
          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-6 border-t">
            <button 
              type="button" 
              onClick={onClose} 
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button 
              type="button" 
              onClick={handleSave} 
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
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
