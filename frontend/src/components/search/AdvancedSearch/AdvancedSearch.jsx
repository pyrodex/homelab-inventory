import React, { useState, useEffect } from 'react';
import { Search, X, Filter, ChevronDown, ChevronUp } from 'lucide-react';
import { searchApi } from '../../../services/api';
import { vendorApi, modelApi, locationApi } from '../../../services/api';
import { DEVICE_TYPES } from '../../../constants/deviceTypes';

function AdvancedSearch({ onResults, onError, initialFilters = {} }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchTerm, setSearchTerm] = useState(initialFilters.q || '');
  const [filters, setFilters] = useState({
    type: initialFilters.type || '',
    vendor_id: initialFilters.vendor_id || '',
    model_id: initialFilters.model_id || '',
    location_id: initialFilters.location_id || '',
    monitoring_enabled: initialFilters.monitoring_enabled !== undefined ? initialFilters.monitoring_enabled : '',
    poe_powered: initialFilters.poe_powered !== undefined ? initialFilters.poe_powered : '',
    has_ip: initialFilters.has_ip !== undefined ? initialFilters.has_ip : '',
  });
  
  const [vendors, setVendors] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilters, setActiveFilters] = useState([]);

  // Load reference data
  useEffect(() => {
    const loadReferenceData = async () => {
      try {
        const [vendorsData, modelsData, locationsData] = await Promise.all([
          vendorApi.getAll(),
          modelApi.getAll(),
          locationApi.getAll()
        ]);
        setVendors(vendorsData);
        setModels(modelsData);
        setLocations(locationsData);
      } catch (err) {
        console.error('Failed to load reference data:', err);
      }
    };
    loadReferenceData();
  }, []);

  // Update active filters display
  useEffect(() => {
    const active = [];
    if (searchTerm) active.push({ key: 'q', label: `Search: "${searchTerm}"`, value: searchTerm });
    if (filters.type) {
      const typeLabel = DEVICE_TYPES.find(t => t.value === filters.type)?.label || filters.type;
      active.push({ key: 'type', label: `Type: ${typeLabel}`, value: filters.type });
    }
    if (filters.vendor_id) {
      const vendor = vendors.find(v => v.id === parseInt(filters.vendor_id));
      if (vendor) active.push({ key: 'vendor_id', label: `Vendor: ${vendor.name}`, value: filters.vendor_id });
    }
    if (filters.model_id) {
      const model = models.find(m => m.id === parseInt(filters.model_id));
      if (model) active.push({ key: 'model_id', label: `Model: ${model.name}`, value: filters.model_id });
    }
    if (filters.location_id) {
      const location = locations.find(l => l.id === parseInt(filters.location_id));
      if (location) active.push({ key: 'location_id', label: `Location: ${location.name}`, value: filters.location_id });
    }
    if (filters.monitoring_enabled !== '') {
      active.push({ 
        key: 'monitoring_enabled', 
        label: `Monitoring: ${filters.monitoring_enabled === 'true' ? 'Enabled' : 'Disabled'}`, 
        value: filters.monitoring_enabled 
      });
    }
    if (filters.poe_powered !== '') {
      active.push({ 
        key: 'poe_powered', 
        label: `PoE: ${filters.poe_powered === 'true' ? 'Powered' : 'Not Powered'}`, 
        value: filters.poe_powered 
      });
    }
    if (filters.has_ip !== '') {
      active.push({ 
        key: 'has_ip', 
        label: `IP Address: ${filters.has_ip === 'true' ? 'Has IP' : 'No IP'}`, 
        value: filters.has_ip 
      });
    }
    setActiveFilters(active);
  }, [searchTerm, filters, vendors, models, locations]);

  // Perform search when filters change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      performSearch();
    }, 300); // Debounce search

    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filters]);

  const performSearch = async () => {
    const hasFilters = searchTerm || Object.values(filters).some(v => v !== '');
    
    if (!hasFilters) {
      // If no filters, return empty to use default device list
      if (onResults) onResults(null);
      return;
    }

    setLoading(true);
    try {
      const searchFilters = {
        q: searchTerm || undefined,
        type: filters.type || undefined,
        vendor_id: filters.vendor_id ? parseInt(filters.vendor_id) : undefined,
        model_id: filters.model_id ? parseInt(filters.model_id) : undefined,
        location_id: filters.location_id ? parseInt(filters.location_id) : undefined,
        monitoring_enabled: filters.monitoring_enabled !== '' ? filters.monitoring_enabled : undefined,
        poe_powered: filters.poe_powered !== '' ? filters.poe_powered : undefined,
        has_ip: filters.has_ip !== '' ? filters.has_ip : undefined,
      };

      const result = await searchApi.advancedSearch(searchFilters);
      if (onResults) onResults(result.results);
    } catch (err) {
      console.error('Search failed:', err);
      if (onError) onError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    
    // Reset dependent filters
    if (key === 'vendor_id') {
      setFilters(prev => ({ ...prev, model_id: '' }));
    }
  };

  const removeFilter = (key) => {
    if (key === 'q') {
      setSearchTerm('');
    } else {
      setFilters(prev => ({ ...prev, [key]: '' }));
    }
  };

  const clearAllFilters = () => {
    setSearchTerm('');
    setFilters({
      type: '',
      vendor_id: '',
      model_id: '',
      location_id: '',
      monitoring_enabled: '',
      poe_powered: '',
      has_ip: '',
    });
  };

  // Filter models by selected vendor
  const filteredModels = filters.vendor_id 
    ? models.filter(m => m.vendor_id === parseInt(filters.vendor_id))
    : models;

  return (
    <div className="space-y-4">
      {/* Main Search Bar */}
      <div className="relative">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, IP, function, serial number, networks..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base"
            />
          </div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`px-4 py-2.5 rounded-lg transition-colors touch-manipulation min-h-[44px] flex items-center gap-2 ${
              showAdvanced || activeFilters.length > 0
                ? 'bg-blue-600 text-white active:bg-blue-700'
                : 'bg-gray-200 text-gray-700 active:bg-gray-300'
            }`}
            aria-label="Toggle advanced filters"
          >
            <Filter size={18} />
            <span className="hidden sm:inline">Filters</span>
            {showAdvanced ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
        {loading && (
          <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>

      {/* Active Filter Chips */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm text-gray-600 font-medium">Active filters:</span>
          {activeFilters.map((filter) => (
            <span
              key={filter.key}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm"
            >
              <span>{filter.label}</span>
              <button
                onClick={() => removeFilter(filter.key)}
                className="hover:bg-blue-200 rounded-full p-0.5 transition-colors touch-manipulation min-w-[20px] min-h-[20px] flex items-center justify-center"
                aria-label={`Remove ${filter.label}`}
              >
                <X size={14} />
              </button>
            </span>
          ))}
          <button
            onClick={clearAllFilters}
            className="text-sm text-blue-600 hover:text-blue-800 underline touch-manipulation min-h-[32px] px-2"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Advanced Filters Panel */}
      {showAdvanced && (
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Device Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Device Type
              </label>
              <select
                value={filters.type}
                onChange={(e) => handleFilterChange('type', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All Types</option>
                {DEVICE_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>

            {/* Vendor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Vendor
              </label>
              <select
                value={filters.vendor_id}
                onChange={(e) => handleFilterChange('vendor_id', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All Vendors</option>
                {vendors.map(vendor => (
                  <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                ))}
              </select>
            </div>

            {/* Model */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Model
              </label>
              <select
                value={filters.model_id}
                onChange={(e) => handleFilterChange('model_id', e.target.value)}
                disabled={!filters.vendor_id}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="">All Models</option>
                {filteredModels.map(model => (
                  <option key={model.id} value={model.id}>{model.name}</option>
                ))}
              </select>
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Location
              </label>
              <select
                value={filters.location_id}
                onChange={(e) => handleFilterChange('location_id', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All Locations</option>
                {locations.map(location => (
                  <option key={location.id} value={location.id}>{location.name}</option>
                ))}
              </select>
            </div>

            {/* Monitoring Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Monitoring Status
              </label>
              <select
                value={filters.monitoring_enabled}
                onChange={(e) => handleFilterChange('monitoring_enabled', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All</option>
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>

            {/* PoE Powered */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                PoE Powered
              </label>
              <select
                value={filters.poe_powered}
                onChange={(e) => handleFilterChange('poe_powered', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            {/* Has IP Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                IP Address
              </label>
              <select
                value={filters.has_ip}
                onChange={(e) => handleFilterChange('has_ip', e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
              >
                <option value="">All</option>
                <option value="true">Has IP</option>
                <option value="false">No IP</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdvancedSearch;

