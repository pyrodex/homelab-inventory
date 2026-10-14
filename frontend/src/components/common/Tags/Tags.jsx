import React, { useId, useState } from 'react';
import { X } from 'lucide-react';

// Same rules as the backend (utils/tags.py) so errors show before saving
const TAG_PATTERN = /^[a-z0-9][a-z0-9._-]{0,49}$/;
export const MAX_TAGS = 25;

export const normalizeTag = (value) => value.trim().toLowerCase().replace(/\s+/g, '-');
export const isValidTag = (tag) => TAG_PATTERN.test(tag);

// Stable, readable color per tag name (light + dark variants)
const PALETTE = [
  'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
  'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200',
  'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
  'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200',
  'bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-200',
  'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/40 dark:text-fuchsia-200',
];
export const tagColor = (name) => {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[hash % PALETTE.length];
};

export function TagChip({ name, onRemove, onClick, active = false, size = 'sm' }) {
  const pad = size === 'xs' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-0.5 text-xs';
  const content = (
    <>
      <span className="opacity-60">#</span>{name}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove(name); }}
          className="ml-0.5 -mr-0.5 rounded-sm hover:bg-black/10 dark:hover:bg-white/10"
          aria-label={`Remove tag ${name}`}
        >
          <X size={12} />
        </button>
      )}
    </>
  );
  const cls = `inline-flex items-center gap-0.5 rounded-md font-medium ${pad} ${tagColor(name)} ${
    active ? 'ring-2 ring-offset-1 ring-blue-500 dark:ring-offset-gray-800' : ''
  }`;
  if (onClick) {
    return (
      <button type="button" onClick={() => onClick(name)} className={`${cls} hover:brightness-95`} title={`Filter by #${name}`}>
        {content}
      </button>
    );
  }
  return <span className={cls}>{content}</span>;
}

/**
 * Chip input: Enter, comma or Tab adds; Backspace on empty input removes
 * the last chip; pasted "a, b c" splits on commas/semicolons.
 */
export function TagInput({ value = [], onChange, suggestions = [] }) {
  const [draft, setDraft] = useState('');
  const [error, setError] = useState(null);
  const listId = useId();

  const add = (raw) => {
    const parts = raw.split(/[,;]/).map(normalizeTag).filter(Boolean);
    if (!parts.length) return;
    const invalid = parts.find((t) => !isValidTag(t));
    if (invalid) {
      setError(`"${invalid}" isn't a valid tag — use letters, numbers, ".", "_" or "-"`);
      return;
    }
    const next = Array.from(new Set([...value, ...parts])).sort();
    if (next.length > MAX_TAGS) {
      setError(`At most ${MAX_TAGS} tags per device`);
      return;
    }
    setError(null);
    onChange(next);
    setDraft('');
  };

  const onKeyDown = (e) => {
    if ((e.key === 'Enter' || e.key === ',' || (e.key === 'Tab' && draft.trim())) && draft.trim()) {
      e.preventDefault();
      add(draft);
    } else if (e.key === 'Backspace' && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  };

  const unused = suggestions.filter((s) => !value.includes(s));

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-2 min-h-[44px] border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus-within:ring-2 focus-within:ring-blue-500">
        {value.map((tag) => (
          <TagChip key={tag} name={tag} onRemove={(t) => onChange(value.filter((v) => v !== t))} />
        ))}
        <input
          type="text"
          value={draft}
          list={listId}
          onChange={(e) => { setDraft(e.target.value); setError(null); }}
          onKeyDown={onKeyDown}
          onBlur={() => draft.trim() && add(draft)}
          placeholder={value.length ? '' : 'prod, storage, k8s…'}
          className="flex-1 min-w-32 bg-transparent outline-hidden text-base text-gray-900 dark:text-gray-100 px-1"
          aria-label="Add tag"
        />
        <datalist id={listId}>
          {unused.map((s) => <option key={s} value={s} />)}
        </datalist>
      </div>
      {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
