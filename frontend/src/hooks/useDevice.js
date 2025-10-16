import { useState, useEffect, useCallback } from 'react';
import { deviceApi } from '../services/api';

/**
 * Custom hook for managing devices
 * @param {string} filterType - Device type filter
 * @returns {Object} Devices data and operations
 */
export const useDevices = (filterType = 'all') => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await deviceApi.getAll(
        filterType === 'all' ? null : filterType
      );
      setDevices(data);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
      setError(err.message || 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  const createDevice = async (deviceData) => {
    try {
      await deviceApi.create(deviceData);
      await fetchDevices();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const updateDevice = async (id, deviceData) => {
    try {
      await deviceApi.update(id, deviceData);
      await fetchDevices();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const deleteDevice = async (id) => {
    try {
      await deviceApi.delete(id);
      await fetchDevices();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const toggleMonitoring = async (device) => {
    try {
      await deviceApi.update(device.id, {
        ...device,
        monitoring_enabled: !device.monitoring_enabled
      });
      await fetchDevices();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  return {
    devices,
    loading,
    error,
    refetch: fetchDevices,
    createDevice,
    updateDevice,
    deleteDevice,
    toggleMonitoring,
  };
};
