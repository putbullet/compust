import React from 'react';
import { GitHubInternshipsView } from './GitHubInternshipsView';
import type { Country } from '../../api/client';

interface InternshipScraperViewProps {
  availableCountries?: Country[];
}

export const InternshipScraperView: React.FC<InternshipScraperViewProps> = () => {
  return <GitHubInternshipsView />;
};
