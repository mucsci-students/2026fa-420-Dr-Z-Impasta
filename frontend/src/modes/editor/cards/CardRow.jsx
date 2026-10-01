// Description: One reusable horizontal row: a section title with a count and ? help icon,
// the scroll buttons, a dashed "+ Add X tile", then the cards. Used by Faculty, Courses,
// Rooms, Labs, and Class Patterns.
//
// Applies to All Cards: Hide what isn't set. Most of the new fields are empty in sample_config.json.
// Showing a line like "Room features" only when it has values keeps the cards close to the mockup
// with real data. For true/false fields such as "Lab uses room", show them only when they differ
// from the default (reserve_room_during_lab defaults to true). Show text, not just color. For
// badges like "Online" and "Hybrid", use the word itself, not only a colored dot. Color alone
// isn't enough. The dialogs need every field. That includes the scores for all three preference
// lists, per-meeting start_time and delivery, and both timing options in TimingDialog.jsx.

/** One section of the editor: a title row, then a dashed "Add" tile and the item cards. */
export default function CardRow({ title, meta, addLabel, onAdd, children }) {
  return (
    <section className="editor-row">
      <header className="editor-row__header">
        <h2 className="editor-row__title">{title}</h2>
        <span className="editor-row__meta">{meta}</span>
      </header>
      <div className="editor-row__items">
        <button type="button" className="editor-row__add" onClick={onAdd}>
        <span aria-hidden="true">+</span> {addLabel}
        </button>
        {children}
      </div>
    </section>
  );
}
