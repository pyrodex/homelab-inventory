const API_URL = '/api';

/**
 * Generic API request handler with error handling
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise} Response data
 */
const apiRequest = async (endpoint, options = {}) => {
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(`${API_URL}${endpoint}`, config);
    
    // Handle non-JSON responses (like blobs)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      
      // Check for standardized error response
      if (!response.ok) {
        const error = new Error(data.error || data.message || `HTTP error! status: ${response.status}`);
        error.status = response.status;
        error.details = data.details || null;
        error.errorCode = data.error_code || null;
        throw error;
      }
      
      // Handle standardized success response
      if (data.success !== undefined) {
        return data.data !== undefined ? data.data : data;
      }
      
      return data;
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response;
  } catch (error) {
    console.error(`API Error: ${endpoint}`, error);
    throw error;
  }
};

// Device API calls
export const deviceApi = {
  getAll: (type = null) => {
    const url = type ? `/devices?type=${encodeURIComponent(type)}` : '/devices';
    return apiRequest(url);
  },
  
  getById: (id) => apiRequest(`/devices/${id}`),
  getHistory: (id, { limit = 50, offset = 0 } = {}) => apiRequest(`/devices/${id}/history?limit=${limit}&offset=${offset}`),
  
  create: (deviceData) => apiRequest('/devices', {
    method: 'POST',
    body: JSON.stringify(deviceData),
  }),
  
  update: (id, deviceData) => apiRequest(`/devices/${id}`, {
    method: 'PUT',
    body: JSON.stringify(deviceData),
  }),
  
  delete: (id) => apiRequest(`/devices/${id}`, {
    method: 'DELETE',
  }),
};

// Monitor API calls
export const monitorApi = {
  create: (deviceId, monitorData) => apiRequest(`/devices/${deviceId}/monitors`, {
    method: 'POST',
    body: JSON.stringify(monitorData),
  }),
  
  delete: (monitorId) => apiRequest(`/monitors/${monitorId}`, {
    method: 'DELETE',
  }),
};

// Vendor API calls
export const vendorApi = {
  getAll: () => apiRequest('/vendors'),
  
  create: (name) => apiRequest('/vendors', {
    method: 'POST',
    body: JSON.stringify({ name }),
  }),
  
  update: (id, name) => apiRequest(`/vendors/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name }),
  }),
  
  delete: (id) => apiRequest(`/vendors/${id}`, {
    method: 'DELETE',
  }),
};

// Model API calls
export const modelApi = {
  getAll: (vendorId = null) => {
    const url = vendorId ? `/models?vendor_id=${encodeURIComponent(vendorId)}` : '/models';
    return apiRequest(url);
  },
  
  create: (name, vendorId) => apiRequest('/models', {
    method: 'POST',
    body: JSON.stringify({ name, vendor_id: vendorId }),
  }),
  
  update: (id, name, vendorId) => apiRequest(`/models/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name, vendor_id: vendorId }),
  }),
  
  delete: (id) => apiRequest(`/models/${id}`, {
    method: 'DELETE',
  }),
};

// Location API calls
export const locationApi = {
  getAll: () => apiRequest('/locations'),
  
  create: (name) => apiRequest('/locations', {
    method: 'POST',
    body: JSON.stringify({ name }),
  }),
  
  update: (id, name) => apiRequest(`/locations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name }),
  }),
  
  delete: (id) => apiRequest(`/locations/${id}`, {
    method: 'DELETE',
  }),
};

// Stats API call
export const statsApi = {
  get: () => apiRequest('/stats'),
};

// Prometheus export API calls
export const prometheusApi = {
  export: async (mode = 'download') => {
    const url = `/prometheus/export?mode=${encodeURIComponent(mode)}`;
    const response = await apiRequest(url);
    
    if (mode === 'write') {
      return response;
    }
    
    // For download mode, return blob
    const blob = await response.blob();
    return blob;
  },
};

// Bulk operations API calls
export const bulkApi = {
  importDevices: async (devices) => {
    return apiRequest('/bulk/devices/import', {
      method: 'POST',
      body: JSON.stringify(devices),
    });
  },
  
  importDevicesCSV: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/bulk/devices/import`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },
  
  exportDevices: async (format = 'json', type = null) => {
    const url = `/bulk/devices/export?format=${format}${type ? `&type=${encodeURIComponent(type)}` : ''}`;
    const response = await apiRequest(url);
    
    if (format === 'csv') {
      const blob = await response.blob();
      return blob;
    }
    
    return response;
  },
  
  deleteDevices: async (deviceIds) => {
    return apiRequest('/bulk/devices/delete', {
      method: 'POST',
      body: JSON.stringify({ device_ids: deviceIds }),
    });
  },
};

// Advanced search API calls
export const searchApi = {
  advancedSearch: async (filters) => {
    const params = new URLSearchParams();
    if (filters.q) params.append('q', filters.q);
    if (filters.type) params.append('type', filters.type);
    if (filters.vendor_id) params.append('vendor_id', filters.vendor_id);
    if (filters.model_id) params.append('model_id', filters.model_id);
    if (filters.location_id) params.append('location_id', filters.location_id);
    if (filters.monitoring_enabled !== undefined) params.append('monitoring_enabled', filters.monitoring_enabled);
    if (filters.poe_powered !== undefined) params.append('poe_powered', filters.poe_powered);
    if (filters.has_ip !== undefined) params.append('has_ip', filters.has_ip);
    
    return apiRequest(`/search/devices?${params.toString()}`);
  },
};

// Discovery API calls
export const discoveryApi = {
  run: async ({ targets = [], range = '', cidr = '' } = {}) => {
    const normalizedTargets = Array.isArray(targets)
      ? targets.filter(Boolean)
      : targets
        ? [targets]
        : [];

    return apiRequest('/discovery', {
      method: 'POST',
      body: JSON.stringify({
        targets: normalizedTargets,
        range: range || null,
        cidr: cidr || null,
      }),
    });
  },
};

// Health check API calls
export const healthApi = {
  check: () => apiRequest('/health'),
  detailed: () => apiRequest('/health/detailed'),
};
