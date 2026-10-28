/**
 * One reusable horizontal row: a section title with a count, optional header
 * buttons, then a sideways-scrolling strip with a dashed "+ Add X" tile and the cards. Cards
 * only partly in view are faded out, so the row only ever shows whole cards. Used by Faculty,
 * Courses, Rooms, Labs, Class Patterns, Time Slots, and Global Settings.
 */

import { useEffect, useRef, useState } from "react";
import Button from "../../../components/Button.jsx";

/**
 * One section of the editor: a title row, then a dashed "Add" tile and the item cards.
 *
 * - `title`: the section heading, e.g. "Faculty".
 * - `meta`: shown next to the title, such as a count ("12") or a summary ("3 of 5 enabled").
 * - `addLabel` / `onAdd`: the "Add" tile's text and click handler. Leave out `onAdd` for a
 *   section you can't add to (Time Slots), and the tile isn't shown.
 * - `actions`: buttons on the right of the title row.
 * - `children`: the cards. Each one should be a single element, since each direct child of
 *   the row is watched and faded on its own.
 *
 * The row scrolls sideways and snaps to each card's left edge. Any tile only partly in
 * view is marked `data-partial` and faded out (see editor.css), so only whole cards show.
 * The ‹ › buttons in the title row scroll one page of whole cards at a time.
 */
export default function CardRow({ title, meta, addLabel, onAdd, actions, children }) {
  const rowRef = useRef(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  // Watch every tile against the row's visible area. Fading a tile doesn't move anything,
  // so this only reacts to scrolling and resizing. Runs again when the cards change so new
  // ones are watched too.
  useEffect(() => {
    const row = rowRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          // 0.99, not 1: fractional pixel widths can keep a whole card just under 1
          entry.target.toggleAttribute("data-partial", entry.intersectionRatio < 0.99);
        }
      },
      { root: row, threshold: [0, 0.99] }
    );
    for (const tile of row.children) observer.observe(tile);
    return () => observer.disconnect();
  }, [children]);

  // Turn each arrow off when the row is already scrolled all the way to that side.
  useEffect(() => {
    const row = rowRef.current;
    const update = () => {
      setCanLeft(row.scrollLeft > 0);
      setCanRight(row.scrollLeft + row.clientWidth < row.scrollWidth - 1); // -1 for fractional pixels
    };
    update();
    row.addEventListener("scroll", update);
    const resize = new ResizeObserver(update);
    resize.observe(row);
    return () => {
      row.removeEventListener("scroll", update);
      resize.disconnect();
    };
  }, [children]);

  /**
   * Scroll one page of whole cards: right (`dir` 1) or left (`dir` -1). The target card is
   * picked here rather than scrolling by the row's width, because snapping to the nearest
   * card edge could otherwise skip the card that was cut off.
   */
  function page(dir) {
    const row = rowRef.current;
    const tiles = [...row.children];
    const start = row.scrollLeft;
    const end = start + row.clientWidth;
    const target =
      dir > 0
        ? tiles.find((t) => t.offsetLeft + t.offsetWidth > end + 1) // first card cut off on the right
        : tiles.find((t) => t.offsetLeft >= start - row.clientWidth - 1); // first card of the previous page
    if (target) row.scrollTo({ left: target.offsetLeft, behavior: "smooth" });
  }

  return (
    <section className="editor-row">
      <header className="editor-row__header">
        <h2 className="editor-row__title">{title}</h2>
        <span className="editor-row__meta">{meta}</span>
        <div className="editor-row__actions">
          {actions}
          {(canLeft || canRight) && (
            <>
              <Button style={{ visibility: canLeft ? "visible" : "hidden" }} onClick={() => page(-1)} aria-label={`Scroll ${title} left`}>
                ‹
              </Button>
              <Button style={{ visibility: canRight ? "visible" : "hidden" }} onClick={() => page(1)} aria-label={`Scroll ${title} right`}>
                ›
              </Button>
            </>
          )}
        </div>
      </header>
      <div className="editor-row__items" ref={rowRef}>
        {onAdd && (
          <button type="button" className="editor-row__add" onClick={onAdd}>
            <span aria-hidden="true">+</span> {addLabel}
          </button>
        )}
        {children}
      </div>
    </section>
  );
}
