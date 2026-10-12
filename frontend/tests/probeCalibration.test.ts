import assert from 'node:assert/strict';
import test from 'node:test';
import { MAX_CALIBRATION_JSON_BYTES, parseProbeTimingCalibration } from '../utils/probeCalibration.ts';
import { argusApi } from '../services/api.ts';

const now = Date.parse('2026-10-07T00:00:00Z');
const record = {
  device_id: 'ESP32_DAC25_ADC34_001122334455', sample_rate_hz: 16000,
  calibration_id: 'fixture-record-001', calibrated_at_utc: '2026-10-06T00:00:00Z',
  reference_sha256: 'a'.repeat(64), operator: 'Fixture operator', drive_family: 'DAC8_SAMPLED_SINE',
  max_sample_jitter_us: 5, max_clock_error_ppm: 100, max_trigger_alignment_error_us: 5,
  max_drive_code_error: 2, arrival_adapter_validated: true,
};

test('operator record requires complete bounded provenance without invented fields', () => {
  assert.deepEqual(parseProbeTimingCalibration(JSON.stringify(record), now), record);
  assert.deepEqual(parseProbeTimingCalibration('\uFEFF' + JSON.stringify(record), now), record);
  for (const change of [
    { arrival_adapter_validated: false }, { arrival_adapter_validated: 1 },
    { device_id: 'ESP32_DAC25_ADC34' }, { drive_family: 'PWM_SQUARE' },
    { sample_rate_hz: 16000.5 }, { sample_rate_hz: 20000 }, { max_clock_error_ppm: 1001 },
    { max_sample_jitter_us: true }, { max_trigger_alignment_error_us: 20 },
    { max_drive_code_error: 3 }, { reference_sha256: ['a'.repeat(64)] },
    { calibrated_at_utc: '2026-01-01T00:00:00Z' }, { calibrated_at_utc: '2026-10-08T00:00:00Z' },
    { calibrated_at_utc: '2026-10-06T00:00:00' }, { extra_self_certification: true },
  ]) assert.throws(() => parseProbeTimingCalibration(JSON.stringify({ ...record, ...change }), now));
  const missing = { ...record } as Partial<typeof record>;
  delete missing.reference_sha256;
  assert.throws(() => parseProbeTimingCalibration(JSON.stringify(missing), now));
});

test('calibration size is measured in bytes before JSON parsing', () => {
  assert.throws(() => parseProbeTimingCalibration(' '.repeat(MAX_CALIBRATION_JSON_BYTES + 1), now), /32 KiB/);
  assert.throws(() => parseProbeTimingCalibration('é'.repeat(MAX_CALIBRATION_JSON_BYTES / 2 + 1), now), /32 KiB/);
});

test('serial reconnect forwards the selected operator record and microphone needs no record', async (context) => {
  const calls: RequestInit[] = [];
  context.mock.method(globalThis, 'fetch', async (_url: string, init: RequestInit) => { calls.push(init); return Response.json({ connected: true }); });
  const calibration = parseProbeTimingCalibration(JSON.stringify(record), now);
  await argusApi.connectDevice('serial_probe', calibration);
  await argusApi.connectDevice('serial_probe', calibration);
  await argusApi.connectDevice('microphone');
  assert.deepEqual(JSON.parse(String(calls[0].body)).timing_calibration, record);
  assert.deepEqual(JSON.parse(String(calls[1].body)).timing_calibration, record);
  assert.ok(!('timing_calibration' in JSON.parse(String(calls[2].body))));
});

test('optional WAV timing declaration is serialized as a separate multipart field', async (context) => {
  let form: FormData | undefined;
  context.mock.method(globalThis, 'fetch', async (_url: string, init: RequestInit) => { form = init.body as FormData; return Response.json({ state: {} }); });
  const metadata = { acquisition_timing: { kind: 'trigger_aligned_recording' } };
  await argusApi.uploadWav('physical-test', new Blob(['recording']), undefined, metadata);
  assert.deepEqual(JSON.parse(String(form?.get('sensor_metadata_json'))), metadata);
});
