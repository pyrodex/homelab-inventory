import React, { useEffect, useMemo, useState } from 'react';
import { X, Activity, Loader2, Check, Minus, ExternalLink } from 'lucide-react';
import { ipamMonitorApi, locationApi } from '../../../services/api';
import { DEVICE_TYPES, MONITOR_TYPES } from '../../../constants/deviceTypes';
import { TagInput } from '../../common/Tags/Tags';

const inputCls = 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent';

const STATUS_TEXT = {
  seen: 'Answers ping, not in inventory',
  dhcp: 'Has a DHCP lease, not in inventory',
  dns: 'Reverse DNS only, not in inventory',
  free: 'Not in inventory',
  unmonitored: 'In inventory, monitoring off',
};

/**
 * Quick "add to monitoring" for an IPAM address.
 *   - not in inventory: creates the device and its monitors in one step
 *   - in inventory with monitoring off: turns monitoring on and adds monitors
 * Probes the address first and pre-selects monitors for whatever answers.
 */
function AddToMonitoringModal({ ip, status, observed, onClose, onDone, onOpenFullForm, onEditDevice }) {
  const [probe, setProbe] = useState(null);
  const [probeError, setProbeError] = useState(null);
  const [locations, setLocations] = useState([]);
  const [form, setForm] = useState({ name: '', device_type: 'icmp_only', location_id: '', deviceFunction: '' });
  const [tags, setTags] = useState([]);
  const [selected, setSelected] = useState({}); // monitor_type -> port string ('' = default)
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const device = probe?.device || null;
  const existingTypes = useMemo(() => new Set((device?.monitors || []).map((m) => m.monitor_type)), [device]);

  useEffect(() => {
    let cancelled = false;
    locationApi.getAll().then((l) => { if (!cancelled) setLocations(l); }).catch(() => {});
    ipamMonitorApi.probe(ip).then((data) => {
      if (cancelled) return;
      setProbe(data);
      setForm((f) => ({
        ...f,
        name: data.suggested.name,
        device_type: data.suggested.device_type,
        location_id: data.subnet?.location_id ?? '',
      }));
      const initial = {};
      data.suggested.monitors.forEach((m) => { initial[m.monitor_type] = ''; });
      (data.device?.monitors || []).forEach((m) => { initial[m.monitor_type] = m.port ? String(m.port) : ''; });
      setSelected(initial);
    }).catch((err) => {
      if (cancelled) return;
      setProbeError(err.message || 'Probe failed');
      setSelected({ icmp: '' });
    });
    return () => { cancelled = true; };
  }, [ip]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const reasons = useMemo(() => {
    const r = {};
    (probe?.suggested?.monitors || []).forEach((m) => { r[m.monitor_type] = m.reason; });
    return r;
  }, [probe]);

  const toggle = (type) => {
    if (existingTypes.has(type)) return; // already on the device
    setSelected((s) => {
      const next = { ...s };
      if (type in next) delete next[type]; else next[type] = '';
      return next;
    });
  };

  const newMonitors = Object.entries(selected)
    .filter(([type]) => !existingTypes.has(type))
    .map(([type, port]) => ({ monitor_type: type, ...(port ? { port: Number(port) } : {}) }));
  const canSubmit = !saving && (device ? (newMonitors.length > 0 || !device.monitoring_enabled) : newMonitors.length > 0);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = device
        ? { device_id: device.id, monitors: newMonitors.length ? newMonitors : [{ monitor_type: device.monitors?.[0]?.monitor_type || 'icmp' }] }
        : { ip, ...form, location_id: form.location_id || null, tags, monitors: newMonitors };
      const result = await ipamMonitorApi.monitor(payload);
      onDone?.(result);
    } catch (err) {
      const details = err.details && typeof err.details === 'object'
        ? Object.entries(err.details).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('; ') : '';
      setError([err.message, details].filter(Boolean).join(' — '));
    } finally {
      setSaving(false);
    }
  };

  const hostname = probe?.hostname || observed?.hostname;
  const mac = observed?.mac;

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center p-2 sm:p-4" role="dialog" aria-modal="true" aria-label={`Add ${ip} to monitoring`}>
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <form onSubmit={submit} className="relative bg-white dark:bg-gray-900 dark:text-gray-100 rounded-lg shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-start gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-200 shrink-0">
              <Activity size={20} />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {device ? 'Turn on monitoring' : 'Add to monitoring'} <span className="font-mono">{ip}</span>
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                {[STATUS_TEXT[status] || STATUS_TEXT.free, hostname, mac].filter(Boolean).join(' · ')}
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-5">
          {/* Probe results */}
          <section className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">What answers at this address</h3>
            {!probe && !probeError && (
              <p className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                <Loader2 size={14} className="animate-spin" /> Checking ping and exporter ports…
              </p>
            )}
            {probeError && <p className="text-sm text-amber-700 dark:text-amber-300">Couldn&apos;t probe: {probeError}. You can still pick monitors below.</p>}
            {probe && (
              <ul className="flex flex-wrap gap-2 text-xs" aria-label="Probe results">
                <li className={`inline-flex items-center gap-1 px-2 py-1 rounded-md ${probe.reachable ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
                  {probe.reachable ? <Check size={12} /> : <Minus size={12} />} Ping{probe.reachable && probe.rtt_ms != null ? ` ${probe.rtt_ms.toFixed(1)} ms` : ''}
                </li>
                {probe.ports.map((p) => (
                  <li key={p.port} className={`inline-flex items-center gap-1 px-2 py-1 rounded-md ${p.open ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
                    {p.open ? <Check size={12} /> : <Minus size={12} />} {p.label} <span className="opacity-70">:{p.port}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Device details (new devices only) */}
          {device ? (
            <p className="text-sm text-gray-700 dark:text-gray-200">
              <span className="font-semibold">{device.name}</span> is in inventory
              {device.monitoring_enabled ? ' and monitored.' : ' with monitoring turned off.'} Saving turns monitoring on
              {newMonitors.length ? ` and adds ${newMonitors.map((m) => m.monitor_type).join(', ')}` : ''}.
            </p>
          ) : (
            <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="block text-sm font-medium mb-1">Name</span>
                <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={100} />
              </label>
              <label className="block">
                <span className="block text-sm font-medium mb-1">Device type</span>
                <select className={inputCls} value={form.device_type} onChange={(e) => setForm({ ...form, device_type: e.target.value })}>
                  {DEVICE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="block text-sm font-medium mb-1">Location</span>
                <select className={inputCls} value={form.location_id ?? ''} onChange={(e) => setForm({ ...form, location_id: e.target.value })}>
                  <option value="">None</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="block text-sm font-medium mb-1">Function <span className="font-normal text-gray-500">(optional)</span></span>
                <input className={inputCls} value={form.deviceFunction} onChange={(e) => setForm({ ...form, deviceFunction: e.target.value })} placeholder="Added from IPAM" maxLength={200} />
              </label>
              <div className="sm:col-span-2">
                <span className="block text-sm font-medium mb-1">Tags <span className="font-normal text-gray-500">(optional)</span></span>
                <TagInput value={tags} onChange={setTags} />
              </div>
            </section>
          )}

          {/* Monitors */}
          <fieldset>
            <legend className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">Monitors</legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {MONITOR_TYPES.map((m) => {
                const on = m.value in selected;
                const already = existingTypes.has(m.value);
                return (
                  <div key={m.value} className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${on ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-200 dark:border-gray-700'}`}>
                    <label className="flex items-center gap-2 flex-1 min-w-0 text-sm">
                      <input type="checkbox" checked={on} disabled={already} onChange={() => toggle(m.value)} aria-label={m.label} />
                      <span className="flex flex-col min-w-0 leading-tight">
                        <span className="truncate">{m.label}</span>
                        {already && <span className="text-xs text-gray-500">already set up</span>}
                        {!already && reasons[m.value] && <span className="text-xs text-green-700 dark:text-green-300">{reasons[m.value]}</span>}
                      </span>
                    </label>
                    {on && !already && m.defaultPort && (
                      <input
                        type="number" min="1" max="65535"
                        value={selected[m.value]}
                        onChange={(e) => setSelected((s) => ({ ...s, [m.value]: e.target.value }))}
                        placeholder={String(m.defaultPort)}
                        className="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                        aria-label={`${m.label} port`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Suggestions come from a ping and TCP checks of common exporter ports. SNMP and IPMI use UDP, so they can&apos;t be detected; tick them yourself if needed.
            </p>
          </fieldset>

          {error && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-sm text-red-700 dark:text-red-200">{error}</div>}
        </div>

        <div className="flex flex-wrap items-center gap-2 px-5 py-4 border-t border-gray-200 dark:border-gray-800">
          {!device && onOpenFullForm && (
            <button type="button" onClick={() => onOpenFullForm({ ...form, hostname })} className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline">
              <ExternalLink size={14} /> Open full device form
            </button>
          )}
          {device && onEditDevice && (
            <button type="button" onClick={() => onEditDevice(device.id)} className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline">
              <ExternalLink size={14} /> Edit device
            </button>
          )}
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg">Cancel</button>
            <button type="submit" disabled={!canSubmit} className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg disabled:opacity-60">
              {saving && <Loader2 size={14} className="animate-spin" />}
              {device ? 'Turn on monitoring' : 'Add & monitor'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default AddToMonitoringModal;
