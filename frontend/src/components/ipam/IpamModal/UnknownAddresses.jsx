import React from 'react';
import { Plus } from 'lucide-react';
import { timeAgo } from './ScanPanel';

/**
 * Addresses the network reports in use (ping or DHCP) that aren't in
 * inventory, with a one-click "Add" that prefills IP and hostname.
 */
function UnknownAddresses({ items = [], onAdd, onSelect }) {
  if (!items.length) return null;
  return (
    <section>
      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
        Not in inventory ({items.length})
      </h4>
      <div className="overflow-x-auto border border-violet-200 dark:border-violet-900 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-violet-50 dark:bg-violet-900/20 text-left text-gray-600 dark:text-gray-300">
            <tr>
              <th className="px-3 py-2">IP</th>
              <th className="px-3 py-2">Hostname</th>
              <th className="px-3 py-2">MAC</th>
              <th className="px-3 py-2">Evidence</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {items.map((u) => {
              const evidence = [
                u.dhcp && (u.dhcp_expires ? `DHCP lease (until ${new Date(u.dhcp_expires).toLocaleString()})` : 'DHCP lease (no expiry)'),
                u.seen && `answered ping ${timeAgo(u.last_seen)}${u.reachable_now ? '' : ', not on last sweep'}`,
                u.status === 'dns' ? 'reverse DNS record only' : u.ptr && 'has PTR',
              ].filter(Boolean).join(' · ');
              return (
                <tr key={u.ip} className="hover:bg-gray-50 dark:hover:bg-gray-800/60">
                  <td className="px-3 py-2 font-mono">
                    <button type="button" onClick={() => onSelect?.(u.ip)} className="hover:underline">{u.ip}</button>
                    {u.in_reserved_range && <span className="ml-2 text-xs text-gray-500">reserved range</span>}
                  </td>
                  <td className="px-3 py-2">{u.hostname || <span className="text-gray-400">—</span>}</td>
                  <td className="px-3 py-2 font-mono text-xs">{u.mac || <span className="text-gray-400">—</span>}</td>
                  <td className="px-3 py-2 text-xs text-gray-600 dark:text-gray-300">{evidence}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => onAdd?.(u)}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-orange-600 text-white"
                      aria-label={`Add ${u.ip} to inventory`}
                    >
                      <Plus size={12} /> Add
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default UnknownAddresses;
