/** Pick any number of names from `options`. `value` is the list of picked names. */
export default function CheckboxList({ legend, options, value, onChange, empty = "None to choose from", error, fieldName = "", localErr = "" }) {

	console.log(localErr);

  function toggle(name) {
    if (value.includes(name)) {
      onChange(value.filter((v) => v !== name));
    } else {
      onChange([...value, name]);
    }
  }

	/** A function to assign the input field the 'input-error' class if it contains invalid data */
	function classNameFunc(field) {
	        if(localError.some((err) => err.field === field)) {
			return "input-error";
		} else {
			return "";
		}
	}

  return (
    <fieldset className="checkbox-list">
      <legend>{legend}</legend>
      {options.length === 0 && <span className="muted">{empty}</span>}
      {options.map((name) => (
        <label key={name} className="checkbox">
          <input type="checkbox" checked={value.includes(name)} onChange={() => toggle(name)} />
          {name}
        </label>
      ))}
      {error || localErr && (
        <p className="field__error">
          <span aria-hidden="true">⚠ </span>
          {localErr}
        </p>
      )}
    </fieldset>
  );
}
