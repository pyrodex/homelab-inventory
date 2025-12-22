import React, { useMemo, useState } from 'react';
import { X, Radar, Search, WifiOff, Wifi, Loader2, RefreshCw, Info } from 'lucide-react';
import { discoveryApi } from '../../../services/api';

const normalizeTargetInput = (value) => {
  if (!value) return [];
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
};

function DiscoveryModal({ onClose, onAddDevice, onEditDevice, existingDevices = [] }) {
  const [singleTargets, setSingleTargets] = useState('');
  const [rangeInput, setRangeInput] = useState('');
  const [cidrInput, setCidrInput] = useState('');
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const reachableCount = useMemo(
    () => results.filter((r) => r.reachable).length,
    [results]
  );

  const existingLookup = useMemo(() => {
    const map = new Map();
    (existingDevices || []).forEach((device) => {
      [device.ip_address, device.name].forEach((key) => {
        if (key && typeof key === 'string') {
          map.set(key.trim().toLowerCase(), device);
        }
      });
    });
    return map;
  }, [existingDevices]);

  const findExistingDevice = (result) => {
    const candidates = [result.ip_address, result.ip, result.input, result.hostname]
      .filter(Boolean)
      .map((value) => (typeof value === 'string' ? value.trim().toLowerCase() : value));

    for (const candidate of candidates) {
      if (!candidate) continue;
      const match = existingLookup.get(candidate);
      if (match) return match;
    }
    return null;
  };

  const handleDiscover = async () => {
    const targets = normalizeTargetInput(singleTargets);

    if (targets.length === 0 && !rangeInput.trim() && !cidrInput.trim()) {
      setError('Add at least one IP/hostname, CIDR, or range to scan.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await discoveryApi.run({
        targets,
        range: rangeInput.trim(),
        cidr: cidrInput.trim(),
      });
      setResults(data.results || []);
      setSummary(data.summary || null);
    } catch (err) {
      setError(err.message || 'Discovery failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAddClick = (result) => {
    const existingDevice = findExistingDevice(result);
    if (existingDevice && onEditDevice) {
      onEditDevice(existingDevice);
      return;
    }

    if (!onAddDevice) return;
    onAddDevice({
      name: result.hostname || result.ip || result.input,
      ip_address: result.ip || result.input,
      device_type: 'icmp_only',
      deviceFunction: result.hostname
        ? `Discovered host (${result.hostname})`
        : 'Discovered host',
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-0 md:p-4 z-40">
      <div className="bg-white dark:bg-gray-900 rounded-none md:rounded-lg max-w-5xl w-full h-full md:h-auto max-h-[100vh] md:max-h-[92vh] overflow-hidden flex flex-col transition-colors">
        <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Radar size={22} className="text-blue-600" />
              <h2 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">
                Network Discovery
              </h2>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Probe hosts with ICMP and attempt reverse DNS to prefill device details.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100 rounded-lg active:bg-gray-100 dark:active:bg-gray-800 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Close discovery"
          >
            <X size={22} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                  Single IPs or hostnames
                </label>
                <textarea
                  value={singleTargets}
                  onChange={(e) => setSingleTargets(e.target.value)}
                  rows={3}
                  placeholder="example.com, 192.168.1.10, 192.168.1.11"
                  className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                    IP range (start-end)
                  </label>
                  <input
                    type="text"
                    value={rangeInput}
                    onChange={(e) => setRangeInput(e.target.value)}
                    placeholder="192.168.1.10-192.168.1.20"
                    className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                    CIDR block
                  </label>
                  <input
                    type="text"
                    value={cidrInput}
                    onChange={(e) => setCidrInput(e.target.value)}
                    placeholder="192.168.1.0/29"
                    className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>
              <div className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-300">
                <Info size={14} className="mt-0.5 flex-shrink-0" />
                <div>
                  ICMP is used for reachability. Reverse DNS runs against responsive IPs to
                  prefill hostnames when available. Discovery is limited to 256 targets per run.
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-2">
                <button
                  onClick={handleDiscover}
                  disabled={loading}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg active:bg-blue-700 disabled:opacity-70 transition-colors touch-manipulation min-h-[48px]"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                  {loading ? 'Scanning…' : 'Run Discovery'}
                </button>
                <button
                  onClick={() => {
                    setSingleTargets('');
                    setRangeInput('');
                    setCidrInput('');
                    setResults([]);
                    setSummary(null);
                    setError(null);
                  }}
                  disabled={loading}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-gray-200 dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-lg active:bg-gray-300 dark:active:bg-gray-700 disabled:opacity-60 transition-colors touch-manipulation min-h-[48px]"
                >
                  <RefreshCw size={18} />
                  Reset
                </button>
              </div>

              {summary && (
                <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3 space-y-1">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Summary</p>
                  <p className="text-sm text-gray-700 dark:text-gray-200">
                    Requested: <span className="font-medium">{summary.requested}</span>
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-200">
                    Reachable: <span className="font-medium">{summary.reachable}</span>
                  </p>
                </div>
              )}

              {error && (
                <div className="text-sm text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg p-3">
                  {error}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Discovery Results
              </h3>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {results.length} scanned · {reachableCount} reachable
              </span>
            </div>

            {loading && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-6 flex items-center justify-center gap-2 text-gray-700 dark:text-gray-200">
                <Loader2 size={20} className="animate-spin" />
                Running discovery…
              </div>
            )}

            {!loading && results.length === 0 && (
              <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/80 p-6 text-center text-gray-600 dark:text-gray-300">
                No results yet. Configure targets above and run discovery.
              </div>
            )}

            {!loading && results.length > 0 && (
              <div className="space-y-2">
                {results.map((result, idx) => {
                  const existingDevice = findExistingDevice(result);
                  const buttonLabel = existingDevice ? 'Edit Device' : 'Add Device';

                  return (
                    <div
                      key={`${result.input}-${idx}`}
                      className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                    >
                      <div className="flex items-start gap-3 flex-1">
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            result.reachable
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200'
                              : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200'
                          }`}
                          aria-label={result.reachable ? 'Reachable' : 'Unreachable'}
                        >
                          {result.reachable ? <Wifi size={18} /> : <WifiOff size={18} />}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                              {result.ip || result.input}
                            </span>
                            {result.hostname && (
                              <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 rounded-full">
                                {result.hostname}
                              </span>
                            )}
                            {existingDevice && (
                              <span className="text-xs px-2 py-0.5 bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 rounded-full">
                                In inventory
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 dark:text-gray-300">
                            Input: {result.input}
                          </p>
                          {existingDevice && (
                            <p className="text-xs text-blue-700 dark:text-blue-300">
                              Matches {existingDevice.name}{existingDevice.ip_address ? ` (${existingDevice.ip_address})` : ''}
                            </p>
                          )}
                          {result.rtt_ms !== null && (
                            <p className="text-xs text-gray-600 dark:text-gray-300">
                              RTT: {result.rtt_ms.toFixed(2)} ms
                            </p>
                          )}
                          {result.error && (
                            <p className="text-xs text-red-600 dark:text-red-300">
                              {result.error}
                            </p>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => handleAddClick(result)}
                        className={`w-full md:w-auto px-4 py-2.5 rounded-lg active:opacity-90 transition-colors touch-manipulation min-h-[44px] ${
                          existingDevice
                            ? 'bg-blue-600 text-white active:bg-blue-700'
                            : 'bg-green-600 text-white active:bg-green-700'
                        }`}
                      >
                        {buttonLabel}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DiscoveryModal;

