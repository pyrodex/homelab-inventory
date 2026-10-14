import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  X, Network, Plus, Pencil, Trash2, Copy, Check, RefreshCw, Loader2,
  AlertTriangle, ArrowLeft, Layers, Router,
} from 'lucide-react';
import { subnetApi, locationApi } from '../../../services/api';
import ScanPanel, { timeAgo } from './ScanPanel';
import UnknownAddresses from './UnknownAddresses';
import DhcpPanel from './DhcpPanel';

const STATUS_STYLES = {
  dhcp: {
    label: 'DHCP lease, not in inventory',
    cell: 'bg-cyan-500 dark:bg-cyan-600 border-cyan-600 text-white',
    swatch: 'bg-cyan-500',
  },
  dns: {
    label: 'Reverse DNS only, not in inventory',
    cell: 'bg-rose-400 dark:bg-rose-600 border-rose-500 text-white',
    swatch: 'bg-rose-400',
  },
  seen: {
    label: 'Answers ping, not in inventory',
    cell: 'bg-violet-500 dark:bg-violet-600 border-violet-600 text-white',
    swatch: 'bg-violet-500',
  },
  free: {
    label: 'Free',
    cell: 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-orange-500 hover:text-orange-600',
    swatch: 'bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600',
  },
  monitored: {
    label: 'Monitored',
    cell: 'bg-green-500 dark:bg-green-600 border-green-600 dark:border-green-500 text-white',
    swatch: 'bg-green-500',
  },
  unmonitored: {
    label: 'In inventory, monitoring off',
    cell: 'bg-amber-400 dark:bg-amber-500 border-amber-500 text-amber-950',
    swatch: 'bg-amber-400',
  },
  gateway: {
    label: 'Gateway',
    cell: 'bg-blue-500 dark:bg-blue-600 border-blue-600 text-white',
    swatch: 'bg-blue-500',
  },
  reserved: {
    label: 'Reserved',
    cell: 'ipam-reserved border-gray-400 dark:border-gray-500 text-gray-700 dark:text-gray-200',
    swatch: 'ipam-reserved border border-gray-400',
  },
  network: {
    label: 'Network / broadcast',
    cell: 'bg-gray-700 dark:bg-black border-gray-800 dark:border-gray-500 text-gray-200 dark:text-gray-400',
    swatch: 'bg-gray-700 dark:bg-black dark:border dark:border-gray-500',
  },
  broadcast: {
    label: 'Network / broadcast',
    cell: 'bg-gray-700 dark:bg-black border-gray-800 dark:border-gray-500 text-gray-200 dark:text-gray-400',
    swatch: 'bg-gray-700 dark:bg-black dark:border dark:border-gray-500',
  },
};

const LEGEND_ORDER = ['free', 'monitored', 'unmonitored', 'seen', 'dhcp', 'dns', 'gateway', 'reserved', 'network'];

// Corner marker shown on any address with a reverse DNS (PTR) record
const PtrDot = ({ className = '' }) => (
  <span className={`w-1.5 h-1.5 rounded-full bg-rose-500 ring-1 ring-white dark:ring-gray-900 ${className}`} aria-hidden="true" />
);

const EMPTY_FORM = {
  cidr: '', name: '', vlan_id: '', gateway: '', location_id: '', reserved_ranges: '', description: '',
};

const formatCount = (n) => {
  if (n === null || n === undefined) return '—';
  if (n >= 1e15) return n.toExponential(2);
  return Number(n).toLocaleString();
};

const cellLabel = (ip, version) => {
  if (version === 4) return ip.split('.').pop();
  const parts = ip.split(':');
  return parts[parts.length - 1] || '0';
};

