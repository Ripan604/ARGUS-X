# Two-laptop distributed demo

Laptop A runs the planner, API, SQLite state, evidence ledger, and dashboard:

```powershell
python run_argus.py --lan
```

Create a **physical** session and note its ID, printed Edge API address, and
operator access key. On Laptop B, install the backend requirements, set
ARGUS_API_TOKEN to the launcher key in that terminal, and run:

```powershell
python run_edge_node.py --server http://192.168.1.20:8000 --session SESSION_ID
```

This monitor mode registers capabilities, heartbeats, retrieves experiment instructions, prints TX/RX placement, and reconnects with bounded backoff. To record the default microphone once for each newly observed instruction:

```powershell
python run_edge_node.py --server http://192.168.1.20:8000 --session SESSION_ID --auto-capture
```

Laptop B posts timestamps, samples, node metadata, and the exact experiment specification through the same physical-session path used by phone/WAV/serial acquisition. Laptop A performs quality gating, joint update, next planning, persistence, and ledger append. The phone may simultaneously provide visual guidance.

Use a trusted private LAN. Shared mode now requires an operator key and exact
origin/host settings; it is not multi-user authentication and does not encrypt
HTTP traffic. Use TLS for untrusted networks or phone microphone/camera capture.
Microphone failure is reported and retried; no synthetic signal replaces it.
