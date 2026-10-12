import assert from 'node:assert/strict';
import test from 'node:test';
import { SessionOperationFence, reconcileOwnedRead, runningOperation, settleOwnedTask } from '../utils/sessionOperations.ts';
import type { EmergencyStopState, OperationTicket } from '../utils/sessionOperations.ts';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function seeded(id = 'session-a') {
  const fence = new SessionOperationFence(() => 123456789);
  const ticket = fence.beginReplacement('Create session')!;
  assert.equal(fence.adopt(ticket, id), true);
  assert.equal(fence.finish(ticket), true);
  return fence;
}

const stopped = (stamp = '2026-10-09T10:00:00.123456+00:00'): EmergencyStopState => ({
  latched: true, reason: 'Operator intervention', latched_at: stamp, released_at: null,
});
const released = (stamp = '2026-10-09T10:00:01.123456+00:00'): EmergencyStopState => ({
  latched: false, reason: 'Operator checked the apparatus', latched_at: '2026-10-09T10:00:00.123456+00:00', released_at: stamp,
});

test('reset fences a dispatched success and its finalizer cannot unlock the next operation', async () => {
  const fence = seeded();
  const old = fence.begin('Physical acquisition')!;
  const pending = deferred<string>();
  let dispatches = 0;
  const work = settleOwnedTask(fence, old, () => { dispatches += 1; return pending.promise; });
  fence.reset();
  const replacement = fence.beginReplacement('Create session')!;
  fence.adopt(replacement, 'session-b');
  pending.resolve('old measurement did complete on engine');
  assert.deepEqual(await work, { status: 'stale' });
  assert.equal(dispatches, 1); // Fencing neither cancels nor retries the physical request.
  assert.equal(fence.finish(old), false);
  assert.equal(fence.owns(replacement), true);
  assert.equal(fence.sessionId, 'session-b');
  assert.equal(fence.isBusy, true);
});

test('late rejection after unmount cannot become a new page error, even when the same ID is resumed', async () => {
  const fence = seeded();
  const old = fence.begin('Read session')!;
  const pending = deferred<string>();
  const work = settleOwnedTask(fence, old, () => pending.promise);
  fence.dispose();
  assert.equal(fence.begin('Unmounted action'), null);
  fence.mount();
  const resume = fence.beginReplacement('Resume session')!;
  fence.adopt(resume, 'session-a');
  pending.reject(new Error('Old page request failed'));
  assert.deepEqual(await work, { status: 'stale' });
  assert.equal(fence.owns(resume), true);
});

test('duplicate actions and duplicate replacement requests cannot dispatch twice', () => {
  const fence = seeded();
  const running = fence.begin('Run experiment')!;
  assert.equal(fence.begin('Run experiment'), null);
  const replacement = fence.beginReplacement('Create session')!;
  assert.equal(fence.owns(running), false);
  assert.equal(fence.beginReplacement('Resume session'), null);
  assert.equal(fence.adopt(replacement, 'session-b'), true);
  assert.equal(fence.owns(replacement), true);
  assert.equal(fence.checkResponse(replacement, 'session-b'), true);
  assert.equal(Object.isFrozen(replacement), true);
  assert.deepEqual(runningOperation(replacement), {
    id: replacement.id, label: 'Create session', status: 'running', startedAt: 123456789, sessionId: null,
  });
});

test('response ID mismatch is rejected while the current session remains owned', () => {
  const fence = seeded();
  const ticket = fence.begin('Run experiment')!;
  assert.throws(() => fence.checkResponse(ticket, 'another-session'), /different session/);
  assert.equal(fence.checkResponse(ticket, 'session-a'), true);
  assert.equal(fence.sessionId, 'session-a');
});

test('stop takes priority during acquisition and blocks the next stage before its acknowledgment arrives', () => {
  const fence = seeded();
  const acquisition = fence.begin('Connect and acquire')!;
  assert.equal(fence.allowsAcquisition(acquisition), true);
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  assert.equal(fence.allowsAcquisition(acquisition), false);
  assert.equal(fence.beginSafety('stop', 'Duplicate emergency stop'), null);
  assert.equal(fence.acknowledgeSafety(stop, 'session-a', stopped()), true);
  fence.finishSafety(stop);
  assert.equal(fence.allowsAcquisition(acquisition), false);
  assert.equal(fence.owns(acquisition), true); // The dispatched engine request still owns its result.
  assert.deepEqual(fence.mergeSafety('session-a', { latched: false, reason: null, latched_at: null, released_at: null }), stopped());
});

test('older stop response cannot undo a newer acknowledged release, including submillisecond revisions', async () => {
  const fence = seeded();
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  const stopResponse = deferred<EmergencyStopState>();
  const stopWork = stopResponse.promise.then(value => fence.acknowledgeSafety(stop, 'session-a', value));
  const release = fence.beginSafety('release', 'Release stop')!;
  const clear = released('2026-10-09T10:00:00.123789+00:00');
  assert.equal(fence.acknowledgeSafety(release, 'session-a', clear), true);
  stopResponse.resolve(stopped('2026-10-09T10:00:00.123456+00:00'));
  assert.equal(await stopWork, false);
  assert.equal(fence.finishSafety(stop), false);
  assert.equal(fence.isBusy, true);
  assert.deepEqual(fence.mergeSafety('session-a', stopped('2026-10-09T10:00:00.123456+00:00')), clear);
});

