import React from 'react';
import { X, Check, Copy, Edit2, Trash2 } from 'lucide-react';
import { DEVICE_TYPES } from '../../../constants/deviceTypes';

function DeviceCard({ device, viewMode, onToggleMonitoring, onEdit, onClone, onDelete }) {
  const deviceTypeLabel = DEVICE_TYPES.find(t => t.value === device.device_type)?.label || device.device_type;

  if (viewMode === 'condensed') {
    return (
      <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4 flex-1">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-gray-900 truncate">{device.name}</h3>
                <span 
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    device.monitoring_enabled 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {device.monitoring_enabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                <span>{deviceTypeLabel}</span>
                {device.ip_address && <span>{device.ip_address}</span>}
                {device.location_name && <span>📍 {device.location_name}</span>}
                {device.monitors && device.monitors.length > 0 && (
                  <span className="text-blue-600">
                    {device.monitors.length} monitor{device.monitors.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2 ml-4">
            <button 
              onClick={() => onToggleMonitoring(device)} 
              className={`p-2 rounded-lg transition-colors ${
                device.monitoring_enabled 
                  ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                  : 'bg-green-100 text-green-600 hover:bg-green-200'
              }`}
              aria-label={device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}
            >
              {device.monitoring_enabled ? <X size={18} /> : <Check size={18} />}
            </button>
            <button 
              onClick={() => onClone(device)} 
              className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200 transition-colors" 
              title="Clone Device"
              aria-label="Clone device"
            >
              <Copy size={18} />
            </button>
            <button 
              onClick={() => onEdit(device)} 
              className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-colors"
              aria-label="Edit device"
            >
              <Edit2 size={18} />
            </button>
            <button 
              onClick={() => onDelete(device.id)} 
              className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
              aria-label="Delete device"
            >
              <Trash2 size={18} />
            </button>
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
            <span 
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                device.monitoring_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {device.monitoring_enabled ? 'Monitoring Active' : 'Monitoring Disabled'}
            </span>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Type</p>
              <p className="font-medium text-gray-900">{deviceTypeLabel}</p>
            </div>
            {device.ip_address && (
              <div>
                <p className="text-gray-600">Address</p>
                <p className="font-medium text-gray-900">{device.ip_address}</p>
              </div>
            )}
            {device.function && (
              <div>
                <p className="text-gray-600">Function</p>
                <p className="font-medium text-gray-900">{device.function}</p>
              </div>
            )}
            {device.networks && (
              <div>
                <p className="text-gray-600">Networks</p>
                <p className="font-medium text-gray-900">{device.networks}</p>
              </div>
            )}
            {device.vendor_name && (
              <div>
                <p className="text-gray-600">Vendor</p>
                <p className="font-medium text-gray-900">{device.vendor_name}</p>
              </div>
            )}
            {device.model_name && (
              <div>
                <p className="text-gray-600">Model</p>
                <p className="font-medium text-gray-900">{device.model_name}</p>
              </div>
            )}
            {device.location_name && (
              <div>
                <p className="text-gray-600">Location</p>
                <p className="font-medium text-gray-900">{device.location_name}</p>
              </div>
            )}
            {device.interface_type && (
              <div>
                <p className="text-gray-600">Interface</p>
                <p className="font-medium text-gray-900">{device.interface_type}</p>
              </div>
            )}
            {device.poe_powered && (
              <div>
                <p className="text-gray-600">PoE Powered</p>
                <p className="font-medium text-green-600">Yes</p>
              </div>
            )}
            {device.poe_standards && (
              <div>
                <p className="text-gray-600">PoE Standards</p>
                <p className="font-medium text-purple-600">{device.poe_standards}</p>
              </div>
            )}
          </div>
          
          {device.monitors && device.monitors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Monitors:</p>
              <div className="flex flex-wrap gap-2">
                {device.monitors.map(monitor => (
                  <span 
                    key={monitor.id} 
                    className={`px-3 py-1 rounded-full text-xs ${
                      monitor.enabled 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {monitor.monitor_type}{monitor.port && `:${monitor.port}`}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="flex gap-2 ml-4">
          <button 
            onClick={() => onToggleMonitoring(device)} 
            className={`p-2 rounded-lg transition-colors ${
              device.monitoring_enabled 
                ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                : 'bg-green-100 text-green-600 hover:bg-green-200'
            }`}
            aria-label={device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}
          >
            {device.monitoring_enabled ? <X size={20} /> : <Check size={20} />}
          </button>
          <button 
            onClick={() => onClone(device)} 
            className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200 transition-colors" 
            title="Clone Device"
            aria-label="Clone device"
          >
            <Copy size={20} />
          </button>
          <button 
            onClick={() => onEdit(device)} 
            className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-colors"
            aria-label="Edit device"
          >
            <Edit2 size={20} />
          </button>
          <button 
            onClick={() => onDelete(device.id)} 
            className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
            aria-label="Delete device"
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeviceCard;
