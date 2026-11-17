/**
 * One reusable card row: a section title with a count, optional header buttons, then a dashed
 * "+ Add X" tile and the cards. Rows scroll sideways by default; `grid` wraps cards into
 * columns and scrolls vertically after the configured number of rows.
 */

import { Children, useEffect, useRef, useState } from "react";
import Button from "../../../components/Button.jsx";

/**
 * One section of the editor: a title row, then a dashed "Add" tile and the item cards.
 *
 * - `title`: the section heading, e.g. "Faculty".
 * - `meta`: shown next to the title, such as a count ("12") or a summary ("3 of 5 enabled").
 * - `addLabel` / `onAdd`: the "Add" tile's text and click handler. Leave out `onAdd` for a
 *   section you can't add to (Time Slots), and the tile isn't shown.
 * - `actions`: buttons on the right of the title row.
 * - `grid`: wrap the cards into columns instead of scrolling sideways.
 * - `visibleRows`: how many complete grid rows to show before vertical scrolling.
 * - `gridColumns`: maximum number of columns in the grid.
 * - `children`: the cards. Each one should be a single element so horizontal rows can watch
 *   and fade each direct child.
 *
 * Horizontal rows scroll sideways and snap to each card's left edge. Any tile only partly in
 * view is marked `data-partial` and faded out (see editor.css), so only whole cards show.
 * The ‹ › buttons in the title row scroll one page of whole cards at a time.
 */
export default function CardRow({
  title,
  meta,
  addLabel,
  onAdd,
  actions,
  grid = false,
  visibleRows = 2,
  gridColumns = 5,
  children,
}) {
  const rowRef = useRef(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);
  const [columnCount, setColumnCount] = useState(gridColumns);
  const hasAdd = Boolean(onAdd);

  // Watch every tile against the row's visible area. Fading a tile doesn't move anything,
  // so this only reacts to scrolling and resizing. Runs again when the cards change so new
  // ones are watched too.
  useEffect(() => {
    if (grid) return;
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
  }, [children, grid]);

  // Turn each arrow off when the row is already scrolled all the way to that side.
  useEffect(() => {
    if (grid) return;
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
  }, [children, grid]);

  useEffect(() => {
    if (!grid) return;
    const row = rowRef.current;
    const updateColumns = () => {
      const width = row.clientWidth;
      const gap = parseFloat(getComputedStyle(row).columnGap) || 0;
      const cardWidth = 190;
      const count = hasAdd
        ? Math.floor((width - 100 - gap) / (cardWidth + gap)) + 1
        : Math.floor((width + gap) / (cardWidth + gap));
      const next = Math.max(1, Math.min(gridColumns, count));
      setColumnCount((current) => current === next ? current : next);
    };
    const resize = new ResizeObserver(updateColumns);
    resize.observe(row);
    return () => resize.disconnect();
  }, [grid, gridColumns, hasAdd]);

  useEffect(() => {
    const row = rowRef.current;
    if (!grid) {
      row.style.maxHeight = "";
      return;
    }
    const fitVisibleRows = () => {
      const tiles = [...row.children];
      if (!tiles.length) return;
      const rowTops = [...new Set(tiles.map((tile) => tile.offsetTop))].slice(0, visibleRows);
      const visibleBottom = Math.max(
        ...tiles
          .filter((tile) => rowTops.includes(tile.offsetTop))
          .map((tile) => tile.offsetTop + tile.offsetHeight)
      );
      const paddingBottom = parseFloat(getComputedStyle(row).paddingBottom) || 0;
      const maxHeight = `${visibleBottom + paddingBottom}px`;
      if (row.style.maxHeight !== maxHeight) {
        const scrollTop = row.scrollTop;
        row.style.maxHeight = maxHeight;
        row.scrollTop = scrollTop;
      }
    };
    const resize = new ResizeObserver(fitVisibleRows);
    resize.observe(row);
    for (const tile of row.children) resize.observe(tile);
    fitVisibleRows();
    return () => resize.disconnect();
  }, [children, columnCount, grid, hasAdd, visibleRows]);

  const gridRows = [];
  if (grid) {
    const cards = Children.toArray(children);
    let index = 0;
    if (hasAdd) {
      gridRows.push(cards.slice(0, columnCount - 1));
      index = columnCount - 1;
    }
    while (index < cards.length) {
      gridRows.push(cards.slice(index, index + columnCount));
      index += columnCount;
    }
  }

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
          {!grid && (canLeft || canRight) && (
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
      <div className={`editor-row__items${grid ? " editor-row__items--grid" : ""}`} ref={rowRef}>
        {grid
          ? gridRows.map((cards, index) => {
              const addTileRow = hasAdd && index === 0;
              const columns = addTileRow
                ? columnCount === 1
                  ? "100px"
                  : `100px repeat(${columnCount - 1}, minmax(0, 1fr))`
                : `repeat(${columnCount}, minmax(0, 1fr))`;
              return (
                <div className="editor-row__grid-line" style={{ gridTemplateColumns: columns }} key={index}>
                  {addTileRow && (
                    <button type="button" className="editor-row__add" onClick={onAdd}>
                      <span aria-hidden="true">+</span> {addLabel}
                    </button>
                  )}
                  {cards}
                </div>
              );
            })
          : (
              <>
                {onAdd && (
                  <button type="button" className="editor-row__add" onClick={onAdd}>
                    <span aria-hidden="true">+</span> {addLabel}
                  </button>
                )}
                {children}
              </>
            )}
      </div>
    </section>
  );
}
