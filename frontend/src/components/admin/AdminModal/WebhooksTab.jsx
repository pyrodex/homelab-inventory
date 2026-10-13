import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, Send, Check, X, Copy, KeyRound, ChevronRight, Loader2 } from 'lucide-react';
import { webhookApi } from '../../../services/api';

const EVENT_LABELS = {
  'device.created': 'Device created',
  'device.updated': 'Device updated',
  'device.deleted': 'Device deleted',
  'device.relationship_changed': 'Relationship changed',
  'ipam.address_discovered': 'New address seen on the network',
};

const inputCls = 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100';
const EMPTY = { name: '', url: '', events: ['*'], enabled: true, secretMode: 'generate', secret: '' };

const when = (iso) => (iso ? new Date(iso).toLocaleString() : '');

function DeliveryBadge({ d }) {
  if (!d) return <span className="text-xs text-gray-500">No deliveries yet</span>;
  return (
    <span className={`text-xs ${d.success ? 'text-green-700 dark:text-green-300' : 'text-red-600 dark:text-red-400'}`}>
      {d.success ? '✓' : '✕'} {d.event} · {d.status_code ?? 'no response'} · {when(d.created_at)}
    </span>
  );
}

function WebhookForm({ initial, events, onCancel, onSaved, onError }) {
  const isEdit = !!initial?.id;
  const [form, setForm] = useState(() => (isEdit
    ? { ...EMPTY, ...initial, secretMode: 'keep', secret: '' }
    : EMPTY));
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const allEvents = form.events.includes('*');
  const toggleEvent = (e) => {
    const current = allEvents ? [...events] : form.events;
    const next = current.includes(e) ? current.filter((x) => x !== e) : [...current, e];
    setForm({ ...form, events: next.length === events.length ? ['*'] : next });
  };

  const submit = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    setFieldErrors({});
    const body = { name: form.name, url: form.url, events: form.events, enabled: form.enabled };
    if (form.secretMode === 'generate') body.generate_secret = true;
    else if (form.secretMode === 'custom') body.secret = form.secret;
    else if (form.secretMode === 'none') body.secret = '';
    try {
      const saved = isEdit ? await webhookApi.update(initial.id, body) : await webhookApi.create(body);
      onSaved(saved);
    } catch (err) {
      if (err.details) setFieldErrors(err.details);
      else onError?.(err.message || 'Failed to save webhook');
    } finally {
      setSaving(false);
    }
  };

  const err = (k) => fieldErrors[k] && <p className="mt-1 text-xs text-red-600">{[].concat(fieldErrors[k]).join(' ')}</p>;

  return (
    <form onSubmit={submit} className="space-y-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="block">
          <span className="block text-sm font-medium mb-1">Name</span>
          <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Home Assistant" required />
          {err('name')}
        </label>
        <label className="block">
          <span className="block text-sm font-medium mb-1">URL</span>
          <input className={`${inputCls} font-mono text-sm`} value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="http://homeassistant.lan:8123/api/webhook/inventory" required />
          {err('url')}
        </label>
      </div>
      <fieldset>
        <legend className="text-sm font-medium mb-1">Events</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          {events.map((e) => (
            <label key={e} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={allEvents || form.events.includes(e)} onChange={() => toggleEvent(e)} />
              {EVENT_LABELS[e] || e}
            </label>
          ))}
        </div>
        {err('events')}
      </fieldset>
      <fieldset>
        <legend className="text-sm font-medium mb-1">Signing secret <span className="font-normal text-gray-500">(HMAC-SHA256 in <code>X-Hub-Signature-256</code>)</span></legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {isEdit && <label className="flex items-center gap-2"><input type="radio" checked={form.secretMode === 'keep'} onChange={() => setForm({ ...form, secretMode: 'keep' })} /> Keep current{initial.has_secret ? '' : ' (none)'}</label>}
          <label className="flex items-center gap-2"><input type="radio" checked={form.secretMode === 'generate'} onChange={() => setForm({ ...form, secretMode: 'generate' })} /> {isEdit ? 'Rotate (generate new)' : 'Generate'}</label>
          <label className="flex items-center gap-2"><input type="radio" checked={form.secretMode === 'custom'} onChange={() => setForm({ ...form, secretMode: 'custom' })} /> Custom</label>
          <label className="flex items-center gap-2"><input type="radio" checked={form.secretMode === 'none'} onChange={() => setForm({ ...form, secretMode: 'none' })} /> None</label>
        </div>
        {form.secretMode === 'custom' && (
          <input className={`${inputCls} mt-2 font-mono text-sm`} value={form.secret} onChange={(e) => setForm({ ...form, secret: e.target.value })} placeholder="shared secret" autoComplete="off" />
        )}
        {err('secret')}
      </fieldset>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled
      </label>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg">Cancel</button>
        <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-70 flex items-center gap-2">
          {saving && <Loader2 size={14} className="animate-spin" />}{isEdit ? 'Save' : 'Add webhook'}
        </button>
      </div>
    </form>
  );
}

