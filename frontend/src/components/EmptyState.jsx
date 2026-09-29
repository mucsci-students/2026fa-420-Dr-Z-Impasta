/** What a page shows when it has nothing to show yet, and what to do about it. */
export default function EmptyState({ title, children, actions }) {
  return (
    <div className="empty">
      <h2 className="empty__title">{title}</h2>
      {children && <div className="empty__text">{children}</div>}
      {actions && <div className="empty__actions">{actions}</div>}
    </div>
  );
}
