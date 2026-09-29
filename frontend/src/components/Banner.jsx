const ROLE = { danger: "alert", warning: "alert" };

/**
 * A message across the page or a section: `tone` is "info", "success", "warning", or
 * "danger". `title` is read first ("Valid.", "Couldn't save."), so the message never
 * depends on color alone.
 */
export default function Banner({ tone = "info", title, children, actions, onDismiss }) {
  return (
    <div className={`banner banner--${tone}`} role={ROLE[tone] ?? "status"}>
      <div className="banner__text">
        {title && <strong className="banner__title">{title}</strong>} {children}
      </div>
      {actions && <div className="banner__actions">{actions}</div>}
      {onDismiss && (
        <button type="button" className="banner__close" aria-label="Dismiss" onClick={onDismiss}>
          ×
        </button>
      )}
    </div>
  );
}
