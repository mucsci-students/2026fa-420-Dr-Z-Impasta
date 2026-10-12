import { useId, useState } from "react";

/** A small "?" that explains a control, on hover, on focus, or when tapped. */
export default function HelpTip({ text }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="help-tip">
      <button
        type="button"
        className="help-tip__button"
        aria-label="Help"
        aria-describedby={id}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onBlur={() => setOpen(false)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        ?
      </button>
      <span id={id} role="tooltip" className="help-tip__text" hidden={!open}>
        {text}
      </span>
    </span>
  );
}
