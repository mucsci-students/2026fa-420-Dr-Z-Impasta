export function getGridColumnCount(width, gap, hasAdd, maxColumns) {
  const cardWidth = 190;
  const addWidth = 100;
  const count = hasAdd
    ? Math.floor((width - addWidth - gap) / (cardWidth + gap)) + 1
    : Math.floor((width + gap) / (cardWidth + gap));
  return Math.max(1, Math.min(maxColumns, count));
}

export function buildGridRows(cards, columnCount, hasAdd) {
  const rows = [];
  let index = 0;
  if (hasAdd) {
    rows.push({ hasAdd: true, cards: cards.slice(0, columnCount - 1) });
    index = columnCount - 1;
  }
  while (index < cards.length) {
    rows.push({ hasAdd: false, cards: cards.slice(index, index + columnCount) });
    index += columnCount;
  }
  return rows;
}

export function getVisibleGridHeight(tiles, visibleRows, paddingBottom) {
  const rowTops = [...new Set(tiles.map((tile) => tile.offsetTop))].slice(0, visibleRows);
  const visibleBottom = Math.max(
    0,
    ...tiles
      .filter((tile) => rowTops.includes(tile.offsetTop))
      .map((tile) => tile.offsetTop + tile.offsetHeight)
  );
  return visibleBottom + paddingBottom;
}

export function getGridTemplateColumns(columnCount, hasAdd, addWidth = 100) {
  if (hasAdd) {
    return columnCount === 1
      ? `${addWidth}px`
      : `${addWidth}px repeat(${columnCount - 1}, minmax(0, 1fr))`;
  }
  return `repeat(${columnCount}, minmax(0, 1fr))`;
}
