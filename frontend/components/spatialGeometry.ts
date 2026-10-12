/** Coordinates of a circle in physical millimeters, not normalized panel distance. */
export function physicalCircle(cx: number, cy: number, radiusMm: number, widthMm: number, heightMm: number, segments = 120) {
  if (![cx, cy, radiusMm, widthMm, heightMm].every(Number.isFinite)
    || widthMm <= 0 || heightMm <= 0 || radiusMm < 0
    || !Number.isInteger(segments) || segments < 3 || segments > 2048) return [];
  return Array.from({ length: segments + 1 }, (_, index) => { const angle = index / segments * Math.PI * 2; return { x: cx + Math.cos(angle) * radiusMm / widthMm, y: cy + Math.sin(angle) * radiusMm / heightMm }; });
}
export function normalizedRelief(posterior: number[][] | undefined) {
  const columns = posterior?.[0]?.length ?? 0;
  if (!Array.isArray(posterior) || !posterior.length || !columns || posterior.length * columns > 65536
    || !Array.from(posterior).every(row => Array.isArray(row) && row.length === columns
      && Array.from(row).every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0))) return null;
  const peak = posterior.reduce((maximum, row) => row.reduce((value, cell) => Math.max(value, cell), maximum), 0);
  return posterior.map((row) => row.map((value) => peak > 0 ? Math.max(0, value) / peak : 0));
}

export interface PanelView {
  widthMm: number;
  heightMm: number;
  viewportWidth: number;
  viewportHeight: number;
  azimuthDeg: number;
  elevationDeg: number;
  zoom: number;
}

export interface ProjectedPoint { x: number; y: number; depth: number }
interface SurfacePoint extends ProjectedPoint { panelX: number; panelY: number }
export interface ReliefFace {
  row: number; column: number; points: SurfacePoint[]; value: number; depth: number;
}

/** Shared painter order keeps picking aligned with the exact displayed relief. */
export function projectedReliefFaces(field: number[][], project: (x: number, y: number, z?: number) => ProjectedPoint): ReliefFace[] {
  const rows = field.length, columns = field[0]?.length ?? 0;
  const faces: ReliefFace[] = [];
  for (let row = 0; row < rows - 1; row++) for (let column = 0; column < columns - 1; column++) {
    const points = [[column, row], [column + 1, row], [column + 1, row + 1], [column, row + 1]].map(([c, r]) => {
      const panelX = (c + .5) / columns, panelY = (r + .5) / rows;
      return { ...project(panelX, panelY, field[r][c] * .23), panelX, panelY };
    });
    faces.push({ row, column, points, value: (field[row][column] + field[row][column + 1] + field[row + 1][column] + field[row + 1][column + 1]) / 4,
      depth: points.reduce((sum, point) => sum + point.depth, 0) / 4 });
  }
  return faces.sort((a, b) => a.depth - b.depth);
}

function trianglePanelPoint(x: number, y: number, a: SurfacePoint, b: SurfacePoint, c: SurfacePoint) {
  const determinant = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
  if (Math.abs(determinant) < 1e-8) return null;
  const wa = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / determinant;
  const wb = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / determinant, wc = 1 - wa - wb;
  if ([wa, wb, wc].some(weight => weight < -1e-8 || weight > 1 + 1e-8)) return null;
  return { x: wa * a.panelX + wb * b.panelX + wc * c.panelX, y: wa * a.panelY + wb * b.panelY + wc * c.panelY };
}

/** Canvas uses a nonzero polygon fill; exclude the outside of concave quads. */
function insideFace(x: number, y: number, points: SurfacePoint[]) {
  let winding = 0;
  for (let index = 0; index < points.length; index++) {
    const a = points[index], b = points[(index + 1) % points.length];
    const cross = (b.x - a.x) * (y - a.y) - (x - a.x) * (b.y - a.y);
    if (Math.abs(cross) < 1e-7 && x >= Math.min(a.x, b.x) - 1e-7 && x <= Math.max(a.x, b.x) + 1e-7
      && y >= Math.min(a.y, b.y) - 1e-7 && y <= Math.max(a.y, b.y) + 1e-7) return true;
    if (a.y <= y && b.y > y && cross > 0) winding++;
    else if (a.y > y && b.y <= y && cross < 0) winding--;
  }
  return winding !== 0;
}