function UtilizationBar({ summary, className = '' }) {
  if (!summary || !summary.usable) {
    return <div className={`h-2 rounded-full bg-gray-200 dark:bg-gray-700 ${className}`} />;
  }
  const pct = (n) => `${Math.min(100, (100 * n) / summary.usable)}%`;
  return (
    <div className={`h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden flex ${className}`}>
      <div className="bg-green-500" style={{ width: pct(summary.monitored) }} />
      <div className="bg-amber-400" style={{ width: pct(summary.unmonitored) }} />
      <div className="bg-violet-500" style={{ width: pct(summary.unknown_active || 0) }} />
      {summary.ptr_blocks_free !== false && <div className="bg-rose-400" style={{ width: pct(summary.dns_only || 0) }} />}
      <div className="ipam-reserved" style={{ width: pct(summary.reserved) }} />
    </div>
  );
}

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable (non-secure context) */
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700"
      title={`Copy ${text}`}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {label}
    </button>
  );
}

function SubnetForm({ initial, locations, onCancel, onSaved, saving, setSaving }) {
  const [form, setForm] = useState(() => ({
    ...EMPTY_FORM,
    ...Object.fromEntries(
      Object.entries(initial || {}).filter(([k]) => k in EMPTY_FORM).map(([k, v]) => [k, v ?? ''])
    ),
  }));
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const isEdit = !!initial?.id;

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});
    setFormError(null);
    const payload = {
      ...form,
      vlan_id: form.vlan_id === '' ? null : Number(form.vlan_id),
      location_id: form.location_id === '' ? null : Number(form.location_id),
    };
    try {
      const saved = isEdit
        ? await subnetApi.update(initial.id, payload)
        : await subnetApi.create(payload);
      onSaved(saved);
    } catch (err) {
      if (err.details && typeof err.details === 'object') setFieldErrors(err.details);
      setFormError(err.message || 'Failed to save subnet');
    } finally {
      setSaving(false);
    }
  };

  const inputCls = 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent';
  const errorFor = (key) => fieldErrors[key] && (
    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{[].concat(fieldErrors[key]).join(' ')}</p>
  );
  const label = (text, hint) => (
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
      {text}{hint && <span className="ml-1 font-normal text-gray-500 dark:text-gray-400">{hint}</span>}
    </label>
  );

  return (
    <form onSubmit={submit} className="space-y-4 max-w-2xl">
      <div className="flex items-center gap-2">
        <button type="button" onClick={onCancel} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Back">
          <ArrowLeft size={18} />
        </button>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{isEdit ? `Edit ${initial.cidr}` : 'Add subnet'}</h3>
      </div>
      {formError && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-sm text-red-700 dark:text-red-200">{formError}</div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          {label('CIDR', '(required)')}
          <input className={`${inputCls} font-mono`} value={form.cidr} onChange={update('cidr')} placeholder="192.168.10.0/24" required autoFocus />
          {errorFor('cidr')}
        </div>
        <div>
          {label('Name')}
          <input className={inputCls} value={form.name} onChange={update('name')} placeholder="IoT" />
          {errorFor('name')}
        </div>
        <div>
          {label('Gateway')}
          <input className={`${inputCls} font-mono`} value={form.gateway} onChange={update('gateway')} placeholder="192.168.10.1" />
          {errorFor('gateway')}
        </div>
        <div>
          {label('VLAN ID')}
          <input className={inputCls} type="number" min="1" max="4094" value={form.vlan_id} onChange={update('vlan_id')} placeholder="10" />
          {errorFor('vlan_id')}
        </div>
        <div className="sm:col-span-2">
          {label('Location')}
          <select className={inputCls} value={form.location_id} onChange={update('location_id')}>
            <option value="">None</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
          {errorFor('location_id')}
        </div>
        <div className="sm:col-span-2">
          {label('Reserved ranges', '— DHCP pools, VIPs, anything not to hand out')}
          <textarea
            className={`${inputCls} font-mono text-sm`}
            rows={3}
            value={form.reserved_ranges}
            onChange={update('reserved_ranges')}
            placeholder={'192.168.10.100-199\n192.168.10.250'}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            One per line or comma-separated: single IPs, ranges (<code>a-b</code> or <code>.100-199</code> shorthand), or CIDR blocks.
          </p>
          {errorFor('reserved_ranges')}
        </div>
        <div className="sm:col-span-2">
          {label('Description')}
          <textarea className={inputCls} rows={2} value={form.description} onChange={update('description')} />
          {errorFor('description')}
        </div>
      </div>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200">
          Cancel
        </button>
        <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-70 flex items-center gap-2">
          {saving && <Loader2 size={16} className="animate-spin" />}
          {isEdit ? 'Save changes' : 'Add subnet'}
        </button>
      </div>
    </form>
  );
}

