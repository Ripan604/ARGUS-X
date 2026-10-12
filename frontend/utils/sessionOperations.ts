/** Client ownership of responses. Invalidating a ticket never cancels engine work. */
export type OperationStatus = 'running' | 'succeeded' | 'partial' | 'failed';

export interface SessionOperation {
  id: number;
  label: string;
  status: OperationStatus;
  startedAt: number;
  finishedAt?: number;
  sessionId: string | null;
  detail?: string;
}

export interface EmergencyStopState {
  latched: boolean;
  reason: string | null;
  latched_at: string | null;
  released_at: string | null;
}

export interface OperationTicket {
  readonly id: number;
  readonly epoch: number;
  readonly label: string;
  readonly startedAt: number;
  readonly sessionId: string | null;
  readonly lane: 'foreground' | 'replacement' | 'safety';
  readonly safetyAction?: 'stop' | 'release';
}

function safetyRevision(stop: EmergencyStopState): number | null {
  const stamp = stop.latched ? stop.latched_at : stop.released_at;
  if (!stamp) return null;
  const millis = Date.parse(stamp);
  if (!Number.isFinite(millis)) return null;
  // The engine records microseconds; Date.parse alone loses ordering in one ms.
  const fraction = stamp.match(/\.(\d+)(?:Z|[+-]\d\d:\d\d)$/)?.[1] || '';
  const micros = millis * 1000 + Number(fraction.slice(3, 6).padEnd(3, '0'));
  return Number.isSafeInteger(micros) ? micros : null;
}

export class SessionOperationFence {
  private epoch = 0;
  private nextId = 1;
  private mounted = true;
  private identity: string | null = null;
  private foreground: { ticket: OperationTicket; sessionId: string | null } | null = null;
  private pendingSafety: OperationTicket | null = null;
  private latestSafety: OperationTicket | null = null;
  private acknowledged: { sessionId: string; stop: EmergencyStopState; revision: number | null } | null = null;
  private clock: () => number;

  constructor(clock: () => number = Date.now) { this.clock = clock; }

  get isMounted() { return this.mounted; }
  get isBusy() { return this.foreground !== null || this.pendingSafety !== null; }
  get sessionId() { return this.identity; }

  allowsAcquisition(ticket: OperationTicket): boolean {
    return this.owns(ticket) && this.pendingSafety?.safetyAction !== 'stop'
      && this.acknowledged?.stop.latched !== true;
  }

  mount() { this.mounted = true; }

  reset() {
    this.epoch += 1;
    this.identity = null;
    this.foreground = null;
    this.pendingSafety = null;
    this.latestSafety = null;
    this.acknowledged = null;
  }

  dispose() { this.reset(); this.mounted = false; }

  private ticket(label: string, lane: OperationTicket['lane'], safetyAction?: 'stop' | 'release'): OperationTicket {
    return Object.freeze({ id: this.nextId++, epoch: this.epoch, label,
      startedAt: this.clock(), sessionId: this.identity, lane, ...(safetyAction ? { safetyAction } : {}) });
  }

  begin(label: string): OperationTicket | null {
    if (!this.mounted || this.isBusy) return null;
    const ticket = this.ticket(label, 'foreground');
    this.foreground = { ticket, sessionId: this.identity };
    return ticket;
  }

  beginReplacement(label: string): OperationTicket | null {
    if (!this.mounted || this.foreground?.ticket.lane === 'replacement') return null;
    this.reset();
    const ticket = this.ticket(label, 'replacement');
    this.foreground = { ticket, sessionId: null };
    return ticket;
  }

  owns(ticket: OperationTicket): boolean {
    return this.mounted && ticket.epoch === this.epoch && this.foreground?.ticket.id === ticket.id
      && this.foreground.sessionId === this.identity;
  }

  adopt(ticket: OperationTicket, sessionId: string): boolean {
    if (!this.owns(ticket) || ticket.lane !== 'replacement') return false;
    if (!sessionId) throw new Error('Engine returned an empty session identity.');
    this.identity = sessionId;
    this.foreground!.sessionId = sessionId;
    return true;
  }

  checkResponse(ticket: OperationTicket, responseSessionId: string): boolean {
    if (!this.owns(ticket)) return false;
    if (!this.identity || responseSessionId !== this.identity) {
      throw new Error('Engine response belongs to a different session; it was not applied.');
    }
    return true;
  }

