import React from 'react';
import styled from 'styled-components';
import {
  Briefcase,
  UserCheck,
  Activity,
  LogIn,
  LogOut,
  FolderKanban,
  Building2,
  Bot,
  Database,
  BookOpen,
  GraduationCap,
  BrainCircuit,
  Puzzle,
} from 'lucide-react';
import type { UserProfile } from '../api/client';
import { useTranslation } from '../i18n';

interface NavbarProps {
  activeTab: 'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision' | 'guide' | 'internships' | 'interview-prep' | 'extension';
  setActiveTab: (tab: 'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision' | 'guide' | 'internships' | 'interview-prep' | 'extension') => void;
  user: UserProfile | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  onOpenAISettings: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  user,
  onOpenAuth,
  onLogout,
  onOpenAISettings,
}) => {
  const { language, setLanguage, t } = useTranslation();

  return (
    <StyledNav>
      <div className="dock-container">
        {/* Logo / Brand */}
        <div
          className="brand"
          onClick={() => setActiveTab('directory')}
          role="button"
          tabIndex={0}
          aria-label="COMPUST Home"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setActiveTab('directory');
            }
          }}
        >
          <img src="/logo-transparent.png" alt="Compust Logo" className="brand-logo" />
          <span className="brand-name">Compust</span>
        </div>

        {/* Navigation Items with Tooltips */}
        <div className="nav-items" role="tablist">
          <div
            className={`nav-item ${activeTab === 'directory' ? 'active' : ''}`}
            onClick={() => setActiveTab('directory')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'directory'}
            aria-label={t.nav.opportunities}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('directory');
              }
            }}
          >
            <Briefcase size={18} />
            <div className="tooltip">{t.nav.opportunities}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'internships' ? 'active' : ''}`}
            onClick={() => setActiveTab('internships')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'internships'}
            aria-label={t.nav.internships}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('internships');
              }
            }}
          >
            <GraduationCap size={18} />
            <div className="tooltip">{t.nav.internships}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'profile'}
            aria-label={t.nav.profile}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('profile');
              }
            }}
          >
            <UserCheck size={18} />
            <div className="tooltip">{t.nav.profile}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'applications' ? 'active' : ''}`}
            onClick={() => setActiveTab('applications')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'applications'}
            aria-label={t.nav.applications}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('applications');
              }
            }}
          >
            <FolderKanban size={18} />
            <div className="tooltip">{t.nav.applications}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'interview-prep' ? 'active' : ''}`}
            onClick={() => setActiveTab('interview-prep')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'interview-prep'}
            aria-label={t.nav.interviewPrep}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('interview-prep');
              }
            }}
          >
            <BrainCircuit size={18} />
            <div className="tooltip">{t.nav.interviewPrep}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'companies' ? 'active' : ''}`}
            onClick={() => setActiveTab('companies')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'companies'}
            aria-label={t.nav.companies}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('companies');
              }
            }}
          >
            <Building2 size={18} />
            <div className="tooltip">{t.nav.companies}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'supervision' ? 'active' : ''}`}
            onClick={() => setActiveTab('supervision')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'supervision'}
            aria-label={t.nav.supervision}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('supervision');
              }
            }}
          >
            <Database size={18} />
            <div className="tooltip">{t.nav.supervision}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'scraper' ? 'active' : ''}`}
            onClick={() => setActiveTab('scraper')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'scraper'}
            aria-label={t.nav.scraperHub}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('scraper');
              }
            }}
          >
            <Activity size={18} />
            <div className="tooltip">{t.nav.scraperHub}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'guide' ? 'active' : ''}`}
            onClick={() => setActiveTab('guide')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'guide'}
            aria-label={t.nav.guide}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('guide');
              }
            }}
          >
            <BookOpen size={18} />
            <div className="tooltip">{t.nav.guide}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'extension' ? 'active' : ''}`}
            onClick={() => setActiveTab('extension')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'extension'}
            aria-label={t.nav.extension}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('extension');
              }
            }}
          >
            <Puzzle size={18} />
            <div className="tooltip">{t.nav.extension}</div>
          </div>
        </div>

        {/* Actions: AI Settings, Language Switcher & Auth */}
        <div className="actions-cluster">
          <button
            className="ai-settings-btn"
            onClick={onOpenAISettings}
            title={t.nav.aiSettings}
            aria-label={t.nav.aiSettings}
          >
            <Bot size={14} />
            <span>AI</span>
          </button>

          {/* Unified 3-way Language Switcher */}
          <div className="global-lang-switcher" role="group" aria-label="Select Language">
            {(['en', 'fr', 'nl'] as const).map((langCode) => (
              <button
                key={langCode}
                type="button"
                className={`lang-option-btn ${language === langCode ? 'active' : ''}`}
                onClick={() => setLanguage(langCode)}
                title={langCode === 'en' ? 'English' : langCode === 'fr' ? 'Français' : 'Nederlands'}
                aria-pressed={language === langCode}
              >
                {langCode.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="auth-action">
            {user ? (
              <div
                className="user-pill"
                onClick={onLogout}
                title="Click to Sign Out"
                role="button"
                tabIndex={0}
                aria-label={`Signed in as ${user.first_name || user.email}. Click to sign out`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onLogout();
                  }
                }}
              >
                <span className="user-name">{user.first_name || user.email.split('@')[0]}</span>
                <LogOut size={15} className="logout-icon" />
              </div>
            ) : (
              <button className="sign-in-btn" onClick={onOpenAuth} aria-label={t.nav.login}>
                <LogIn size={15} />
                <span>{t.nav.login}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </StyledNav>
  );
};

const StyledNav = styled.header`
  position: sticky;
  top: 14px;
  z-index: 100;
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 0 16px;

  .dock-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 6px 16px;
    background: rgba(10, 15, 26, 0.88);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.06);
    width: fit-content;
    max-width: min(1180px, calc(100% - 16px));
    min-width: 0;
    transition: all 0.3s ease;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
    flex-shrink: 0;
  }

  .brand-logo {
    width: 26px;
    height: 26px;
    object-fit: contain;
    filter: drop-shadow(0 0 8px rgba(0, 240, 255, 0.4));
    transition: transform 0.25s ease, filter 0.25s ease;
  }

  .brand:hover .brand-logo {
    transform: scale(1.08);
    filter: drop-shadow(0 0 12px rgba(124, 58, 237, 0.6));
  }

  .brand-name {
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 1.15rem;
    letter-spacing: -0.02em;
    color: #ffffff;
    white-space: nowrap;
  }

  .nav-items {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    flex: 1 1 auto;
    min-width: 0;
  }

  .nav-item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    color: #94a3b8;
    background: transparent;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

    svg {
      width: 18px;
      height: 18px;
    }

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
      transform: translateY(-2px);
    }

    &.active {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.16);
      border: 1px solid rgba(59, 130, 246, 0.35);
      box-shadow: 0 0 14px rgba(59, 130, 246, 0.25);
    }
  }

  .tooltip {
    position: absolute;
    bottom: -36px;
    left: 50%;
    transform: translateX(-50%) scale(0.85);
    background: #0f172a;
    color: #f8fafc;
    font-size: 0.75rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: all 0.2s ease;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
    z-index: 1000;
  }

  .nav-item:hover .tooltip {
    opacity: 1;
    transform: translateX(-50%) scale(1);
  }

  .actions-cluster {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .ai-settings-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    border-radius: 14px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    color: #93c5fd;
    font-size: 0.72rem;
    font-weight: 700;
    cursor: pointer;
    flex-shrink: 0;
    white-space: nowrap;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(59, 130, 246, 0.25);
      border-color: #3b82f6;
      color: #ffffff;
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
  }

  .global-lang-switcher {
    display: inline-flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 2px;
    gap: 1px;
    flex-shrink: 0;
  }

  .lang-option-btn {
    padding: 3px 7px;
    border-radius: 10px;
    font-size: 0.68rem;
    font-weight: 700;
    line-height: 1;
    color: #94a3b8;
    background: transparent;
    cursor: pointer;
    transition: all 0.16s ease;
    border: none;
    white-space: nowrap;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
    }

    &.active {
      background: rgba(59, 130, 246, 0.35);
      color: #60a5fa;
      box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 1px;
    }
  }

  .auth-action {
    flex-shrink: 0;
  }

  .user-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 16px;
    cursor: pointer;
    flex-shrink: 0;
    white-space: nowrap;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(244, 63, 94, 0.15);
      border-color: rgba(244, 63, 94, 0.3);
      color: #f43f5e;
    }
  }

  .user-name {
    font-size: 0.8rem;
    font-weight: 600;
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .sign-in-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 13px;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.8rem;
    font-weight: 600;
    border-radius: 16px;
    border: none;
    cursor: pointer;
    flex-shrink: 0;
    white-space: nowrap;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);

    &:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
    }
  }

  .nav-item:focus-visible,
  .brand:focus-visible,
  .user-pill:focus-visible,
  .sign-in-btn:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: 2px;
  }

  @media (max-width: 1240px) {
    padding: 0 12px;

    .dock-container {
      gap: 10px;
      padding: 5px 12px;
    }

    .nav-items {
      gap: 3px;
    }

    .nav-item {
      width: 35px;
      height: 35px;

      svg {
        width: 16px;
        height: 16px;
      }
    }

    .brand-name {
      font-size: 1.05rem;
    }

    .actions-cluster {
      gap: 6px;
    }
  }

  @media (max-width: 992px) {
    .brand-name {
      display: none;
    }

    .nav-items {
      gap: 2px;
    }

    .nav-item {
      width: 34px;
      height: 34px;

      svg {
        width: 16px;
        height: 16px;
      }
    }

    .sign-in-btn span {
      display: none;
    }

    .sign-in-btn {
      padding: 5px 8px;
    }
  }

  @media (max-width: 768px) {
    top: 8px;
    padding: 0 8px;

    .dock-container {
      width: 100%;
      max-width: 100%;
      padding: 5px 8px;
      gap: 6px;
      border-radius: 18px;
    }

    .nav-items {
      gap: 2px;
      overflow-x: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;
      &::-webkit-scrollbar {
        display: none;
      }
      max-width: 48vw;
    }

    .nav-item {
      width: 32px;
      height: 32px;
      flex-shrink: 0;

      svg {
        width: 15px;
        height: 15px;
      }
    }

    .actions-cluster {
      gap: 4px;
    }

    .ai-settings-btn {
      padding: 4px 6px;
      font-size: 0.65rem;
    }

    .lang-option-btn {
      padding: 2px 4px;
      font-size: 0.62rem;
    }

    .user-name {
      display: none;
    }
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`;
