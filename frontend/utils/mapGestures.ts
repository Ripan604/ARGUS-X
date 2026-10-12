import type { PanelPoint } from './heatmapGeometry.ts';

/** One explicit drawing mode and one owning pointer per map lifecycle. */
export interface MapDraft { start: PanelPoint; end: PanelPoint; pointerId: number }
export interface MapGestureState { contextKey: string; editing: boolean; draft: MapDraft | null }
export type MapGestureEvent =
  | { type: 'mode'; contextKey: string; editing: boolean; blocked: boolean }
  | { type: 'down' | 'move' | 'up'; contextKey: string; pointerId: number; point: PanelPoint | null; blocked: boolean }
  | { type: 'cancel'; contextKey: string; pointerId?: number; leaveEditing?: boolean };

const pointValid = (point: PanelPoint | null): point is PanelPoint => point !== null
  && [point.x, point.y].every(value => Number.isFinite(value) && value >= 0 && value <= 1);
export const initialMapGesture = (contextKey: string): MapGestureState => ({ contextKey, editing: false, draft: null });

export function transitionMapGesture(state: MapGestureState, event: MapGestureEvent): { state: MapGestureState; completed: MapDraft | null } {
  const unchanged = { state, completed: null };
  // Events from a prior session, view, stop/disabled state or restriction set
  // cannot roll back the current lifecycle or complete an old gesture.
  if (event.contextKey !== state.contextKey) return unchanged;
  if (event.type === 'mode') return { state: { ...state, editing: !event.blocked && event.editing, draft: null }, completed: null };
  if (event.type === 'cancel') {
    if (event.pointerId !== undefined && state.draft?.pointerId !== event.pointerId) return unchanged;
    return { state: { ...state, draft: null, editing: event.leaveEditing ? false : state.editing }, completed: null };
  }
  if (!Number.isInteger(event.pointerId) || event.pointerId < 0) return unchanged;
  if (state.draft && state.draft.pointerId !== event.pointerId) return unchanged;
  if (event.blocked) return { state: initialMapGesture(state.contextKey), completed: null };
  if (event.type === 'down') {
    if (!state.editing || state.draft || !pointValid(event.point)) return unchanged;
    return { state: { ...state, draft: { pointerId: event.pointerId, start: { ...event.point }, end: { ...event.point } } }, completed: null };
  }
  if (!state.editing || state.draft?.pointerId !== event.pointerId) return unchanged;
  if (event.type === 'move') {
    if (!pointValid(event.point)) return unchanged;
    return { state: { ...state, draft: { ...state.draft, end: { ...event.point } } }, completed: null };
  }
  return { state: initialMapGesture(state.contextKey),
    completed: pointValid(event.point) ? { ...state.draft, end: { ...event.point } } : null };
}
