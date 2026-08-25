'use client';

import { useEffect, useMemo, useState } from 'react';
import { api, apiBlob, apiDownload } from '@/lib/api';
import { useConfirmDialog } from './AppDialog';

type NavItem = {
  id: string;
  label: string;
  href: string;
  visible: boolean;
  children?: NavItem[];
};

type NavRecord = {
  id: string;
  key: string;
  locale: string;
  items: NavItem[];
};

type Media = {
  id: string;
  title: string;
  file_path: string;
  mime_type: string;
  alt_text: string;
  accessibility_tags: string[];
  original_name: string;
  file_size: number;
  sha256: string;
  scan_status: string;
  visibility: 'public' | 'private';
  decorative: boolean;
};

type LeadField = {
  name: string;
  label: string;
  type: string;
  required: boolean;
};

type LeadForm = {
  id: string;
  key: string;
  name: string;
  fields: LeadField[];
  routing: Record<string, unknown>;
  is_active: boolean;
};

type EditableLeadField = LeadField & { id: string };

const uid = () => crypto.randomUUID();

const flatten = (items: NavItem[]) =>
  items.map((item) => ({
    ...item,
    id: item.id || uid(),
    children: (item.children || []).map((child) => ({ ...child, id: child.id || uid() })),
  }));

const strip = (items: NavItem[]) =>
  items.map(({ id: _id, ...item }) => ({
    ...item,
    children: (item.children || []).map(({ id: _childId, ...child }) => child),
  }));

export function NavigationBuilder({
  records,
  onSaved,
}: {
  records: NavRecord[];
  onSaved: (records: NavRecord[]) => void;
}) {
  const [selected, setSelected] = useState('new');
  const [key, setKey] = useState('primary');
  const [locale, setLocale] = useState('en');
  const [items, setItems] = useState<NavItem[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const record = records.find((candidate) => candidate.id === selected);
    if (!record) return;
    setKey(record.key);
    setLocale(record.locale);
    setItems(flatten(record.items || []));
  }, [selected, records]);

  function move(index: number, delta: number) {
    const nextIndex = index + delta;
    if (nextIndex < 0 || nextIndex >= items.length) return;
    setItems((current) => {
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
  }

  function patch(index: number, patchValue: Partial<NavItem>) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patchValue } : item,
      ),
    );
  }

  function childPatch(index: number, childIndex: number, patchValue: Partial<NavItem>) {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              children: (item.children || []).map((child, nestedIndex) =>
                nestedIndex === childIndex ? { ...child, ...patchValue } : child,
              ),
            }
          : item,
      ),
    );
  }

  async function save() {
    setError('');
    setMessage('');
    try {
      await api('/platform/navigation', {
        method: 'POST',
        body: JSON.stringify({ key, locale, items: strip(items) }),
      });
      const response = await api<{ results: NavRecord[] }>('/platform/navigation');
      onSaved(response.results || []);
      setMessage('Navigation saved and ordered visually.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Navigation save failed');
    }
  }

  return (
    <section className="panel console-panel full">
      <div className="ops-head">
        <div>
          <span className="eyebrow">Visual navigation</span>
          <h3>Menus, dropdowns & footer groups</h3>
          <p>Order links visually and add one-level dropdown children without editing JSON.</p>
        </div>
        <select
          value={selected}
          onChange={(event) => {
            const value = event.target.value;
            setSelected(value);
            if (value === 'new') {
              setKey('primary');
              setLocale('en');
              setItems([]);
            }
          }}
        >
          <option value="new">+ New menu</option>
          {records.map((record) => (
            <option key={record.id} value={record.id}>
              {record.key} · {record.locale}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <div className="console-form">
        <label>
          <span>Menu group</span>
          <select value={key} onChange={(event) => setKey(event.target.value)}>
            <option>primary</option>
            <option>footer</option>
            <option>legal</option>
            <option>social</option>
          </select>
        </label>
        <label>
          <span>Locale</span>
          <input value={locale} onChange={(event) => setLocale(event.target.value)} />
        </label>
      </div>

      <div className="nav-builder-list">
        {items.map((item, index) => (
          <article className="nav-builder-row" key={item.id}>
            <div className="nav-builder-main">
              <span className="drag-handle" aria-hidden="true">
                ⋮⋮
              </span>
              <input
                aria-label="Navigation label"
                value={item.label}
                placeholder="Label"
                onChange={(event) => patch(index, { label: event.target.value })}
              />
              <input
                aria-label="Navigation destination"
                value={item.href}
                placeholder="/path or #section"
                onChange={(event) => patch(index, { href: event.target.value })}
              />
              <label className="check">
                <input
                  type="checkbox"
                  checked={item.visible !== false}
                  onChange={(event) => patch(index, { visible: event.target.checked })}
                />
                <span>Visible</span>
              </label>
              <button className="secondary" onClick={() => move(index, -1)} disabled={index === 0}>
                ↑
              </button>
              <button
                className="secondary"
                onClick={() => move(index, 1)}
                disabled={index === items.length - 1}
              >
                ↓
              </button>
              <button
                className="secondary"
                onClick={() =>
                  patch(index, {
                    children: [
                      ...(item.children || []),
                      { id: uid(), label: '', href: '', visible: true },
                    ],
                  })
                }
              >
                + Dropdown item
              </button>
              <button
                className="secondary danger"
                onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))}
              >
                Remove
              </button>
            </div>

            {(item.children || []).map((child, childIndex) => (
              <div className="nav-builder-child" key={child.id}>
                <span aria-hidden="true">↳</span>
                <input
                  aria-label="Dropdown label"
                  value={child.label}
                  placeholder="Dropdown label"
                  onChange={(event) => childPatch(index, childIndex, { label: event.target.value })}
                />
                <input
                  aria-label="Dropdown destination"
                  value={child.href}
                  placeholder="/destination"
                  onChange={(event) => childPatch(index, childIndex, { href: event.target.value })}
                />
                <label className="check">
                  <input
                    type="checkbox"
                    checked={child.visible !== false}
                    onChange={(event) => childPatch(index, childIndex, { visible: event.target.checked })}
                  />
                  <span>Visible</span>
                </label>
                <button
                  className="secondary danger"
                  onClick={() =>
                    patch(index, {
                      children: (item.children || []).filter(
                        (_, nestedIndex) => nestedIndex !== childIndex,
                      ),
                    })
                  }
                >
                  Remove
                </button>
              </div>
            ))}
          </article>
        ))}
      </div>

      <div className="console-actions">
        <button
          className="secondary"
          onClick={() =>
            setItems((current) => [
              ...current,
              { id: uid(), label: '', href: '', visible: true },
            ])
          }
        >
          + Add navigation item
        </button>
        <button className="primary" onClick={() => void save()}>
          Save menu
        </button>
      </div>
    </section>
  );
}