function IpamModal({ onClose, onAddDevice, onEditDevice, refreshKey = 0 }) {
  const [subnets, setSubnets] = useState([]);
  const [unassigned, setUnassigned] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedId, setSelectedId] = useState(null); // number | 'unassigned' | 'dhcp'
  const [detail, setDetail] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);
  const [formMode, setFormMode] = useState(null); // null | 'create' | 'edit'
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState('all');
  const [selectedIp, setSelectedIp] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    try {
      const [subnetData, orphanData] = await Promise.all([subnetApi.getAll(), subnetApi.getUnassigned()]);
      setSubnets(subnetData);
      setUnassigned(orphanData);
      setSelectedId((current) => {
        if (current === 'unassigned' || current === 'dhcp') return current;
        if (current && subnetData.some((s) => s.id === current)) return current;
        return subnetData[0]?.id ?? null;
      });
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load subnets');
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadDetail = useCallback(async (id) => {
    if (!id || id === 'unassigned' || id === 'dhcp') {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    try {
      setDetail(await subnetApi.getById(id));
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load subnet');
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadList();
    locationApi.getAll().then(setLocations).catch(() => setLocations([]));
  }, [loadList, refreshKey]);

  useEffect(() => {
    setSelectedIp(null);
    setConfirmDelete(false);
    loadDetail(selectedId);
  }, [selectedId, loadDetail, refreshKey]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !formMode) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, formMode]);

  const visibleAddresses = useMemo(() => {
    if (!detail?.addresses) return [];
    if (filter === 'free') return detail.addresses.filter((a) => a.status === 'free');
    if (filter === 'used') return detail.addresses.filter((a) => a.status === 'monitored' || a.status === 'unmonitored');
    return detail.addresses;
  }, [detail, filter]);

  const firstFree = detail?.free_ranges?.[0]?.start || null;
  const selectedEntry = useMemo(
    () => detail?.addresses?.find((a) => a.ip === selectedIp)
      || (selectedIp ? { ip: selectedIp, status: 'free' } : null),
    [detail, selectedIp]
  );

  const handleSaved = async (saved) => {
    setFormMode(null);
    await loadList();
    setSelectedId(saved.id);
    loadDetail(saved.id);
  };

  const handleDelete = async () => {
    if (!detail) return;
    setSaving(true);
    try {
      await subnetApi.delete(detail.subnet.id);
      setSelectedId(null);
      setDetail(null);
      setConfirmDelete(false);
      await loadList();
    } catch (err) {
      setError(err.message || 'Failed to delete subnet');
    } finally {
      setSaving(false);
    }
  };

  const addDeviceAt = (ip, observed = null) => onAddDevice?.({
    ip_address: ip,
    location_id: detail?.subnet?.location_id ?? '',
    name: observed?.hostname ? observed.hostname.split('.')[0] : '',
    hostname: observed?.hostname || null,
    discovered: !!observed,
  });

  const renderList = () => (
    <aside className="md:w-72 md:shrink-0 border-b md:border-b-0 md:border-r border-gray-200 dark:border-gray-800 flex flex-col max-h-60 md:max-h-none">
      <div className="p-3 border-b border-gray-200 dark:border-gray-800">
        <button
          onClick={() => setFormMode('create')}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-orange-600 text-white rounded-lg active:bg-orange-700 text-sm"
        >
          <Plus size={16} /> Add subnet
        </button>
      </div>
      <div className="overflow-y-auto flex-1">
        {loadingList && subnets.length === 0 ? (
          <div className="p-4 text-sm text-gray-500 flex items-center gap-2"><Loader2 size={16} className="animate-spin" /> Loading…</div>
        ) : subnets.length === 0 ? (
          <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No subnets yet. Add one in CIDR form to see which addresses are free.</p>
        ) : (
          <ul>
            {subnets.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => { setFormMode(null); setSelectedId(s.id); }}
                  className={`w-full text-left px-3 py-3 border-l-4 transition-colors ${
                    selectedId === s.id && !formMode
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/30'
                      : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-sm font-semibold text-gray-900 dark:text-white truncate">{s.cidr}</span>
                    {s.vlan_id && <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">VLAN {s.vlan_id}</span>}
                  </div>
                  {s.name && <div className="text-xs text-gray-600 dark:text-gray-300 truncate">{s.name}</div>}
                  <UtilizationBar summary={s.summary} className="mt-2" />
                  <div className="mt-1 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>
                      {formatCount(s.summary?.free)} free
                      {s.summary?.unknown_active > 0 && (
                        <span className="ml-1 text-violet-600 dark:text-violet-300" title="Answering or leased but not in inventory">
                          · {s.summary.unknown_active} unknown
                        </span>
                      )}
                      {s.summary?.dns_only > 0 && (
                        <span className="ml-1 text-rose-600 dark:text-rose-300" title="Reverse DNS record but nothing else claims the address">
                          · {s.summary.dns_only} DNS
                        </span>
                      )}
                    </span>
                    <span className="flex items-center gap-1">
                      {(s.conflict_count > 0 || s.reserved_error) && <AlertTriangle size={12} className="text-amber-500" />}
                      {s.summary?.utilization_percent ?? 0}% used
                    </span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <button
        onClick={() => { setFormMode(null); setSelectedId('dhcp'); }}
        className={`flex items-center gap-2 px-3 py-3 text-sm border-t border-gray-200 dark:border-gray-800 border-l-4 ${
          selectedId === 'dhcp' && !formMode ? 'border-l-blue-600 bg-blue-50 dark:bg-blue-900/30' : 'border-l-transparent hover:bg-gray-50 dark:hover:bg-gray-800'
        }`}
      >
        <Router size={16} className="text-gray-700 dark:text-gray-200" />
        <span className="text-gray-700 dark:text-gray-200">DHCP leases</span>
      </button>
      <button
        onClick={() => { setFormMode(null); setSelectedId('unassigned'); }}
        className={`flex items-center justify-between gap-2 px-3 py-3 text-sm border-t border-gray-200 dark:border-gray-800 border-l-4 ${
          selectedId === 'unassigned' && !formMode ? 'border-l-blue-600 bg-blue-50 dark:bg-blue-900/30' : 'border-l-transparent hover:bg-gray-50 dark:hover:bg-gray-800'
        }`}
      >
        <span className="flex items-center gap-2 text-gray-700 dark:text-gray-200"><Layers size={16} /> Outside any subnet</span>
        <span className={`px-2 py-0.5 rounded-full text-xs ${unassigned.length ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
          {unassigned.length}
        </span>
      </button>
    </aside>
  );

  const renderUnassigned = () => (
    <div className="space-y-3">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Devices outside any subnet</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">Inventory IPs not covered by a defined subnet — usually a sign a subnet is missing.</p>
      </div>
      {unassigned.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Every device IP falls inside a defined subnet.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-left text-gray-600 dark:text-gray-300">
              <tr><th className="px-3 py-2">IP</th><th className="px-3 py-2">Device</th><th className="px-3 py-2">Monitoring</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {unassigned.map((d) => (
                <tr key={d.device_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/60 cursor-pointer" onClick={() => onEditDevice?.(d.device_id)}>
                  <td className="px-3 py-2 font-mono">{d.ip_address}</td>
                  <td className="px-3 py-2">{d.name}</td>
                  <td className="px-3 py-2">{d.monitoring_enabled ? 'On' : 'Off'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  const renderSelectedIp = () => {
    if (!selectedEntry) {
      return <p className="text-sm text-gray-500 dark:text-gray-400">Click an address for details. Free addresses can be turned straight into a new device.</p>;
    }
    const style = STATUS_STYLES[selectedEntry.status] || STATUS_STYLES.free;
    return (
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`w-4 h-4 rounded-sm shrink-0 ${style.swatch}`} />
          <span className="font-mono font-semibold text-gray-900 dark:text-white">{selectedEntry.ip}</span>
          <span className="text-sm text-gray-600 dark:text-gray-300">{style.label}</span>
          {selectedEntry.ptr && selectedEntry.status !== 'dns' && (
            <span className="inline-flex items-center gap-1 text-xs text-rose-700 dark:text-rose-300"><PtrDot /> PTR {selectedEntry.ptr}</span>
          )}
          {selectedEntry.observed && (
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {[selectedEntry.observed.hostname, selectedEntry.observed.mac,
                selectedEntry.observed.seen && `ping ${timeAgo(selectedEntry.observed.last_seen)}`].filter(Boolean).join(' · ')}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
          {(selectedEntry.devices || []).map((d) => (
            <button
              key={`${d.device_id}-${d.source}`}
              onClick={() => onEditDevice?.(d.device_id)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-100"
              title={d.source === 'device' ? 'Device IP' : `Referenced by ${d.source.replace('monitor:', '')} monitor`}
            >
              <Pencil size={12} /> {d.name}{d.source !== 'device' && <span className="text-gray-500"> ({d.source.replace('monitor:', '')})</span>}
            </button>
          ))}
          <CopyButton text={selectedEntry.ip} />
          {(selectedEntry.status === 'free' || selectedEntry.observed) && (
            <button
              onClick={() => addDeviceAt(selectedEntry.ip, selectedEntry.observed || null)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-orange-600 text-white"
            >
              <Plus size={14} /> {selectedEntry.observed ? 'Add to inventory' : 'Add device here'}
            </button>
          )}
        </div>
      </div>
    );
  };

  const renderDetail = () => {
    if (!detail) {
      return loadingDetail
        ? <div className="flex items-center gap-2 text-gray-500"><Loader2 size={16} className="animate-spin" /> Loading…</div>
        : <p className="text-gray-500 dark:text-gray-400">Select or add a subnet to see address usage.</p>;
    }
    const { subnet, summary, version } = detail;

    return (
      <div className={`space-y-5 ${loadingDetail ? 'opacity-60' : ''}`}>
        <div className="flex flex-col sm:flex-row sm:items-start gap-3">
          <div className="min-w-0">
            <h3 className="text-xl font-semibold font-mono text-gray-900 dark:text-white">{subnet.cidr}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {[subnet.name, subnet.vlan_id && `VLAN ${subnet.vlan_id}`, subnet.location_name, subnet.gateway && `gw ${subnet.gateway}`]
                .filter(Boolean).join(' · ') || 'No details'}
            </p>
            {detail.first_usable && (
              <p className="text-xs text-gray-500 dark:text-gray-500 font-mono mt-0.5">
                usable {detail.first_usable} – {detail.last_usable}
              </p>
            )}
            {subnet.description && <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{subnet.description}</p>}
          </div>
          <div className="flex gap-2 sm:ml-auto shrink-0">
            <button onClick={() => setFormMode('edit')} className="px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-1">
              <Pencil size={14} /> Edit
            </button>
            {confirmDelete ? (
              <>
                <button onClick={handleDelete} disabled={saving} className="px-3 py-2 text-sm rounded-lg bg-red-600 text-white disabled:opacity-70">Confirm delete</button>
                <button onClick={() => setConfirmDelete(false)} className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600">Cancel</button>
              </>
            ) : (
              <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 flex items-center gap-1" title="Deletes the subnet only; devices are untouched">
                <Trash2 size={14} /> Delete
              </button>
            )}
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {[
            ['Free', summary.free, 'text-gray-900 dark:text-white'],
            ['Monitored', summary.monitored, 'text-green-600 dark:text-green-400'],
            ['Monitoring off', summary.unmonitored, 'text-amber-600 dark:text-amber-400'],
            ['Not in inventory', summary.unknown_active || 0, summary.unknown_active ? 'text-violet-600 dark:text-violet-300' : 'text-gray-600 dark:text-gray-300'],
            ['DNS only', summary.dns_only || 0, summary.dns_only ? 'text-rose-600 dark:text-rose-300' : 'text-gray-600 dark:text-gray-300'],
            ['Reserved', summary.reserved, 'text-gray-600 dark:text-gray-300'],
            ['Usable', summary.usable, 'text-gray-600 dark:text-gray-300'],
          ].map(([label, value, color]) => (
            <div key={label} className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
              <div className={`text-xl font-bold tabular-nums ${color}`}>{formatCount(value)}</div>
            </div>
          ))}
        </div>
        <div>
          <UtilizationBar summary={summary} className="h-3" />
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{summary.utilization_percent}% of usable addresses taken</div>
        </div>

        {/* Warnings */}
        {(detail.conflicts.length > 0 || detail.reserved_error) && (
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-200 space-y-1">
            {detail.reserved_error && <div className="flex gap-2"><AlertTriangle size={16} className="shrink-0 mt-0.5" /> Reserved ranges ignored: {detail.reserved_error}</div>}
            {detail.conflicts.map((c) => (
              <div key={c.ip} className="flex gap-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                <span><span className="font-mono">{c.ip}</span> is claimed by {c.devices.map((d) => d.name).join(', ')}</span>
              </div>
            ))}
          </div>
        )}

        <ScanPanel
          subnet={subnet}
          scan={detail.scan}
          onChanged={() => { loadList(); loadDetail(subnet.id); }}
          onScanned={() => { loadList(); loadDetail(subnet.id); }}
        />

        {/* Next free */}
        <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-300">Next free:</span>
          {firstFree ? (
            <>
              <span className="font-mono font-semibold text-gray-900 dark:text-white">{firstFree}</span>
              <CopyButton text={firstFree} />
              <button onClick={() => addDeviceAt(firstFree)} className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-orange-600 text-white">
                <Plus size={14} /> Add device
              </button>
            </>
          ) : (
            <span className="text-sm font-semibold text-red-600">Subnet is full</span>
          )}
        </div>

        {/* Address grid */}
        {detail.addresses ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="inline-flex rounded-lg bg-gray-100 dark:bg-gray-800 p-1 text-sm">
                {[['all', 'All'], ['free', 'Free'], ['used', 'In use']].map(([key, text]) => (
                  <button
                    key={key}
                    onClick={() => setFilter(key)}
                    className={`px-3 py-1 rounded-md ${filter === key ? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'}`}
                  >
                    {text}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
                {LEGEND_ORDER.map((key) => (
                  <span key={key} className="flex items-center gap-1">
                    <span className={`w-3 h-3 rounded-xs ${STATUS_STYLES[key].swatch}`} /> {STATUS_STYLES[key].label}
                  </span>
                ))}
                <span className="flex items-center gap-1">
                  <span className="relative w-3 h-3 rounded-xs border border-gray-300 dark:border-gray-600"><PtrDot className="absolute -top-0.5 -right-0.5" /></span>
                  Has reverse DNS (PTR)
                </span>
              </div>
            </div>
            <div className="grid grid-cols-8 sm:grid-cols-16 gap-1">
              {visibleAddresses.map((a) => {
                const style = STATUS_STYLES[a.status] || STATUS_STYLES.free;
                const names = (a.devices || []).map((d) => d.name).join(', ');
                return (
                  <button
                    key={a.ip}
                    onClick={() => setSelectedIp(a.ip)}
                    title={`${a.ip} — ${style.label}${names ? `: ${names}` : ''}${a.ptr ? `\nPTR: ${a.ptr}` : ''}`}
                    className={`relative h-8 rounded border text-[11px] font-mono tabular-nums transition-colors ${style.cell} ${
                      selectedIp === a.ip ? 'ring-2 ring-offset-1 ring-blue-500 dark:ring-offset-gray-900' : ''
                    }`}
                  >
                    {cellLabel(a.ip, version)}
                    {a.ptr && a.status !== 'dns' && <PtrDot className="absolute top-0.5 right-0.5" />}
                  </button>
                );
              })}
            </div>
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">{renderSelectedIp()}</div>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            This subnet has more than {formatCount(detail.address_listing_limit)} addresses, so the grid is hidden. Free ranges and used addresses are listed below.
          </p>
        )}

        <UnknownAddresses
          items={detail.unknown_addresses || []}
          onAdd={(u) => addDeviceAt(u.ip, u)}
          onSelect={(ip) => { setFilter('all'); setSelectedIp(ip); }}
        />

        {/* Free ranges + used list */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <section>
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Free ranges ({detail.free_ranges.length})</h4>
            <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-800 rounded-lg divide-y divide-gray-100 dark:divide-gray-800">
              {detail.free_ranges.length === 0 && <p className="p-3 text-sm text-gray-500">None</p>}
              {detail.free_ranges.map((r) => {
                const text = r.start === r.end ? r.start : `${r.start}-${r.end}`;
                return (
                  <div key={r.start} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
                    <span className="font-mono truncate text-gray-900 dark:text-gray-100">{text}</span>
                    <span className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-gray-500 tabular-nums">{formatCount(r.size)}</span>
                      <CopyButton text={text} label="" />
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
          <section>
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">In use ({detail.used_addresses.length})</h4>
            <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-800 rounded-lg divide-y divide-gray-100 dark:divide-gray-800">
              {detail.used_addresses.length === 0 && <p className="p-3 text-sm text-gray-500">No inventoried devices in this subnet</p>}
              {detail.used_addresses.map((u) => (
                <button
                  key={u.ip}
                  onClick={() => onEditDevice?.(u.devices[0]?.device_id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-gray-50 dark:hover:bg-gray-800/60"
                >
                  <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_STYLES[u.status].swatch}`} />
                  <span className="font-mono w-36 shrink-0 truncate">{u.ip}</span>
                  <span className="truncate text-gray-700 dark:text-gray-200">{u.devices.map((d) => d.name).join(', ')}</span>
                  {u.ptr && <span className="truncate text-xs text-rose-700 dark:text-rose-300 font-mono" title="Reverse DNS (PTR)">{u.ptr}</span>}
                  {!u.ptr && u.ptr_checked && <span className="text-xs text-gray-400 shrink-0" title="Swept, but no PTR record">no PTR</span>}
                  {u.notes.length > 0 && <span className="ml-auto text-xs text-amber-600 shrink-0">{u.notes.join(', ')}</span>}
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-xs" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 dark:text-gray-100 rounded-lg shadow-2xl w-full max-w-6xl h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-200">
              <Network size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">IPAM</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">Subnet usage from your inventory — find free addresses fast</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => { loadList(); loadDetail(selectedId); }}
              className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700"
              aria-label="Refresh"
              title="Refresh"
            >
              <RefreshCw size={18} className={loadingList || loadingDetail ? 'animate-spin' : ''} />
            </button>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
              <X size={20} />
            </button>
          </div>
        </div>

        {error && (
          <div className="mx-5 mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-sm text-red-700 dark:text-red-200">{error}</div>
        )}

        <div className="flex flex-col md:flex-row flex-1 min-h-0">
          {renderList()}
          <main className="flex-1 min-w-0 overflow-y-auto p-4 sm:p-5">
            {formMode ? (
              <SubnetForm
                key={formMode === 'edit' ? detail?.subnet?.id : 'new'}
                initial={formMode === 'edit' ? detail?.subnet : null}
                locations={locations}
                onCancel={() => setFormMode(null)}
                onSaved={handleSaved}
                saving={saving}
                setSaving={setSaving}
              />
            ) : selectedId === 'unassigned' ? renderUnassigned()
              : selectedId === 'dhcp' ? <DhcpPanel onImported={() => loadList()} />
                : renderDetail()}
          </main>
        </div>
      </div>
    </div>
  );
}

export default IpamModal;
