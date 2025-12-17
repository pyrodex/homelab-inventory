import React, { useState } from 'react';
import { X, Check, Copy, Edit2, Trash2, MoreVertical } from 'lucide-react';
import { DEVICE_TYPES } from '../../../constants/deviceTypes';

function DeviceCard({ device, viewMode, onToggleMonitoring, onEdit, onClone, onDelete }) {
  const deviceTypeLabel = DEVICE_TYPES.find(t => t.value === device.device_type)?.label || device.device_type;
  const deviceFunction = device.deviceFunction || '';
  const [actionsOpen, setActionsOpen] = useState(false);

  const handleAction = (callback) => {
    callback(device);
    setActionsOpen(false);
  };

  if (viewMode === 'condensed') {
    return (
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow active:shadow-lg transition-all">
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-3">
          <div className="flex items-start md:items-center gap-3 flex-1 min-w-0">
            <div className="flex-1 min-w-0">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 mb-2">
                <h3 className="text-base md:text-lg font-bold text-gray-900 dark:text-gray-100 truncate">{device.name}</h3>
                <span 
                  className={`px-2 py-1 rounded-full text-xs font-medium self-start ${
                    device.monitoring_enabled 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {device.monitoring_enabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm text-gray-600 dark:text-gray-300">
                <span>{deviceTypeLabel}</span>
                {device.ip_address && <span className="break-all">{device.ip_address}</span>}
                {device.location_name && <span>📍 {device.location_name}</span>}
                {device.monitors && device.monitors.length > 0 && (
                  <span className="text-blue-600">
                    {device.monitors.length} monitor{device.monitors.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2 md:ml-4 items-center">
            {/* Mobile menu */}
            <div className="relative md:hidden">
              <button
                onClick={() => setActionsOpen(!actionsOpen)}
                className="p-2.5 bg-gray-200 text-gray-700 rounded-lg active:bg-gray-300 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-haspopup="true"
                aria-expanded={actionsOpen}
              >
                <MoreVertical size={18} />
              </button>
              {actionsOpen && (
                <div className="absolute right-0 mt-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg w-44 z-10">
                  <button 
                    onClick={() => handleAction(onToggleMonitoring)} 
                    className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                  >
                    <span>{device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}</span>
                    {device.monitoring_enabled ? <X size={14} /> : <Check size={14} />}
                  </button>
                  <button 
                    onClick={() => handleAction(onClone)} 
                    className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                  >
                    <span>Clone</span>
                    <Copy size={14} />
                  </button>
                  <button 
                    onClick={() => handleAction(onEdit)} 
                    className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                  >
                    <span>Edit</span>
                    <Edit2 size={14} />
                  </button>
                  <button 
                    onClick={() => handleAction(onDelete)} 
                    className="w-full flex items-center justify-between px-3 py-2 text-sm text-red-600 active:bg-gray-50"
                  >
                    <span>Delete</span>
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </div>

            {/* Desktop actions */}
            <div className="hidden md:flex gap-2">
              <button 
                onClick={() => onToggleMonitoring(device)} 
                className={`p-2.5 rounded-lg transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center ${
                  device.monitoring_enabled 
                    ? 'bg-red-100 text-red-600 active:bg-red-200' 
                    : 'bg-green-100 text-green-600 active:bg-green-200'
                }`}
                aria-label={device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}
              >
                {device.monitoring_enabled ? <X size={18} /> : <Check size={18} />}
              </button>
              <button 
                onClick={() => onClone(device)} 
                className="p-2.5 bg-purple-100 text-purple-600 rounded-lg active:bg-purple-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center" 
                title="Clone Device"
                aria-label="Clone device"
              >
                <Copy size={18} />
              </button>
              <button 
                onClick={() => onEdit(device)} 
                className="p-2.5 bg-blue-100 text-blue-600 rounded-lg active:bg-blue-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Edit device"
              >
                <Edit2 size={18} />
              </button>
              <button 
                onClick={() => onDelete(device)} 
                className="p-2.5 bg-red-100 text-red-600 rounded-lg active:bg-red-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Delete device"
              >
                <Trash2 size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-4 md:p-6 rounded-lg shadow active:shadow-lg transition-all">
      <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-3">
            <h3 className="text-lg md:text-xl font-bold text-gray-900 dark:text-gray-100 break-words">{device.name}</h3>
            <span 
              className={`px-3 py-1 rounded-full text-xs font-medium self-start ${
                device.monitoring_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {device.monitoring_enabled ? 'Monitoring Active' : 'Monitoring Disabled'}
            </span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-300">Type</p>
              <p className="font-medium text-gray-900 dark:text-gray-100">{deviceTypeLabel}</p>
            </div>
            {device.ip_address && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Address</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.ip_address}</p>
              </div>
            )}
            {deviceFunction && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Device Function</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{deviceFunction}</p>
              </div>
            )}
            {device.networks && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Networks</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.networks}</p>
              </div>
            )}
            {device.vendor_name && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Vendor</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.vendor_name}</p>
              </div>
            )}
            {device.model_name && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Model</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.model_name}</p>
              </div>
            )}
            {device.location_name && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Location</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.location_name}</p>
              </div>
            )}
            {device.interface_type && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">Interface</p>
                <p className="font-medium text-gray-900 dark:text-gray-100">{device.interface_type}</p>
              </div>
            )}
            {device.poe_powered && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">PoE Powered</p>
                <p className="font-medium text-green-600">Yes</p>
              </div>
            )}
            {device.poe_standards && (
              <div>
                <p className="text-gray-600 dark:text-gray-300">PoE Standards</p>
                <p className="font-medium text-purple-600">{device.poe_standards}</p>
              </div>
            )}
          </div>
          
          {device.monitors && device.monitors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Monitors:</p>
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
        
        <div className="flex gap-2 md:ml-4 self-start md:self-auto items-center">
          <div className="relative md:hidden">
            <button
              onClick={() => setActionsOpen(!actionsOpen)}
              className="p-2.5 bg-gray-200 text-gray-700 rounded-lg active:bg-gray-300 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-haspopup="true"
              aria-expanded={actionsOpen}
            >
              <MoreVertical size={20} />
            </button>
            {actionsOpen && (
              <div className="absolute right-0 mt-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg w-48 z-10">
                <button 
                  onClick={() => handleAction(onToggleMonitoring)} 
                  className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                >
                  <span>{device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}</span>
                  {device.monitoring_enabled ? <X size={14} /> : <Check size={14} />}
                </button>
                <button 
                  onClick={() => handleAction(onClone)} 
                  className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                >
                  <span>Clone</span>
                  <Copy size={14} />
                </button>
                <button 
                  onClick={() => handleAction(onEdit)} 
                  className="w-full flex items-center justify-between px-3 py-2 text-sm active:bg-gray-50"
                >
                  <span>Edit</span>
                  <Edit2 size={14} />
                </button>
                <button 
                  onClick={() => handleAction(onDelete)} 
                  className="w-full flex items-center justify-between px-3 py-2 text-sm text-red-600 active:bg-gray-50"
                >
                  <span>Delete</span>
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>

          <div className="hidden md:flex gap-2">
            <button 
              onClick={() => onToggleMonitoring(device)} 
              className={`p-2.5 rounded-lg transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center ${
                device.monitoring_enabled 
                  ? 'bg-red-100 text-red-600 active:bg-red-200' 
                  : 'bg-green-100 text-green-600 active:bg-green-200'
              }`}
              aria-label={device.monitoring_enabled ? 'Disable monitoring' : 'Enable monitoring'}
            >
              {device.monitoring_enabled ? <X size={20} /> : <Check size={20} />}
            </button>
            <button 
              onClick={() => onClone(device)} 
              className="p-2.5 bg-purple-100 text-purple-600 rounded-lg active:bg-purple-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center" 
              title="Clone Device"
              aria-label="Clone device"
            >
              <Copy size={20} />
            </button>
            <button 
              onClick={() => onEdit(device)} 
              className="p-2.5 bg-blue-100 text-blue-600 rounded-lg active:bg-blue-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Edit device"
            >
              <Edit2 size={20} />
            </button>
            <button 
              onClick={() => onDelete(device)} 
              className="p-2.5 bg-red-100 text-red-600 rounded-lg active:bg-red-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Delete device"
            >
              <Trash2 size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DeviceCard;
