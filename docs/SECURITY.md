# ARGUS security and acquisition contract

Updated 7 October 2026. This is a local operator research instrument, not a
multi-tenant service or a hardware safety controller.

## Start locally

```powershell
python run_argus.py
```

The launcher binds the frontend and backend to 127.0.0.1. It prefers the project
`.venv` interpreter when present. The usual frontend address is
http://localhost:5173; the configured API port in this workspace is 8001.
Other devices cannot access local mode. The backend also checks the peer address,
Host header and exact browser origin, so alternate Uvicorn bind flags do not
silently convert local mode into anonymous LAN control.

## Explicit shared LAN mode

```powershell
python run_argus.py --lan
```

The launcher generates a per-run access key unless ARGUS_API_TOKEN is provided,
sets exact hosts/origins for its discovered LAN address, and prints the key only
to the operator terminal. Enter it under **Shared engine access** on the main or
phone page. The key is scoped to the API and browser tab, not placed in a URL,
localStorage, a NEXT_PUBLIC variable, or the frontend child-process environment.

Direct backend configuration uses ARGUS_NETWORK_MODE=lan, ARGUS_BIND_HOST,
ARGUS_API_TOKEN, ARGUS_ALLOWED_HOSTS and ARGUS_ALLOWED_ORIGINS. LAN configuration
fails closed unless all required controls exist. Tokens contain 32-256 URL-safe
characters. Browser requests use Authorization: Bearer; browser WebSockets carry
the key in a non-echoed authentication subprotocol, never a query string. `/health`
is public but returns only service/security mode information. API documentation
requires an authorized client when authentication is enabled.

HTTP LAN mode is for a trusted network: it does not encrypt the key or data.
Use a correctly configured TLS reverse proxy and exact HTTPS origins for hostile
or shared networks. A shared key has operator-wide access; per-user roles,
tenant isolation, institutional authentication and distributed rate limiting are
not implemented. Default limits assume one ASGI worker.

The edge client reads ARGUS_API_TOKEN from its environment. It refuses HTTP
redirects rather than forwarding credentials to another destination, registers
once per connection, and acquires each newly observed recommendation. Keep the
operator responsible for actual probe placement.

Modern phones require a trustworthy HTTPS context for microphone/camera access.
The printed plain HTTP LAN page supports manual placement and engine connection;
it explicitly disables unavailable capture. Localhost microphone/WAV acquisition
and the laptop edge client remain alternatives. No sensor permission is bypassed.

## Bounded inputs and execution

- HTTP JSON: 16 MiB; WAV file: 10 MiB; bundle file: 50 MiB, with bounded multipart
  overhead, body/chunk deadlines and work-concurrency/rate limits.
- WebSocket frame: 64 KiB before JSON parsing, with connection, message and idle
  limits. Authentication, Host and origin checks apply to sockets too.
- Original waveform: finite mono samples, adequate declared window, at most
  384,000 samples and original-rate Nyquist support for the excitation band.
  Short captures are rejected. Longer captures may be explicitly cropped;
  resampling and window provenance are recorded. Missing evidence is not padded.
- Client sensor labels cannot disable physical reference/OOD checks. Acquisition
  provenance is chosen by the server adapter.
- Non-normalized units require explicit finite affine normalization and a named
  reference. This records a declaration, not a verified physical transfer function.
- Candidate, beam, rollout, cache and acquisition allocations are bounded.
  Metadata is JSON-only, finite, size/depth bounded and rejects unknown fields.
- Device paths are restricted to discovered serial ports. Per-device locks
  serialize access. Emergency latch, no-go geometry and drive limits are checked
  before physical acquisition begins.

The UI dispatches emergency-stop requests even during a pending acquisition and
preserves an acknowledged latch against late responses. An already-running
hardware action is not interrupted: session/device locks span acquisition. A
real apparatus requires an independently tested physical emergency interlock.

## Models, bundles and evidence

The current trainer writes pickle-free ZIP/NPY/JSON forward checkpoints. Readers
preflight member counts, expanded size, paths, NPY dimensions/dtypes, hashes,
finite weights and normalization scales. Historical torch/pickle checkpoints
are refused without deserializing or silently converting them. Retrain using
the current trainer. Safe round-trip prediction is covered by regression tests.

Imported bundles and replay banks are checked before state hydration. Bounded
zlib decoding prevents stored-waveform decompression from growing without a
limit. Replay requires sealed truth and recorded compatible actions; explicitly
labelled reference recordings alone may be used as calibration evidence.

Ledger schema 2 binds planner and diagnostic metadata as well as waveform,
analysis and posterior content. Software identity includes dirty and untracked
source bytes, not just Git HEAD. Hashes establish consistency, not authorship,
sensor authenticity or trusted time. Retain an independent checkpoint if full
history replacement is in scope.

## Dependency verification boundary

Next.js was patched to 16.3.8 following the publisher's September 2026 release.
The project virtual environment uses PyTorch 2.6.0+cpu, which closes the published
<=2.5.1 checkpoint-loading issue. Pickle-based readers were removed independently
of that package update. The newest tested CPU build failed Windows DLL integration;
the working release was deliberately pinned to the compatible patched version.

Online npm audit was rejected by automatic approval review because sending
dependency metadata requires explicit user permission. Until that permission is
received, no complete transitive-advisory audit is claimed. Public advisories and
local lockfile/source checks informed the fixes; an unperformed audit is not
reported as zero vulnerabilities.

Sources: [Next.js publisher release](https://nextjs.org/blog/september-2026-security-release),
[PyTorch publisher advisory GHSA-53q9-r3pm-6pq6](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6).
