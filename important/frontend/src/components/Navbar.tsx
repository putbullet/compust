import React from 'react';
import styled from 'styled-components';
import {
  Briefcase,
  UserCheck,
  Activity,
  LogIn,
  LogOut,
  Globe,
  FolderKanban,
  Building2,
  Bot,
  Database,
} from 'lucide-react';
import type { UserProfile } from '../api/client';
import { useTranslation } from '../i18n';

interface NavbarProps {
  activeTab: 'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision';
  setActiveTab: (tab: 'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision') => void;
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
            <Briefcase size={20} />
            <div className="tooltip">{t.nav.opportunities}</div>
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
            <UserCheck size={20} />
            <div className="tooltip">{t.nav.profile}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'applications' ? 'active' : ''}`}
            onClick={() => setActiveTab('applications')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'applications'}
            aria-label={language === 'fr' ? 'Mes Candidatures' : 'My Applications'}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('applications');
              }
            }}
          >
            <FolderKanban size={20} />
            <div className="tooltip">{language === 'fr' ? 'Mes Candidatures' : 'My Applications'}</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'companies' ? 'active' : ''}`}
            onClick={() => setActiveTab('companies')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'companies'}
            aria-label="Companies and Sources"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('companies');
              }
            }}
          >
            <Building2 size={20} />
            <div className="tooltip">Companies & Sources</div>
          </div>

          <div
            className={`nav-item ${activeTab === 'supervision' ? 'active' : ''}`}
            onClick={() => setActiveTab('supervision')}
            role="tab"
            tabIndex={0}
            aria-selected={activeTab === 'supervision'}
            aria-label="Data Supervision"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setActiveTab('supervision');
              }
            }}
          >
            <Database size={20} />
            <div className="tooltip">Data Supervision</div>
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
            <Activity size={20} />
            <div className="tooltip">{t.nav.scraperHub}</div>
          </div>
        </div>

        {/* Actions: AI Settings, Language Switcher & Auth */}
        <div className="actions-cluster">
          <button
            className="ai-settings-btn"
            onClick={onOpenAISettings}
            title="Local AI & Model Settings"
            aria-label="Local AI and Model Settings"
          >
            <Bot size={15} />
            <span>AI</span>
          </button>

          <button
            className="lang-btn"
            onClick={() => setLanguage(language === 'en' ? 'fr' : 'en')}
            title={`Switch to ${language === 'en' ? 'Français' : 'English'}`}
            aria-label={`Current language: ${language.toUpperCase()}. Click to switch language`}
          >
            <Globe size={14} />
            <span>{language.toUpperCase()}</span>
          </button>

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
                <LogOut size={16} className="logout-icon" />
              </div>
            ) : (
              <button className="sign-in-btn" onClick={onOpenAuth} aria-label={t.nav.login}>
                <LogIn size={16} />
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
  top: 16px;
  z-index: 100;
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 0 16px;

  .dock-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 8px 18px;
    background: rgba(10, 15, 26, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
    width: 100%;
    max-width: 960px;
    transition: all 0.3s ease;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }

  .brand-logo {
    width: 28px;
    height: 28px;
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
    font-size: 1.25rem;
    letter-spacing: -0.02em;
    color: #ffffff;
  }

  .nav-items {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .nav-item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    color: #94a3b8;
    background: transparent;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
      transform: translateY(-2px);
    }

    &.active {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      box-shadow: 0 0 16px rgba(59, 130, 246, 0.25);
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
  }

  .nav-item:hover .tooltip {
    opacity: 1;
    transform: translateX(-50%) scale(1);
  }

  .user-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(244, 63, 94, 0.15);
      border-color: rgba(244, 63, 94, 0.3);
      color: #f43f5e;
    }
  }

  .user-name {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .sign-in-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.85rem;
    font-weight: 600;
    border-radius: 20px;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);

    &:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
    }
  }

  .actions-cluster {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .ai-settings-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 12px;
    border-radius: 16px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    color: #93c5fd;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
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

  .lang-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 12px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #cbd5e1;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(59, 130, 246, 0.4);
      color: #3b82f6;
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }
  }

  .nav-item:focus-visible,
  .brand:focus-visible,
  .user-pill:focus-visible,
  .sign-in-btn:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: 2px;
  }

  @media (max-width: 768px) {
    top: 8px;
    padding: 0 8px;

    .dock-container {
      padding: 6px 10px;
      gap: 8px;
      border-radius: 18px;
    }

    .brand-name {
      display: none;
    }

    .nav-items {
      gap: 4px;
      overflow-x: auto;
      padding-bottom: 2px;
      max-width: 55vw;
    }

    .nav-item {
      width: 36px;
      height: 36px;
      flex-shrink: 0;
    }

    .actions-cluster {
      gap: 6px;
    }

    .ai-settings-btn,
    .lang-btn {
      padding: 5px 8px;
      font-size: 0.7rem;
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
