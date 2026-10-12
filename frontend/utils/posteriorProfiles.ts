import type { GridCell } from './heatmapGeometry.ts';

/** Exact, unnormalised row and column slices; never conditional distributions. */
export function posteriorProfiles(grid: number[][], cell: GridCell, widthMm: number, heightMm: number) {
  if (!Array.isArray(grid) || !Array.isArray(grid[0]) || !cell) return null;
  const rows = grid.length, columns = grid[0]?.length ?? 0;
  if (!rows || !columns || rows * columns > 65536
    || ![widthMm, heightMm].every(value => Number.isFinite(value) && value > 0)
    || !Number.isInteger(cell.row) || !Number.isInteger(cell.column)
    || cell.row < 0 || cell.row >= rows || cell.column < 0 || cell.column >= columns
    || Array.from(grid).some(row => !Array.isArray(row) || row.length !== columns || Array.from(row).some(value => !Number.isFinite(value) || value < 0 || value > 1))) return null;
  const values = grid.flat(), total = values.reduce((sum, p) => sum + p, 0);
  if (Math.abs(total - 1) > 1e-6) return null;
  const xMm = (cell.column + .5) / columns * widthMm;
  const yMm = (cell.row + .5) / rows * heightMm;
  return {
    rows, columns, xMm, yMm, probability: grid[cell.row][cell.column], peak: Math.max(...values),
    horizontal: grid[cell.row].map((probability, index) => ({ coordinateMm: (index + .5) / columns * widthMm, probability })),
    vertical: grid.map((row, index) => ({ coordinateMm: (index + .5) / rows * heightMm, probability: row[cell.column] })),
  };
}

export function profileCsv(profiles: NonNullable<ReturnType<typeof posteriorProfiles>>) {
  const rows = ['slice,x_mm,y_mm,cell_probability_mass'];
  for (const point of profiles.horizontal) rows.push(['horizontal', point.coordinateMm, profiles.yMm, point.probability].join(','));
  for (const point of profiles.vertical) rows.push(['vertical', profiles.xMm, point.coordinateMm, point.probability].join(','));
  return rows.join('\n') + '\n';
}
