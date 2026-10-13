import React, { useState, useEffect } from 'react';
import { Plus, Server, Activity, Download, Settings, List, Grid, Check, X, FileDown, ChevronDown, Sun, Moon, Monitor, Radar, MoreHorizontal, History, Network, HeartPulse, Share2 } from 'lucide-react';

// Components
import ErrorAlert from './components/common/ErrorAlert/ErrorAlert';
import DeviceList from './components/devices/DeviceList/DeviceList';
import DeviceModal from './components/devices/DeviceModal/DeviceModal';
import AdminModal from './components/admin/AdminModal/AdminModal';
import BulkOperationsModal from './components/bulk/BulkOperationsModal/BulkOperationsModal';
import DiscoveryModal from './components/discovery/DiscoveryModal/DiscoveryModal';
import AdvancedSearch from './components/search/AdvancedSearch/AdvancedSearch';
import HistoryModal from './components/history/HistoryModal.jsx';
import IpamModal from './components/ipam/IpamModal';
import PrometheusSdModal from './components/prometheus/PrometheusSdModal/PrometheusSdModal';
import ExportModal from './components/exports/ExportModal/ExportModal';

// Services
import { deviceApi, statsApi, prometheusApi, tagApi } from './services/api';
import { TagChip } from './components/common/Tags/Tags';

// Constants
import { DEVICE_TYPES } from './constants/deviceTypes';

// Utils
import { downloadBlob } from './utils/helpers';
import { useTheme } from './hooks/useTheme.jsx';