function WebhooksTab({ onError }) {
  const [data, setData] = useState({ events: [], webhooks: [] });
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null | 'new' | webhook
  const [revealed, setRevealed] = useState(null); // { name, secret }
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState({});
  const [openLog, setOpenLog] = useState(null);
  const [log, setLog] = useState([]);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    try {
      setData(await webhookApi.getAll());
    } catch (err) {
      onError?.(err.message || 'Failed to load webhooks');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const saved = (hook) => {
    setEditing(null);
    if (hook.secret) setRevealed({ name: hook.name, secret: hook.secret });
    load();
  };

  const test = async (hook) => {
    setTesting(hook.id);
    try {
      const result = await webhookApi.test(hook.id);
      setTestResult((r) => ({ ...r, [hook.id]: result }));
      load();
    } catch (err) {
      onError?.(err.message || 'Test failed');
    } finally {
      setTesting(null);
    }
  };

  const toggleLog = async (hook) => {
    if (openLog === hook.id) { setOpenLog(null); return; }
    setOpenLog(hook.id);
    setLog(await webhookApi.deliveries(hook.id).catch(() => []));
  };

  const remove = async (id) => {
    await webhookApi.delete(id).catch((err) => onError?.(err.message));
    setConfirmDelete(null);
    load();
  };

  const copySecret = async () => {
    try {
      await navigator.clipboard.writeText(revealed.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable */
    }
  };

  if (loading) return <p className="text-gray-600 dark:text-gray-300">Loading…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-300">
        POST a JSON event to a URL (Home Assistant, n8n, ntfy, …) when devices change or a new address shows up on the network.
        Failed deliveries are retried twice (after 10 s and 60 s).
      </p>

      {revealed && (
        <div className="p-3 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-sm space-y-2">
          <div className="flex items-center gap-2 font-medium text-amber-900 dark:text-amber-100">
            <KeyRound size={16} /> Signing secret for &quot;{revealed.name}&quot;. Copy it now; it won&apos;t be shown again.
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900 font-mono text-xs break-all">{revealed.secret}</code>
            <button onClick={copySecret} className="p-1.5 rounded-md bg-white dark:bg-gray-800" aria-label="Copy secret">{copied ? <Check size={14} /> : <Copy size={14} />}</button>
            <button onClick={() => setRevealed(null)} className="p-1.5 rounded-md bg-white dark:bg-gray-800" aria-label="Dismiss"><X size={14} /></button>
          </div>
        </div>
      )}

      {editing ? (
        <WebhookForm
          initial={editing === 'new' ? null : editing}
          events={data.events}
          onCancel={() => setEditing(null)}
          onSaved={saved}
          onError={onError}
        />
      ) : (
        <button onClick={() => setEditing('new')} className="flex items-center gap-2 px-4 py-2.5 bg-orange-600 text-white rounded-lg">
          <Plus size={16} /> Add webhook
        </button>
      )}

      {data.webhooks.length === 0 ? (
        !editing && <p className="text-gray-500 dark:text-gray-400">No webhooks yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
          {data.webhooks.map((hook) => {
            const result = testResult[hook.id];
            return (
              <li key={hook.id} className="p-4 space-y-2">
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{hook.name}</span>
                      {!hook.enabled && <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 dark:bg-gray-700">disabled</span>}
                      {hook.has_secret && <KeyRound size={14} className="text-gray-500" aria-label="signed" />}
                    </div>
                    <div className="font-mono text-xs text-gray-600 dark:text-gray-400 break-all">{hook.url}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {hook.events.includes('*') ? 'All events' : hook.events.map((e) => EVENT_LABELS[e] || e).join(', ')}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => test(hook)} disabled={testing === hook.id} className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-800">
                      {testing === hook.id ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Test
                    </button>
                    <button onClick={() => setEditing(hook)} className="p-2 rounded-lg bg-blue-100 text-blue-600" aria-label={`Edit ${hook.name}`}><Edit2 size={16} /></button>
                    {confirmDelete === hook.id ? (
                      <button onClick={() => remove(hook.id)} className="px-3 py-1.5 text-sm rounded-lg bg-red-600 text-white">Delete</button>
                    ) : (
                      <button onClick={() => setConfirmDelete(hook.id)} className="p-2 rounded-lg bg-red-100 text-red-600" aria-label={`Delete ${hook.name}`}><Trash2 size={16} /></button>
                    )}
                  </div>
                </div>
                {result && (
                  <div className={`text-sm ${result.success ? 'text-green-700 dark:text-green-300' : 'text-red-600 dark:text-red-400'}`}>
                    Test: {result.success ? `delivered (HTTP ${result.status_code}, ${result.duration_ms} ms)` : result.error}
                  </div>
                )}
                <button onClick={() => toggleLog(hook)} className="flex items-center gap-1 text-left" aria-expanded={openLog === hook.id}>
                  <ChevronRight size={14} className={`transition-transform ${openLog === hook.id ? 'rotate-90' : ''}`} />
                  <DeliveryBadge d={hook.last_delivery} />
                </button>
                {openLog === hook.id && (
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {log.map((d) => (
                        <tr key={d.id}>
                          <td className="py-1 pr-2">{d.success ? '✓' : '✕'}</td>
                          <td className="py-1 pr-2 font-mono">{d.event}</td>
                          <td className="py-1 pr-2">#{d.attempt}</td>
                          <td className="py-1 pr-2">{d.status_code ?? '—'}</td>
                          <td className="py-1 pr-2 text-gray-500">{d.error || `${d.duration_ms} ms`}</td>
                          <td className="py-1 text-gray-500 whitespace-nowrap">{when(d.created_at)}</td>
                        </tr>
                      ))}
                      {log.length === 0 && <tr><td className="py-1 text-gray-500">No deliveries yet</td></tr>}
                    </tbody>
                  </table>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default WebhooksTab;
