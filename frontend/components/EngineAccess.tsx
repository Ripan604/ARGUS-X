'use client';

import { useState } from 'react';
import { argusApi, setApiToken } from '@/services/api';

export function EngineAccess({ required = false }: { required?: boolean }) {
  const [key, setKey] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const connect = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      setApiToken(key);
      await argusApi.jobs();
      setKey('');
      setStatus('Access key accepted for this browser tab.');
    } catch (reason) {
      setApiToken('');
      setStatus(reason instanceof Error ? reason.message : 'Access could not be verified.');
    } finally { setBusy(false); }
  };
  return <details className="engine-access" open={required || undefined}>
    <summary>{required ? 'Access key required by this engine' : 'Shared engine access'}</summary>
    <form onSubmit={connect}>
      <label>Access key <input type="password" autoComplete="off" value={key} onChange={(event) => setKey(event.target.value)} placeholder="Key from the Laptop A launcher" aria-label="ARGUS engine access key" /></label>
      <button type="submit" disabled={busy || !key.trim()}>{busy ? 'Checking access...' : 'Connect'}</button>
      <button type="button" onClick={() => { setApiToken(''); setKey(''); setStatus('Access key cleared from this tab.'); }}>Clear key</button>
    </form>
    <p>The key is kept in this browser tab and is never included in links. Local-only sessions do not require a key.</p>
    {status && <p role="status">{status}</p>}
  </details>;
}
