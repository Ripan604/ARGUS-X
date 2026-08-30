# Smartphone probe

Start ARGUS, create a physical session, and open the printed LAN URL `http://<Laptop-A-IP>:5173/probe` on a phone connected to the same trusted Wi-Fi. Paste the session ID and press **Connect to ARGUS**.

The page detects microphone, camera, motion, orientation, touch, and WebSocket support. Permission denial leaves a manual fallback and never crashes the session. It displays capabilities, permission state, node/session identity, timestamps, connection/recording state, recommended TX/RX coordinates, and the planner explanation.

Camera registration uses four clockwise corner taps and bilinear panel mapping to overlay source, receiver, and current estimate. Manual X/Y sliders remain available. Microphone capture disables echo cancellation, noise suppression, and automatic gain where the browser permits, then uploads float samples with orientation, acceleration RMS, position, and timestamp metadata.

Phone audio is a commodity audio-range demonstration. It is not ultrasonic CFRP validation, a calibrated microphone, or a certified NDE result. Motion, coupling, placement, and signal-quality values are inferred proxies. Browser sensor support varies; iOS commonly requires a direct user gesture and HTTPS for some APIs. On a plain LAN HTTP origin, use the manual fallback if a browser blocks a sensor.

