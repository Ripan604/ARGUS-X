export const MATERIALS = {
  aluminum: { label: 'Aluminum 6061', densityKgM3: 2700, youngsModulusGPa: 69, poissonRatio: 0.33, lossFactor: 0.006 },
  steel: { label: 'Mild steel', densityKgM3: 7850, youngsModulusGPa: 200, poissonRatio: 0.29, lossFactor: 0.004 },
  acrylic: { label: 'Acrylic sheet', densityKgM3: 1180, youngsModulusGPa: 3.2, poissonRatio: 0.35, lossFactor: 0.032 },
  plywood: { label: 'Birch plywood', densityKgM3: 680, youngsModulusGPa: 10, poissonRatio: 0.30, lossFactor: 0.045 },
  glass: { label: 'Soda-lime glass', densityKgM3: 2500, youngsModulusGPa: 70, poissonRatio: 0.23, lossFactor: 0.008 },
} as const;

export type MaterialKey = keyof typeof MATERIALS;
export type DefectType = 'mass_loading' | 'delamination' | 'crack' | 'damping_patch';
export type SensorMode = 'phone_microphone' | 'contact_accelerometer';

export interface NormalizedPoint {
  x: number;
  y: number;
}

export interface VirtualExperimentConfig {
  material: MaterialKey;
  panelWidthMm: number;
  panelHeightMm: number;
  thicknessMm: number;
  source: NormalizedPoint;
  receiver: NormalizedPoint;
  defect: NormalizedPoint;
  defectType: DefectType;
  defectRadiusMm: number;
  defectSeverity: number;
  impactEnergyJ: number;
  centerFrequencyHz: number;
  noiseFloorDb: number;
  boundaryReflectivity: number;
  sensorGain: number;
  sensorMode: SensorMode;
  sampleRateHz: number;
  durationMs: number;
  velocityScale: number;
  seed: number;
}

export interface SimulationPath {
  id: string;
  label: string;
  kind: 'direct' | 'scatter' | 'reflection';
  lengthM: number;
  arrivalMs: number;
  relativeGain: number;
}

export interface SpectrumPoint {
  frequencyHz: number;
  magnitudeDb: number;
}

export interface VirtualSimulation {
  config: VirtualExperimentConfig;
  samples: number[];
  spectrum: SpectrumPoint[];
  paths: SimulationPath[];
  metrics: {
    groupVelocityMps: number;
    flexuralRigidityNm: number;
    wavelengthMm: number;
    directPathM: number;
    scatterPathM: number;
    directArrivalMs: number;
    scatterArrivalMs: number;
    scatterDelayUs: number;
    rms: number;
    peakAmplitude: number;
    peakFrequencyHz: number;
    timeResolutionUs: number;
    defectIntercept: number;
    clipped: boolean;
  };
}

export const DEFAULT_VIRTUAL_CONFIG: VirtualExperimentConfig = {
  material: 'aluminum',
  panelWidthMm: 600,
  panelHeightMm: 400,
  thicknessMm: 3,
  source: { x: 0.16, y: 0.24 },
  receiver: { x: 0.84, y: 0.76 },
  defect: { x: 0.58, y: 0.48 },
  defectType: 'mass_loading',
  defectRadiusMm: 22,
  defectSeverity: 0.55,
  impactEnergyJ: 0.6,
  centerFrequencyHz: 6000,
  noiseFloorDb: -42,
  boundaryReflectivity: 0.3,
  sensorGain: 1,
  sensorMode: 'phone_microphone',
  sampleRateHz: 48000,
  durationMs: 120,
  velocityScale: 1,
  seed: 604,
};

const DEFECT_SCATTER: Record<DefectType, number> = {
  mass_loading: 0.72,
  delamination: 0.92,
  crack: 1.08,
  damping_patch: 0.58,
};

export function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, Number.isFinite(value) ? value : minimum));
}

