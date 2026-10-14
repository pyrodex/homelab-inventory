import React, { useEffect, useMemo, useState } from 'react';
import { X, Share2, Copy, Check, Download, Loader2, Terminal, Database } from 'lucide-react';
import { exportApi, tagApi } from '../../../services/api';
import { TagChip } from '../../common/Tags/Tags';

function CopyBlock({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable outside secure contexts */
    }
  };
  return (
    <div className="relative group">
      <pre className="p-3 pr-12 rounded-lg bg-gray-950 text-gray-100 text-xs leading-relaxed overflow-x-auto whitespace-pre">{text}</pre>
      <button
        type="button"
        onClick={copy}
        className="absolute top-2 right-2 p-1.5 rounded-md bg-gray-800 text-gray-200 hover:bg-gray-700"
        aria-label="Copy to clipboard"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  );
}

const linkBtn = 'inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium';

function ExportModal({ onClose }) {
  const [tab, setTab] = useState('ansible');
  const [allTags, setAllTags] = useState([]);
  const [tags, setTags] = useState([]);
  const [monitoringOnly, setMonitoringOnly] = useState(false);
  const [includeAllTypes, setIncludeAllTypes] = useState(false);
  const [defaultSite, setDefaultSite] = useState('Homelab');
  const [inventory, setInventory] = useState(null);
  const [netbox, setNetbox] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const filters = useMemo(
    () => ({ tags, monitoringOnly, includeAllTypes, defaultSite: defaultSite.trim() || 'Homelab' }),
    [tags, monitoringOnly, includeAllTypes, defaultSite]
  );

  useEffect(() => {
    tagApi.getAll().then((data) => setAllTags(data.map((t) => t.name))).catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    const handle = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        if (tab === 'ansible') {
          const data = await exportApi.ansible(filters);
          if (!cancelled) setInventory(data);
        } else {
          const data = await exportApi.netboxSummary(filters);
          if (!cancelled) setNetbox(data);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to build export');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(handle); };
  }, [tab, filters]);

  const toggleTag = (t) => setTags((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  const origin = window.location.origin;
  const filterQuery = exportApi.query({ tags, monitoringOnly, includeAllTypes });
  const ansibleSetup = [
    `curl -o homelab_inventory.py ${origin}${exportApi.ansibleScriptUrl()}`,
    'chmod +x homelab_inventory.py',
    `export HOMELAB_INVENTORY_URL=${origin}`,
    ...(filterQuery ? [`export HOMELAB_INVENTORY_FILTER='${filterQuery}'`] : []),
    'ansible-inventory -i homelab_inventory.py --graph',
  ].join('\n');

  const groups = useMemo(() => {
    if (!inventory) return [];
    return (inventory.all?.children || [])
      .filter((g) => g !== 'ungrouped')
      .map((g) => ({ name: g, count: inventory[g]?.hosts?.length || 0 }));
  }, [inventory]);
  const hostCount = inventory ? Object.keys(inventory._meta?.hostvars || {}).length : 0;

  const tabBtn = (key, label, Icon) => (
    <button
      key={key}
      onClick={() => setTab(key)}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
        tab === key ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200'
      }`}
    >
      <Icon size={16} /> {label}
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-xs" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 dark:text-gray-100 rounded-lg shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-200">
              <Share2 size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Export</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">Use your inventory in Ansible or move it into NetBox</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-5">
          <div className="flex flex-wrap gap-2">
            {tabBtn('ansible', 'Ansible inventory', Terminal)}
            {tabBtn('netbox', 'NetBox CSV', Database)}
          </div>

          {/* Shared filters */}
          <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 space-y-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-1">Only tags</span>
              {allTags.length === 0 && <span className="text-sm text-gray-500">No tags yet</span>}
              {allTags.map((t) => <TagChip key={t} name={t} onClick={toggleTag} active={tags.includes(t)} />)}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-700 dark:text-gray-200">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={monitoringOnly} onChange={(e) => setMonitoringOnly(e.target.checked)} />
                Only devices with monitoring enabled
              </label>
              {tab === 'ansible' && (
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={includeAllTypes} onChange={(e) => setIncludeAllTypes(e.target.checked)} />
                  Include URL / DNS record entries
                </label>
              )}
              {tab === 'netbox' && (
                <label className="flex items-center gap-2">
                  Site for devices without a location
                  <input
                    value={defaultSite}
                    onChange={(e) => setDefaultSite(e.target.value)}
                    className="px-2 py-1 w-36 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
                    aria-label="Default site"
                  />
                </label>
              )}
            </div>
          </div>

          {error && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-sm text-red-700 dark:text-red-200">{error}</div>}

          {tab === 'ansible' ? (
            <div className="space-y-5">
              <section className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Dynamic inventory (always current)</h3>
                <CopyBlock text={ansibleSetup} />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  The script uses only the Python standard library. Target groups like <code>tag_prod</code>,
                  <code> location_basement_rack</code> or <code>&apos;tag_proxmox:&amp;monitoring_enabled&apos;</code>.
                </p>
              </section>
              <section className="flex flex-wrap items-center gap-2">
                <a href={exportApi.ansibleYamlUrl(filters)} className={`${linkBtn} bg-blue-600 text-white`} download>
                  <Download size={16} /> Static inventory (YAML)
                </a>
                <a href={exportApi.ansibleScriptUrl()} className={`${linkBtn} bg-gray-100 dark:bg-gray-800`} download>
                  <Download size={16} /> Inventory script
                </a>
              </section>
              <section>
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2 flex items-center gap-2">
                  Preview {loading && <Loader2 size={14} className="animate-spin" />}
                  {inventory && <span className="font-normal text-gray-500">{hostCount} hosts · {groups.length} groups</span>}
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {groups.map((g) => (
                    <span key={g.name} className="px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-xs font-mono">
                      {g.name} <span className="text-gray-500">· {g.count}</span>
                    </span>
                  ))}
                </div>
              </section>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Import the files <strong>in order</strong> in NetBox (each object list → <em>Import</em>), since later files
                refer to objects created by earlier ones. Built against NetBox 4.7&apos;s import formats.
              </p>
              <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-left text-gray-600 dark:text-gray-300">
                    <tr>
                      <th className="px-3 py-2">File</th>
                      <th className="px-3 py-2">Import into</th>
                      <th className="px-3 py-2 text-right">Rows</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {(netbox || []).map((f) => (
                      <tr key={f.key} className={f.rows ? '' : 'opacity-50'}>
                        <td className="px-3 py-2 font-mono text-xs">{f.filename}</td>
                        <td className="px-3 py-2">{f.where}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{f.rows}</td>
                        <td className="px-3 py-2 text-right">
                          {f.rows > 0 && (
                            <a href={exportApi.netboxFileUrl(f.key, filters)} className="text-blue-600 dark:text-blue-400 hover:underline" download>
                              CSV
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                    {!netbox && (
                      <tr><td colSpan={4} className="px-3 py-4 text-gray-500"><Loader2 size={14} className="inline animate-spin mr-2" />Building…</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <a href={exportApi.netboxZipUrl(filters)} className={`${linkBtn} bg-blue-600 text-white`} download>
                <Download size={16} /> Download all (ZIP with import notes)
              </a>
              <ul className="text-xs text-gray-500 dark:text-gray-400 list-disc pl-5 space-y-1">
                <li>Locations become sites; devices without one go to the site above.</li>
                <li>Missing vendor/model become manufacturer &quot;Generic&quot; / type &quot;Unknown&quot;. Device roles come from the device type.</li>
                <li>VMs attach to their &quot;runs on&quot; host. IPs use the subnet&apos;s prefix length and aren&apos;t assigned to interfaces.</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ExportModal;
