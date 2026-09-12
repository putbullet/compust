import React, { useState } from 'react';
import styled from 'styled-components';
import { BookOpen, Heart, ExternalLink, X, Info } from 'lucide-react';
import { GITHUB_REPO_URL, DONATE_URL, GITHUB_DISCUSSIONS_URL } from '../../config/guideConfig';

export const GitHubIcon: React.FC<{ size?: number; className?: string }> = ({ size = 15, className }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5" />
  </svg>
);

interface FloatingHelpControlsProps {
  onNavigateToGuide: () => void;
  activeTab?: string;
}

export const FloatingHelpControls: React.FC<FloatingHelpControlsProps> = ({
  onNavigateToGuide,
  activeTab,
}) => {
  const [showSupportModal, setShowSupportModal] = useState(false);

  const handleDonateClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (DONATE_URL) {
      window.open(DONATE_URL, '_blank', 'noopener,noreferrer');
    } else {
      setShowSupportModal(true);
    }
  };

  return (
    <>
      <FloatingStack aria-label="Compust Quick Help and Community Controls">
        {/* Upper Row: GitHub repo link & Donate / Support button */}
        <TopRow>
          <GitHubButton
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            title="Visit our official GitHub repository (putbullet/compust)"
            aria-label="Visit our official GitHub repository"
          >
            <GitHubIcon size={15} />
            <span className="btn-text">GitHub</span>
          </GitHubButton>


          <DonateButton
            onClick={handleDonateClick}
            title="Support / Donate to Compust"
            aria-label="Support the project"
            type="button"
          >
            <Heart size={15} className="heart-icon" />
            <span className="expand-text">Support</span>
          </DonateButton>
        </TopRow>

        {/* Lower Row: Need Help? See Guide */}
        <GuideButton
          onClick={onNavigateToGuide}
          $isActive={activeTab === 'guide'}
          title="Open Compust In-App Guide & Documentation"
          aria-label="Need Help? See Guide"
          type="button"
        >
          <BookOpen size={17} className="guide-icon" />
          <span className="guide-label">Need Help? See Guide</span>
        </GuideButton>
      </FloatingStack>

      {/* Community Support Modal if donation URL is not configured yet */}
      {showSupportModal && (
        <SupportModalOverlay onClick={() => setShowSupportModal(false)} role="dialog" aria-modal="true">
          <SupportModalContent onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="header-title">
                <Heart size={20} className="modal-heart" />
                <h3>Support Compust</h3>
              </div>
              <button
                className="close-btn"
                onClick={() => setShowSupportModal(false)}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p>
                <strong>Compust</strong> is a free, open-source local career intelligence and scraper platform developed with care for the developer and job-seeking community.
              </p>
              <div className="info-box">
                <Info size={16} />
                <span>
                  Official community sponsorships will be announced directly on our official GitHub repository.
                </span>
              </div>
              <p>
                You can support the project today by starring the repository, reporting issues, contributing portal adapters, or sharing feedback with the community!
              </p>
            </div>

            <div className="modal-actions">
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="primary-action-btn"
                onClick={() => setShowSupportModal(false)}
              >
                <GitHubIcon size={16} />
                <span>Star on GitHub</span>
                <ExternalLink size={14} />
              </a>

              <a
                href={GITHUB_DISCUSSIONS_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="secondary-action-btn"
                onClick={() => setShowSupportModal(false)}
              >
                <span>Community Discussions</span>
              </a>
            </div>
          </SupportModalContent>
        </SupportModalOverlay>
      )}
    </>
  );
};

/* --- Styled Components --- */

const FloatingStack = styled.div`
  position: fixed;
  bottom: 84px; /* Sits directly above the AI Assistant (which is at bottom: 24px) */
  right: 24px;
  z-index: 998;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  pointer-events: auto;

  @media (max-width: 640px) {
    bottom: 76px;
    right: 16px;
    gap: 6px;
  }
`;

const TopRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const GitHubButton = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(15, 23, 42, 0.92);
  color: #cbd5e1;
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);

  &:hover {
    color: #ffffff;
    background: #1e293b;
    border-color: rgba(255, 255, 255, 0.28);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
  }

  &:focus-visible {
    outline: 2px solid #38bdf8;
    outline-offset: 2px;
  }

  @media (max-width: 640px) {
    padding: 6px 10px;
    .btn-text {
      display: none;
    }
  }
