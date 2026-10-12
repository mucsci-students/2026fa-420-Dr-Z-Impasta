/**
 * What a page shows when it has nothing to show yet, and what to do about it. `mark` is an
 * optional decorative icon above the title, such as one from PastaMarks.jsx.
 */
export default function EmptyState({ title, mark, children, actions }) {
  return (
    <div className="empty">
      {mark && <div className="empty__mark">{mark}</div>}
      <h2 className="empty__title">{title}</h2>
      {children && <div className="empty__text">{children}</div>}
      {actions && <div className="empty__actions">{actions}</div>}
    </div>
  );
}
