#pragma once

// Portable, allocation-free protocol and waveform logic for the reference probe.
// This code describes a sampled DAC waveform, not a calibrated actuator output.
#include <cmath>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace argus {
constexpr uint32_t kMaximumRate = 16000;
constexpr uint32_t kMinimumRate = 1000;
constexpr uint32_t kMaximumSamples = 4096;
constexpr uint32_t kMaximumWindowUs = 250000;
constexpr uint32_t kMinimumWindowUs = 20000;
constexpr uint32_t kPretriggerSamples = 16;
constexpr double kMaximumAmplitude = 0.60;
constexpr uint8_t kDacIdle = 128;
constexpr double kPi = 3.14159265358979323846;

struct Request {
  char id[33] = {};
  char experimentHash[65] = {};
  double startHz = 0;
  double endHz = 0;
  double amplitude = 0;
  uint32_t windowUs = 0;
  char waveform[16] = {};
  uint32_t rate = 0;
  uint32_t pretrigger = 0;
};

inline bool isLowerHex(const char* value, size_t length) {
  if (std::strlen(value) != length) return false;
  for (size_t i = 0; i < length; ++i)
    if (!((value[i] >= '0' && value[i] <= '9') || (value[i] >= 'a' && value[i] <= 'f'))) return false;
  return true;
}

inline uint32_t posttriggerCount(const Request& request) {
  return static_cast<uint32_t>((static_cast<uint64_t>(request.windowUs) * request.rate + 500000) / 1000000);
}

inline uint32_t burstCount(const Request& request) {
  const double burstUs = std::fmin(10000.0, request.windowUs * 0.22);
  const uint32_t count = static_cast<uint32_t>(std::floor(burstUs * request.rate / 1000000.0 + 0.5));
  return count < 16 ? 16 : count;
}

inline uint32_t burstWindowUs(const Request& request) {
  return static_cast<uint32_t>((static_cast<uint64_t>(burstCount(request)) * 1000000 + request.rate / 2) / request.rate);
}

inline const char* validateRequest(const Request& request) {
  if (!isLowerHex(request.id, 32) || !isLowerHex(request.experimentHash, 64)) return "INVALID_ID_OR_HASH";
  if (!std::isfinite(request.startHz) || !std::isfinite(request.endHz) || !std::isfinite(request.amplitude)) return "NONFINITE_PARAMETER";
  if (request.rate < kMinimumRate || request.rate > kMaximumRate) return "RATE_LIMIT";
  if (request.windowUs < kMinimumWindowUs || request.windowUs > kMaximumWindowUs) return "WINDOW_LIMIT";
  if (request.pretrigger != kPretriggerSamples) return "PRETRIGGER_UNSUPPORTED";
  if (request.amplitude <= 0 || request.amplitude > kMaximumAmplitude) return "AMPLITUDE_LIMIT";
  if (request.startHz < 100 || request.endHz < request.startHz || request.endHz > 6000 || request.endHz > request.rate * 0.40) return "BAND_LIMIT";
  if (std::strcmp(request.waveform, "CHIRP") != 0 && std::strcmp(request.waveform, "TONE_BURST") != 0) return "UNSUPPORTED_WAVEFORM";
  if (std::strcmp(request.waveform, "TONE_BURST") == 0 && request.startHz != request.endHz) return "TONE_ENDPOINT_MISMATCH";
  if (posttriggerCount(request) + request.pretrigger > kMaximumSamples) return "BUFFER_LIMIT";
  if (burstCount(request) >= posttriggerCount(request)) return "MISSING_QUIET_WINDOW";
  return nullptr;
}

inline bool unsignedToken(const char* token, uint32_t& result) {
  if (!*token) return false;
  for (const char* p = token; *p; ++p) if (*p < '0' || *p > '9') return false;
  errno = 0;
  const unsigned long long parsed = std::strtoull(token, nullptr, 10);
  if (errno || parsed > UINT32_MAX) return false;
  result = static_cast<uint32_t>(parsed);
  return true;
}

