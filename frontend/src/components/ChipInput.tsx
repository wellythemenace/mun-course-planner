import { useState } from "react";

interface Props {
  label: string;
  hint?: string;
  values: string[];
  onChange: (values: string[]) => void;
  suggestions: string[];
  listId: string;
  placeholder?: string;
}

export default function ChipInput({ label, hint, values, onChange, suggestions, listId, placeholder }: Props) {
  const [text, setText] = useState("");

  function add(raw: string) {
    const code = raw.trim().toUpperCase().replace(/\s+/g, " ");
    if (code && !values.includes(code)) onChange([...values, code]);
    setText("");
  }

  function handleChange(value: string) {
    // picking a suggestion from the list adds it right away
    if (suggestions.includes(value.trim().toUpperCase())) add(value);
    else setText(value);
  }

  return (
    <div className="field">
      <label>{label}</label>
      {hint && <div className="muted small">{hint}</div>}
      <div className="chips">
        {values.map((v) => (
          <span key={v} className="chip">
            {v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}>
              ×
            </button>
          </span>
        ))}
      </div>
      <input
        list={listId}
        value={text}
        placeholder={placeholder}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add(text);
          }
        }}
        onBlur={() => add(text)}
      />
      <datalist id={listId}>
        {suggestions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </div>
  );
}
