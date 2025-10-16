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
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    // Handle non-JSON responses (like blobs)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
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
