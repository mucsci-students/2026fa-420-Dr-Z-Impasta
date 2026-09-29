/** A bordered section with an optional title row (title, meta text, and actions). */
export default function Card({ title, meta, actions, footer, className = "", children, ...rest }) {
  return (
    <section className={`card ${className}`} {...rest}>
      {(title || actions) && (
        <header className="card__header">
          <div className="card__heading">
            {title && <h2 className="card__title">{title}</h2>}
            {meta && <span className="card__meta">{meta}</span>}
          </div>
          {actions && <div className="card__actions">{actions}</div>}
        </header>
      )}
      <div className="card__body">{children}</div>
      {footer && <footer className="card__footer">{footer}</footer>}
    </section>
  );
}