`;

const DonateButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  min-width: 32px;
  padding: 0 8px;
  background: rgba(15, 23, 42, 0.92);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.3);
  border-radius: 20px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);

  .heart-icon {
    flex-shrink: 0;
    transition: transform 0.2s ease;
  }

  .expand-text {
    font-size: 0.78rem;
    font-weight: 600;
    color: #fda4af;
    max-width: 0;
    opacity: 0;
    white-space: nowrap;
    transition: max-width 0.28s ease, opacity 0.24s ease;
  }

  &:hover {
    background: rgba(244, 63, 94, 0.15);
    border-color: #f43f5e;
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(244, 63, 94, 0.25);

    .heart-icon {
      transform: scale(1.15);
    }

    .expand-text {
      max-width: 80px;
      opacity: 1;
      margin-left: 2px;
    }
  }

  &:focus-visible {
    outline: 2px solid #f43f5e;
    outline-offset: 2px;
  }
`;

const GuideButton = styled.button<{ $isActive?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  background: ${(props) =>
    props.$isActive
      ? 'linear-gradient(135deg, #0284c7, #2563eb)'
      : 'rgba(15, 23, 42, 0.94)'};
  color: #f8fafc;
  border: 1px solid
    ${(props) => (props.$isActive ? '#38bdf8' : 'rgba(56, 189, 248, 0.35)')};
  border-radius: 26px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45),
    0 0 12px ${(props) => (props.$isActive ? 'rgba(56, 189, 248, 0.4)' : 'rgba(56, 189, 248, 0.15)')};
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all 0.24s cubic-bezier(0.16, 1, 0.3, 1);

  .guide-icon {
    color: #38bdf8;
    flex-shrink: 0;
    transition: transform 0.22s ease;
  }

  .guide-label {
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  &:hover {
    transform: translateY(-2px);
    background: ${(props) =>
      props.$isActive
        ? 'linear-gradient(135deg, #0369a1, #1d4ed8)'
        : 'rgba(30, 41, 59, 0.98)'};
    border-color: #38bdf8;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.55), 0 0 16px rgba(56, 189, 248, 0.35);

    .guide-icon {
      transform: scale(1.1);
    }
  }

  &:focus-visible {
    outline: 2px solid #38bdf8;
    outline-offset: 2px;
  }

  @media (max-width: 640px) {
    padding: 8px 12px;
    .guide-label {
      font-size: 0.78rem;
    }
  }
`;

const SupportModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(6px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.2s ease-out;

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

const SupportModalContent = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 18px;
  width: 100%;
  max-width: 460px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7);
  overflow: hidden;

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 22px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);

    .header-title {
      display: flex;
      align-items: center;
      gap: 10px;

      h3 {
        margin: 0;
        font-size: 1.1rem;
        color: #f8fafc;
      }

      .modal-heart {
        color: #f43f5e;
      }
    }

    .close-btn {
      background: none;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;

      &:hover {
        color: #f8fafc;
        background: rgba(255, 255, 255, 0.1);
      }
    }
  }

  .modal-body {
    padding: 22px;
    color: #cbd5e1;
    font-size: 0.92rem;
    line-height: 1.55;

    p {
      margin: 0 0 14px 0;
      &:last-child {
        margin-bottom: 0;
      }
    }

    .info-box {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 14px;
      font-size: 0.85rem;
      color: #7dd3fc;

      svg {
        flex-shrink: 0;
        margin-top: 2px;
      }
    }
  }

  .modal-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 22px 20px;
    background: rgba(15, 23, 42, 0.6);
    border-top: 1px solid rgba(255, 255, 255, 0.06);

    a {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 0.86rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .primary-action-btn {
      flex: 1;
      background: #2563eb;
      color: #ffffff;
      &:hover {
        background: #1d4ed8;
      }
    }

    .secondary-action-btn {
      background: rgba(255, 255, 255, 0.08);
      color: #cbd5e1;
      &:hover {
        background: rgba(255, 255, 255, 0.14);
        color: #ffffff;
      }
    }
  }
`;