  finish(ticket: OperationTicket): boolean {
    if (!this.owns(ticket)) return false;
    this.foreground = null;
    return true;
  }

  beginSafety(action: 'stop' | 'release', label: string): OperationTicket | null {
    if (!this.mounted || !this.identity || this.pendingSafety?.safetyAction === action) return null;
    const ticket = this.ticket(label, 'safety', action);
    this.latestSafety = ticket;
    this.pendingSafety = ticket;
    return ticket;
  }

  private safetyContextCurrent(ticket: OperationTicket): boolean {
    return this.mounted && ticket.epoch === this.epoch && ticket.lane === 'safety'
      && ticket.sessionId !== null && ticket.sessionId === this.identity;
  }

  ownsSafety(ticket: OperationTicket): boolean {
    return this.safetyContextCurrent(ticket) && this.latestSafety?.id === ticket.id;
  }

  finishSafety(ticket: OperationTicket): boolean {
    if (!this.ownsSafety(ticket) || this.pendingSafety?.id !== ticket.id) return false;
    this.pendingSafety = null;
    return true;
  }

  acknowledgeSafety(ticket: OperationTicket, responseSessionId: string, stop: EmergencyStopState): boolean {
    if (!this.safetyContextCurrent(ticket)) return false;
    if (responseSessionId !== this.identity) {
      throw new Error('Safety acknowledgment belongs to a different session; it was not applied.');
    }
    const revision = safetyRevision(stop);
    if (typeof stop.latched !== 'boolean' || stop.latched !== (ticket.safetyAction === 'stop') || revision === null) {
      throw new Error('Engine did not return a valid acknowledgment of the requested safety state. Refresh the session before proceeding.');
    }
    const previous = this.acknowledged;
    if (!this.ownsSafety(ticket)) {
      // A superseded release never clears a newer stop request. An older stop
      // processed later on the engine may still be its newest confirmed state.
      if (!stop.latched || revision === null || (previous?.revision !== null
          && previous?.revision !== undefined && revision <= previous.revision)) return false;
    }
    if (previous?.revision !== null && previous?.revision !== undefined && revision !== null
        && revision < previous.revision) return false;
    this.acknowledged = { sessionId: responseSessionId, stop: { ...stop }, revision };
    return true;
  }

  mergeSafety(sessionId: string, stop: EmergencyStopState): EmergencyStopState {
    const previous = this.acknowledged;
    if (!previous || previous.sessionId !== sessionId) return { ...stop };
    const revision = safetyRevision(stop);
    const newer = revision !== null && (previous.revision === null || revision > previous.revision);
    const pendingStop = this.pendingSafety?.safetyAction === 'stop';
    if (newer && (!pendingStop || stop.latched)) {
      this.acknowledged = { sessionId, stop: { ...stop }, revision };
      return { ...stop };
    }
    return { ...previous.stop };
  }
}

export function runningOperation(ticket: OperationTicket): SessionOperation {
  return { id: ticket.id, label: ticket.label, status: 'running', startedAt: ticket.startedAt,
    sessionId: ticket.sessionId };
}

export type OwnedOutcome<T> = { status: 'succeeded'; value: T }
  | { status: 'failed'; error: unknown } | { status: 'stale' };

/** A late success or rejection belongs to its original context, never the next. */
export async function settleOwnedTask<T>(fence: SessionOperationFence, ticket: OperationTicket,
  work: () => Promise<T>): Promise<OwnedOutcome<T>> {
  if (!fence.owns(ticket)) return { status: 'stale' };
  try {
    const value = await work();
    return fence.owns(ticket) ? { status: 'succeeded', value } : { status: 'stale' };
  } catch (error) {
    return fence.owns(ticket) ? { status: 'failed', error } : { status: 'stale' };
  }
}

export type ReadReconciliation = { status: 'completed' | 'stale' }
  | { status: 'partial'; error: unknown };

/** Failure of a read after a committed action does not turn that action into failure. */
export async function reconcileOwnedRead<T>(fence: SessionOperationFence, ticket: OperationTicket,
  request: () => Promise<T>, commit: (value: T) => void): Promise<ReadReconciliation> {
  if (!fence.owns(ticket)) return { status: 'stale' };
  try {
    const value = await request();
    if (!fence.owns(ticket)) return { status: 'stale' };
    commit(value);
    return { status: 'completed' };
  } catch (error) {
    return fence.owns(ticket) ? { status: 'partial', error } : { status: 'stale' };
  }
}
