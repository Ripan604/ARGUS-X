'use client';

import { Component, type ReactNode } from 'react';

/** A failed plot or deferred view must not remove navigation and session-stop controls. */
export class InstrumentViewBoundary extends Component<{ children: ReactNode; onOverview: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <section className="review-invalid" role="alert"><h2>This instrument view could not be displayed.</h2><p>The session controls are still available. Return to Overview or refresh the saved state from the toolbar.</p><button className="workbench-button" onClick={this.props.onOverview}>Return to Overview</button></section>;
    return this.props.children;
  }
}