function App() {
  // State management
  const [devices, setDevices] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedType, setSelectedType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [cloningDevice, setCloningDevice] = useState(null);
  const [discoveryPrefill, setDiscoveryPrefill] = useState(null);
  const [allDevices, setAllDevices] = useState([]);
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showIpamModal, setShowIpamModal] = useState(false);
  const [ipamPrefill, setIpamPrefill] = useState(null);
  const [ipamRefreshKey, setIpamRefreshKey] = useState(0);
  const [promStatus, setPromStatus] = useState(null);
  const [showSdModal, setShowSdModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [allTags, setAllTags] = useState([]);
  const [activeTags, setActiveTags] = useState([]);
  const [showOtherActions, setShowOtherActions] = useState(false);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('full');
  const [error, setError] = useState(null);
  const [errorDetails, setErrorDetails] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const { theme, resolvedTheme, setTheme } = useTheme();

  const cycleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
    } else if (theme === 'dark') {
      setTheme('system');
    } else {
      setTheme('light');
    }
  };

  const themeLabel = theme === 'system' ? 'Auto' : theme === 'dark' ? 'Dark' : 'Light';
  const themeIcon = theme === 'system'
    ? <Monitor size={20} className="flex-shrink-0" />
    : resolvedTheme === 'dark'
      ? <Moon size={20} className="flex-shrink-0" />
      : <Sun size={20} className="flex-shrink-0" />;

  // Load data on mount and when filter changes
  useEffect(() => {
    if (searchResults === null) {
      fetchDevices();
    }
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedType]);

  // Update devices when search results change
  useEffect(() => {
    if (searchResults) {
      let filtered = searchResults;
      if (selectedType !== 'all') {
        filtered = searchResults.filter(d => d.device_type === selectedType);
      }
      setDevices(filtered);
    } else if (searchResults === null) {
      // Reset to default list when search is cleared
      fetchDevices();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchResults, selectedType]);

  const fetchDevices = async () => {
    try {
      // If search results are active, don't fetch default list
      if (searchResults !== null) {
        return;
      }
      const data = await deviceApi.getAll(selectedType === 'all' ? null : selectedType);
      setDevices(data);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
      setError(err.message || 'Failed to load devices');
      setErrorDetails(err.details || null);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllDevices = async () => {
    try {
      const data = await deviceApi.getAll();
      setAllDevices(data);
    } catch (err) {
      console.error('Failed to fetch all devices:', err);
    }
  };

  useEffect(() => {
    fetchAllDevices();
  }, []);

  const fetchPromStatus = async (refresh = false) => {
    try {
      setPromStatus(await prometheusApi.status(refresh));
    } catch (err) {
      setPromStatus({ enabled: false, error: err.message, devices: {} });
    }
  };

  // Live status: poll every 60s while the tab is visible
  useEffect(() => {
    fetchPromStatus();
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') fetchPromStatus();
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  const fetchTags = async () => {
    try {
      setAllTags(await tagApi.getAll());
    } catch (err) {
      console.error('Failed to load tags:', err);
    }
  };

  useEffect(() => {
    fetchTags();
  }, []);

  const toggleTagFilter = (tag) => {
    setActiveTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };

  // Tag filter applies on top of type filter and search results (all tags must match)
  const visibleDevices = activeTags.length
    ? devices.filter((d) => activeTags.every((t) => d.tags?.includes(t)))
    : devices;

  const promEnabled = !!promStatus?.enabled;
  const statusById = promStatus?.devices || {};

  const handleSearchResults = (results) => {
    setSearchResults(results);
    if (results) {
      // Filter by device type if not 'all'
      let filtered = results;
      if (selectedType !== 'all') {
        filtered = results.filter(d => d.device_type === selectedType);
      }
      setDevices(filtered);
      setLoading(false);
    } else {
      // No search active, reset to null so default fetch happens
      setSearchResults(null);
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
      setExporting(true);
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
    } finally {
      setExporting(false);
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
      fetchPromStatus(true);
    } catch (err) {
      console.error('Failed to toggle monitoring:', err);
      setError(err.message || 'Failed to toggle monitoring');
      setErrorDetails(err.details || null);
    }
  };

  const requestDelete = (device) => {
    setPendingDelete(device);
  };

  const deleteDevice = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deviceApi.delete(pendingDelete.id);
      fetchDevices();
      fetchStats();
      fetchAllDevices();
    } catch (err) {
      console.error('Failed to delete device:', err);
      setError(err.message || 'Failed to delete device');
      setErrorDetails(err.details || null);
    } finally {
      setDeleting(false);
      setPendingDelete(null);
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

  const handleDiscoveryAdd = (result) => {
    setEditingDevice(null);
    setCloningDevice(null);
    setDiscoveryPrefill({
      name: result.name || result.hostname || result.ip_address || result.ip || result.input || '',
      device_type: result.device_type || 'icmp_only',
      ip_address: result.ip_address || result.ip || result.input || '',
      deviceFunction: result.deviceFunction || (result.hostname ? `Discovered host (${result.hostname})` : 'Discovered host'),
      networks: 'LAN',
      monitoring_enabled: true,
    });
    setShowAddModal(true);
  };

  const handleDiscoveryEdit = (device) => {
    setDiscoveryPrefill(null);
    setCloningDevice(null);
    setShowAddModal(false);
    setEditingDevice(device);
    setShowDiscoveryModal(false);
  };

  const handleIpamAdd = ({ ip_address, location_id, name, hostname, discovered }) => {
    setEditingDevice(null);
    setCloningDevice(null);
    if (discovered) {
      // Seen on the network: use the discovery flow (quick add, relaxed required fields)
      setIpamPrefill(null);
      setDiscoveryPrefill({
        name: name || ip_address,
        device_type: 'icmp_only',
        ip_address,
        location_id: location_id ?? '',
        deviceFunction: hostname ? `Discovered host (${hostname})` : 'Discovered host',
        networks: 'LAN',
        monitoring_enabled: true,
      });
    } else {
      setDiscoveryPrefill(null);
      setIpamPrefill({ ip_address, location_id: location_id ?? '', networks: 'LAN', monitoring_enabled: true });
    }
    setShowAddModal(true);
  };

  const handleIpamEdit = async (deviceId) => {
    if (!deviceId) return;
    try {
      const device = allDevices.find((d) => d.id === deviceId) || await deviceApi.getById(deviceId);
      setDiscoveryPrefill(null);
      setIpamPrefill(null);
      setCloningDevice(null);
      setShowAddModal(false);
      setEditingDevice(device);
    } catch (err) {
      setError(err.message || 'Failed to load device');
    }
  };

  const handleModalClose = () => {
    setShowAddModal(false);
    setEditingDevice(null);
    setCloningDevice(null);
    setDiscoveryPrefill(null);
    setIpamPrefill(null);
  };

  const handleModalSave = () => {
    fetchDevices();
    fetchStats();
    fetchAllDevices();
    setIpamRefreshKey((k) => k + 1);
    fetchPromStatus(true);
    fetchTags();
    handleModalClose();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-gray-100 overflow-x-hidden w-full max-w-full transition-colors">
      <ErrorAlert 
        message={error} 
        details={errorDetails}
        onClose={() => {
          setError(null);
          setErrorDetails(null);
        }} 
      />
      
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow overflow-visible transition-colors">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 md:py-6 w-full">
          <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
            <div className="min-w-0 flex-shrink">
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 dark:text-white truncate">Homelab Inventory</h1>
              <p className="text-xs sm:text-sm md:text-base text-gray-600 dark:text-gray-300 mt-1">Manage your infrastructure monitoring</p>
            </div>
            <div className="w-full md:w-auto flex-shrink-0">
              {/* Desktop actions */}
              <div className="hidden md:flex md:flex-wrap md:justify-end md:items-center gap-3 relative">
                <button 
                  onClick={() => {
                    setDiscoveryPrefill(null);
                    setEditingDevice(null);
                    setCloningDevice(null);
                    setShowAddModal(true);
                  }} 
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg active:bg-orange-700 transition-colors touch-manipulation min-h-[44px] text-sm md:text-base"
                  aria-label="Add new device"
                >
                  <Plus size={20} className="flex-shrink-0" />
                  <span className="truncate">Add Device</span>
                </button>
                <button 
                  onClick={() => setShowAdminModal(true)} 
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg active:bg-gray-700 transition-colors touch-manipulation min-h-[44px] text-sm md:text-base"
                  aria-label="Open admin panel"
                >
                  <Settings size={20} className="flex-shrink-0" />
                  <span className="truncate">Admin</span>
                </button>
                <div className="relative">
                  <button
                    onClick={() => setShowOtherActions(prev => !prev)}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg active:bg-blue-700 transition-colors touch-manipulation min-h-[44px] text-sm md:text-base"
                    aria-haspopup="true"
                    aria-expanded={showOtherActions}
                  >
                    <MoreHorizontal size={20} className="flex-shrink-0" />
                    <span className="truncate">Other Actions</span>
                    <ChevronDown size={16} className={`${showOtherActions ? 'rotate-180' : ''} transition-transform`} />
                  </button>
                  {showOtherActions && (
                    <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
                      <button
                        onClick={() => { handleExportPrometheus('write'); setShowOtherActions(false); }}
                        disabled={exporting}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-70"
                      >
                        <Check size={16} className="flex-shrink-0" />
                        Write Prometheus
                      </button>
                      <button
                        onClick={() => { handleExportPrometheus('download'); setShowOtherActions(false); }}
                        disabled={exporting}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-70"
                      >
                        <Download size={16} className="flex-shrink-0" />
                        Download Config
                      </button>
                      <button
                        onClick={() => { setShowSdModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <HeartPulse size={16} className="flex-shrink-0" />
                        Prometheus SD &amp; Status
                      </button>
                      <button
                        onClick={() => { setShowBulkModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <FileDown size={16} className="flex-shrink-0" />
                        Bulk Ops
                      </button>
                      <button
                        onClick={() => { setShowExportModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <Share2 size={16} className="flex-shrink-0" />
                        Export (Ansible / NetBox)
                      </button>
                      <button
                        onClick={() => { setShowHistoryModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <History size={16} className="flex-shrink-0" />
                        History
                      </button>
                      <button
                        onClick={() => { setShowDiscoveryModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <Radar size={16} className="flex-shrink-0" />
                        Discover
                      </button>
                      <button
                        onClick={() => { setShowIpamModal(true); setShowOtherActions(false); }}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <Network size={16} className="flex-shrink-0" />
                        IPAM / Subnets
                      </button>
                    </div>
                  )}
                </div>
                <button 
                  onClick={cycleTheme}
                  className="flex items-center justify-center p-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-full active:bg-gray-300 dark:active:bg-gray-600 transition-colors touch-manipulation min-h-[40px] min-w-[40px]"
                  aria-label={`Toggle theme (current: ${themeLabel})`}
                  title={`Theme: ${themeLabel}`}
                >
                  {themeIcon}
                </button>
              </div>

              {/* Mobile action launcher */}
              <div className="md:hidden">
                <button
                  onClick={() => setShowActionMenu(!showActionMenu)}
                  className="w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-blue-600 text-white rounded-lg active:bg-blue-700 transition-colors touch-manipulation min-h-[44px]"
                  aria-expanded={showActionMenu}
                  aria-controls="action-menu"
                >
                  <span className="font-medium">Actions</span>
                  <ChevronDown className={`transition-transform ${showActionMenu ? 'rotate-180' : ''}`} size={18} />
                </button>
                {showActionMenu && (
                  <div id="action-menu" className="mt-2 bg-white border border-gray-200 rounded-lg shadow divide-y divide-gray-100">
                    <button
                      onClick={() => { cycleTheme(); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2">
                        {themeIcon}
                        Theme: {themeLabel}
                      </span>
                    </button>
                    <button
                      onClick={() => { 
                        setDiscoveryPrefill(null);
                        setEditingDevice(null);
                        setCloningDevice(null);
                        setShowAddModal(true); 
                        setShowActionMenu(false); 
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><Plus size={18} /> Add Device</span>
                    </button>
                    <button
                      onClick={() => { setShowDiscoveryModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><Radar size={18} /> Discover</span>
                    </button>
                    <button
                      onClick={() => { setShowIpamModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><Network size={18} /> IPAM / Subnets</span>
                    </button>
                    <button
                      onClick={() => { setShowBulkModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><FileDown size={18} /> Bulk Ops</span>
                    </button>
                    <button
                      onClick={() => { setShowExportModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><Share2 size={18} /> Export (Ansible / NetBox)</span>
                    </button>
                    <button
                      onClick={() => { setShowHistoryModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><History size={18} /> History</span>
                    </button>
                    <button
                      onClick={() => { handleExportPrometheus('download'); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50 disabled:opacity-70"
                      disabled={exporting}
                    >
                      <span className="flex items-center gap-2"><Download size={18} /> Download Config</span>
                    </button>
                    <button
                      onClick={() => { handleExportPrometheus('write'); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50 disabled:opacity-70"
                      disabled={exporting}
                    >
                      <span className="flex items-center gap-2"><Check size={18} /> Write Prometheus</span>
                    </button>
                    <button
                      onClick={() => { setShowSdModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><HeartPulse size={18} /> Prometheus SD &amp; Status</span>
                    </button>
                    <button
                      onClick={() => { setShowAdminModal(true); setShowActionMenu(false); }}
                      className="w-full flex items-center justify-between px-4 py-3 text-left active:bg-gray-50"
                    >
                      <span className="flex items-center gap-2"><Settings size={18} /> Admin</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      {stats && (
        <div className="max-w-7xl mx-auto px-4 py-4 md:py-6">
          <div className={`grid grid-cols-1 ${promEnabled ? 'md:grid-cols-2 lg:grid-cols-4' : 'md:grid-cols-3'} gap-3 md:gap-4`}>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">Total Devices</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total_devices}</p>
                </div>
                <Server className="text-blue-600" size={40} />
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">Monitoring Enabled</p>
                  <p className="text-3xl font-bold text-green-600">{stats.enabled_devices}</p>
                </div>
                <Activity className="text-green-600" size={40} />
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">Monitoring Disabled</p>
                  <p className="text-3xl font-bold text-red-600">{stats.disabled_devices}</p>
                </div>
                <X className="text-red-600" size={40} />
              </div>
            </div>
            {promEnabled && (
              <button
                type="button"
                onClick={() => setShowSdModal(true)}
                className="text-left bg-white dark:bg-gray-800 p-6 rounded-lg shadow transition-colors hover:ring-2 hover:ring-blue-500"
                title={promStatus.error || `${promStatus.summary?.up ?? 0} up, ${promStatus.summary?.down ?? 0} down, ${promStatus.summary?.degraded ?? 0} degraded, ${promStatus.summary?.unknown ?? 0} not scraped`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 dark:text-gray-300 text-sm">Prometheus</p>
                    {promStatus.error ? (
                      <p className="text-base font-semibold text-amber-600 mt-2">Unreachable</p>
                    ) : (
                      <p className="text-3xl font-bold tabular-nums">
                        <span className="text-green-600">{promStatus.summary?.up ?? 0}</span>
                        <span className="text-gray-400 text-xl"> up · </span>
                        <span className={(promStatus.summary?.down || promStatus.summary?.degraded) ? 'text-red-600' : 'text-gray-400'}>
                          {(promStatus.summary?.down ?? 0) + (promStatus.summary?.degraded ?? 0)}
                        </span>
                        <span className="text-gray-400 text-xl"> {((promStatus.summary?.down ?? 0) + (promStatus.summary?.degraded ?? 0)) === 1 ? 'issue' : 'issues'}</span>
                      </p>
                    )}
                  </div>
                  <HeartPulse className={promStatus.error ? 'text-amber-500' : 'text-blue-600'} size={40} />
                </div>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow space-y-4 transition-colors">
          {/* Advanced Search Component */}
          <AdvancedSearch
            onResults={handleSearchResults}
            onError={setError}
          />
          
          {/* Device Type Filter and View Mode */}
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 pt-2 border-t border-gray-200">
            <div className="flex-1 w-full md:w-auto">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Device Type
              </label>
              <select 
                value={selectedType} 
                onChange={(e) => {
                  setSelectedType(e.target.value);
                  setSearchResults(null); // Clear search when changing type filter
                }} 
                className="w-full md:w-64 px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="all">All Devices</option>
                {DEVICE_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 self-start md:self-auto">
              <button 
                onClick={() => setViewMode('full')} 
                className={`p-2.5 md:p-2 rounded-lg transition-colors touch-manipulation min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center ${
                  viewMode === 'full' 
                    ? 'bg-blue-600 text-white active:bg-blue-700' 
                    : 'bg-gray-200 text-gray-700 active:bg-gray-300'
                }`} 
                title="Full View"
                aria-label="Full view"
              >
                <Grid size={20} />
              </button>
              <button 
                onClick={() => setViewMode('condensed')} 
                className={`p-2.5 md:p-2 rounded-lg transition-colors touch-manipulation min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center ${
                  viewMode === 'condensed' 
                    ? 'bg-blue-600 text-white active:bg-blue-700' 
                    : 'bg-gray-200 text-gray-700 active:bg-gray-300'
                }`} 
                title="Condensed View"
                aria-label="Condensed view"
              >
                <List size={20} />
              </button>
            </div>
          </div>
          {allTags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-gray-200 dark:border-gray-700">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-1">Tags</span>
              {allTags.map((t) => (
                <TagChip key={t.id} name={t.name} onClick={toggleTagFilter} active={activeTags.includes(t.name)} />
              ))}
              {activeTags.length > 0 && (
                <button onClick={() => setActiveTags([])} className="ml-1 text-xs text-blue-600 dark:text-blue-400 hover:underline">
                  Clear ({activeTags.length})
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Device List */}
      <main className="max-w-7xl mx-auto px-4 py-4 pb-8">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1,2,3,4].map(key => (
              <div key={key} className="bg-white p-4 md:p-6 rounded-lg shadow">
                <div className="animate-pulse space-y-3">
                  <div className="h-5 bg-gray-200 rounded w-2/3"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded"></div>
                  </div>
                  <div className="h-10 bg-gray-200 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : devices.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 p-12 rounded-lg shadow text-center transition-colors">
            <Server className="mx-auto text-gray-400 dark:text-gray-300 mb-4" size={48} />
            <p className="text-gray-600 dark:text-gray-200">No devices found. Add your first device to get started.</p>
          </div>
        ) : (
          <DeviceList 
            devices={visibleDevices} 
            searchTerm={searchResults ? '' : searchTerm} 
            viewMode={viewMode} 
            onToggleMonitoring={toggleMonitoring} 
            onEdit={setEditingDevice} 
            onClone={handleClone} 
            onDelete={requestDelete} 
            statusById={statusById}
            onClearSearch={() => {
              setSearchTerm('');
              setSearchResults(null);
              setActiveTags([]);
            }} 
            onTagClick={toggleTagFilter}
            activeTags={activeTags}
          />
        )}
      </main>

      {/* Modals */}
      {showIpamModal && (
        <IpamModal
          onClose={() => setShowIpamModal(false)}
          onAddDevice={handleIpamAdd}
          onEditDevice={handleIpamEdit}
          refreshKey={ipamRefreshKey}
        />
      )}

      {(showAddModal || editingDevice || cloningDevice) && (
        <DeviceModal 
          key={editingDevice?.id ?? (ipamPrefill ? `ipam-${ipamPrefill.ip_address}` : 'new')}
          device={editingDevice || cloningDevice || discoveryPrefill || ipamPrefill} 
          onClose={handleModalClose} 
          onSave={handleModalSave}
          onError={setError}
          fromDiscovery={!!discoveryPrefill}
          isPrefill={!editingDevice && !cloningDevice && !!(discoveryPrefill || ipamPrefill)}
        />
      )}
      
      {showAdminModal && (
        <AdminModal 
          onClose={() => { setShowAdminModal(false); fetchTags(); fetchDevices(); }} 
          onError={setError} 
        />
      )}
      
      {showDiscoveryModal && (
        <DiscoveryModal 
          onClose={() => setShowDiscoveryModal(false)}
          onAddDevice={handleDiscoveryAdd}
          onEditDevice={handleDiscoveryEdit}
          existingDevices={allDevices}
        />
      )}
      
      {showBulkModal && (
        <BulkOperationsModal
          onClose={() => {
            setShowBulkModal(false);
            fetchDevices();
            fetchStats();
          }}
          onSuccess={(message) => {
            setSuccessMessage(message);
            setTimeout(() => setSuccessMessage(null), 5000);
            fetchDevices();
            fetchStats();
          }}
          onError={setError}
        />
      )}
      
      {showExportModal && <ExportModal onClose={() => setShowExportModal(false)} />}

      {showSdModal && (
        <PrometheusSdModal
          status={promStatus}
          onClose={() => setShowSdModal(false)}
        />
      )}

      {showHistoryModal && (
        <HistoryModal
          onClose={() => setShowHistoryModal(false)}
        />
      )}
      
      {pendingDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full transition-colors">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Delete device</h3>
            </div>
            <div className="p-4 space-y-2">
              <p className="text-gray-700 dark:text-gray-200">Are you sure you want to delete <span className="font-semibold">{pendingDelete.name}</span>?</p>
              <p className="text-sm text-gray-500 dark:text-gray-300">This will remove its monitors and stats. You can re-add it later if needed.</p>
            </div>
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex flex-col-reverse md:flex-row md:justify-end gap-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="w-full md:w-auto px-4 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg active:bg-gray-50 dark:active:bg-gray-700 transition-colors touch-manipulation min-h-[44px]"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={deleteDevice}
                className="w-full md:w-auto px-4 py-2.5 bg-red-600 text-white rounded-lg active:bg-red-700 transition-colors touch-manipulation min-h-[44px] disabled:opacity-70"
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {successMessage && (
        <div className="fixed top-4 left-4 right-4 md:right-4 md:left-auto z-50 max-w-md md:max-w-md mx-auto md:mx-0">
          <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg p-4 shadow-lg">
            <div className="flex items-start gap-3">
              <Check className="text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" size={20} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-green-700 dark:text-green-200 break-words">{successMessage}</p>
              </div>
              <button 
                onClick={() => setSuccessMessage(null)} 
                className="text-green-400 dark:text-green-300 active:text-green-600 dark:active:text-green-200 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center flex-shrink-0"
                aria-label="Close success message"
              >
                <X size={18} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
