import { useState } from "react";

/** A list of short tags (e.g. features): chips with ×, plus a box to type a new one. */
export default function TagInput({ value, onChange, suggestions = [], placeholder = "Type and press Enter", ...inputProps }) {
  const [text, setText] = useState("");
  const listId = `${inputProps.id}-suggestions`;

  function add() {
    const tag = text.trim();
    setText("");
    if (tag === "" || value.includes(tag)) return;
    onChange([...value, tag]);
  }

  function remove(tag) {
    onChange(value.filter((t) => t !== tag));
  }

  return (
    <div className="tag-input">
      {value.map((tag) => (
        <span key={tag} className="tag-input__chip">
          {tag}
          <button type="button" aria-label={`Remove ${tag}`} onClick={() => remove(tag)}>
            ×
          </button>
        </span>
      ))}
      <input
        {...inputProps}
        value={text}
        list={listId}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
      />
      <datalist id={listId}>
        {suggestions.filter((s) => !value.includes(s)).map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </div>
  );
}
