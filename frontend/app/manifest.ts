import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'ARGUS NEO Smart Probe',
    short_name: 'ARGUS Probe',
    description: 'Local research smart-probe interface for ARGUS adaptive physical experiments.',
    start_url: '/probe',
    display: 'standalone',
    background_color: '#07100f',
    theme_color: '#b8ff42',
  };
}

