/** Validate an optional research payload: missing data must never become fake zeroes. */
export interface NuisanceDesignSummary {
  method: string;
  informationBits: number;
  normalizedInformation: number;
  nuisancePenaltyBits: number;
  quadratureErrorBits: number;
  regionCount: number;
  posteriorMass: number;
}

function finiteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function readNuisanceDesign(value: unknown): NuisanceDesignSummary | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const { method, information_bits, normalized_information, nuisance_penalty_bits,
    quadrature_error_bits, region_count, posterior_mass } = record;
  if (typeof method !== 'string' || !method.trim()
    || !finiteNumber(information_bits) || information_bits < 0
    || !finiteNumber(normalized_information) || normalized_information < 0 || normalized_information > 1
    || !finiteNumber(nuisance_penalty_bits)
    || !finiteNumber(quadrature_error_bits) || quadrature_error_bits < 0
    || !finiteNumber(region_count) || !Number.isInteger(region_count) || region_count < 1
    || !finiteNumber(posterior_mass) || posterior_mass <= 0 || posterior_mass > 1 + 1e-8) return null;
  return {
    method, informationBits: information_bits, normalizedInformation: normalized_information,
    nuisancePenaltyBits: nuisance_penalty_bits, quadratureErrorBits: quadrature_error_bits,
    regionCount: region_count, posteriorMass: Math.min(1, posterior_mass),
  };
}
