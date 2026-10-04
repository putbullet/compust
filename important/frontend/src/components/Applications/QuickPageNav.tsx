import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { ArrowUp, ArrowDown, BarChart2 } from 'lucide-react';
import { useTranslation } from '../../i18n';

interface QuickPageNavProps {
  mode?: 'analytics' | 'page';
  analyticsElementId?: string;
  topElementId?: string;
  bottomElementId?: string;
}

export const QuickPageNav: React.FC<QuickPageNavProps> = ({
  mode,
  analyticsElementId,
  topElementId = 'applications-top',
  bottomElementId,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;
  const [scrollY, setScrollY] = useState(0);
  const [canScroll, setCanScroll] = useState(true);

  // Analytics is only active if explicitly in analytics mode or if analyticsElementId is provided without page mode
  const isAnalyticsMode = mode === 'analytics' || (!mode && Boolean(analyticsElementId));

  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const checkScrollable = () => {
      const scrollable = document.documentElement.scrollHeight > window.innerHeight + 80;
      setCanScroll(scrollable);
    };
    checkScrollable();
    window.addEventListener('resize', checkScrollable);
    const observer = new MutationObserver(checkScrollable);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      window.removeEventListener('resize', checkScrollable);
      observer.disconnect();
    };
  }, []);

  const scrollToTop = () => {
    if (topElementId) {
      const el = document.getElementById(topElementId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollToBottom = () => {
    if (bottomElementId) {
      const el = document.getElementById(bottomElementId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'end' });
        return;
      }
    }
    window.scrollTo({
      top: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
      behavior: 'smooth',
    });
  };

  const scrollToAnalytics = () => {
    if (!analyticsElementId) return;
    const el = document.getElementById(analyticsElementId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // If the page is not scrollable at all and has no analytics destination, hide the floating control
  if (!canScroll && !isAnalyticsMode) {
    return null;
  }

  const isScrolledDown = scrollY > 200;

  return (
    <NavDock aria-label={isAnalyticsMode ? tApp.quickNavScrollToAnalytics : tApp.quickNavScrollToBottom}>
      {/* Downward navigation: Analytics jump for applications workspace, Bottom jump for pages without analytics */}
      {isAnalyticsMode ? (
        <NavBtn
          type="button"
          onClick={scrollToAnalytics}
          title={tApp.quickNavScrollToAnalytics}
          className="analytics-jump-btn"
          aria-label={tApp.quickNavScrollToAnalytics}
        >
          <BarChart2 size={13} />
          <span className="btn-label">{tApp.quickNavAnalytics}</span>
          <ArrowDown size={12} />
        </NavBtn>
      ) : (
        <NavBtn
          type="button"
          onClick={scrollToBottom}
          title={tApp.quickNavScrollToBottom}
          className="bottom-jump-btn"
          aria-label={tApp.quickNavScrollToBottom}
        >
          <ArrowDown size={13} />
          <span className="btn-label">{tApp.quickNavBottom}</span>
        </NavBtn>
      )}

      {/* Upward navigation / Return to Top button (visible when scrolled down) */}
      {isScrolledDown && (
        <NavBtn
          type="button"
          onClick={scrollToTop}
          title={tApp.quickNavScrollToTop}
          className="top-jump-btn"
          aria-label={tApp.quickNavScrollToTop}
        >
          <ArrowUp size={13} />
          <span className="btn-label">{tApp.quickNavTop}</span>
        </NavBtn>
      )}
    </NavDock>
  );
};

const NavDock = styled.div`
  position: fixed;
  bottom: 24px;
  left: 24px;
  z-index: 95;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9999px;
  padding: 4px 6px;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  animation: fadeIn 0.2s ease;

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 600px) {
    bottom: 16px;
    left: 16px;
    .btn-label {
      display: none;
    }
  }
`;

const NavBtn = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 9999px;
  padding: 5px 10px;
  font-size: 11.5px;
  font-weight: 500;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.08);
  }

  &.analytics-jump-btn,
  &.bottom-jump-btn {
    color: #38bdf8;
    &:hover {
      background: rgba(56, 189, 248, 0.15);
      border-color: rgba(56, 189, 248, 0.3);
    }
  }

  &.top-jump-btn {
    color: #e2e8f0;
    &:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.2);
    }
  }
`;
