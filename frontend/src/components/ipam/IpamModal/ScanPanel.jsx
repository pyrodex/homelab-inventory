import React, { useEffect, useRef, useState } from 'react';
import { Radar, Loader2, Play } from 'lucide-react';
import { subnetApi } from '../../../services/api';

const INTERVALS = [
  { value: 15, label: 'every 15 min' },
  { value: 30, label: 'every 30 min' },
  { value: 60, label: 'hourly' },
  { value: 360, label: 'every 6 hours' },
  { value: 1440, label: 'daily' },
];

export const timeAgo = (iso) => {
  if (!iso) return null;
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86400)} d ago`;
};

/**
 * Ping-sweep controls for one subnet: schedule toggle + interval, "Scan now",
 * and the last result. Polls while a sweep is running and calls onScanned
 * when it finishes so the grid refreshes.
 */
function ScanPanel({ subnet, scan, onChanged, onScanned }) {
  const [running, setRunning] = useState(!!scan?.running);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => { setRunning(!!scan?.running); }, [scan?.running, subnet.id]);

  useEffect(() => {
    if (!running) return undefined;
    pollRef.current = setInterval(async () => {
      try {
        const status = await subnetApi.scanStatus(subnet.id);
        if (!status.running) {
          setRunning(false);
          if (status.last_scan_error) setError(status.last_scan_error);
          onScanned?.();
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return () => clearInterval(pollRef.current);
  }, [running, subnet.id, onScanned]);

  const save = async (patch) => {
    setBusy(true);
    setError(null);
    try {
      await subnetApi.update(subnet.id, patch);
      onChanged?.();
    } catch (err) {
      const details = err.details ? Object.values(err.details).flat().join(' ') : null;
      setError(details || err.message || 'Failed to update scan settings');
    } finally {
      setBusy(false);
    }
  };

  const scanNow = async () => {
    setError(null);
    try {
      await subnetApi.scan(subnet.id);
      setRunning(true);
    } catch (err) {
      if (err.status === 409) setRunning(true);
      else setError(err.message || 'Failed to start scan');
    }
  };

  if (scan && !scan.eligible) {
    return (
      <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm text-gray-600 dark:text-gray-300">
        <Radar size={16} className="mt-0.5 flex-shrink-0" />
        <span>Ping sweeps unavailable: {scan.ineligible_reason}</span>
      </div>
    );
  }

  const last = subnet.last_scan_at
    ? `Last sweep ${timeAgo(subnet.last_scan_at)}: ${subnet.last_scan_alive ?? 0} answered${
      subnet.last_scan_duration_ms != null ? ` in ${(subnet.last_scan_duration_ms / 1000).toFixed(1)} s` : ''}`
    : 'Not swept yet';

  return (
    <div className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <Radar size={16} className="text-violet-600 dark:text-violet-300" />
        <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-100">
          <input
            type="checkbox"
            checked={!!subnet.scan_enabled}
            disabled={busy}
            onChange={(e) => save({ scan_enabled: e.target.checked })}
          />
          Ping sweep
        </label>
        <select
          value={subnet.scan_interval_minutes || 60}
          disabled={busy || !subnet.scan_enabled}
          onChange={(e) => save({ scan_interval_minutes: Number(e.target.value) })}
          className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 disabled:opacity-50"
          aria-label="Sweep interval"
        >
          {INTERVALS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
          {!INTERVALS.some((i) => i.value === subnet.scan_interval_minutes) && subnet.scan_interval_minutes && (
            <option value={subnet.scan_interval_minutes}>every {subnet.scan_interval_minutes} min</option>
          )}
        </select>
        <button
          type="button"
          onClick={scanNow}
          disabled={running}
          className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-violet-600 text-white disabled:opacity-70"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? 'Sweeping…' : 'Scan now'}
        </button>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {last}. Addresses that answered within the last {Math.round(scan?.stale_after_hours ?? 72)} h, or hold an active
        DHCP lease, aren&apos;t counted as free.
      </p>
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

export default ScanPanel;
