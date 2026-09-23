import React, { useState } from 'react';

interface CompanyLogoProps {
  company: string;
  domain?: string | null;
  logoUrl?: string | null;
  size?: number;
  className?: string;
}

const GRADIENT_PALETTES = [
  ['#3b82f6', '#1d4ed8'],
  ['#8b5cf6', '#6d28d9'],
  ['#ec4899', '#be185d'],
  ['#10b981', '#047857'],
  ['#f59e0b', '#b45309'],
  ['#06b6d4', '#0e7490'],
  ['#6366f1', '#4338ca'],
  ['#14b8a6', '#0f766e'],
];

function getPalette(name: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % GRADIENT_PALETTES.length;
  return GRADIENT_PALETTES[index] as [string, string];
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'CO';
  if (parts.length === 1) {
    const word = parts[0]!;
    return word.slice(0, 2).toUpperCase();
  }
  const first = parts[0]!;
  const second = parts[1]!;
  return (first[0]! + second[0]!).toUpperCase();
}

export const CompanyLogo: React.FC<CompanyLogoProps> = ({
  company,
  domain,
  logoUrl,
  size = 40,
  className = '',
}) => {
  const [stage, setStage] = useState<number>(0); // 0: primary logoUrl, 1: clearbit, 2: fallback initials

  const initials = getInitials(company);
  const [gradStart, gradEnd] = getPalette(company);

  const primaryUrl = logoUrl || (domain ? `https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${domain}&size=128` : '');
  const clearbitUrl = domain ? `https://logo.clearbit.com/${domain}` : '';

  const handleError = () => {
    if (stage === 0 && clearbitUrl && clearbitUrl !== primaryUrl) {
      setStage(1);
    } else {
      setStage(2);
    }
  };

  const currentSrc = stage === 0 ? primaryUrl : stage === 1 ? clearbitUrl : '';

  if (stage === 2 || !currentSrc) {
    return (
      <div
        className={`company-logo-initials ${className}`}
        style={{
          width: size,
          height: size,
          minWidth: size,
          minHeight: size,
          borderRadius: size > 40 ? 12 : 9,
          background: `linear-gradient(135deg, ${gradStart}, ${gradEnd})`,
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: Math.max(11, Math.round(size * 0.38)),
          letterSpacing: '0.05em',
          boxShadow: '0 2px 6px rgba(0,0,0,0.18)',
          userSelect: 'none',
        }}
        title={company}
      >
        {initials}
      </div>
    );
  }

  return (
    <div
      className={`company-logo-wrapper ${className}`}
      style={{
        width: size,
        height: size,
        minWidth: size,
        minHeight: size,
        borderRadius: size > 40 ? 12 : 9,
        background: 'rgba(255, 255, 255, 0.08)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
      }}
      title={company}
    >
      <img
        src={currentSrc}
        alt={`${company} logo`}
        style={{
          width: '78%',
          height: '78%',
          objectFit: 'contain',
        }}
        onError={handleError}
        loading="lazy"
      />
    </div>
  );
};
