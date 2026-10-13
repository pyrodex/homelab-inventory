import React from 'react';

export const STATUS_META = {
  up: { label: 'Up', dot: 'bg-green-500', pill: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' },
  down: { label: 'Down', dot: 'bg-red-500', pill: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' },
  degraded: { label: 'Degraded', dot: 'bg-amber-500', pill: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
  unknown: { label: 'Not scraped', dot: 'bg-gray-400', pill: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200' },
};

const describe = (status) => {
  const lines = (status.monitors || []).map((m) => {
    const state = STATUS_META[m.state]?.label || m.state;
    const via = m.metric ? ` via ${m.metric}${m.job ? ` (${m.job})` : ''}` : '';
    return `${m.monitor_type} ${m.target}: ${state}${via}`;
  });
  return lines.length ? lines.join('\n') : 'No enabled monitors';
};

/**
 * Live Prometheus state for a device. Renders nothing when Prometheus isn't
 * configured or the device has monitoring disabled.
 */
function StatusBadge({ status, compact = false }) {
  if (!status || status.state === 'disabled') return null;
  const meta = STATUS_META[status.state] || STATUS_META.unknown;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium self-start ${meta.pill} ${compact ? 'px-2 py-1 text-xs' : 'px-3 py-1 text-xs'}`}
      title={describe(status)}
    >
      <span className={`w-2 h-2 rounded-full ${meta.dot} ${status.state === 'down' ? 'animate-pulse' : ''}`} />
      {meta.label}
    </span>
  );
}

export default StatusBadge;
