import React, { useEffect, useMemo, useState } from 'react';
import { X, History as HistoryIcon, ChevronLeft, ChevronRight, RefreshCcw } from 'lucide-react';
import { deviceApi } from '../../services/api';

const LIMIT_OPTIONS = [
  { value: '50', label: 'Last 50 changes' },
  { value: '100', label: 'Last 100 changes' },
  { value: '250', label: 'Last 250 changes' },
  { value: '500', label: 'Last 500 changes' },
  { value: 'all', label: 'All changes' },
];

const FIELD_LABELS = {
  name: 'Name',
  device_type: 'Device Type',
  ip_address: 'IP Address',
  deviceFunction: 'Function',
  vendor_id: 'Vendor',
  model_id: 'Model',
  location_id: 'Location',
  serial_number: 'Serial Number',
  networks: 'Networks',
  interface_type: 'Interface Type',
  poe_powered: 'PoE Powered',
  poe_standards: 'PoE Standards',
  monitoring_enabled: 'Monitoring',
};

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') return 'Empty';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

const getDisplayChange = (entry, field, change) => {
  const display = entry.display_diff?.[field] || change || {};
  return {
    old: display.old_label ?? display.old,
    new: display.new_label ?? display.new,
  };
};

function HistoryModal({ onClose }) {
  const [entries, setEntries] = useState([]);
  const [meta, setMeta] = useState({ total: 0, limit: 50, offset: 0 });
  const [selectedLimit, setSelectedLimit] = useState('50');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isAll = selectedLimit === 'all';
  const effectiveLimit = useMemo(() => {
    if (isAll) {
      return meta.total || entries.length || 0;
    }
    return Number(selectedLimit) || meta.limit || 50;
  }, [isAll, meta.limit, meta.total, selectedLimit, entries.length]);

  const totalPages = useMemo(() => {
    if (isAll) return 1;
    const total = meta.total || 0;
    return Math.max(1, Math.ceil(total / (meta.limit || Number(selectedLimit) || 1)));
  }, [isAll, meta.limit, meta.total, selectedLimit]);

  const currentPage = useMemo(() => {
    if (isAll) return 1;
    const limit = meta.limit || Number(selectedLimit) || 1;
    return Math.floor((meta.offset || 0) / limit) + 1;
  }, [isAll, meta.limit, meta.offset, selectedLimit]);

  const canPrev = !isAll && (meta.offset || 0) > 0;
  const canNext = !isAll && (meta.offset || 0) + (meta.limit || Number(selectedLimit) || 0) < (meta.total || 0);

  useEffect(() => {
    loadHistory(0, selectedLimit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLimit]);

  const loadHistory = async (offset = 0, limitOverride) => {
    const limitToUse = limitOverride ?? selectedLimit;
    setLoading(true);
    setError(null);
    try {
      const payload = await deviceApi.getAllHistory({
        limit: limitToUse,
        offset,
      });
      setEntries(payload.items || []);
      setMeta({
        total: payload.total ?? payload.items?.length ?? 0,
        limit: payload.limit ?? (limitToUse === 'all' ? payload.total || 0 : Number(limitToUse)),
        offset: payload.offset ?? offset,
      });
    } catch (err) {
      console.error('Failed to load history:', err);
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const handleLimitChange = (e) => {
    const value = e.target.value;
    setSelectedLimit(value);
  };

  const handlePrev = () => {
    if (!canPrev) return;
    const newOffset = Math.max((meta.offset || 0) - (meta.limit || effectiveLimit || 0), 0);
    loadHistory(newOffset, selectedLimit);
  };

  const handleNext = () => {
    if (!canNext) return;
    const newOffset = (meta.offset || 0) + (meta.limit || effectiveLimit || 0);
    loadHistory(newOffset, selectedLimit);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-white dark:bg-gray-900 rounded-lg shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-200">
              <HistoryIcon size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">History</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">All device changes across your inventory</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => loadHistory(meta.offset || 0, selectedLimit)}
              className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
              disabled={loading}
            >
              <RefreshCcw size={16} />
              Refresh
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg transition-colors"
              aria-label="Close history"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-800 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
            <span className="font-medium">{meta.total}</span>
            <span className="text-gray-600 dark:text-gray-400">changes recorded</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
            <span className="text-gray-600 dark:text-gray-400">Showing</span>
            <select
              value={selectedLimit}
              onChange={handleLimitChange}
              className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            >
              {LIMIT_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {error && (
            <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(key => (
                <div key={key} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-gray-600 dark:text-gray-300">
              No history found yet.
            </div>
          ) : (
            entries.map(entry => (
              <div key={entry.id} className="border border-gray-200 dark:border-gray-800 rounded-lg p-4 bg-gray-50 dark:bg-gray-900/60">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">{entry.summary || 'Change recorded'}</p>
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 capitalize">
                        {entry.change_type?.replace('_', ' ') || 'update'}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-gray-600 dark:text-gray-400 flex flex-wrap gap-3 items-center">
                      <span>{new Date(entry.created_at).toLocaleString()}</span>
                      <span className="text-gray-400">•</span>
                      <span className="font-medium text-gray-800 dark:text-gray-200">{entry.device_name || 'Unknown device'}</span>
                      {entry.device_id && (
                        <span className="text-gray-500 dark:text-gray-400">(ID {entry.device_id})</span>
                      )}
                      {entry.device_ip && (
                        <>
                          <span className="text-gray-400">•</span>
                          <span className="text-gray-600 dark:text-gray-300">{entry.device_ip}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {((entry.diff && Object.keys(entry.diff).length > 0) || (entry.display_diff && Object.keys(entry.display_diff).length > 0)) ? (
                  <div className="mt-3 space-y-2">
                    {Object.entries(entry.display_diff || entry.diff || {}).map(([field, change]) => {
                      const displayChange = getDisplayChange(entry, field, change);
                      return (
                        <div key={field} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <span className="text-sm text-gray-700 dark:text-gray-300">{FIELD_LABELS[field] || field}</span>
                          <div className="text-sm text-gray-900 dark:text-gray-100 sm:text-right">
                            <span className="text-xs text-gray-500 dark:text-gray-400 pr-1">from</span>
                            {formatValue(displayChange.old)}
                            <span className="text-xs text-gray-500 dark:text-gray-400 px-1">to</span>
                            {formatValue(displayChange.new)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">No field changes recorded.</p>
                )}
              </div>
            ))
          )}
        </div>

        <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white/80 dark:bg-gray-900/80 backdrop-blur">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrev}
              disabled={!canPrev}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-200 disabled:opacity-50 bg-white dark:bg-gray-900"
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <button
              type="button"
              className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100 bg-gray-50 dark:bg-gray-800"
            >
              Page {currentPage} of {totalPages}
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={!canNext}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-200 disabled:opacity-50 bg-white dark:bg-gray-900"
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-300">
            Showing up to {isAll ? 'all' : effectiveLimit} changes per page
          </div>
        </div>
      </div>
    </div>
  );
}

export default HistoryModal;

