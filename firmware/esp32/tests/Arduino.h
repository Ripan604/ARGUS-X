#pragma once
// Deterministic host mock. This is not the Arduino/ESP32 board SDK.
#include <cstdint>
#include <cstdarg>
#include <cstdio>
#include <deque>
#include <string>
#include <vector>

constexpr uint8_t INPUT = 0, OUTPUT = 1, INPUT_PULLUP = 2, LOW = 0, HIGH = 1;
inline uint32_t mockTimeUs = 0;
inline uint32_t mockAdcCalls = 0;
inline uint32_t mockAdcCostUs = 8;
inline uint32_t mockStopAtAdc = UINT32_MAX;
inline bool mockInterlock = false;
inline uint8_t mockDacCode = 128;
inline uint8_t mockTriggerCode = LOW;
struct MockAdcRead { uint32_t time; uint8_t code; };
inline std::vector<MockAdcRead> mockReads;

inline uint32_t micros() { return mockTimeUs++; }
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t pin, uint8_t code) { if (pin == 26) mockTriggerCode = code; }
inline int digitalRead(uint8_t) { return mockInterlock || mockAdcCalls >= mockStopAtAdc ? LOW : HIGH; }
inline void analogReadResolution(uint8_t) {}
inline void dacWrite(uint8_t, uint8_t code) { mockDacCode = code; mockTimeUs += 2; }
inline int analogRead(uint8_t) {
  mockReads.push_back({mockTimeUs, mockDacCode});
  mockTimeUs += mockAdcCostUs;
  ++mockAdcCalls;
  return 2048 + (static_cast<int>(mockDacCode) - 128) * 4;
}

class MockSerial {
 public:
  std::deque<char> input;
  std::string output;
  void begin(uint32_t) {}
  void setTimeout(uint32_t) {}
  int available() const { return static_cast<int>(input.size()); }
  int read() { const char value = input.front(); input.pop_front(); return value; }
  void println(const char* text) { output += text; output += '\n'; }
  void printf(const char* format, ...) {
    char line[768]; va_list arguments; va_start(arguments, format);
    const int length = std::vsnprintf(line, sizeof(line), format, arguments); va_end(arguments);
    if (length > 0 && static_cast<size_t>(length) < sizeof(line)) output.append(line, static_cast<size_t>(length));
  }
};
inline MockSerial Serial;
struct MockESP { uint64_t getEfuseMac() const { return 0x001122334455ULL; } };
inline MockESP ESP;

inline void resetMock() {
  mockTimeUs = 0; mockAdcCalls = 0; mockAdcCostUs = 8;
  mockStopAtAdc = UINT32_MAX; mockInterlock = false; mockDacCode = 128; mockTriggerCode = LOW;
  mockReads.clear(); Serial.input.clear(); Serial.output.clear();
}
