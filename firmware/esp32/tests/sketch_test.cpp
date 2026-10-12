#include "Arduino.h"
#include "../argus_probe.ino"
#include <cassert>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

const std::string command = "EXPERIMENT2 " + std::string(32, '0') + " " + std::string(64, 'a') + " 1200 3000 0.28 120000 CHIRP 16000 16";
void resetAll() { resetMock(); stopLatched = false; }

int main(int argc, char** argv) {
  resetAll(); setup();
  assert(Serial.output == "ARGUS_PROBE_READY,2\n");
  Serial.output.clear(); handleCommand(command.c_str());
  assert(mockReads.size() == 1936);
  for (size_t i = 0; i < 16; ++i) assert(mockReads[i].code == 128);
  bool droveDuringAcquisition = false;
  for (size_t i = 16; i < 176; ++i) if (mockReads[i].code != 128) droveDuringAcquisition = true;
  assert(droveDuringAcquisition);
  for (size_t i = 176; i < 1936; ++i) assert(mockReads[i].code == 128);
  assert(mockDacCode == 128);
  assert(mockTriggerCode == LOW);
  assert(Serial.output.find(",OK,") != std::string::npos);
  std::istringstream frame(Serial.output);
  std::string line; uint32_t count = 0, previous = 0, checksum = 2166136261u;
  while (std::getline(frame, line)) {
    if (line.rfind("DATA2,", 0) == 0) {
      unsigned index, elapsed, adc, drive;
      assert(std::sscanf(line.c_str(), "DATA2,%u,%u,%u,%u", &index, &elapsed, &adc, &drive) == 4);
      assert(index == count && (count == 0 ? elapsed == 0 : elapsed > previous));
      checksum = argus::checksumUpdate(checksum, index, elapsed, static_cast<uint16_t>(adc), static_cast<uint8_t>(drive));
      previous = elapsed; ++count;
    } else if (line.rfind("END2,", 0) == 0) {
      char id[33], status[32]; unsigned wireCount, maximumLate; unsigned long wireChecksum;
      assert(std::sscanf(line.c_str(), "END2,%32[^,],%u,%lx,%31[^,],%u", id, &wireCount, &wireChecksum, status, &maximumLate) == 5);
      assert(wireCount == count && wireChecksum == checksum && std::strcmp(status, "OK") == 0);
      assert(maximumLate <= argus::latenessLimitUs(16000));
    }
  }
  assert(count == 1936);
  if (argc > 1) { std::ofstream fixture(argv[1]); fixture << Serial.output; assert(fixture.good()); }
  resetAll(); mockStopAtAdc = 60; handleCommand(command.c_str());
  assert(mockReads.size() == 60 && stopLatched && mockDacCode == 128);
  assert(Serial.output.find(",STOPPED,") != std::string::npos);
  Serial.output.clear(); handleCommand(command.c_str());
  assert(Serial.output == "ERROR,STOP_LATCHED\n");
  handleCommand("RESET_STOP"); assert(stopLatched);
  resetAll(); mockAdcCostUs = 200; handleCommand(command.c_str());
  assert(mockReads.size() < 1936 && mockDacCode == 128);
  assert(Serial.output.find(",OVERRUN,") != std::string::npos);
  resetAll(); handleCommand("EXPERIMENT 1200 0.28 120 CHIRP 16000");
  assert(mockReads.empty() && Serial.output == "ERROR,BAD_COMMAND\n");
  resetAll(); handleCommand("PING"); handleCommand("CAPABILITIES");
  assert(Serial.output.find("PONG,ARGUS_PROBE,2") != std::string::npos);
  assert(Serial.output.find("ESP32_DAC25_ADC34_001122334455") != std::string::npos);
  assert(Serial.output.find("DAC8_SAMPLED_SINE,CHIRP|TONE_BURST,16") != std::string::npos);
  resetAll(); mockTimeUs = UINT32_MAX - 300; handleCommand(command.c_str());
  assert(mockReads.size() == 1936 && Serial.output.find(",OK,") != std::string::npos);
  std::cout << "Full sketch mock passed: overlapping drive/capture, pretrigger, frame integrity, STOP, overrun, rollover.\n";
}
