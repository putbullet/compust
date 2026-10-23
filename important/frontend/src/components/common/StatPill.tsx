import React from 'react';
import './StatPill.css';

export interface StatPillProps {
  variant?: 'hero' | 'metric';
  value: string | number;
  label: string;
  subtext?: string;
  icon?: React.ReactNode;
  iconColor?: 'blue' | 'purple' | 'cyan' | 'emerald';
  tone?: 'green' | 'amber' | 'blue' | 'red';
  titleTooltip?: string;
  className?: string;
}

export const StatPill: React.FC<StatPillProps> = ({
  variant = 'hero',
  value,
  label,
  subtext,
  icon,
  iconColor = 'blue',
  tone,
  titleTooltip,
  className = '',
}) => {
  if (variant === 'hero') {
    return (
      <div
        className={`compust-stat-pill compust-stat-pill--hero ${className}`}
        title={titleTooltip || `${label}: ${value}`}
        role="group"
      >
        {icon && (
          <div className={`pill-icon-wrap icon-${iconColor}`} aria-hidden="true">
            {icon}
          </div>
        )}
        <div className="pill-text-col">
          <span className="pill-value">{value}</span>
          <span className="pill-label">{label}</span>
        </div>
      </div>
    );
  }

  // Variant: 'metric' (3-part layout for Internships & detailed metrics)
  const fullTooltip = titleTooltip || `${label}: ${value}${subtext ? ` (${subtext})` : ''}`;
  const toneClass = tone ? `tone-${tone}` : '';

  return (
    <div
      className={`compust-stat-pill compust-stat-pill--metric ${toneClass} ${className}`}
      title={fullTooltip}
      role="group"
    >
      <div className="pill-label-side" title={label}>
        {icon && <span className="inline-icon" aria-hidden="true">{icon}</span>}
        <span>{label}</span>
      </div>

      <div className={`pill-metric-value ${toneClass}`}>
        {value}
      </div>

      {subtext && (
        <div className="pill-sub-side" title={subtext}>
          {subtext}
        </div>
      )}
    </div>
  );
};
