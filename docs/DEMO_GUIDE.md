# Judge demo: 3 minutes

## 0:00–0:25 — Frame the difference

“Most defect AI waits for a measurement and classifies it. ARGUS owns the experiment loop: it maintains uncertainty and decides which physical measurement is worth doing next.”

Start a **Medium** secret simulation. Point out that ground truth is locked.

## 0:25–1:20 — Let the loop speak

Run three to five experiments. For each:

1. Show the changing source, receiver, and frequency.
2. Read the generated “why this probe” explanation.
3. Point at the posterior and entropy reduction.
4. Open the planner audit once: every candidate has information, disagreement, cost, and final scores.

The key sentence: “It is not scanning a grid. It is choosing a geometry where its competing explanations predict different echoes.”

## 1:20–1:50 — Prove it is signal processing

Open Signal. Show the time response, FFT, spectrogram, noise/SNR, and decay features. State that the belief update matched-filters the defect residual and maps time of flight back to spatial likelihood.

## 1:50–2:15 — Reveal

When confidence stops the run, click **Reveal Ground Truth**. Quote the measured millimetre error and number of experiments. Never reveal early.

## 2:15–2:40 — Establish credibility

Open Belief Evolution and Benchmark. The benchmark is saved per-run JSON/CSV from the local simulator; do not overclaim field accuracy. Emphasize lower posterior entropy and auditable adaptive behavior.

## 2:40–3:00 — Hardware and expansion

Show Camera Align or the ESP32 probe. Close with: “Today it chooses acoustic experiments. The abstraction is modality-independent: tomorrow the same belief-and-planning loop can choose thermal, RF, impedance, or robotic tactile experiments.”

## Demo insurance

- Start both services before judges arrive and open `/health` once.
- Use seed 17/easy for a short guaranteed reveal; use medium for normal demo.
- Keep `python scripts/demo_simulation.py --preset easy --seed 17 --experiments 8` as the no-browser fallback.
- Do not promise real-world defect certification; call it a research prototype.
