import React from 'react';
import { Server } from 'lucide-react';
import DeviceCard from '../DeviceCard/DeviceCard';
import { DEVICE_TYPES } from '../../../constants/deviceTypes';

function DeviceList({ 
  devices, 
  searchTerm, 
  viewMode, 
  onToggleMonitoring, 
  onEdit, 
  onClone, 
  onDelete, 
  onClearSearch 
}) {
  const filteredDevices = devices.filter(device => {
    if (!searchTerm) return true;
    
    const search = searchTerm.toLowerCase();
    const deviceTypeLabel = DEVICE_TYPES.find(t => t.value === device.device_type)?.label || '';
    const deviceFunction = device.deviceFunction || '';
    
    return (
      device.name?.toLowerCase().includes(search) ||
      device.ip_address?.toLowerCase().includes(search) ||
      deviceFunction.toLowerCase().includes(search) ||
      device.vendor_name?.toLowerCase().includes(search) ||
      device.model_name?.toLowerCase().includes(search) ||
      device.location_name?.toLowerCase().includes(search) ||
      device.serial_number?.toLowerCase().includes(search) ||
      device.networks?.toLowerCase().includes(search) ||
      device.interface_type?.toLowerCase().includes(search) ||
      device.poe_standards?.toLowerCase().includes(search) ||
      deviceTypeLabel.toLowerCase().includes(search) ||
      device.monitors?.some(m => m.monitor_type.toLowerCase().includes(search))
    );
  });

  if (filteredDevices.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 p-12 rounded-lg shadow text-center transition-colors">
        <Server className="mx-auto text-gray-400 dark:text-gray-300 mb-4" size={48} />
        <p className="text-gray-600 dark:text-gray-200">No devices match your search criteria.</p>
        <button 
          onClick={onClearSearch} 
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
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
          onDelete={() => onDelete(device)} 
        />
      ))}
    </div>
  );
}

export default DeviceList;
