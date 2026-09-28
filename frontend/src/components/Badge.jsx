/** A short label. `tone`: "neutral", "info", "success", "warning", or "danger". */
export default function Badge({ tone = "neutral", children }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}
