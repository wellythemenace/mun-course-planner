import { useEffect, useMemo, useRef, useState } from "react";

export interface Option {
  value: string;
  label: string;
  group?: string;
}

interface Props {
  label: string;
  hint?: string;
  options: Option[];
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  searchable?: boolean;
  showChips?: boolean;
}

// A dropdown where you tick boxes. It stays open while you tick, so you can pick many at once.
export default function CheckboxDropdown({
  label, hint, options, values, onChange, placeholder = "Select…", searchable = true, showChips = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter((o) => (o.value + " " + o.label).toLowerCase().includes(q)) : options;
  }, [options, query]);

  const grouped = useMemo(() => {
    const map = new Map<string, Option[]>();
    for (const o of shown) map.set(o.group ?? "", [...(map.get(o.group ?? "") ?? []), o]);
    return [...map.entries()];
  }, [shown]);

  // keep the selection in the same order as the options list
  function commit(selected: Set<string>) {
    const known = options.map((o) => o.value).filter((v) => selected.has(v));
    const extra = [...selected].filter((v) => !options.some((o) => o.value === v));
    onChange([...known, ...extra]);
  }

  function toggle(value: string) {
    const next = new Set(values);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    commit(next);
  }

  const names = new Map(options.map((o) => [o.value, o.label]));
  let summary: string;
  if (values.length === 0) summary = placeholder;
  else if (!showChips && values.length <= 3) summary = values.map((v) => names.get(v) ?? v).join(", ");
  else summary = `${values.length} selected`;

  return (
    <div className="field" ref={ref}>
      <label>{label}</label>
      {hint && <div className="muted small">{hint}</div>}
      <div className="dd">
        <button type="button" className="dd-button" aria-haspopup="listbox" aria-expanded={open}
          onClick={() => setOpen(!open)}>
          <span className={values.length === 0 ? "muted" : ""}>{summary}</span>
          <span aria-hidden="true">▾</span>
        </button>
        {open && (
          <div className="dd-panel">
            {searchable && (
              <input autoFocus placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
            )}
            <div className="dd-actions">
              <button type="button" onClick={() => commit(new Set([...values, ...shown.map((o) => o.value)]))}>
                Select all shown
              </button>
              <button type="button" onClick={() => onChange([])}>Clear</button>
              <button type="button" className="primary" onClick={() => setOpen(false)}>Done</button>
            </div>
            <div className="dd-list">
              {shown.length === 0 && <div className="muted small">Nothing matches.</div>}
              {grouped.map(([group, items]) => (
                <div key={group}>
                  {group && <div className="dd-group">{group}</div>}
                  {items.map((o) => (
                    <label key={o.value} className="dd-option">
                      <input type="checkbox" checked={values.includes(o.value)} onChange={() => toggle(o.value)} />
                      {o.label}
                    </label>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      {showChips && values.length > 0 && (
        <div className="chips">
          {values.map((v) => (
            <span key={v} className="chip">
              {v}
              <button type="button" aria-label={`Remove ${v}`} onClick={() => toggle(v)}>×</button>
            </span>
          ))}
          <button type="button" className="clear-btn" onClick={() => onChange([])}>Clear all</button>
        </div>
      )}
    </div>
  );
}
