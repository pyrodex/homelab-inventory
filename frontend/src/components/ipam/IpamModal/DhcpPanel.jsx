import React, { useCallback, useEffect, useState } from 'react';
import { Upload, Loader2, FileText } from 'lucide-react';
import { dhcpApi } from '../../../services/api';

const Code = ({ children }) => (
  <pre className="p-3 rounded-lg bg-gray-950 text-gray-100 text-xs overflow-x-auto whitespace-pre">{children}</pre>
);

/** dnsmasq lease sources: watched files, push via curl, or manual upload. */
function DhcpPanel({ onImported }) {
  const [status, setStatus] = useState(null);
  const [text, setText] = useState('');
  const [source, setSource] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    dhcpApi.status().then(setStatus).catch((err) => setError(err.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async (file = null) => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await dhcpApi.upload({ file, text, source: source.trim() });
      setResult(res);
      setText('');
      load();
      onImported?.();
    } catch (err) {
      setError(err.message || 'Import failed');
    } finally {
      setBusy(false);
    }
  };

  const origin = window.location.origin;
  const label = source.trim() || 'dnsmasq';
  const auth = status?.token_required ? ' -H "Authorization: Bearer $IPAM_LEASES_TOKEN"' : '';

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">DHCP leases (dnsmasq)</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Active leases mark addresses as in use and show their hostname and MAC, even for devices you haven&apos;t inventoried.
          Each source is a snapshot: leases missing from the next import are released.
        </p>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Active leases by source</div>
          {status && Object.keys(status.active_by_source).length === 0 && <div className="text-sm text-gray-500">None yet</div>}
          {status && Object.entries(status.active_by_source).map(([src, n]) => (
            <div key={src} className="flex justify-between text-sm"><span className="font-mono truncate">{src}</span><span className="tabular-nums">{n}</span></div>
          ))}
        </div>
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Watched lease files (DNSMASQ_LEASES_PATH)</div>
          {status && status.watched_files.length === 0 && <div className="text-sm text-gray-500">Not configured</div>}
          {status && status.watched_files.map((path) => {
            const r = status.file_results?.[path];
            return (
              <div key={path} className="text-sm">
                <span className="font-mono">{path}</span>{' '}
                <span className={r?.error ? 'text-red-600' : 'text-gray-500'}>
                  {r?.error ? r.error : r ? `${r.active} active` : 'waiting'}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Push from the dnsmasq host</h4>
        <p className="text-xs text-gray-600 dark:text-gray-400">Add to cron on the machine running dnsmasq (e.g. every 5 minutes):</p>
        <Code>{`curl -fsS --data-binary @/var/lib/misc/dnsmasq.leases${auth} \\\n  "${origin}/api/ipam/dhcp/leases?source=${encodeURIComponent(label)}"`}</Code>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Or mount the lease file into the backend container and set <code>DNSMASQ_LEASES_PATH</code>; it&apos;s re-read whenever it changes.
        </p>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Import now</h4>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="source label (optional)"
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
            aria-label="Lease source label"
          />
          <label className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 cursor-pointer">
            <FileText size={14} /> Choose file
            <input type="file" className="hidden" onChange={(e) => e.target.files?.[0] && submit(e.target.files[0])} />
          </label>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="…or paste the contents of dnsmasq.leases"
          className="w-full px-3 py-2 font-mono text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          aria-label="Lease file contents"
        />
        <button
          type="button"
          onClick={() => submit()}
          disabled={busy || !text.trim()}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-blue-600 text-white disabled:opacity-60"
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Import pasted leases
        </button>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        {result && (
          <p className="text-sm text-green-700 dark:text-green-300">
            Imported {result.leases} leases from <span className="font-mono">{result.source}</span>: {result.active} active,
            {' '}{result.expired} expired, {result.released} released{result.skipped?.length ? `, ${result.skipped.length} lines skipped` : ''}.
          </p>
        )}
      </section>
    </div>
  );
}

export default DhcpPanel;
