/** Geometry for inspecting a discrete posterior on a physical rectangle. */
export interface PanelMapGeometry {
  width: number; height: number; left: number; top: number; fieldWidth: number; fieldHeight: number;
  widthMm: number; heightMm: number;
}
export interface PanelPoint { x: number; y: number }
export interface GridCell { row: number; column: number }

export function panelMapGeometry(widthM: number, heightM: number, maximumWidth = 900, maximumHeight = 650): PanelMapGeometry {
  if (![widthM, heightM, maximumWidth, maximumHeight].every(Number.isFinite)
    || widthM <= 0 || heightM <= 0 || maximumWidth < 140 || maximumWidth > 2048 || maximumHeight < 140 || maximumHeight > 2048) {
    throw new RangeError('Physical dimensions and drawing limits must be finite and positive.');
  }
  const left = 56, top = 30, right = 30, bottom = 58;
  const scale = Math.min((maximumWidth - left - right) / widthM, (maximumHeight - top - bottom) / heightM);
  const fieldWidth = widthM * scale, fieldHeight = heightM * scale;
  return { width: Math.ceil(left + fieldWidth + right), height: Math.ceil(top + fieldHeight + bottom),
    left, top, fieldWidth, fieldHeight, widthMm: widthM * 1000, heightMm: heightM * 1000 };
}

export function panelPointAt(px: number, py: number, geometry: PanelMapGeometry, clamp = false): PanelPoint | null {
  if (![px, py].every(Number.isFinite)) return null;
  const x = (px - geometry.left) / geometry.fieldWidth, y = (py - geometry.top) / geometry.fieldHeight;
  if (!Number.isFinite(x) || !Number.isFinite(y) || (!clamp && (x < 0 || x > 1 || y < 0 || y > 1))) return null;
  return { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
}

export function gridCellAt(point: PanelPoint, rows: number, columns: number): GridCell | null {
  if (![point.x, point.y].every(v => Number.isFinite(v) && v >= 0 && v <= 1)
    || !Number.isInteger(rows) || !Number.isInteger(columns) || rows < 1 || columns < 1 || rows * columns > 65536) return null;
  return { row: Math.min(rows - 1, Math.floor(point.y * rows)), column: Math.min(columns - 1, Math.floor(point.x * columns)) };
}

export function inspectGridCell(grid: number[][], cell: GridCell, widthM: number, heightM: number) {
  const rows = grid.length, columns = grid[0]?.length ?? 0;
  if (!rows || !columns || grid.some(row => row.length !== columns)
    || ![widthM, heightM].every(v => Number.isFinite(v) && v > 0)
    || !Number.isInteger(cell.row) || !Number.isInteger(cell.column) || cell.row < 0 || cell.row >= rows || cell.column < 0 || cell.column >= columns) return null;
  const probability = grid[cell.row][cell.column];
  if (!Number.isFinite(probability) || probability < 0 || probability > 1) return null;
  const x = (cell.column + .5) / columns, y = (cell.row + .5) / rows;
  return { ...cell, x, y, xMm: x * widthM * 1000, yMm: y * heightM * 1000, probability };
}

export function moveInspectionCell(current: GridCell, key: string, rows: number, columns: number): GridCell | null {
  if (!Number.isInteger(rows) || !Number.isInteger(columns) || rows < 1 || columns < 1 || rows * columns > 65536) return null;
  const row = Math.max(0, Math.min(rows - 1, current.row)), column = Math.max(0, Math.min(columns - 1, current.column));
  if (key === 'Home') return { row: 0, column: 0 };
  if (key === 'End') return { row: rows - 1, column: columns - 1 };
  if (key === 'ArrowLeft') return { row, column: Math.max(0, column - 1) };
  if (key === 'ArrowRight') return { row, column: Math.min(columns - 1, column + 1) };
  if (key === 'ArrowUp') return { row: Math.max(0, row - 1), column };
  if (key === 'ArrowDown') return { row: Math.min(rows - 1, row + 1), column };
  return null;
}

export function restrictedRectangle(start: PanelPoint, end: PanelPoint, index: number) {
  if (![start.x, start.y, end.x, end.y].every(v => Number.isFinite(v) && v >= 0 && v <= 1)
    || !Number.isInteger(index) || index < 0) return null;
  const x_min = Math.min(start.x, end.x), x_max = Math.max(start.x, end.x);
  const y_min = Math.min(start.y, end.y), y_max = Math.max(start.y, end.y);
  if (x_max - x_min < .02 - 1e-12 || y_max - y_min < .02 - 1e-12) return null;
  return { x_min, y_min, x_max, y_max, label: `no-go ${index + 1}` };
}

export function physicalAxisTicks(lengthPx: number): number[] {
  return lengthPx >= 320 ? [0, .25, .5, .75, 1] : lengthPx >= 160 ? [0, .5, 1] : [0, 1];
}
