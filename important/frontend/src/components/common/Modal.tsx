import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import styled from 'styled-components';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  maxWidth?: string;
  className?: string;
  ariaLabel?: string;
}

/**
 * Universal Modal Portal Primitive
 * Renders directly into document.body to guarantee escaping all parent stacking contexts,
 * CSS transforms, and backdrop-filter containment boxes.
 */
export const ModalPortal: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (typeof document === 'undefined') return null;
  return ReactDOM.createPortal(children, document.body);
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  icon,
  children,
  maxWidth = '580px',
  className = '',
  ariaLabel,
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <ModalPortal>
      <ModalBackdrop
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : ariaLabel || 'Dialog'}
      >
        <ModalCard
          $maxWidth={maxWidth}
          className={`compust-modal-card ${className}`}
          onClick={(e) => e.stopPropagation()}
        >
          {title && (
            <ModalHeader className="compust-modal-header">
              <div className="title-area">
                {icon && <span className="header-icon">{icon}</span>}
                <h3 className="modal-title-text">{title}</h3>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={onClose}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </ModalHeader>
          )}
          <ModalBody className="compust-modal-body">
            {children}
          </ModalBody>
        </ModalCard>
      </ModalBackdrop>
    </ModalPortal>
  );
};

/* =========================================================================
   Central Z-Index Scale & Theme-Tokenized Styles
   Modals sit at z-index: 9999, directly below global Toast (10000)
   ========================================================================= */

const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(10, 15, 29, 0.78);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: modalFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);

  @keyframes modalFadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

const ModalCard = styled.div<{ $maxWidth?: string }>`
  position: relative;
  width: 100%;
  max-width: ${(props) => props.$maxWidth || '580px'};
  max-height: calc(100vh - 48px);
  background: var(--bg-card, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.12));
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 65px -10px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.05);
  overflow: hidden;
  animation: modalPop 0.22s cubic-bezier(0.16, 1, 0.3, 1);

  @keyframes modalPop {
    from {
      opacity: 0;
      transform: scale(0.96) translateY(8px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  @media (max-width: 640px) {
    max-height: calc(100vh - 24px);
    border-radius: 14px;
  }
`;

const ModalHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  background: rgba(255, 255, 255, 0.02);

  .title-area {
    display: flex;
    align-items: center;
    gap: 12px;

    .header-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      color: #38bdf8;
    }

    .modal-title-text {
      margin: 0;
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-primary, #f8fafc);
      letter-spacing: -0.01em;
    }
  }

  .close-btn {
    background: transparent;
    border: none;
    color: var(--text-muted, #94a3b8);
    cursor: pointer;
    padding: 6px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;

    &:hover {
      color: var(--text-primary, #ffffff);
      background: rgba(255, 255, 255, 0.08);
    }
  }

  @media (max-width: 640px) {
    padding: 14px 18px;
  }
`;

const ModalBody = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  color: var(--text-primary, #e2e8f0);

  /* Clean custom scrollbar */
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.2);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.35);
  }

  @media (max-width: 640px) {
    padding: 18px;
  }
`;