export function MediaLibrary() {
  const [rows, setRows] = useState<Media[]>([]);
  const [q, setQ] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Media | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const confirm = useConfirmDialog();

  async function load() {
    setError('');
    try {
      const response = await api<{ results: Media[] }>(
        `/platform/media${q ? `?q=${encodeURIComponent(q)}` : ''}`,
      );
      setRows(response.results || []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Media load failed');
    }
  }

  useEffect(() => {
    void load();
    // Search is submitted explicitly, so q is intentionally not a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  async function preview(record: Media) {
    setError('');
    try {
      const blob = await apiBlob(`/platform/media/${record.id}/download`);
      setSelected(record);
      setPreviewUrl(URL.createObjectURL(blob));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Preview failed');
    }
  }

  async function saveMetadata(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setError('');
    setMessage('');
    const form = new FormData(event.currentTarget);
    try {
      await api(`/platform/media/${selected.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: form.get('title'),
          visibility: form.get('visibility'),
          alt_text: form.get('alt_text'),
          decorative: form.get('decorative') === 'on',
        }),
      });
      setMessage('Media metadata saved.');
      setSelected(null);
      setPreviewUrl('');
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Metadata update failed');
    }
  }

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    const form = event.currentTarget;
    try {
      await api('/platform/media', { method: 'POST', body: new FormData(form) });
      form.reset();
      setMessage('Media asset validated and saved.');
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Upload failed');
    }
  }

  async function remove(record: Media) {
    const approved = await confirm.ask(`Delete “${record.title}”? Referenced assets cannot be removed.`, {
      title: 'Delete media asset',
      danger: true,
      confirmLabel: 'Delete',
    });
    if (!approved) return;
    setError('');
    setMessage('');
    try {
      await api(`/platform/media/${record.id}`, { method: 'DELETE' });
      setMessage('Media asset deleted.');
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Delete failed');
    }
  }

  return (
    <section className="panel console-panel full">
      <span className="eyebrow">Media library</span>
      <h3>Validated reusable assets</h3>
      <p>
        Meaningful public images require alt text. Decorative images persist a distinct accessibility
        designation; private assets remain marked private.
      </p>
      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}
      <form className="console-form" onSubmit={upload}>
        <label>
          <span>Title</span>
          <input name="title" required />
        </label>
        <label>
          <span>Visibility</span>
          <select name="visibility">
            <option>private</option>
            <option>public</option>
          </select>
        </label>
        <label className="wide">
          <span>Accessible description / alt text</span>
          <input name="alt_text" placeholder="Describe the image meaningfully" />
        </label>
        <label className="check">
          <input type="checkbox" name="decorative" />
          <span>Decorative image (empty alt is correct)</span>
        </label>
        <label className="wide">
          <span>File</span>
          <input
            type="file"
            name="file"
            accept="image/png,image/jpeg,application/pdf"
            required
          />
        </label>
        <div className="console-actions">
          <button className="primary">Validate & upload</button>
        </div>
      </form>
      {selected && (
        <div className="media-preview-panel">
          <div className="media-preview-frame">
            {previewUrl && selected.mime_type.startsWith('image/') ? (
              // Blob URLs contain server-authorized bytes and never disclose private storage paths.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={previewUrl} alt={selected.decorative ? '' : selected.alt_text} />
            ) : previewUrl ? (
              <iframe src={previewUrl} title={`Preview ${selected.title}`} sandbox="" />
            ) : (
              <span>Loading preview…</span>
            )}
          </div>
          <form className="console-form" key={selected.id} onSubmit={saveMetadata}>
            <h4>Edit metadata</h4>
            <label><span>Title</span><input name="title" defaultValue={selected.title} required /></label>
            <label><span>Visibility</span><select name="visibility" defaultValue={selected.visibility}><option>private</option><option>public</option></select></label>
            <label className="wide"><span>Accessible description / alt text</span><input name="alt_text" defaultValue={selected.alt_text} /></label>
            <label className="check"><input type="checkbox" name="decorative" defaultChecked={selected.decorative} /><span>Decorative image</span></label>
            <div className="console-actions"><button className="primary">Save metadata</button><button className="secondary" type="button" onClick={() => { setSelected(null); setPreviewUrl(''); }}>Close</button></div>
          </form>
        </div>
      )}
      <div className="ops-head">
        <input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search media" />
        <button className="secondary" onClick={() => void load()}>
          Search
        </button>
      </div>
      <div className="media-grid">
        {rows.map((record) => (
          <article key={record.id}>
            <button className="media-thumb" onClick={() => void preview(record)}>{record.mime_type.startsWith('image/') ? 'Preview image' : 'Preview file'}</button>
            <b>{record.title}</b>
            <small>{record.visibility} · scan {record.scan_status || 'legacy'} · {record.file_size || 0} bytes</small>
            <small>
              {record.alt_text || (record.decorative ? 'Decorative' : 'No alt text')}
            </small>
            <div className="console-actions"><button className="secondary" onClick={() => void preview(record)}>Preview & edit</button><button className="secondary" onClick={() => void apiDownload(`/platform/media/${record.id}/download`, record.original_name || `${record.title}.bin`)}>Download</button><button className="secondary danger" onClick={() => void remove(record)}>Delete</button></div>
          </article>
        ))}
      </div>
      {confirm.dialog}
    </section>
  );
}

export function LeadFormBuilder({
  forms,
  onSaved,
}: {
  forms: LeadForm[];
  onSaved: (forms: LeadForm[]) => void;
}) {
  const [selected, setSelected] = useState('new');
  const [key, setKey] = useState('');
  const [name, setName] = useState('');
  const [routing, setRouting] = useState('');
  const [fields, setFields] = useState<EditableLeadField[]>([
    { id: uid(), name: 'name', label: 'Name', type: 'text', required: true },
    { id: uid(), name: 'email', label: 'Email', type: 'email', required: true },
  ]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const current = useMemo(() => forms.find((form) => form.id === selected), [forms, selected]);

  useEffect(() => {
    if (!current) return;
    setKey(current.key);
    setName(current.name);
    const emails = current.routing?.emails;
    setRouting(Array.isArray(emails) ? emails.filter((value): value is string => typeof value === 'string').join(', ') : '');
    setFields(
      (current.fields || []).map((field) => ({
        ...field,
        id: uid(),
        type: field.type || 'text',
        required: Boolean(field.required),
      })),
    );
  }, [current]);

  function patch(index: number, patchValue: Partial<EditableLeadField>) {
    setFields((currentFields) =>
      currentFields.map((field, fieldIndex) =>
        fieldIndex === index ? { ...field, ...patchValue } : field,
      ),
    );
  }

  async function save() {
    setError('');
    setMessage('');
    const normalizedKey = key.trim();
    const normalizedName = name.trim();
    if (!normalizedKey || !normalizedName) {
      setError('Form key and name are required.');
      return;
    }
    if (!fields.length || fields.some((field) => !field.name.trim() || !field.label.trim())) {
      setError('Add at least one field and provide a field name and label for every row.');
      return;
    }
    if (new Set(fields.map((field) => field.name.trim().toLowerCase())).size !== fields.length) {
      setError('Field names must be unique.');
      return;
    }

    try {
      await api('/platform/lead-forms', {
        method: 'POST',
        body: JSON.stringify({
          key: normalizedKey,
          name: normalizedName,
          fields: fields.map(({ id: _id, ...field }) => ({ ...field, name: field.name.trim(), label: field.label.trim() })),
          routing: {
            emails: routing
              .split(',')
              .map((value) => value.trim())
              .filter(Boolean),
          },
          is_active: true,
        }),
      });
      const response = await api<{ results: LeadForm[] }>('/platform/lead-forms');
      onSaved(response.results || []);
      setMessage('Lead form saved with field validation and routing.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Lead form save failed');
    }
  }

  return (
    <section className="panel console-panel full">
      <span className="eyebrow">Visual lead-form builder</span>
      <h3>Fields, validation & routing</h3>
      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <div className="console-form">
        <label>
          <span>Existing form</span>
          <select
            value={selected}
            onChange={(event) => {
              const value = event.target.value;
              setSelected(value);
              if (value === 'new') {
                setKey('');
                setName('');
                setRouting('');
                setFields([
                  { id: uid(), name: 'name', label: 'Name', type: 'text', required: true },
                  { id: uid(), name: 'email', label: 'Email', type: 'email', required: true },
                ]);
              }
            }}
          >
            <option value="new">+ New form</option>
            {forms.map((form) => (
              <option key={form.id} value={form.id}>
                {form.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Form key</span>
          <input value={key} onChange={(event) => setKey(event.target.value)} placeholder="demo-request" />
        </label>
        <label>
          <span>Name</span>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Request a demo" />
        </label>
        <label className="wide">
          <span>Routing emails · comma separated</span>
          <input value={routing} onChange={(event) => setRouting(event.target.value)} />
        </label>
      </div>

      <div className="field-builder">
        {fields.map((field, index) => (
          <div key={field.id}>
            <input
              aria-label="Field name"
              value={field.name}
              onChange={(event) => patch(index, { name: event.target.value })}
              placeholder="field_name"
            />
            <input
              aria-label="Field label"
              value={field.label}
              onChange={(event) => patch(index, { label: event.target.value })}
              placeholder="Label"
            />
            <select value={field.type} onChange={(event) => patch(index, { type: event.target.value })}>
              <option>text</option>
              <option>email</option>
              <option>tel</option>
              <option>textarea</option>
              <option>select</option>
              <option>checkbox</option>
            </select>
            <label className="check">
              <input
                type="checkbox"
                checked={field.required}
                onChange={(event) => patch(index, { required: event.target.checked })}
              />
              <span>Required</span>
            </label>
            <button
              className="secondary danger"
              onClick={() => setFields((currentFields) => currentFields.filter((_, fieldIndex) => fieldIndex !== index))}
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="console-actions">
        <button
          className="secondary"
          onClick={() =>
            setFields((currentFields) => [
              ...currentFields,
              { id: uid(), name: '', label: '', type: 'text', required: false },
            ])
          }
        >
          + Add field
        </button>
        <button className="primary" onClick={() => void save()}>
          Save lead form
        </button>
      </div>
    </section>
  );
}
