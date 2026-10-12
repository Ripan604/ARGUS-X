/* ARGUS v2 reference probe, classic ESP32 with Arduino core 2.x.
 * GPIO25 is an 8-bit DAC: use an AC-coupled external amplifier with hardware
 * amplitude limits. The DAC must never directly power an exciter.
 * GPIO34 receives a biased/protected 0..3.3 V sensor signal.
 * GPIO26 is a logic-only trigger marker for external timing instrumentation.
 * GPIO27 is a normally-high STOP input; ground it to disable the DAC waveform.
 * Compile/mock tests do not characterize ADC aperture, clock, DAC or actuator.
 */
#include <Arduino.h>
#include "argus_protocol.h"

constexpr uint8_t EXCITER_PIN = 25;
constexpr uint8_t SENSOR_PIN = 34;
constexpr uint8_t TRIGGER_PIN = 26;
constexpr uint8_t STOP_PIN = 27;
constexpr uint8_t STATUS_LED_PIN = 2;
constexpr uint32_t SERIAL_BAUD = 115200;
uint16_t adcSamples[argus::kMaximumSamples];
uint8_t driveCodes[argus::kMaximumSamples];
uint32_t sampleTimes[argus::kMaximumSamples];
bool stopLatched = false;

void idleDriver() { dacWrite(EXCITER_PIN, argus::kDacIdle); digitalWrite(TRIGGER_PIN, LOW); }

// Poll STOP while waiting/acquiring; other serial commands cannot start another drive.
bool captureStopRequested() {
  static char command[32];
  static uint8_t length = 0;
  if (digitalRead(STOP_PIN) == LOW) stopLatched = true;
  while (Serial.available()) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      command[length] = 0;
      if (std::strcmp(command, "STOP") == 0) stopLatched = true;
      length = 0;
    } else if (value != '\r') {
      if (length < sizeof(command) - 1) command[length++] = value;
      else { length = 0; stopLatched = true; }
    }
  }
  return stopLatched;
}

void runExperiment(const argus::Request& request) {
  const uint32_t requestedCount = request.pretrigger + argus::posttriggerCount(request);
  // Compute trigonometric/envelope work before entering the timed capture loop.
  for (uint32_t index = 0; index < requestedCount; ++index)
    driveCodes[index] = index < request.pretrigger ? argus::kDacIdle : argus::driveCode(request, index - request.pretrigger);
  uint32_t count = 0, firstRead = 0, triggerTime = 0, driveStart = 0, driveEnd = 0, maximumLate = 0;
  const char* status = "OK";
  bool driveStarted = false, driveEnded = false;
  idleDriver();
  digitalWrite(STATUS_LED_PIN, HIGH);
  const uint32_t began = micros();
  for (uint32_t index = 0; index < requestedCount; ++index) {
    const uint32_t deadline = began + argus::sampleOffsetUs(index, request.rate);
    while (static_cast<int32_t>(micros() - deadline) < 0) {
      if (captureStopRequested()) { status = "STOPPED"; break; }
    }
    if (captureStopRequested() || std::strcmp(status, "STOPPED") == 0) { status = "STOPPED"; break; }
    const uint32_t now = micros();
    const uint32_t late = now - deadline;
    if (late > maximumLate) maximumLate = late;
    if (late > argus::latenessLimitUs(request.rate)) { status = "OVERRUN"; break; }
    const uint8_t code = driveCodes[index];
    if (index == request.pretrigger) {
      driveStarted = true;
      triggerTime = micros();
      driveStart = triggerTime;
      digitalWrite(TRIGGER_PIN, HIGH);
    }
    if (index >= request.pretrigger && index - request.pretrigger >= argus::burstCount(request) && !driveEnded) {
      driveEnd = micros();
      driveEnded = true;
      digitalWrite(TRIGGER_PIN, LOW);
    }
    dacWrite(EXCITER_PIN, code);
    // Timestamp denotes analogRead call start; external validation must measure
    // actual ADC aperture and trigger-to-drive delay on the chosen board.
    const uint32_t readTime = micros();
    const uint16_t adc = static_cast<uint16_t>(analogRead(SENSOR_PIN));
    if (index == 0) firstRead = readTime;
    sampleTimes[count] = readTime - firstRead;
    adcSamples[count] = adc;
    driveCodes[count] = code;
    ++count;
    if (adc > 4095) { status = "ADC_RANGE_ERROR"; break; }
  }
  const uint32_t stoppedAt = micros();
  idleDriver();
  digitalWrite(STATUS_LED_PIN, LOW);
  if (driveStarted && !driveEnded) driveEnd = stoppedAt;
  if (count != requestedCount && std::strcmp(status, "OK") == 0) status = "INCOMPLETE";
  const uint32_t triggerOffset = driveStarted ? triggerTime - firstRead : 0;
  const uint32_t startOffset = driveStarted ? driveStart - firstRead : 0;
  const uint32_t endOffset = driveStarted ? driveEnd - firstRead : 0;
  Serial.printf("BEGIN2,%s,%s,%lu,%lu,12,DAC8_SAMPLED_SINE,%s,%lu,%lu,%.9g,%.9g,%.9g,%lu,%lu,%lu,%lu\n",
      request.id, request.experimentHash, static_cast<unsigned long>(count), static_cast<unsigned long>(request.rate), request.waveform,
      static_cast<unsigned long>(request.pretrigger), static_cast<unsigned long>(triggerOffset), request.startHz, request.endHz,
      request.amplitude, static_cast<unsigned long>(request.windowUs), static_cast<unsigned long>(argus::burstWindowUs(request)),
      static_cast<unsigned long>(startOffset), static_cast<unsigned long>(endOffset));
  uint32_t checksum = 2166136261u;
  for (uint32_t index = 0; index < count; ++index) {
    checksum = argus::checksumUpdate(checksum, index, sampleTimes[index], adcSamples[index], driveCodes[index]);
    Serial.printf("DATA2,%lu,%lu,%u,%u\n", static_cast<unsigned long>(index), static_cast<unsigned long>(sampleTimes[index]),
        static_cast<unsigned>(adcSamples[index]), static_cast<unsigned>(driveCodes[index]));
  }
  Serial.printf("END2,%s,%lu,%08lx,%s,%lu\n", request.id, static_cast<unsigned long>(count), static_cast<unsigned long>(checksum),
      status, static_cast<unsigned long>(maximumLate));
}

