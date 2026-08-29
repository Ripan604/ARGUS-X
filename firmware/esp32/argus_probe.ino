/* ARGUS reference probe firmware (ESP32 Arduino core 2.x)
 * Commands: PING, STATUS, EXCITE, READ, EXPERIMENT, STOP
 * The serial protocol is deliberately text-based and inspectable.
 */

#include <Arduino.h>

constexpr uint8_t EXCITER_PIN = 25;
constexpr uint8_t SENSOR_PIN = 34;
constexpr uint8_t STATUS_LED_PIN = 2;
constexpr uint8_t PWM_CHANNEL = 0;
constexpr uint16_t MAX_SAMPLES = 4096;
constexpr uint32_t SERIAL_BAUD = 115200;

uint16_t samples[MAX_SAMPLES];
volatile bool stopRequested = false;

void setExciter(float frequency, float amplitude) {
  if (frequency <= 0 || amplitude <= 0) {
    ledcWriteTone(PWM_CHANNEL, 0);
    ledcWrite(PWM_CHANNEL, 0);
    return;
  }
  ledcWriteTone(PWM_CHANNEL, frequency);
  ledcWrite(PWM_CHANNEL, constrain(static_cast<int>(amplitude * 255), 0, 255));
}

void excite(float startHz, float amplitude, uint32_t durationMs, const String &waveform) {
  stopRequested = false;
  const uint32_t started = millis();
  if (waveform == "IMPULSE") {
    setExciter(startHz, amplitude);
    delay(min(durationMs, static_cast<uint32_t>(8)));
    setExciter(0, 0);
    if (durationMs > 8) delay(durationMs - 8);
    return;
  }
  while (!stopRequested && millis() - started < durationMs) {
    const float fraction = static_cast<float>(millis() - started) / max(durationMs, static_cast<uint32_t>(1));
    const float frequency = waveform == "CHIRP" ? startHz * (1.0f + 1.6f * fraction) : startHz;
    setExciter(frequency, amplitude);
    delay(2);
  }
  setExciter(0, 0);
}

uint16_t acquireSamples(uint32_t durationMs, uint32_t requestedRate) {
  const uint32_t sampleRate = constrain(requestedRate, 500, 16000);
  const uint16_t count = min(static_cast<uint32_t>(MAX_SAMPLES), durationMs * sampleRate / 1000);
  const uint32_t intervalUs = 1000000UL / sampleRate;
  uint32_t nextSample = micros();
  for (uint16_t index = 0; index < count && !stopRequested; index++) {
    while (static_cast<int32_t>(micros() - nextSample) < 0) yield();
    samples[index] = analogRead(SENSOR_PIN);
    nextSample += intervalUs;
  }
  return count;
}

void emitSamples(uint16_t count, uint32_t sampleRate) {
  Serial.printf("BEGIN,%u,%lu\n", count, sampleRate);
  for (uint16_t index = 0; index < count; index++) {
    Serial.printf("DATA,%u,%u\n", index, samples[index]);
  }
  Serial.println("END");
}

void handleCommand(String command) {
  command.trim();
  if (command == "PING") { Serial.println("PONG,ARGUS_PROBE,1"); return; }
  if (command == "STATUS") {
    Serial.printf("STATUS,READY,SENSOR_PIN=%u,EXCITER_PIN=%u,MAX_SAMPLES=%u\n", SENSOR_PIN, EXCITER_PIN, MAX_SAMPLES);
    return;
  }
  if (command == "STOP") { stopRequested = true; setExciter(0, 0); Serial.println("OK,STOPPED"); return; }

  char buffer[160]; command.toCharArray(buffer, sizeof(buffer));
  char operation[16] = {0}, waveform[16] = {0};
  float frequency = 0, amplitude = 0; unsigned long durationMs = 0, sampleRate = 0;
  const int fields = sscanf(buffer, "%15s %f %f %lu %15s %lu", operation, &frequency, &amplitude, &durationMs, waveform, &sampleRate);
  if (strcmp(operation, "EXCITE") == 0 && fields >= 5) {
    digitalWrite(STATUS_LED_PIN, HIGH); excite(frequency, amplitude, durationMs, String(waveform)); digitalWrite(STATUS_LED_PIN, LOW); Serial.println("OK,EXCITE"); return;
  }
  if (strcmp(operation, "READ") == 0 && fields >= 3) {
    // READ <duration_ms> <sample_rate>
    unsigned long readDuration = static_cast<unsigned long>(frequency);
    unsigned long readRate = static_cast<unsigned long>(amplitude);
    stopRequested = false; emitSamples(acquireSamples(readDuration, readRate), readRate); return;
  }
  if (strcmp(operation, "EXPERIMENT") == 0 && fields >= 6) {
    stopRequested = false; digitalWrite(STATUS_LED_PIN, HIGH);
    // Excite briefly, then acquire the decay/echo response. For simultaneous
    // acquisition, connect an external actuator driver with its own trigger.
    excite(frequency, amplitude, min(durationMs, 12UL), String(waveform));
    uint16_t count = acquireSamples(durationMs, sampleRate); digitalWrite(STATUS_LED_PIN, LOW); emitSamples(count, sampleRate); return;
  }
  Serial.println("ERROR,BAD_COMMAND");
}

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT); pinMode(SENSOR_PIN, INPUT);
  analogReadResolution(12); ledcSetup(PWM_CHANNEL, 2000, 8); ledcAttachPin(EXCITER_PIN, PWM_CHANNEL);
  Serial.begin(SERIAL_BAUD); Serial.setTimeout(100); delay(200); Serial.println("ARGUS_PROBE_READY");
}

void loop() {
  if (Serial.available()) handleCommand(Serial.readStringUntil('\n'));
}