/** Pick the visible relief first, then its floor rim; never guess outside the panel. */
export function pickPosteriorCell(posterior: number[][], view: PanelView, x: number, y: number) {
  const field = normalizedRelief(posterior);
  if (!field || ![x, y].every(Number.isFinite)) return null;
  const { project } = panelProjection(view), rows = field.length, columns = field[0].length;
  const floor = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([panelX, panelY]) => ({ ...project(panelX, panelY), panelX, panelY }));
  let point = trianglePanelPoint(x, y, floor[0], floor[1], floor[2]) ?? trianglePanelPoint(x, y, floor[0], floor[2], floor[3]);
  for (const face of projectedReliefFaces(field, project)) {
    if (!insideFace(x, y, face.points)) continue;
    const [a, b, c, d] = face.points;
    const hit = trianglePanelPoint(x, y, a, b, c) ?? trianglePanelPoint(x, y, a, c, d);
    if (hit) point = hit;
  }
  if (!point) return null;
  return { row: Math.min(rows - 1, Math.max(0, Math.floor(point.y * rows))),
    column: Math.min(columns - 1, Math.max(0, Math.floor(point.x * columns))) };
}

export function wrapAzimuth(degrees: number) {
  if (!Number.isFinite(degrees)) throw new RangeError('Camera azimuth must be finite.');
  return ((degrees + 180) % 360 + 360) % 360 - 180;
}

/** Orthographic orbit camera. Z is a display coordinate, never physical depth. */
export function panelProjection(view: PanelView) {
  if (!Object.values(view).every(Number.isFinite) || view.widthMm <= 0 || view.heightMm <= 0
    || view.viewportWidth <= 0 || view.viewportHeight <= 0 || view.zoom < .6 || view.zoom > 1.6
    || view.elevationDeg < 0 || view.elevationDeg > 90) throw new RangeError('Panel camera is outside its finite view bounds.');
  const longest = Math.max(view.widthMm, view.heightMm);
  const aspectX = view.widthMm / longest, aspectY = view.heightMm / longest;
  const azimuth = wrapAzimuth(view.azimuthDeg) * Math.PI / 180;
  const elevation = view.elevationDeg * Math.PI / 180;
  const rotate = (x: number, y: number, z: number) => {
    const px = (x - .5) * aspectX, py = (y - .5) * aspectY;
    const horizontal = px * Math.cos(azimuth) - py * Math.sin(azimuth);
    const forward = px * Math.sin(azimuth) + py * Math.cos(azimuth);
    return { x: horizontal, y: forward * Math.sin(elevation) - z * Math.cos(elevation),
      depth: forward * Math.cos(elevation) + z * Math.sin(elevation) };
  };
  // Fit both the schematic base and the maximum display-relief range, even
  // when no posterior exists. Controls therefore do not invent landing peaks.
  const bounds = [-.10, 1.10].flatMap(x => [-.10, 1.10].flatMap(y => [-.045, .30].map(z => rotate(x, y, z))));
  const minX = Math.min(...bounds.map(point => point.x)), maxX = Math.max(...bounds.map(point => point.x));
  const minY = Math.min(...bounds.map(point => point.y)), maxY = Math.max(...bounds.map(point => point.y));
  const availableWidth = Math.max(1, view.viewportWidth - 82), availableHeight = Math.max(1, view.viewportHeight - 85);
  const scale = Math.min(availableWidth / Math.max(.001, maxX - minX),
    availableHeight / Math.max(.001, maxY - minY)) * view.zoom;
  return { scale, aspectX, aspectY,
    project: (x: number, y: number, z = 0): ProjectedPoint => {
      if (![x, y, z].every(Number.isFinite)) throw new RangeError('Panel coordinates must be finite.');
      const point = rotate(x, y, z);
      return { x: view.viewportWidth / 2 + (point.x - (minX + maxX) / 2) * scale,
        y: view.viewportHeight / 2 + (point.y - (minY + maxY) / 2) * scale, depth: point.depth };
    },
  };
}

/** Unit normal for graphic shading, using the panel's true planar aspect. */
export function reliefNormal(dx: number, dy: number, aspectX: number, aspectY: number) {
  if (![dx, dy, aspectX, aspectY].every(Number.isFinite) || aspectX <= 0 || aspectY <= 0) {
    throw new RangeError('Relief normal requires finite slopes and positive panel aspects.');
  }
  const nx = -dx / aspectX, ny = -dy / aspectY;
  const magnitude = Math.hypot(nx, ny, 1);
  return { x: nx / magnitude, y: ny / magnitude, z: 1 / magnitude };
}
