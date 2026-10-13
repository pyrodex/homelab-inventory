import React, { useEffect, useState } from 'react';
import { Edit2, Trash2, Check, X } from 'lucide-react';
import { tagApi } from '../../../services/api';
import { TagChip, normalizeTag, isValidTag } from '../../common/Tags/Tags';

/**
 * Tag management: rename (renaming onto an existing tag merges them) and
 * delete. Tags are created by adding them to a device.
 */
function TagsTab({ onError }) {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // { id, name }
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      setTags(await tagApi.getAll());
    } catch (err) {
      onError?.(err.message || 'Failed to load tags');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    const name = normalizeTag(editing.name);
    if (!isValidTag(name)) {
      onError?.('Tags may contain letters, numbers, ".", "_" or "-"');
      return;
    }
    try {
      await tagApi.rename(editing.id, name);
      setEditing(null);
      load();
    } catch (err) {
      onError?.(err.message || 'Failed to rename tag');
    }
  };

  const remove = async (id) => {
    try {
      await tagApi.delete(id);
      setConfirmDelete(null);
      load();
    } catch (err) {
      onError?.(err.message || 'Failed to delete tag');
    }
  };

  if (loading) return <p className="text-gray-600 dark:text-gray-300">Loading…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-300">
        Tags are created by adding them to a device. Renaming a tag to one that already exists merges the two.
      </p>
      {tags.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">No tags yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
          {tags.map((tag) => (
            <li key={tag.id} className="flex items-center gap-3 px-4 py-3">
              {editing?.id === tag.id ? (
                <>
                  <input
                    autoFocus
                    value={editing.name}
                    onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                    onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(null); }}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
                    aria-label={`New name for ${tag.name}`}
                  />
                  <button onClick={save} className="p-2 rounded-lg bg-green-100 text-green-700" aria-label="Save"><Check size={16} /></button>
                  <button onClick={() => setEditing(null)} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700" aria-label="Cancel"><X size={16} /></button>
                </>
              ) : (
                <>
                  <TagChip name={tag.name} />
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {tag.device_count} device{tag.device_count === 1 ? '' : 's'}
                  </span>
                  <div className="ml-auto flex gap-2">
                    {confirmDelete === tag.id ? (
                      <>
                        <button onClick={() => remove(tag.id)} className="px-3 py-1.5 text-sm rounded-lg bg-red-600 text-white">Delete</button>
                        <button onClick={() => setConfirmDelete(null)} className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600">Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setEditing({ id: tag.id, name: tag.name })} className="p-2 rounded-lg bg-blue-100 text-blue-600" aria-label={`Rename ${tag.name}`}><Edit2 size={16} /></button>
                        <button onClick={() => setConfirmDelete(tag.id)} className="p-2 rounded-lg bg-red-100 text-red-600" aria-label={`Delete ${tag.name}`}><Trash2 size={16} /></button>
                      </>
                    )}
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default TagsTab;
