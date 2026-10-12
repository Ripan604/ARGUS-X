import assert from 'node:assert/strict';
import test from 'node:test';
import { initialMapGesture, transitionMapGesture, type MapGestureState } from '../utils/mapGestures.ts';

function start(contextKey = 'session:editable'): MapGestureState {
  let state = initialMapGesture(contextKey);
  state = transitionMapGesture(state, { type: 'mode', contextKey, editing: true, blocked: false }).state;
  return transitionMapGesture(state, { type: 'down', contextKey, pointerId: 1, point: { x: .1, y: .2 }, blocked: false }).state;
}

test('inspection mode never starts or completes a restriction drawing', () => {
  const state = initialMapGesture('inspect');
  const result = transitionMapGesture(state, { type: 'down', contextKey: 'inspect', pointerId: 1, point: { x: .1, y: .2 }, blocked: false });
  assert.strictEqual(result.state, state);
  assert.equal(transitionMapGesture(result.state, { type: 'up', contextKey: 'inspect', pointerId: 1, point: { x: .8, y: .9 }, blocked: false }).completed, null);
});

test('a second pointer cannot overwrite, move, release or cancel an owned draft', () => {
  const state = start();
  for (const type of ['down', 'move', 'up'] as const) {
    const result = transitionMapGesture(state, { type, contextKey: state.contextKey, pointerId: 2, point: { x: .8, y: .9 }, blocked: false });
    assert.strictEqual(result.state, state);
    assert.equal(result.completed, null);
  }
  const cancelled = transitionMapGesture(state, { type: 'cancel', contextKey: state.contextKey, pointerId: 2 });
  assert.strictEqual(cancelled.state, state);
  const completed = transitionMapGesture(state, { type: 'up', contextKey: state.contextKey, pointerId: 1, point: { x: .4, y: .5 }, blocked: false });
  assert.deepEqual(completed.completed, { pointerId: 1, start: { x: .1, y: .2 }, end: { x: .4, y: .5 } });
  assert.equal(completed.state.draft, null);
  assert.equal(completed.state.editing, false);
});

test('disabled or stop state cannot complete an existing draft', () => {
  const state = start();
  const result = transitionMapGesture(state, { type: 'up', contextKey: state.contextKey, pointerId: 1, point: { x: .8, y: .9 }, blocked: true });
  assert.equal(result.completed, null);
  assert.equal(result.state.draft, null);
  assert.equal(result.state.editing, false);
});

test('view/disabled/session/restriction lifecycle changes prevent stale events after unlocking', () => {
  const old = start('old-lifecycle');
  const locked = initialMapGesture('disabled-lifecycle');
  const unlocked = initialMapGesture('new-editable-lifecycle');
  for (const state of [locked, unlocked]) {
    const result = transitionMapGesture(state, { type: 'up', contextKey: old.contextKey, pointerId: 1, point: { x: .8, y: .9 }, blocked: false });
    assert.strictEqual(result.state, state);
    assert.equal(result.completed, null);
    assert.equal(result.state.editing, false);
  }
  // Even the same original context string cannot revive a removed draft.
  assert.equal(transitionMapGesture(initialMapGesture(old.contextKey), { type: 'up', contextKey: old.contextKey, pointerId: 1, point: { x: .8, y: .9 }, blocked: false }).completed, null);
});

test('Escape/owned capture loss cancel; later pointer release does not mutate', () => {
  const state = start();
  for (const cancel of [
    { type: 'cancel' as const, contextKey: state.contextKey, pointerId: 1 },
    { type: 'cancel' as const, contextKey: state.contextKey, leaveEditing: true },
  ]) {
    const cancelled = transitionMapGesture(state, cancel).state;
    assert.equal(cancelled.draft, null);
    assert.equal(transitionMapGesture(cancelled, { type: 'up', contextKey: state.contextKey, pointerId: 1, point: { x: .8, y: .9 }, blocked: false }).completed, null);
  }
});

test('invalid coordinates cannot become a committed rectangle or corrupt the start point', () => {
  const state = start(), before = JSON.stringify(state);
  const moved = transitionMapGesture(state, { type: 'move', contextKey: state.contextKey, pointerId: 1, point: { x: NaN, y: .5 }, blocked: false });
  assert.strictEqual(moved.state, state);
  assert.equal(JSON.stringify(state), before);
  assert.equal(transitionMapGesture(state, { type: 'up', contextKey: state.contextKey, pointerId: 1, point: null, blocked: false }).completed, null);
});