void handleCommand(const char* line) {
  if (std::strcmp(line, "PING") == 0) { Serial.println("PONG,ARGUS_PROBE,2"); return; }
  if (std::strcmp(line, "CAPABILITIES") == 0 || std::strcmp(line, "CAPS") == 0 || std::strcmp(line, "STATUS") == 0) {
    const unsigned long long identity = static_cast<unsigned long long>(ESP.getEfuseMac()) & 0xffffffffffffULL;
    Serial.printf("CAPS,2,ESP32_DAC25_ADC34_%012llx,16000,4096,12,concurrent_triggered,DAC8_SAMPLED_SINE,CHIRP|TONE_BURST,16\n", identity); return;
  }
  if (std::strcmp(line, "STOP") == 0) { stopLatched = true; idleDriver(); Serial.println("OK,STOPPED"); return; }
  if (std::strcmp(line, "RESET_STOP") == 0) {
    if (digitalRead(STOP_PIN) == LOW) { Serial.println("ERROR,INTERLOCK_ACTIVE"); return; }
    stopLatched = false; Serial.println("OK,STOP_RESET"); return;
  }
  argus::Request request;
  const char* error = argus::parseRequest(line, request);
  if (error) { Serial.printf("ERROR,%s\n", error); return; }
  if (stopLatched || digitalRead(STOP_PIN) == LOW) { stopLatched = true; idleDriver(); Serial.println("ERROR,STOP_LATCHED"); return; }
  runExperiment(request);
}

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT); pinMode(SENSOR_PIN, INPUT); pinMode(TRIGGER_PIN, OUTPUT); pinMode(STOP_PIN, INPUT_PULLUP);
  analogReadResolution(12); idleDriver();
  Serial.begin(SERIAL_BAUD); Serial.setTimeout(100);
  Serial.println("ARGUS_PROBE_READY,2");
}

void loop() {
  static char line[256];
  static uint16_t length = 0;
  static bool overflow = false;
  if (digitalRead(STOP_PIN) == LOW) { stopLatched = true; idleDriver(); }
  while (Serial.available()) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      line[length] = 0;
      if (overflow) Serial.println("ERROR,COMMAND_TOO_LONG");
      else handleCommand(line);
      length = 0; overflow = false;
    } else if (value != '\r') {
      if (length < sizeof(line) - 1) line[length++] = value;
      else overflow = true;
    }
  }
}