export function flexuralPlateProperties(materialKey: MaterialKey, thicknessMm: number, frequencyHz: number) {
  const material = MATERIALS[materialKey];
  const thicknessM = clamp(thicknessMm, 0.2, 50) / 1000;
  const frequency = clamp(frequencyHz, 100, 40000);
  const youngsModulusPa = material.youngsModulusGPa * 1e9;
  const rigidity = youngsModulusPa * thicknessM ** 3 / (12 * (1 - material.poissonRatio ** 2));
  const dispersionCoefficient = Math.sqrt(rigidity / (material.densityKgM3 * thicknessM));
  const angularFrequency = 2 * Math.PI * frequency;
  const groupVelocity = 2 * Math.sqrt(angularFrequency * dispersionCoefficient);
  return {
    flexuralRigidityNm: rigidity,
    groupVelocityMps: groupVelocity,
    // For a Kirchhoff-Love flexural wave, group velocity is twice phase
    // velocity. Wavelength is phase velocity / frequency.
    wavelengthM: groupVelocity / (2 * frequency),
  };
}

function toMeters(point: NormalizedPoint, config: VirtualExperimentConfig) {
  return {
    x: clamp(point.x, 0, 1) * config.panelWidthMm / 1000,
    y: clamp(point.y, 0, 1) * config.panelHeightMm / 1000,
  };
}

function distance(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function distanceToSegment(point: { x: number; y: number }, start: { x: number; y: number }, end: { x: number; y: number }) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const denominator = dx * dx + dy * dy;
  if (denominator === 0) return distance(point, start);
  const projection = clamp(((point.x - start.x) * dx + (point.y - start.y) * dy) / denominator, 0, 1);
  return distance(point, { x: start.x + projection * dx, y: start.y + projection * dy });
}

