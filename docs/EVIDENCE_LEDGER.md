# Evidence ledger and research bundles

Every accepted or explicitly rejected acquisition attempt persisted as an experiment receives a SHA-256 record containing session/step/time, previous record hash, experiment/action, acquisition source, raw/processed/likelihood/posterior hashes, preprocessing configuration, model identity/fidelity, planner score decomposition, nuisance/calibration/quality/OOD/discrepancy state, software revision, and seed.

```text
entry_hash[n] = SHA256(canonical_JSON(entry[n]))
entry[n].previous_record_hash = entry_hash[n-1]
```

`GET /api/ledger/{session}/verify` recomputes every hash and link and reports `PASS` or the first failed record. This is a tamper-evident research hash chain, not a blockchain, digital signature, access-control system, or certification record. An attacker who can rewrite the database and an external head-hash record can rewrite the chain; archive/export hashes externally when stronger provenance is needed.

Research bundle export creates a ZIP containing session, experiment metadata, `.npy` signals, audit chain, events, posterior history, configuration, result summary, README, and a per-file size/SHA-256 manifest. Import rejects traversal paths, oversized expanded content, missing/tampered files, and verifies the manifest before database writes. If the original session ID already exists, the importer creates a new ID and does not pretend the original ledger identity is preserved.

