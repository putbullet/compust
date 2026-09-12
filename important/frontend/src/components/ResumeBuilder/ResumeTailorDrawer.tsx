import React from 'react';
import { Sparkles, X } from 'lucide-react';
import type { JobDetail } from '../../api/client';
import './ResumeTailorDrawer.css';

interface ResumeTailorDrawerProps {
  job: JobDetail;
  onClose: () => void;
  onOpenBuilderWithResume?: (resumeId: number) => void;
}

export const ResumeTailorDrawer: React.FC<ResumeTailorDrawerProps> = ({
  job,
  onClose,
}) => {
  return (
    <div className="tailor-drawer-overlay" role="dialog" aria-modal="true" aria-label="AI Resume Tailoring">
      <div className="tailor-drawer-content">
        {/* Header */}
        <div className="drawer-head">
          <div className="drawer-title-col">
            <div className="drawer-badge">
              <Sparkles size={14} className="sparkle-icon" />
              <span>AI Resume Studio</span>
              <span className="coming-soon-badge">Coming Soon</span>
            </div>
            <h2>Tailor Resume for &quot;{job.title}&quot;</h2>
            <p className="drawer-sub">
              AI resume tailoring is coming soon. Non-destructive vacancy-specific tailoring and bullet refinement workflows are currently under development.
            </p>
          </div>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close drawer">
            <X size={18} />
          </button>
        </div>

        {/* Drawer Body Coming Soon State */}
        <div className="drawer-body" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div style={{ maxWidth: 460, margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
            <Sparkles size={44} style={{ color: '#60a5fa' }} />
            <h3 style={{ fontSize: '1.25rem', color: '#ffffff', margin: 0 }}>AI Resume Tailoring is Coming Soon</h3>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
              Automated vacancy-specific resume tailoring and bullet refinement are currently in development. Your master resume remains secure and intact.
            </p>
            <div style={{ marginTop: 12 }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '10px 22px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  cursor: 'pointer',
                }}
              >
                Back to Job Posting
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
