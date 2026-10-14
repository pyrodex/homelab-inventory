import React, { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2, Server, Network, Plug, AlertTriangle, ChevronRight } from 'lucide-react';
import { linkApi } from '../../../services/api';

export const LINK_TYPES = [
  { value: 'runs_on', label: 'Runs on', hint: 'VM or container → host', icon: Server, portLabel: null },
  { value: 'connected_to', label: 'Connected to', hint: 'Device → switch / AP', icon: Network, portLabel: 'Port' },
  { value: 'powered_by', label: 'Powered by', hint: 'Device → UPS / PDU / PoE switch', icon: Plug, portLabel: 'Outlet / port' },
];
const TYPE_BY_VALUE = Object.fromEntries(LINK_TYPES.map((t) => [t.value, t]));

const inputCls = 'w-full px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-base focus:ring-2 focus:ring-blue-500 focus:border-transparent';

function ImpactPanel({ deviceId, refreshKey }) {
  const [impact, setImpact] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    linkApi.impact(deviceId).then((data) => { if (!cancelled) setImpact(data); }).catch(() => setImpact(null));
    return () => { cancelled = true; };
  }, [deviceId, refreshKey]);

  // Depth-first order so each device sits directly under the one it depends on
  const ordered = useMemo(() => {
    if (!impact) return [];
    const children = new Map();
    impact.affected.forEach((d) => {
      const parent = d.depth === 1 ? null : d.via[d.via.length - 1].from_id;
      if (!children.has(parent)) children.set(parent, []);
      children.get(parent).push(d);
    });
    const out = [];
    const walk = (parent) => (children.get(parent) || []).forEach((d) => { out.push(d); walk(d.device_id); });
    walk(null);
    return out;
  }, [impact]);

  if (!impact) return null;
  if (impact.count === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">Nothing depends on this device.</p>;
  }
  return (
    <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm text-amber-900 dark:text-amber-100"
        aria-expanded={open}
      >
        <AlertTriangle size={16} className="shrink-0" />
        <span className="flex-1">
          If this goes down, <strong>{impact.count}</strong> device{impact.count === 1 ? '' : 's'} {impact.count === 1 ? 'is' : 'are'} affected
          {impact.count !== impact.direct && <> ({impact.direct} directly)</>}
        </span>
        <ChevronRight size={16} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <ul className="border-t border-amber-200 dark:border-amber-800 divide-y divide-amber-100 dark:divide-amber-900/50 max-h-64 overflow-y-auto">
          {ordered.map((d) => {
            const last = d.via[d.via.length - 1];
            return (
              <li key={d.device_id} className="px-3 py-2 text-sm flex items-center gap-2" style={{ paddingLeft: `${0.75 + (d.depth - 1) * 1.25}rem` }}>
                <span className="font-medium text-gray-900 dark:text-gray-100">{d.name}</span>
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {TYPE_BY_VALUE[last.link_type]?.label.toLowerCase()} {last.from}{last.port ? ` (${last.port})` : ''}
                </span>
                {!d.monitoring_enabled && <span className="ml-auto text-xs text-gray-500">monitoring off</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/**
 * Controlled editor for a device's outgoing links.
 * `links` items: { id?, target_id, target_name, link_type, port }
 * The parent persists changes on save (create new, delete removed, update port).
 */
function Relationships({ deviceId, links, onChange, devices = [], impactRefreshKey = 0 }) {
  const [draft, setDraft] = useState({ link_type: 'runs_on', target_id: '', port: '' });
  const [error, setError] = useState(null);

  const candidates = useMemo(
    () => devices.filter((d) => d.id !== deviceId).sort((a, b) => a.name.localeCompare(b.name)),
    [devices, deviceId]
  );

  const add = () => {
    const targetId = Number(draft.target_id);
    if (!targetId) {
      setError('Pick a device');
      return;
    }
    if (links.some((l) => l.link_type === draft.link_type && l.target_id === targetId)) {
      setError('That relationship already exists');
      return;
    }
    if (draft.link_type === 'runs_on' && links.some((l) => l.link_type === 'runs_on')) {
      setError('A device can only run on one host. Remove the current one first.');
      return;
    }
    const target = candidates.find((d) => d.id === targetId);
    onChange([...links, {
      id: null,
      link_type: draft.link_type,
      target_id: targetId,
      target_name: target?.name || `#${targetId}`,
      port: TYPE_BY_VALUE[draft.link_type].portLabel ? draft.port.trim() || null : null,
    }]);
    setDraft((d) => ({ ...d, target_id: '', port: '' }));
    setError(null);
  };

  const updatePort = (index, port) => {
    onChange(links.map((l, i) => (i === index ? { ...l, port } : l)));
  };

  const typeMeta = TYPE_BY_VALUE[draft.link_type];

  return (
    <div className="space-y-4">
      {links.length > 0 ? (
        <ul className="space-y-2">
          {links.map((link, index) => {
            const meta = TYPE_BY_VALUE[link.link_type];
            const Icon = meta?.icon || Server;
            return (
              <li key={`${link.link_type}-${link.target_id}`} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/40">
                <Icon size={18} className="text-gray-500 dark:text-gray-400 shrink-0" />
                <div className="flex-1 min-w-0 text-sm">
                  <span className="text-gray-600 dark:text-gray-300">{meta?.label}</span>{' '}
                  <span className="font-semibold text-gray-900 dark:text-gray-100">{link.target_name}</span>
                  {!link.id && <span className="ml-2 text-xs text-blue-600 dark:text-blue-300">new</span>}
                </div>
                {meta?.portLabel && (
                  <input
                    type="text"
                    value={link.port || ''}
                    onChange={(e) => updatePort(index, e.target.value)}
                    placeholder={meta.portLabel}
                    maxLength={50}
                    className="w-28 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                    aria-label={`${meta.portLabel} for ${link.target_name}`}
                  />
                )}
                <button
                  type="button"
                  onClick={() => onChange(links.filter((_, i) => i !== index))}
                  className="p-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                  aria-label={`Remove ${meta?.label} ${link.target_name}`}
                >
                  <Trash2 size={16} />
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">No relationships yet.</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-[10rem_1fr_8rem_auto] gap-2 items-start">
        <select
          value={draft.link_type}
          onChange={(e) => setDraft({ ...draft, link_type: e.target.value })}
          className={inputCls}
          aria-label="Relationship type"
        >
          {LINK_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select
          value={draft.target_id}
          onChange={(e) => { setDraft({ ...draft, target_id: e.target.value }); setError(null); }}
          className={inputCls}
          aria-label="Related device"
        >
          <option value="">{typeMeta.hint}…</option>
          {candidates.map((d) => (
            <option key={d.id} value={d.id}>{d.name}{d.ip_address ? ` (${d.ip_address})` : ''}</option>
          ))}
        </select>
        <input
          type="text"
          value={draft.port}
          onChange={(e) => setDraft({ ...draft, port: e.target.value })}
          placeholder={typeMeta.portLabel || '—'}
          disabled={!typeMeta.portLabel}
          maxLength={50}
          className={`${inputCls} disabled:opacity-50`}
          aria-label={typeMeta.portLabel || 'Port'}
        />
        <button
          type="button"
          onClick={add}
          className="flex items-center justify-center gap-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg active:bg-blue-700 min-h-[44px]"
          aria-label="Add relationship"
        >
          <Plus size={16} /> Add
        </button>
      </div>
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

      {deviceId && <ImpactPanel deviceId={deviceId} refreshKey={impactRefreshKey} />}
    </div>
  );
}

export default Relationships;
