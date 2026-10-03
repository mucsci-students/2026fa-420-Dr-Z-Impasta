import Button from "../../components/Button.jsx";

/**
 * Name → score pairs, such as { "CMSC 362": 5, "CMSC 161": 4 }. `options` are the names that
 * can be added; a name already in `value` stays selectable even if it isn't in `options`.
 * Each name appears once, so a row's dropdown offers only names no other row uses.
 */
export default function PreferenceEditor({ legend, options, value, onChange, addLabel = "+ Add", error }) {
  const rows = Object.entries(value); // [["CMSC 362", 5], ["CMSC 161", 4]]
  const used = rows.map(([name]) => name);
  const unused = options.filter((name) => !used.includes(name));

  /** Save a new list of rows back as an object. */
  function update(nextRows) {
    onChange(Object.fromEntries(nextRows));
  }

  return (
    <fieldset className="pref-editor">
      <legend>{legend}</legend>
      {rows.length === 0 && <span className="muted">None</span>}
      {rows.map(([name, score], i) => (
        <div key={i} className="pref-editor__row">
          <select
            aria-label={`${legend} ${i + 1}`}
            value={name}
            onChange={(e) => update(rows.map((row, j) => (j === i ? [e.target.value, row[1]] : row)))}
          >
            {[name, ...unused].map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            max={10}
            aria-label={`Score for ${name}`}
            value={score ?? ""}
            onChange={(e) =>
              update(rows.map((row, j) => (j === i ? [row[0], e.target.value === "" ? null : Number(e.target.value)] : row)))
            }
          />
          <button
            type="button"
            className="pref-editor__remove"
            aria-label={`Remove ${name}`}
            onClick={() => update(rows.filter((_, j) => j !== i))}
          >
            ×
          </button>
        </div>
      ))}
      <div>
        <Button size="sm" variant="ghost" disabled={unused.length === 0} onClick={() => update([...rows, [unused[0], 5]])}>
          {addLabel}
        </Button>
      </div>
      {error && (
        <p className="field__error">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </fieldset>
  );
}
