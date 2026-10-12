/**
 * Pick one of a few options, like "Room & lab | Faculty" in the viewer:
 *
 *   <SegmentedControl label="Group by" value={group} onChange={setGroup}
 *     options={[{ value: "room", label: "Room & lab" }, { value: "faculty", label: "Faculty" }]} />
 */
export default function SegmentedControl({ label, options, value, onChange }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {label && <span className="segmented__label">{label}</span>}
      <div className="segmented__options">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className="segmented__option"
            aria-pressed={option.value === value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
