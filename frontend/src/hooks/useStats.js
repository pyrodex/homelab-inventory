import { useState, useEffect, useCallback } from 'react';
import { statsApi } from '../services/api';

/**
 * Custom hook for managing statistics
 * @returns {Object} Stats data and operations
 */
export const useStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await statsApi.get();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
      setError(err.message || 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refetch: fetchStats,
  };
};