inline bool doubleToken(const char* token, double& result) {
  char* end = nullptr;
  errno = 0;
  result = std::strtod(token, &end);
  return !errno && *token && end && !*end && std::isfinite(result);
}

inline const char* parseRequest(const char* line, Request& request) {
  char operation[16] = {};
  char extra = 0;
  char start[32] = {}, end[32] = {}, amplitude[32] = {}, window[24] = {}, rate[24] = {}, pretrigger[24] = {};
  const int fields = std::sscanf(line, "%15s %32s %64s %31s %31s %31s %23s %15s %23s %23s %c", operation,
      request.id, request.experimentHash, start, end, amplitude, window, request.waveform, rate, pretrigger, &extra);
  if (fields != 10 || std::strcmp(operation, "EXPERIMENT2") != 0) return "BAD_COMMAND";
  if (!unsignedToken(window, request.windowUs) || !unsignedToken(rate, request.rate) || !unsignedToken(pretrigger, request.pretrigger)
      || !doubleToken(start, request.startHz) || !doubleToken(end, request.endHz) || !doubleToken(amplitude, request.amplitude)) return "INVALID_NUMERIC_TOKEN";
  return validateRequest(request);
}

inline uint32_t sampleOffsetUs(uint32_t index, uint32_t rate) {
  // Rational deadlines avoid a 16 kHz request becoming 16129 Hz through integer truncation.
  return static_cast<uint32_t>((static_cast<uint64_t>(index) * 1000000) / rate);
}

inline uint32_t latenessLimitUs(uint32_t rate) {
  const uint32_t quarterPeriod = 1000000 / (4 * rate);
  return quarterPeriod > 2 ? quarterPeriod : 2;
}

inline uint8_t driveCode(const Request& request, uint32_t posttriggerIndex) {
  const uint32_t count = burstCount(request);
  if (posttriggerIndex >= count) return kDacIdle;
  const double ratio = static_cast<double>(posttriggerIndex) / (count - 1);
  const double alpha = 0.45;
  double envelope = 1;
  if (ratio < alpha / 2) envelope = 0.5 * (1 + std::cos(kPi * (2 * ratio / alpha - 1)));
  else if (ratio > 1 - alpha / 2) envelope = 0.5 * (1 + std::cos(kPi * (2 * ratio / alpha - 2 / alpha + 1)));
  const double t = static_cast<double>(posttriggerIndex) / request.rate;
  const double endTime = static_cast<double>(count - 1) / request.rate;
  double phase = 2 * kPi * request.startHz * t;
  if (std::strcmp(request.waveform, "CHIRP") == 0) {
    // scipy.signal.chirp starts at phase zero => cosine, with exact requested endpoints.
    const double slope = (request.endHz - request.startHz) / endTime;
    phase += kPi * slope * t * t;
  }
  const double wave = std::strcmp(request.waveform, "CHIRP") == 0 ? std::cos(phase) : std::sin(phase);
  const int code = static_cast<int>(std::lround(kDacIdle + 127 * request.amplitude * envelope * wave));
  return static_cast<uint8_t>(code < 0 ? 0 : (code > 255 ? 255 : code));
}

inline uint32_t checksumUpdate(uint32_t checksum, uint32_t index, uint32_t elapsedUs, uint16_t adc, uint8_t drive) {
  char canonical[64];
  const int size = std::snprintf(canonical, sizeof(canonical), "%lu,%lu,%u,%u\n",
      static_cast<unsigned long>(index), static_cast<unsigned long>(elapsedUs), static_cast<unsigned>(adc), static_cast<unsigned>(drive));
  for (int i = 0; i < size; ++i) {
    checksum ^= static_cast<uint8_t>(canonical[i]);
    checksum *= 16777619u;
  }
  return checksum;
}
}  // namespace argus