function seededRandom(seed: number) {
  let state = Math.trunc(seed) >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

function gaussian(random: () => number) {
  const u = Math.max(1e-12, random());
  const v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function fftSpectrum(samples: number[], sampleRateHz: number) {
  let size = 1;
  while (size < samples.length) size <<= 1;
  const real = new Float64Array(size);
  const imaginary = new Float64Array(size);
  for (let index = 0; index < samples.length; index += 1) {
    const window = samples.length > 1 ? 0.5 * (1 - Math.cos(2 * Math.PI * index / (samples.length - 1))) : 1;
    real[index] = samples[index] * window;
  }
  for (let index = 1, reversed = 0; index < size; index += 1) {
    let bit = size >> 1;
    for (; reversed & bit; bit >>= 1) reversed ^= bit;
    reversed ^= bit;
    if (index < reversed) {
      [real[index], real[reversed]] = [real[reversed], real[index]];
      [imaginary[index], imaginary[reversed]] = [imaginary[reversed], imaginary[index]];
    }
  }
  for (let length = 2; length <= size; length <<= 1) {
    const angle = -2 * Math.PI / length;
    const rotationReal = Math.cos(angle);
    const rotationImaginary = Math.sin(angle);
    for (let offset = 0; offset < size; offset += length) {
      let phaseReal = 1;
      let phaseImaginary = 0;
      for (let index = 0; index < length / 2; index += 1) {
        const even = offset + index;
        const odd = even + length / 2;
        const oddReal = real[odd] * phaseReal - imaginary[odd] * phaseImaginary;
        const oddImaginary = real[odd] * phaseImaginary + imaginary[odd] * phaseReal;
        real[odd] = real[even] - oddReal;
        imaginary[odd] = imaginary[even] - oddImaginary;
        real[even] += oddReal;
        imaginary[even] += oddImaginary;
        const nextReal = phaseReal * rotationReal - phaseImaginary * rotationImaginary;
        phaseImaginary = phaseReal * rotationImaginary + phaseImaginary * rotationReal;
        phaseReal = nextReal;
      }
    }
  }
  const limitHz = Math.min(20000, sampleRateHz / 2);
  const raw: Array<{ frequencyHz: number; magnitude: number }> = [];
  let maximum = 1e-12;
  for (let index = 1; index <= size / 2; index += 1) {
    const frequencyHz = index * sampleRateHz / size;
    if (frequencyHz > limitHz) break;
    const magnitude = Math.hypot(real[index], imaginary[index]);
    maximum = Math.max(maximum, magnitude);
    raw.push({ frequencyHz, magnitude });
  }
  let peakFrequencyHz = 0;
  let peakMagnitude = -1;
  for (const point of raw) {
    if (point.frequencyHz >= 100 && point.magnitude > peakMagnitude) {
      peakMagnitude = point.magnitude;
      peakFrequencyHz = point.frequencyHz;
    }
  }
  return {
    peakFrequencyHz,
    spectrum: raw.map((point) => ({ frequencyHz: point.frequencyHz, magnitudeDb: Math.max(-100, 20 * Math.log10(Math.max(point.magnitude, 1e-12) / maximum)) })),
  };
}

export function simulateVirtualExperiment(input: VirtualExperimentConfig): VirtualSimulation {
  const sampleRateHz = clamp(Math.round(input.sampleRateHz), 8000, 96000);
  const config: VirtualExperimentConfig = {
    ...input,
    panelWidthMm: clamp(input.panelWidthMm, 100, 5000),
    panelHeightMm: clamp(input.panelHeightMm, 100, 5000),
    thicknessMm: clamp(input.thicknessMm, 0.2, 50),
    defectRadiusMm: clamp(input.defectRadiusMm, 1, 250),
    defectSeverity: clamp(input.defectSeverity, 0, 1),
    impactEnergyJ: clamp(input.impactEnergyJ, 0.01, 10),
    centerFrequencyHz: clamp(input.centerFrequencyHz, 100, Math.min(40000, sampleRateHz * 0.42)),
    noiseFloorDb: clamp(input.noiseFloorDb, -100, -6),
    boundaryReflectivity: clamp(input.boundaryReflectivity, 0, 0.95),
    sensorGain: clamp(input.sensorGain, 0.1, 10),
    sampleRateHz,
    durationMs: clamp(input.durationMs, 20, 500),
    velocityScale: clamp(input.velocityScale, 0.5, 1.5),
    source: { x: clamp(input.source.x, 0.01, 0.99), y: clamp(input.source.y, 0.01, 0.99) },
    receiver: { x: clamp(input.receiver.x, 0.01, 0.99), y: clamp(input.receiver.y, 0.01, 0.99) },
    defect: { x: clamp(input.defect.x, 0.01, 0.99), y: clamp(input.defect.y, 0.01, 0.99) },
  };
  const plate = flexuralPlateProperties(config.material, config.thicknessMm, config.centerFrequencyHz);
  const velocity = plate.groupVelocityMps * config.velocityScale;
  const material = MATERIALS[config.material];
  const source = toMeters(config.source, config);
  const receiver = toMeters(config.receiver, config);
  const defect = toMeters(config.defect, config);
  const panelWidthM = config.panelWidthMm / 1000;
  const panelHeightM = config.panelHeightMm / 1000;
  const directLength = Math.max(0.001, distance(source, receiver));
  const scatterLength = Math.max(0.001, distance(source, defect) + distance(defect, receiver));
  const radiusM = config.defectRadiusMm / 1000;
  const clearance = distanceToSegment(defect, source, receiver);
  const intercept = Math.exp(-0.5 * (clearance / Math.max(radiusM, 0.001)) ** 2);
  const attenuationPerM = material.lossFactor * 18 * Math.sqrt(config.centerFrequencyHz / 6000);
  const attenuation = (lengthM: number) => Math.exp(-attenuationPerM * lengthM) / Math.sqrt(Math.max(0.04, lengthM));
  const directGain = attenuation(directLength) * (1 - 0.48 * config.defectSeverity * intercept);
  const sizeRatio = radiusM / Math.max(plate.wavelengthM, 0.001);
  const scatteringStrength = config.defectSeverity * DEFECT_SCATTER[config.defectType] * (1 - Math.exp(-2.2 * sizeRatio));
  const scatterGain = attenuation(scatterLength) * scatteringStrength;
  const reflectionImages = [
    { id: 'left', label: 'LEFT EDGE', point: { x: -source.x, y: source.y } },
    { id: 'right', label: 'RIGHT EDGE', point: { x: 2 * panelWidthM - source.x, y: source.y } },
    { id: 'top', label: 'TOP EDGE', point: { x: source.x, y: -source.y } },
    { id: 'bottom', label: 'BOTTOM EDGE', point: { x: source.x, y: 2 * panelHeightM - source.y } },
  ];
  const paths: SimulationPath[] = [
    { id: 'direct', label: 'DIRECT FLEXURAL', kind: 'direct', lengthM: directLength, arrivalMs: directLength / velocity * 1000, relativeGain: directGain },
    { id: 'scatter', label: 'DEFECT SCATTER', kind: 'scatter', lengthM: scatterLength, arrivalMs: (scatterLength + radiusM * config.defectSeverity * 0.3) / velocity * 1000, relativeGain: scatterGain },
    ...reflectionImages.map((image, index) => {
      const lengthM = distance(image.point, receiver);
      return { id: image.id, label: image.label, kind: 'reflection' as const, lengthM, arrivalMs: lengthM / velocity * 1000, relativeGain: attenuation(lengthM) * config.boundaryReflectivity * (0.34 - index * 0.025) };
    }),
  ];
  const sampleCount = Math.max(2, Math.round(config.sampleRateHz * config.durationMs / 1000));
  const samples = new Array<number>(sampleCount).fill(0);
  const sensorTransfer = config.sensorMode === 'phone_microphone'
    ? 0.68 * Math.sqrt(config.centerFrequencyHz / 6000) / (1 + (config.centerFrequencyHz / 14500) ** 4)
    : 1;
  const excitationScale = 0.17 * Math.sqrt(config.impactEnergyJ) * config.sensorGain * sensorTransfer;
  const decaySeconds = 0.022 / (1 + material.lossFactor * 45);
  paths.forEach((path, pathIndex) => {
    const arrivalSeconds = path.arrivalMs / 1000;
    const frequencyScale = path.kind === 'scatter' ? 1 - 0.13 * config.defectSeverity : path.kind === 'reflection' ? 0.94 - pathIndex * 0.012 : 1;
    const frequency = config.centerFrequencyHz * frequencyScale;
    for (let index = Math.max(0, Math.floor(arrivalSeconds * config.sampleRateHz)); index < sampleCount; index += 1) {
      const elapsed = index / config.sampleRateHz - arrivalSeconds;
      const envelope = Math.exp(-elapsed / (decaySeconds * (path.kind === 'direct' ? 1 : 0.82)));
      const dispersivePhase = 2 * Math.PI * (frequency * elapsed + 0.5 * frequency * 9.5 * elapsed ** 2);
      const carrier = Math.sin(dispersivePhase) + 0.22 * Math.sin(2 * Math.PI * frequency * 0.53 * elapsed + 0.7);
      samples[index] += excitationScale * path.relativeGain * envelope * carrier;
    }
  });
  const random = seededRandom(config.seed);
  const noiseAmplitude = 10 ** (config.noiseFloorDb / 20);
  for (let index = 0; index < sampleCount; index += 1) samples[index] += noiseAmplitude * gaussian(random);
  const peakAmplitude = samples.reduce((maximum, value) => Math.max(maximum, Math.abs(value)), 0);
  const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / sampleCount);
  const spectral = fftSpectrum(samples, config.sampleRateHz);
  return {
    config,
    samples,
    spectrum: spectral.spectrum,
    paths,
    metrics: {
      groupVelocityMps: velocity,
      flexuralRigidityNm: plate.flexuralRigidityNm,
      wavelengthMm: velocity / (2 * config.centerFrequencyHz) * 1000,
      directPathM: directLength,
      scatterPathM: scatterLength,
      directArrivalMs: paths[0].arrivalMs,
      scatterArrivalMs: paths[1].arrivalMs,
      scatterDelayUs: (paths[1].arrivalMs - paths[0].arrivalMs) * 1000,
      rms,
      peakAmplitude,
      peakFrequencyHz: spectral.peakFrequencyHz,
      timeResolutionUs: 1e6 / config.sampleRateHz,
      defectIntercept: intercept,
      clipped: peakAmplitude > 1,
    },
  };
}
