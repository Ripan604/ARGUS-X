# Two-laptop distributed demo

Laptop A runs the planner, API, SQLite state, evidence ledger, and dashboard:

```powershell
.\run_argus.ps1
```

Create a **physical** session and note its ID and the printed Edge API address. On Laptop B, install the backend requirements and run:

```powershell
python run_edge_node.py --server http://192.168.1.20:8000 --session SESSION_ID
```

This monitor mode registers capabilities, heartbeats, retrieves experiment instructions, prints TX/RX placement, and reconnects with bounded backoff. To record the default microphone once for each newly observed instruction:

```powershell
python run_edge_node.py --server http://192.168.1.20:8000 --session SESSION_ID --auto-capture
```

Laptop B posts timestamps, samples, node metadata, and the exact experiment specification through the same physical-session path used by phone/WAV/serial acquisition. Laptop A performs quality gating, joint update, next planning, persistence, and ledger append. The phone may simultaneously provide visual guidance.

Use a trusted private LAN. The prototype has no multi-user authentication or TLS terminator. Do not expose port 8000/5173 to the public internet. Microphone permission/device failure is reported and retried; no synthetic signal is substituted for a failed physical capture.

