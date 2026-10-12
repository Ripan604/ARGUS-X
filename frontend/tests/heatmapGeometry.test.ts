import assert from 'node:assert/strict';
import test from 'node:test';
import { gridCellAt, inspectGridCell, moveInspectionCell, panelMapGeometry, panelPointAt, restrictedRectangle } from '../utils/heatmapGeometry.ts';

test('map drawing preserves physical aspect for wide, tall, and square panels', () => {
  for (const [width, height] of [[.6, .4], [.1, 5], [5, .1], [1, 1]]) {
    const g = panelMapGeometry(width, height);
    assert.ok(g.width <= 900 && g.height <= 650);
    assert.ok(Math.abs(g.fieldWidth / g.fieldHeight - width / height) < 1e-10);
    assert.equal(g.widthMm, width * 1000);
    assert.equal(g.heightMm, height * 1000);
  }
  for (const dimensions of [[0, 1], [1, Infinity], [-1, 1]]) assert.throws(() => panelMapGeometry(...dimensions as [number, number]), RangeError);
});

test('pointer geometry excludes axis margins and clamps only explicit edit endpoints', () => {
  const g = panelMapGeometry(.6, .4);
  assert.deepEqual(panelPointAt(g.left, g.top, g), { x: 0, y: 0 });
  assert.deepEqual(panelPointAt(g.left + g.fieldWidth, g.top + g.fieldHeight, g), { x: 1, y: 1 });
  assert.equal(panelPointAt(g.left - 1, g.top, g), null);
  assert.equal(panelPointAt(NaN, 0, g), null);
  assert.deepEqual(panelPointAt(g.left - 20, g.top + g.fieldHeight + 20, g, true), { x: 0, y: 1 });
  assert.deepEqual(gridCellAt({ x: 1, y: 1 }, 3, 4), { row: 2, column: 3 });
  assert.equal(gridCellAt({ x: 1.01, y: .5 }, 3, 4), null);
});

test('inspection reports exact cell mass and physical cell centre without changing the grid', () => {
  const grid = [[.1, .2], [.3, .4]], before = JSON.stringify(grid);
  const cell = inspectGridCell(grid, { row: 1, column: 0 }, .6, .4);
  assert.ok(cell);
  assert.deepEqual({ row: cell.row, column: cell.column, x: cell.x, y: cell.y, probability: cell.probability }, { row: 1, column: 0, x: .25, y: .75, probability: .3 });
  assert.ok(Math.abs(cell.xMm - 150) < 1e-9);
  assert.ok(Math.abs(cell.yMm - 300) < 1e-9);
  assert.equal(JSON.stringify(grid), before);
  assert.equal(inspectGridCell([[NaN]], { row: 0, column: 0 }, 1, 1), null);
  assert.equal(inspectGridCell([[.2], [.4, .4]], { row: 0, column: 0 }, 1, 1), null);
  assert.equal(inspectGridCell(grid, { row: 2, column: 0 }, .6, .4), null);
});

test('keyboard movement stays inside rectangular grids and uses the upper-left origin', () => {
  assert.deepEqual(moveInspectionCell({ row: 0, column: 0 }, 'ArrowLeft', 2, 3), { row: 0, column: 0 });
  assert.deepEqual(moveInspectionCell({ row: 0, column: 1 }, 'ArrowDown', 2, 3), { row: 1, column: 1 });
  assert.deepEqual(moveInspectionCell({ row: 1, column: 1 }, 'Home', 2, 3), { row: 0, column: 0 });
  assert.deepEqual(moveInspectionCell({ row: 0, column: 0 }, 'End', 2, 3), { row: 1, column: 2 });
  assert.equal(moveInspectionCell({ row: 0, column: 0 }, 'Enter', 2, 3), null);
});

test('rectangle editing accepts either drag direction and refuses tiny or invalid regions', () => {
  assert.deepEqual(restrictedRectangle({ x: .8, y: .7 }, { x: .2, y: .3 }, 2), { x_min: .2, y_min: .3, x_max: .8, y_max: .7, label: 'no-go 3' });
  assert.equal(restrictedRectangle({ x: .2, y: .3 }, { x: .21, y: .7 }, 0), null);
  assert.equal(restrictedRectangle({ x: NaN, y: .3 }, { x: .8, y: .7 }, 0), null);
  assert.equal(restrictedRectangle({ x: .2, y: .3 }, { x: 1.2, y: .7 }, 0), null);
});
