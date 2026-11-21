import assert from "node:assert/strict";
import test from "node:test";
import {
  buildGridRows,
  getGridColumnCount,
  getGridTemplateColumns,
  getVisibleGridHeight,
} from "../frontend/src/modes/editor/cards/gridLayout.js";

test("grid column count stays within available width and its configured maximum", () => {
  assert.equal(getGridColumnCount(1100, 12, true, 5), 5);
  assert.equal(getGridColumnCount(470, 12, true, 5), 2);
  assert.equal(getGridColumnCount(150, 12, true, 5), 1);
  assert.equal(getGridColumnCount(1100, 12, false, 1), 1);
});

test("the add tile only narrows the first row, not subsequent card rows", () => {
  const cards = ["Rogers", "Wertz", "Hobbs", "Yang", "Schwartz", "Zoppetti"];
  const rows = buildGridRows(cards, 5, true);

  assert.deepEqual(rows, [
    { hasAdd: true, cards: ["Rogers", "Wertz", "Hobbs", "Yang"] },
    { hasAdd: false, cards: ["Schwartz", "Zoppetti"] },
  ]);
  assert.equal(getGridTemplateColumns(5, rows[0].hasAdd), "100px repeat(4, minmax(0, 1fr))");
  assert.equal(getGridTemplateColumns(5, rows[1].hasAdd), "repeat(5, minmax(0, 1fr))");
});

test("grid rows contain the requested number of cards, with no add tile", () => {
  assert.deepEqual(buildGridRows(["A", "B", "C", "D", "E"], 2, false), [
    { hasAdd: false, cards: ["A", "B"] },
    { hasAdd: false, cards: ["C", "D"] },
    { hasAdd: false, cards: ["E"] },
  ]);
});

test("visible grid height includes only the selected complete rows and bottom padding", () => {
  const tiles = [
    { offsetTop: 0, offsetHeight: 160 },
    { offsetTop: 0, offsetHeight: 190 },
    { offsetTop: 202, offsetHeight: 170 },
  ];

  assert.equal(getVisibleGridHeight(tiles, 1, 12), 202);
  assert.equal(getVisibleGridHeight(tiles, 2, 12), 384);
  assert.equal(getVisibleGridHeight([], 1, 12), 12);
});