test('older request processed later by the engine preserves its genuinely newer latched state', () => {
  const fence = seeded();
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  const release = fence.beginSafety('release', 'Release stop')!;
  fence.acknowledgeSafety(release, 'session-a', released('2026-10-09T10:00:00.123456+00:00'));
  const laterEngineState = stopped('2026-10-09T10:00:00.123789+00:00');
  assert.equal(fence.acknowledgeSafety(stop, 'session-a', laterEngineState), true);
  assert.deepEqual(fence.mergeSafety('session-a', released('2026-10-09T10:00:00.123456+00:00')), laterEngineState);
});

test('superseded release never clears a newer stop; read reconciliation can learn the actual latest engine state', () => {
  const fence = seeded();
  const release = fence.beginSafety('release', 'Release stop')!;
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  const latched = stopped('2026-10-09T10:00:02.000001+00:00');
  fence.acknowledgeSafety(stop, 'session-a', latched);
  const clear = released('2026-10-09T10:00:03.000001+00:00');
  assert.equal(fence.acknowledgeSafety(release, 'session-a', clear), false);
  assert.deepEqual(fence.mergeSafety('session-a', clear), latched); // Stop still awaiting settlement.
  fence.finishSafety(stop);
  assert.deepEqual(fence.mergeSafety('session-a', clear), clear); // Explicit state read observes server fact.
});

test('old run snapshots cannot clear a confirmed stop or re-latch a confirmed release', () => {
  const fence = seeded();
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  const latched = stopped();
  fence.acknowledgeSafety(stop, 'session-a', latched); fence.finishSafety(stop);
  const initial: EmergencyStopState = { latched: false, reason: null, latched_at: null, released_at: null };
  assert.deepEqual(fence.mergeSafety('session-a', initial), latched);
  const release = fence.beginSafety('release', 'Release stop')!;
  const clear = released();
  fence.acknowledgeSafety(release, 'session-a', clear); fence.finishSafety(release);
  assert.deepEqual(fence.mergeSafety('session-a', latched), clear);
});

test('safety state snapshots are immutable to callers and never transfer to a replacement session', () => {
  const fence = seeded();
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  const value = stopped();
  fence.acknowledgeSafety(stop, 'session-a', value);
  value.latched = false;
  const copy = fence.mergeSafety('session-a', released('2026-10-09T09:59:00.000000+00:00'));
  assert.equal(copy.latched, true);
  copy.latched = false;
  assert.equal(fence.mergeSafety('session-a', value).latched, true);
  const replacement = fence.beginReplacement('Create session')!;
  fence.adopt(replacement, 'session-b');
  assert.equal(fence.acknowledgeSafety(stop, 'session-a', stopped()), false);
  const initial: EmergencyStopState = { latched: false, reason: null, latched_at: null, released_at: null };
  assert.deepEqual(fence.mergeSafety('session-b', initial), initial);
});

test('safety acknowledgment requires the session ID, expected state and engine timestamp', () => {
  const fence = seeded();
  const stop = fence.beginSafety('stop', 'Emergency stop')!;
  assert.throws(() => fence.acknowledgeSafety(stop, 'session-b', stopped()), /different session/);
  assert.throws(() => fence.acknowledgeSafety(stop, 'session-a', released()), /valid acknowledgment/);
  assert.throws(() => fence.acknowledgeSafety(stop, 'session-a', { ...stopped(), latched_at: 'unknown' }), /valid acknowledgment/);
});

test('successful measurement survives a rejected history read and is not a failed physical operation', async () => {
  const fence = seeded();
  const ticket = fence.begin('Run experiment')!;
  const measurement = deferred<{ samples: number }>();
  const history = deferred<string[]>();
  let recorded: { samples: number } | undefined;
  let warning: unknown;
  const work = settleOwnedTask(fence, ticket, async () => {
    const result = await measurement.promise;
    assert.equal(fence.checkResponse(ticket, 'session-a'), true);
    recorded = result;
    const followup = await reconcileOwnedRead(fence, ticket, () => history.promise, () => assert.fail('Rejected history was applied'));
    if (followup.status === 'partial') warning = followup.error;
    return result;
  });
  measurement.resolve({ samples: 1936 });
  await Promise.resolve();
  assert.deepEqual(recorded, { samples: 1936 });
  history.reject(new Error('History read unavailable'));
  assert.deepEqual(await work, { status: 'succeeded', value: { samples: 1936 } });
  assert.match(String(warning), /History read unavailable/);
});

test('stale history response after reset is discarded and creates no partial warning', async () => {
  const fence = seeded();
  const ticket = fence.begin('Refresh history')!;
  const pending = deferred<string[]>();
  let commits = 0;
  const read = reconcileOwnedRead(fence, ticket, () => pending.promise, () => { commits += 1; });
  fence.reset();
  pending.resolve(['old-session-event']);
  assert.deepEqual(await read, { status: 'stale' });
  assert.equal(commits, 0);
});

test('a microphone or device preparation completing after reset cannot dispatch its acquisition stage', async () => {
  const fence = seeded();
  const ticket: OperationTicket = fence.begin('Prepare physical acquisition')!;
  const prepared = deferred<void>();
  let acquisitions = 0;
  const work = settleOwnedTask(fence, ticket, async () => {
    await prepared.promise;
    if (fence.allowsAcquisition(ticket)) acquisitions += 1;
  });
  fence.reset();
  prepared.resolve();
  assert.deepEqual(await work, { status: 'stale' });
  assert.equal(acquisitions, 0);
});
