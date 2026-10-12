import assert from 'node:assert/strict';
import test from 'node:test';
import { posteriorProfiles, profileCsv } from '../utils/posteriorProfiles.ts';

// Rows sum to .20, .16 and .64. The global peak is outside both selected slices.
const rectangularPosterior = [
  [.02, .04, .06, .08],
  [.01, .03, .05, .07],
  [.09, .11, .14, .30],
];

test('linked slices retain exact cell masses and the shared global peak, without marginalizing or renormalizing', () => {
  const result = posteriorProfiles(rectangularPosterior, { row: 0, column: 1 }, 1200, 300)!;
  assert.equal(result.rows, 3);
  assert.equal(result.columns, 4);
  assert.equal(result.probability, .04);
  assert.equal(result.peak, .30);
  assert.deepEqual(result.horizontal.map(point => point.probability), [.02, .04, .06, .08]);
  assert.deepEqual(result.vertical.map(point => point.probability), [.04, .03, .11]);
  assert.ok(Math.abs(result.horizontal.reduce((sum, point) => sum + point.probability, 0) - .20) < 1e-12);
  assert.ok(Math.abs(result.vertical.reduce((sum, point) => sum + point.probability, 0) - .18) < 1e-12);
  assert.ok(result.peak > Math.max(...result.horizontal.map(point => point.probability)));
  assert.ok(result.peak > Math.max(...result.vertical.map(point => point.probability)));
});

test('rectangular grids use physical cell centers independently for each panel extent', () => {
  const result = posteriorProfiles(rectangularPosterior, { row: 0, column: 1 }, 1200, 300)!;
  assert.equal(result.xMm, 450);
  assert.equal(result.yMm, 50);
  assert.deepEqual(result.horizontal.map(point => point.coordinateMm), [150, 450, 750, 1050]);
  assert.deepEqual(result.vertical.map(point => point.coordinateMm), [50, 150, 250]);

  const portrait = posteriorProfiles(rectangularPosterior, { row: 2, column: 3 }, 80, 900)!;
  assert.equal(portrait.xMm, 70);
  assert.equal(portrait.yMm, 750);
  assert.deepEqual(portrait.horizontal.map(point => point.coordinateMm), [10, 30, 50, 70]);
  assert.deepEqual(portrait.vertical.map(point => point.coordinateMm), [150, 450, 750]);

  const singleCell = posteriorProfiles([[1]], { row: 0, column: 0 }, 600, 400)!;
  assert.deepEqual(singleCell.horizontal, [{ coordinateMm: 300, probability: 1 }]);
  assert.deepEqual(singleCell.vertical, [{ coordinateMm: 200, probability: 1 }]);
  assert.equal(singleCell.peak, 1);
});

test('profile extraction and CSV generation leave the stored posterior and selection unchanged', () => {
  const grid = rectangularPosterior.map(row => [...row]);
  const cell = { row: 0, column: 1 };
  grid.forEach(Object.freeze);
  Object.freeze(grid);
  Object.freeze(cell);
  const before = JSON.stringify({ grid, cell });
  const result = posteriorProfiles(grid, cell, 1200, 300)!;
  const outputBefore = JSON.stringify(result);
  profileCsv(result);
  assert.equal(JSON.stringify(result), outputBefore);
  result.horizontal[0].probability = .99;
  result.vertical[0].coordinateMm = -1;
  assert.equal(JSON.stringify({ grid, cell }), before);
});

test('invalid distributions cannot produce convincing slice plots', () => {
  const invalid: number[][][] = [
    [], [[]], [[.5], [.25, .25]], [[NaN, 1]], [[Infinity, 0]],
    [[-.1, 1.1]], [[0, 0]], [[.6, .6]], [[.2, .2]], [[1.0001]],
  ];
  for (const grid of invalid) assert.equal(posteriorProfiles(grid, { row: 0, column: 0 }, 600, 400), null);
  assert.equal(posteriorProfiles(Array.from({ length: 257 }, () => Array(256).fill(1 / (257 * 256))), { row: 0, column: 0 }, 600, 400), null);
});

test('malformed runtime shapes and sparse arrays are rejected rather than silently dropping missing cells', () => {
  const sparseRow = new Array<number>(3);
  sparseRow[0] = .5;
  sparseRow[2] = .5;
  const sparseGrid = new Array<number[]>(3);
  sparseGrid[0] = [.5];
  sparseGrid[2] = [.5];
  const malformed: unknown[] = [
    null, undefined, {}, 1, [null], [[1], null], [[1], {}],
    [[null, 1]], [['0', 1]], [sparseRow], sparseGrid,
  ];
  for (const grid of malformed) {
    assert.equal(posteriorProfiles(grid as number[][], { row: 0, column: 0 }, 600, 400), null);
  }
  assert.equal(posteriorProfiles([[1]], null as unknown as { row: number; column: number }, 600, 400), null);
});

test('invalid selected cells and physical dimensions are rejected without clamping', () => {
  for (const cell of [
    { row: -1, column: 0 }, { row: 3, column: 0 }, { row: 0, column: -1 }, { row: 0, column: 4 },
    { row: .5, column: 0 }, { row: 0, column: 1.5 }, { row: NaN, column: 0 }, { row: 0, column: Infinity },
  ]) assert.equal(posteriorProfiles(rectangularPosterior, cell, 1200, 300), null);
  for (const value of [0, -1, NaN, Infinity, -Infinity]) {
    assert.equal(posteriorProfiles(rectangularPosterior, { row: 0, column: 1 }, value, 300), null);
    assert.equal(posteriorProfiles(rectangularPosterior, { row: 0, column: 1 }, 1200, value), null);
  }
});

test('CSV exports both exact slices with correct fixed-axis coordinates and cell mass units', () => {
  const result = posteriorProfiles(rectangularPosterior, { row: 0, column: 1 }, 1200, 300)!;
  assert.equal(profileCsv(result), [
    'slice,x_mm,y_mm,cell_probability_mass',
    'horizontal,150,50,0.02',
    'horizontal,450,50,0.04',
    'horizontal,750,50,0.06',
    'horizontal,1050,50,0.08',
    'vertical,450,50,0.04',
    'vertical,450,150,0.03',
    'vertical,450,250,0.11',
    '',
  ].join('\n'));
});
