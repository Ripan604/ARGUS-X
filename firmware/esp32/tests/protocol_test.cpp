#include "../argus_protocol.h"
#include <cassert>
#include <iostream>
#include <string>

const std::string ids = std::string(32, '0') + " " + std::string(64, 'a');
argus::Request parse(const std::string& parameters, bool accepted) {
  argus::Request request;
  const std::string line = "EXPERIMENT2 " + ids + " " + parameters;
  const char* error = argus::parseRequest(line.c_str(), request);
  assert((error == nullptr) == accepted);
  return request;
}

int main() {
  const auto request = parse("1200 3000 0.28 120000 CHIRP 16000 16", true);
  assert(argus::posttriggerCount(request) == 1920);
  assert(argus::burstCount(request) == 160);
  assert(argus::burstWindowUs(request) == 10000);
  assert(argus::sampleOffsetUs(16000, 16000) == 1000000);
  assert(argus::sampleOffsetUs(1, 16000) == 62);
  assert(argus::sampleOffsetUs(2, 16000) == 125);
  assert(argus::driveCode(request, 0) == 128);
  assert(argus::driveCode(request, 159) == 128);
  assert(argus::driveCode(request, 160) == 128);
  for (uint32_t rate : {1000u, 4000u, 8000u, 16000u}) {
    auto varied = request; varied.rate = rate; varied.startHz = 100; varied.endHz = rate * 0.35;
    assert(!argus::validateRequest(varied));
    uint32_t previous = 0;
    for (uint32_t i = 1; i < argus::posttriggerCount(varied); ++i) {
      const uint32_t now = argus::sampleOffsetUs(i, rate);
      assert(now > previous);
      assert(now - previous == 1000000 / rate || now - previous == 1000000 / rate + 1);
      previous = now;
    }
    for (double amplitude : {0.001, 0.28, 0.60}) {
      varied.amplitude = amplitude;
      for (uint32_t i = 0; i <= argus::burstCount(varied); ++i)
        assert(std::abs(static_cast<int>(argus::driveCode(varied, i)) - 128) <= std::ceil(127 * amplitude));
    }
  }
  parse("1200 3000 0.61 120000 CHIRP 16000 16", false);
  parse("1200 3000 nan 120000 CHIRP 16000 16", false);
  parse("1200 3000 0.28 120000 RICKER 16000 16", false);
  parse("1200 3000 0.28 120000 TONE_BURST 16000 16", false);
  parse("1200 3000 0.28 120000 CHIRP 1000 16", false);
  parse("1200 3000 0.28 300000 CHIRP 16000 16", false);
  parse("1200 3000 0.28 120000 CHIRP 16000 15", false);
  parse("1200 3000 0.28 4295087296 CHIRP 16000 16", false);
  parse("1200 3000 0.28 -4294847296 CHIRP 16000 16", false);
  parse("1200 3000 0.28 120000 CHIRP 16000 16 TRAILING", false);
  parse("1200x 3000 0.28 120000 CHIRP 16000 16", false);
  parse("1200 1200 0.28 120000 TONE_BURST 16000 16", true);
  argus::Request legacy;
  assert(argus::parseRequest("EXPERIMENT 1200 0.28 120 CHIRP 16000", legacy));
  const uint32_t first = argus::checksumUpdate(2166136261u, 0, 0, 2048, 128);
  assert(first != argus::checksumUpdate(2166136261u, 0, 0, 2049, 128));
  assert(first != argus::checksumUpdate(2166136261u, 0, 1, 2048, 128));
  assert(first != argus::checksumUpdate(2166136261u, 1, 0, 2048, 128));
  std::cout << "Protocol properties passed: strict parsing, bounded DAC, exact deadlines, unsupported families, checksums.\n";
}
