import React, { useState, useEffect } from 'react';
import { Plus, Server, Activity, Download, Settings, List, Grid, Check, X } from 'lucide-react';

// Components
import ErrorAlert from './components/common/ErrorAlert/ErrorAlert';
import DeviceList from './components/devices/DeviceList/DeviceList';
import DeviceModal from './components/devices/DeviceModal/DeviceModal';
import AdminModal from './components/admin/AdminModal/AdminModal';

// Services
import { deviceApi, statsApi, prometheusApi } from './services/api';

// Constants
import { DEVICE_TYPES } from './constants/deviceTypes';

// Utils
import { downloadBlob } from './utils/helpers';

function App() {
  // State management
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
  const [error, setError] = useState(null);

  // Load data on mount and when filter changes
  useEffect(() => {
    fetchDevices();
    fetchStats();
  }, [selectedType]);

  const fetchDevices = async () => {
    try {
      const data = await deviceApi.getAll(selectedType === 'all' ? null : selectedType);
      setDevices(data);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
      setError('Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await statsApi.get();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const handleExportPrometheus = async (mode = 'download') => {
    try {
      if (mode === 'write') {
        const data = await prometheusApi.export('write');
        alert(`Success! ${data.message}`);
      } else {
        const blob = await prometheusApi.export('download');
        downloadBlob(blob, 'prometheus_targets.zip');
      }
    } catch (err) {
      console.error('Failed to export:', err);
      setError('Failed to export configuration');
    }
  };

  const toggleMonitoring = async (device) => {
    try {
      await deviceApi.update(device.id, {
        ...device,
        monitoring_enabled: !device.monitoring_enabled
      });
      fetchDevices();
      fetchStats();
    } catch (err) {
      console.error('Failed to toggle monitoring:', err);
      setError(err.message || 'Failed to toggle monitoring');
    }
  };

  const deleteDevice = async (id) => {
    if (!window.confirm('Are you sure you want to delete this device?')) {
      return;
    }
    
    try {
      await deviceApi.delete(id);
      fetchDevices();
      fetchStats();
    } catch (err) {
      console.error('Failed to delete device:', err);
      setError(err.message || 'Failed to delete device');
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

  const handleModalClose = () => {
    setShowAddModal(false);
    setEditingDevice(null);
    setCloningDevice(null);
  };

  const handleModalSave = () => {
    fetchDevices();
    fetchStats();
    handleModalClose();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ErrorAlert message={error} onClose={() => setError(null)} />
      
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Homelab Inventory</h1>
              <p className="text-gray-600 mt-1">Manage your infrastructure monitoring</p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={() => setShowAdminModal(true)} 
                className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                aria-label="Open admin panel"
              >
                <Settings size={20} />
                Admin
              </button>
              <button 
                onClick={() => handleExportPrometheus('write')} 
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                aria-label="Write Prometheus files"
              >
                <Check size={20} />
                Write Prometheus Files
              </button>
              <button 
                onClick={() => handleExportPrometheus('download')} 
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                aria-label="Download configuration"
              >
                <Download size={20} />
                Download Config
              </button>
              <button 
                onClick={() => setShowAddModal(true)} 
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                aria-label="Add new device"
              >
                <Plus size={20} />
                Add Device
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      {stats && (
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Total Devices</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.total_devices}</p>
                </div>
                <Server className="text-blue-600" size={40} />
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Monitoring Enabled</p>
                  <p className="text-3xl font-bold text-green-600">{stats.enabled_devices}</p>
                </div>
                <Activity className="text-green-600" size={40} />
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Monitoring Disabled</p>
                  <p className="text-3xl font-bold text-red-600">{stats.disabled_devices}</p>
                </div>
                <X className="text-red-600" size={40} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-end justify-between gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Device Type
              </label>
              <select 
                value={selectedType} 
                onChange={(e) => setSelectedType(e.target.value)} 
                className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Devices</option>
                {DEVICE_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <div className="flex-1 max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Devices
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name, IP, function, vendor, model..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <button 
                onClick={() => setViewMode('full')} 
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === 'full' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`} 
                title="Full View"
                aria-label="Full view"
              >
                <Grid size={20} />
              </button>
              <button 
                onClick={() => setViewMode('condensed')} 
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === 'condensed' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`} 
                title="Condensed View"
                aria-label="Condensed view"
              >
                <List size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Device List */}
      <main className="max-w-7xl mx-auto px-4 py-4 pb-8">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading devices...</p>
          </div>
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
      </main>

      {/* Modals */}
      {(showAddModal || editingDevice || cloningDevice) && (
        <DeviceModal 
          device={editingDevice || cloningDevice} 
          onClose={handleModalClose} 
          onSave={handleModalSave}
          onError={setError}
        />
      )}
      
      {showAdminModal && (
        <AdminModal 
          onClose={() => setShowAdminModal(false)} 
          onError={setError} 
        />
      )}
    </div>
  );
}

export default App;
