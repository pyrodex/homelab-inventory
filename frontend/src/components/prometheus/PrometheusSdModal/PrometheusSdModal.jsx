import React, { useCallback, useEffect, useState } from 'react';
import { X, Activity, Copy, Check, RefreshCw, Loader2 } from 'lucide-react';
import { prometheusApi } from '../../../services/api';

const inputCls = 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

function PrometheusSdModal({ onClose, status }) {
  const [baseUrl, setBaseUrl] = useState(() => window.location.origin);
  const [blackbox, setBlackbox] = useState('blackbox-exporter:9115');
  const [snmpExporter, setSnmpExporter] = useState('snmp-exporter:9116');
  const [includeAll, setIncludeAll] = useState(false);
  const [groups, setGroups] = useState([]);
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [groupData, yamlText] = await Promise.all([
        prometheusApi.sdGroups(),
        prometheusApi.scrapeConfig({ baseUrl, blackbox, snmpExporter, all: includeAll }),
      ]);
      setGroups(groupData);
      setConfig(yamlText);
    } catch (err) {
      setError(err.message || 'Failed to load service discovery info');
    } finally {
      setLoading(false);
    }
  }, [baseUrl, blackbox, snmpExporter, includeAll]);

  useEffect(() => {
    const handle = setTimeout(load, 300); // debounce typing
    return () => clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(config);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable outside secure contexts */
    }
  };

  const statusLine = () => {
    if (!status) return 'Checking…';
    if (!status.enabled) return 'Not configured. Set PROMETHEUS_URL on the backend to show live up/down state on devices.';
    if (status.error) return `Configured, but ${status.error}`;
    const s = status.summary || {};
    return `Connected: ${s.up || 0} up, ${s.down || 0} down, ${s.degraded || 0} degraded, ${s.unknown || 0} not scraped.`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 dark:text-gray-100 rounded-lg shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-200">
              <Activity size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Prometheus Service Discovery</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">Let Prometheus pull targets directly — no file export or reload</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-5">
          <div className={`p-3 rounded-lg text-sm ${
            status?.enabled && !status?.error
              ? 'bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-200'
              : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
          }`}>
            <span className="font-semibold">Live status: </span>{statusLine()}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="sm:col-span-3 block">
              <span className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">How Prometheus reaches this app</span>
              <input className={inputCls} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
            </label>
            <label className="block">
              <span className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Blackbox exporter</span>
              <input className={inputCls} value={blackbox} onChange={(e) => setBlackbox(e.target.value)} />
            </label>
            <label className="block">
              <span className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">SNMP exporter</span>
              <input className={inputCls} value={snmpExporter} onChange={(e) => setSnmpExporter(e.target.value)} />
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200 sm:pt-6">
              <input type="checkbox" checked={includeAll} onChange={(e) => setIncludeAll(e.target.checked)} />
              Include all groups
            </label>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Groups with targets</h3>
            <div className="flex flex-wrap gap-2">
              {groups.length === 0 && !loading && <span className="text-sm text-gray-500">No enabled monitors yet.</span>}
              {groups.map((g) => (
                <span key={g.group} className="px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-xs font-mono">
                  {g.group} <span className="text-gray-500">· {g.targets}</span>
                </span>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">scrape_configs snippet</h3>
              <div className="flex gap-2">
                <button onClick={load} className="p-1.5 rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700" aria-label="Regenerate">
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                </button>
                <button onClick={copy} disabled={!config} className="inline-flex items-center gap-1 px-2 py-1 text-sm rounded-md bg-blue-600 text-white disabled:opacity-60">
                  {copied ? <Check size={14} /> : <Copy size={14} />} Copy
                </button>
              </div>
            </div>
            {error && <div className="mb-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-sm text-red-700 dark:text-red-200">{error}</div>}
            <pre className="p-4 rounded-lg bg-gray-950 text-gray-100 text-xs leading-relaxed overflow-x-auto max-h-96">{config || '# loading…'}</pre>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Each job polls <code>/api/prometheus/sd?group=…</code>. Set <code>PROMETHEUS_SD_TOKEN</code> on the backend to require a bearer token.
              Targets carry the same labels as the file export, plus <code>inventory_device_id</code> and <code>inventory_group</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PrometheusSdModal;
