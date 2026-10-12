export const MAX_CALIBRATION_JSON_BYTES = 32 * 1024;

/** An operator declaration referencing an external bench record; no invented defaults. */
export interface ProbeTimingCalibration {
  device_id: string;
  sample_rate_hz: number;
  calibration_id: string;
  calibrated_at_utc: string;
  reference_sha256: string;
  operator: string;
  drive_family: 'DAC8_SAMPLED_SINE';
  max_sample_jitter_us: number;
  max_clock_error_ppm: number;
  max_trigger_alignment_error_us: number;
  max_drive_code_error: number;
  arrival_adapter_validated: true;
}

const fields = ['device_id', 'sample_rate_hz', 'calibration_id', 'calibrated_at_utc', 'reference_sha256', 'operator',
  'drive_family', 'max_sample_jitter_us', 'max_clock_error_ppm', 'max_trigger_alignment_error_us',
  'max_drive_code_error', 'arrival_adapter_validated'].sort();

export function parseProbeTimingCalibration(text: string, now = Date.now()): ProbeTimingCalibration {
  if (new TextEncoder().encode(text).byteLength > MAX_CALIBRATION_JSON_BYTES) throw new Error('Calibration JSON exceeds 32 KiB.');
  let value: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(text.replace(/^\uFEFF/, ''));
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
    value = parsed as Record<string, unknown>;
  } catch { throw new Error('Use a complete JSON object from your recorded operator calibration.'); }
  if (JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(fields)) throw new Error('Calibration JSON must contain every supported field and no additional fields.');
  const isString = (name: string, minimum: number, maximum: number) => typeof value[name] === 'string'
    && (value[name] as string).trim().length >= minimum && (value[name] as string).length <= maximum;
  const numberIn = (name: string, minimum: number, maximum: number, integer = false) => typeof value[name] === 'number'
    && Number.isFinite(value[name]) && (value[name] as number) >= minimum && (value[name] as number) <= maximum
    && (!integer || Number.isInteger(value[name]));
  if (!isString('device_id', 29, 64) || !/^ESP32_DAC25_ADC34_[0-9a-f]{12}$/.test(value.device_id as string)
      || !isString('calibration_id', 3, 128) || !/^[A-Za-z0-9_.:-]+$/.test(value.calibration_id as string)
      || !isString('operator', 3, 128) || !isString('reference_sha256', 64, 64) || !/^[0-9a-f]{64}$/.test(value.reference_sha256 as string)) {
    throw new Error('Calibration requires the chip ID, bounded operator/calibration identifiers, and a reference SHA256.');
  }
  if (value.drive_family !== 'DAC8_SAMPLED_SINE' || value.arrival_adapter_validated !== true) {
    throw new Error('The operator must explicitly attest the supported arrival and DAC drive adapter against external bench evidence.');
  }
  if (!numberIn('sample_rate_hz', 1000, 16000, true) || !numberIn('max_clock_error_ppm', Number.MIN_VALUE, 1000)
      || !numberIn('max_drive_code_error', 0, 2, true)) throw new Error('Unsupported sample rate, clock bound, or DAC tolerance.');
  const timingLimit = Math.min(20, 250000 / (value.sample_rate_hz as number));
  if (!numberIn('max_sample_jitter_us', Number.MIN_VALUE, timingLimit)
      || !numberIn('max_trigger_alignment_error_us', Number.MIN_VALUE, timingLimit)) {
    throw new Error('Timing bounds must be positive, at most 20 microseconds, and at most one quarter of the sample period.');
  }
  const dated = value.calibrated_at_utc;
  if (typeof dated !== 'string' || dated.length > 48 || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(dated)) {
    throw new Error('Calibration time must include its ISO-8601 timezone.');
  }
  const observed = Date.parse(dated);
  if (!Number.isFinite(observed) || observed < now - 90 * 86400000 || observed > now + 300000) {
    throw new Error('Calibration is expired or dated in the future. The 90-day limit is an operator policy.');
  }
  return value as unknown as ProbeTimingCalibration;
}
