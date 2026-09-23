import React from 'react';
import { CheckCircle2, XCircle, Shield, Flag, HelpCircle, Lock } from 'lucide-react';
import type { GitHubVisaStatus } from '../../api/client';

interface VisaBadgeProps {
  status: GitHubVisaStatus;
  customText?: string;
  isClosed?: boolean;
  size?: 'sm' | 'md';
}

export const VisaBadge: React.FC<VisaBadgeProps> = ({
  status,
  customText,
  isClosed = false,
  size = 'md',
}) => {
  if (isClosed || status === 'closed') {
    return (
      <span className={`visa-badge visa-badge-closed visa-badge-${size}`}>
        <Lock size={size === 'sm' ? 12 : 13} />
        <span>Closed</span>
      </span>
    );
  }

  switch (status) {
    case 'sponsors_visa':
      return (
        <span className={`visa-badge visa-badge-sponsor visa-badge-${size}`}>
          <CheckCircle2 size={size === 'sm' ? 12 : 13} />
          <span>{customText || 'Visa Sponsored'}</span>
        </span>
      );

    case 'no_sponsorship':
      return (
        <span className={`visa-badge visa-badge-nosponsor visa-badge-${size}`}>
          <XCircle size={size === 'sm' ? 12 : 13} />
          <span>{customText || 'No Sponsorship (🛂)'}</span>
        </span>
      );

    case 'us_citizen_only':
      return (
        <span className={`visa-badge visa-badge-uscit visa-badge-${size}`}>
          <Flag size={size === 'sm' ? 12 : 13} />
          <span>{customText || 'US Citizens / Clearance (🇺🇸)'}</span>
        </span>
      );

    case 'canada_authorized':
      return (
        <span className={`visa-badge visa-badge-canada visa-badge-${size}`}>
          <Shield size={size === 'sm' ? 12 : 13} />
          <span>{customText || 'Canada Eligible (🇨🇦)'}</span>
        </span>
      );

    case 'not_specified':
    default:
      return (
        <span className={`visa-badge visa-badge-unspecified visa-badge-${size}`}>
          <HelpCircle size={size === 'sm' ? 12 : 13} />
          <span>{customText || 'Visa: Not Specified'}</span>
        </span>
      );
  }
};
