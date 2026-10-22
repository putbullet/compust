import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  api,
  getStoredToken,
  setStoredToken,
} from './api/client';
import type {
  Company,
  Country,
  Job,
  JobDetail,
  UserProfile,
} from './api/client';
import { Navbar } from './components/Navbar';
import { SearchBar } from './components/SearchBar';
import { JobCard } from './components/JobCard';
import { JobDetailModal } from './components/JobDetailModal';
import { AuthModal } from './components/AuthModal';
import { ProfileView } from './components/ProfileView';
import { ScraperDashboard } from './components/ScraperDashboard';
import { ApplicationsView } from './components/ApplicationsView';
import { CompanyManagementView } from './components/CompanyManagementView';
import { MyDataSupervisionView } from './components/MyDataSupervisionView';
import { GuideView } from './components/Guide/GuideView';
import { InternshipScraperView } from './components/Internships/InternshipScraperView';
import { InterviewPrepView } from './components/InterviewPrep/InterviewPrepView';
import { ExtensionInstallView } from './components/ExtensionInstallView';
import { FloatingHelpControls } from './components/Guide/FloatingHelpControls';
import { AISettingsModal } from './components/AISettingsModal';
import { AIAssistantWidget } from './components/AIAssistantWidget';
import { SyncStatusBanner } from './components/common/SyncStatusBanner';
import { Loader } from './components/Loader';
import { Sparkles, Layers, ShieldCheck, ChevronLeft, ChevronRight, Bookmark, Briefcase, Building2, Globe2 } from 'lucide-react';
import { useTranslation } from './i18n';

type AppTab = 'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision' | 'guide' | 'internships' | 'interview-prep' | 'extension';

export const App: React.FC = () => {
  const { t } = useTranslation();

  // Navigation & View
  const [activeTab, setActiveTab] = useState<AppTab>(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get('tab');
      if (tab && ['directory', 'profile', 'scraper', 'applications', 'companies', 'supervision', 'guide', 'internships', 'interview-prep', 'extension'].includes(tab)) {
        return tab as AppTab;
      }
      if (window.location.pathname.includes('/interview-prep') || window.location.hash.startsWith('#interview-prep')) {
        return 'interview-prep';
      }
      if (window.location.hash.startsWith('#extension')) {
        return 'extension';
      }
      if (window.location.hash.startsWith('#guide')) {
        return 'guide';
      }
    } catch {}
    return 'directory';
  });
  const [isAISettingsOpen, setIsAISettingsOpen] = useState(false);
  const [targetJobForAssistant, setTargetJobForAssistant] = useState<{
    role: string;
    description: string;
    companyName: string;
  } | null>(null);

  // Metadata
  const [countries, setCountries] = useState<Country[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCountry, setSelectedCountry] = useState<number | null>(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const c = params.get('country_id');
      return c ? parseInt(c, 10) : null;
    } catch {
      return null;
    }
  });
  const [selectedRemote, setSelectedRemote] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleSelectCountry = (cId: number | null) => {
    setSelectedCountry(cId);
    setCurrentPage(1);
    try {
      const params = new URLSearchParams(window.location.search);
      if (cId !== null) {
        params.set('country_id', cId.toString());
      } else {
        params.delete('country_id');
      }
      const newQuery = params.toString();
      const newUrl = `${window.location.pathname}${newQuery ? '?' + newQuery : ''}`;
      window.history.replaceState(null, '', newUrl);
    } catch {}
  };

  // Jobs Data
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [selectedJobDetail, setSelectedJobDetail] = useState<JobDetail | null>(null);

  // User & Auth State
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // Saved Jobs
  const [savedJobIds, setSavedJobIds] = useState<number[]>(() => {
    try {
      const saved = localStorage.getItem('compust_saved_jobs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [showOnlySaved, setShowOnlySaved] = useState(false);

  // Initial Load: User & Metadata
  useEffect(() => {
    const initApp = async () => {
      try {
        const [cList, compList] = await Promise.all([
          api.getCountries(),
          api.getCompanies(),
        ]);
        setCountries(cList);
        setCompanies(compList);

        const token = getStoredToken();
        if (token) {
          try {
            const [profile, userApps] = await Promise.all([
              api.getMe(),
              api.getApplications().catch(() => []),
            ]);
            setUser(profile);
            if (userApps && userApps.length > 0) {
              const ids = userApps.map((a) => a.job_id).filter((id): id is number => id !== null);
              setSavedJobIds((prev) => Array.from(new Set([...prev, ...ids])));
            }
          } catch {
            setStoredToken(null);
          }
        }
      } catch (err) {
        console.error('Initialization error:', err);
      }
    };
    initApp();
  }, []);

  // Fetch Jobs when filters or user change
  useEffect(() => {
    const fetchJobs = async () => {
      setLoadingJobs(true);
      try {
        const res = await api.getJobs({
          country_id: selectedCountry,
          remote_type: selectedRemote,
          search: searchTerm.trim() || undefined,
          page: currentPage,
          page_size: 12,
        });
        setJobs(res.items);
        setTotalJobs(res.total);
        setTotalPages(res.pages || 1);
      } catch (err) {
        console.error('Failed to load jobs:', err);
      } finally {
        setLoadingJobs(false);
      }
    };

    const timer = setTimeout(fetchJobs, 250);
    return () => clearTimeout(timer);
  }, [searchTerm, selectedCountry, selectedRemote, currentPage, user, refreshTrigger]);

  const refreshCompaniesAndJobs = async () => {
    try {
      const [cList, compList] = await Promise.all([
        api.getCountries(),
        api.getCompanies(),
      ]);
      setCountries(cList);
      setCompanies(compList);
      setRefreshTrigger((prev) => prev + 1);
    } catch (err) {
      console.error('Failed to refresh companies & countries:', err);
    }
  };

  const handleOpenJob = async (jobId: number) => {
    try {
      const detail = await api.getJobDetail(jobId);
      setSelectedJobDetail(detail);
    } catch (err: any) {
      alert(`Could not load job details: ${err.message}`);
    }
  };

  const toggleSaveJob = async (jobId: number) => {
    const isCurrentlySaved = savedJobIds.includes(jobId);
    setSavedJobIds((prev) => {
      const updated = isCurrentlySaved ? prev.filter((id) => id !== jobId) : [...prev, jobId];
      localStorage.setItem('compust_saved_jobs', JSON.stringify(updated));
      return updated;
    });

    if (user) {
      try {
        if (isCurrentlySaved) {
          await api.deleteApplicationByJob(jobId);
        } else {
          await api.trackApplication(jobId, { status: 'saved' });
        }
      } catch (err) {
        console.error('Failed to sync saved job to database:', err);
      }
    }
  };

  const handleLogout = () => {
    setStoredToken(null);
    setUser(null);
    if (activeTab === 'profile') setActiveTab('directory');
  };

  const getCompanyName = (companyId: number) => {
    const found = companies.find((c) => c.id === companyId);
    return found ? found.name : 'Verified Employer';
  };

  const displayedJobs = showOnlySaved
    ? jobs.filter((j) => savedJobIds.includes(j.id))
    : jobs;

  return (
    <StyledApp>
      {/* Floating Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={handleLogout}
        onOpenAISettings={() => setIsAISettingsOpen(true)}
      />

      <main className={`main-content ${activeTab === 'profile' || activeTab === 'interview-prep' ? 'wide' : ''}`}>
        {/* VIEW 1: DIRECTORY */}
        {activeTab === 'directory' && (
          <div className="directory-view">
            {/* Hero Banner */}
            <section className="hero-section">
              <div className="hero-badge">
                <Sparkles size={14} />
                <span>{t.hero.badge}</span>
              </div>
              <h1 className="hero-title">
                {t.hero.titlePrefix}<span className="gradient-text">{t.hero.titleHighlight}</span>{t.hero.titleSuffix}
              </h1>
              <p className="hero-subtitle">
                {t.hero.subtitle}
              </p>

              {/* Stats Ribbon */}
              <div className="stats-ribbon" role="region" aria-label="Directory statistics">
                <div className="stat-card stat-vacancies">
                  <div className="stat-icon-wrap icon-blue">
                    <Briefcase size={20} />
                  </div>
                  <div className="stat-text-col">
                    <span className="stat-val">{totalJobs}</span>
                    <span className="stat-lbl">Active Vacancies</span>
                  </div>
                </div>
                <div className="stat-card stat-sources">
                  <div className="stat-icon-wrap icon-purple">
                    <Building2 size={20} />
                  </div>
                  <div className="stat-text-col">
                    <span className="stat-val">{companies.length || 3}</span>
                    <span className="stat-lbl">Direct Sources</span>
                  </div>
                </div>
                <div className="stat-card stat-countries">
                  <div className="stat-icon-wrap icon-cyan">
                    <Globe2 size={20} />
                  </div>
                  <div className="stat-text-col">
                    <span className="stat-val">{countries.length || 2}</span>
                    <span className="stat-lbl">Countries</span>
                  </div>
                </div>
                <div className="stat-card stat-sanitized">
                  <div className="stat-icon-wrap icon-emerald">
                    <ShieldCheck size={20} />
                  </div>
                  <div className="stat-text-col">
                    <span className="stat-val">100%</span>
                    <span className="stat-lbl">Access Sanitized</span>
                  </div>
                </div>
              </div>

              {/* Search & Filter Bar */}
              <SearchBar
                searchTerm={searchTerm}
                onSearchChange={(val) => { setSearchTerm(val); setCurrentPage(1); }}
                selectedCountry={selectedCountry}
                onSelectCountry={handleSelectCountry}
                countries={countries}
                selectedRemote={selectedRemote}
                onSelectRemote={(r) => { setSelectedRemote(r); setCurrentPage(1); }}
              />
            </section>

            {/* Central Time Service & Auto-Sync Freshness Header */}
            <SyncStatusBanner onSyncCompleted={refreshCompaniesAndJobs} />

            {/* Controls Row */}
            <div className="controls-row">
              <div className="results-count">
                <span>Showing <strong>{displayedJobs.length}</strong> opportunities</span>
                {user && (
                  <span className="match-active-tag">
                    <Sparkles size={13} />
                    Personalized matching active
                  </span>
                )}
              </div>

              <div className="saved-toggle">
                <button
                  className={`toggle-saved-btn ${showOnlySaved ? 'active' : ''}`}
                  onClick={() => setShowOnlySaved(!showOnlySaved)}
                >
                  <Bookmark size={15} fill={showOnlySaved ? '#3b82f6' : 'none'} />
                  <span>Saved ({savedJobIds.length})</span>
                </button>
              </div>
            </div>

            {/* Jobs Grid */}
            {loadingJobs ? (
              <Loader message="Fetching verified opportunities..." />
            ) : displayedJobs.length === 0 ? (
              <div className="empty-state glass-panel">
                <Layers size={48} className="empty-icon" />
                <h3>{t.directory.noJobsFound}</h3>
                <p>{t.directory.noJobsSub}</p>
                <button
                  className="reset-btn"
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedCountry(null);
                    setSelectedRemote(null);
                    setShowOnlySaved(false);
                  }}
                >
                  Clear All Filters
                </button>
              </div>
            ) : (
              <div className="jobs-grid">
                {displayedJobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    companyName={getCompanyName(job.company_id)}
                    isSaved={savedJobIds.includes(job.id)}
                    onToggleSave={() => toggleSaveJob(job.id)}
                    onSelect={() => handleOpenJob(job.id)}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && !showOnlySaved && (
              <div className="pagination-bar">
                <button
                  className="page-nav-btn"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={16} />
                  <span>{t.directory.prev}</span>
                </button>
                <span className="page-indicator">
                  {t.directory.page} {currentPage} {t.directory.of} {totalPages}
                </span>
                <button
                  className="page-nav-btn"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                >
                  <span>{t.directory.next}</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: PROFILE & MATCH */}
        {activeTab === 'profile' && (
          <div className="profile-wrapper">
            {user ? (
              <ProfileView
                user={user}
                onUpdate={(updated) => setUser(updated)}
                initialJobTarget={targetJobForAssistant}
                onClearJobTarget={() => setTargetJobForAssistant(null)}
                onNavigateToApplications={() => setActiveTab('applications')}
                onNavigateToInterviewPrep={() => setActiveTab('interview-prep')}
              />
            ) : (
              <div className="unauth-profile glass-panel">
                <Sparkles size={40} className="sparkle-icon" />
                <h2>Unlock Rule-Based Matching</h2>
                <p>
                  Sign in or create a profile to configure your preferred work mode, city,
                  and salary expectations. Compust will calculate exact percentage matches
                  and explain missing or satisfied requirements for every vacancy.
                </p>
                <button className="open-auth-btn" onClick={() => setAuthModalOpen(true)}>
                  Sign In to Configure Profile
                </button>
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: APPLICATIONS TRACKER */}
        {activeTab === 'applications' && (
          <div className="applications-wrapper">
            {user ? (
              <ApplicationsView onSelectJob={(job) => handleOpenJob(job.id)} />
            ) : (
              <div className="unauth-profile glass-panel">
                <Sparkles size={40} className="sparkle-icon" />
                <h2>Personal Application Tracking</h2>
                <p>
                  Sign in or create an account to manage your opportunity pipeline from saved
                  bookmarks to applications, interviews, and confirmed offers.
                </p>
                <button className="open-auth-btn" onClick={() => setAuthModalOpen(true)}>
                  Sign In to View Applications
                </button>
              </div>
            )}
          </div>
        )}

        {/* VIEW: INTERNSHIP INTELLIGENCE */}
        {activeTab === 'internships' && (
          <InternshipScraperView availableCountries={countries} />
        )}

        {/* VIEW 4: SCRAPER DASHBOARD */}
        {activeTab === 'scraper' && (
          <ScraperDashboard companies={companies} />
        )}

        {/* VIEW 5: COMPANY & SOURCE MANAGEMENT */}
        {activeTab === 'companies' && (
          <CompanyManagementView
            countries={countries}
            onRefreshCountries={refreshCompaniesAndJobs}
            onCompanyUpdated={refreshCompaniesAndJobs}
          />
        )}

        {/* VIEW 6: DATA SUPERVISION */}
        {activeTab === 'supervision' && (
          <MyDataSupervisionView />
        )}

        {/* VIEW 7: GUIDE & DOCUMENTATION CENTER */}
        {activeTab === 'guide' && (
          <GuideView />
        )}

        {/* VIEW 8: INTERVIEW PREPARATION KNOWLEDGE CENTER */}
        {activeTab === 'interview-prep' && (
          <InterviewPrepView onNavigateToProfile={() => setActiveTab('profile')} />
        )}

        {/* VIEW 9: EXTENSION ONBOARDING & INSTALLATION */}
        {activeTab === 'extension' && (
          <ExtensionInstallView />
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <img src="/logo-transparent.png" alt="Compust Logo" className="f-logo" />
            <span className="f-name">Compust</span>
            <span className="f-tag">Local-First Career Intelligence</span>
          </div>
          <div className="footer-links">
            <button type="button" className="footer-link-btn" onClick={() => setActiveTab('directory')}>Opportunities</button>
            <span className="footer-dot" aria-hidden="true">•</span>
            <button type="button" className="footer-link-btn" onClick={() => setActiveTab('internships')}>Internships</button>
            <span className="footer-dot" aria-hidden="true">•</span>
            <button type="button" className="footer-link-btn" onClick={() => setActiveTab('applications')}>Applications</button>
            <span className="footer-dot" aria-hidden="true">•</span>
            <button type="button" className="footer-link-btn" onClick={() => setActiveTab('interview-prep')}>Interview Prep</button>
            <span className="footer-dot" aria-hidden="true">•</span>
            <button type="button" className="footer-link-btn" onClick={() => setActiveTab('guide')}>Guide & Docs</button>
          </div>
          <div className="footer-meta">
            <ShieldCheck size={14} className="f-shield" />
            <span>Private & Local-First • Compust v2.4</span>
          </div>
        </div>
      </footer>

      {/* Job Detail Modal */}
      <JobDetailModal
        job={selectedJobDetail}
        companyName={selectedJobDetail ? getCompanyName(selectedJobDetail.company_id) : ''}
        onClose={() => setSelectedJobDetail(null)}
        isAppliedInitially={selectedJobDetail ? savedJobIds.includes(selectedJobDetail.id) : false}
        onApplicationStatusChanged={(jobId) => {
          setSavedJobIds((prev) => Array.from(new Set([...prev, jobId])));
        }}
        onTargetJob={(jobData) => {
          setTargetJobForAssistant(jobData);
          setActiveTab('profile');
          setSelectedJobDetail(null);
        }}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={(newUser) => setUser(newUser)}
      />

      {/* Persistent Floating Quick Help, GitHub & Support Controls */}
      <FloatingHelpControls
        onNavigateToGuide={() => setActiveTab('guide')}
        activeTab={activeTab}
      />

      {/* Local AI Assistant Widget */}
      <AIAssistantWidget onOpenSettings={() => setIsAISettingsOpen(true)} />


      {/* Local AI Settings Modal */}
      <AISettingsModal
        isOpen={isAISettingsOpen}
        onClose={() => setIsAISettingsOpen(false)}
      />
    </StyledApp>
  );
};

const StyledApp = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100vh;

  .main-content {
    flex: 1;
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding: 32px 20px 80px;
    transition: max-width 0.25s ease;
  }

  .main-content.wide {
    max-width: 1560px;
  }

  .directory-view {
    display: flex;
    flex-direction: column;
    gap: 36px;
  }

  .hero-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 20px;
    margin: 20px auto 0;
    width: 100%;
    max-width: 900px;
  }

  .hero-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 6px 14px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 20px;
    color: var(--primary);
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0 auto;
  }

  [data-theme='light'] .hero-badge,
  :root[data-theme='light'] .hero-badge,
  .light .hero-badge {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #1e40af;
  }

  .hero-title {
    font-size: clamp(2rem, 4vw, 3.2rem);
    line-height: 1.15;
    max-width: 850px;
    margin: 0 auto;
    text-align: center;
    color: var(--text-primary);
  }

  .gradient-text {
    background: linear-gradient(135deg, #60a5fa 20%, #c084fc 80%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    color: #3b82f6;
  }

  [data-theme='light'] .gradient-text,
  :root[data-theme='light'] .gradient-text,
  .light .gradient-text {
    background: linear-gradient(135deg, #1d4ed8 20%, #6d28d9 80%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    color: #1d4ed8;
  }

  .hero-subtitle {
    font-size: 1.05rem;
    color: var(--text-muted);
    max-width: 680px;
    line-height: 1.6;
    margin: 0 auto;
    text-align: center;
  }

  .stats-ribbon {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 14px;
    width: 100%;
    max-width: 980px;
    margin: 12px auto 26px;
  }

  .stat-card {
    display: inline-flex;
    flex-direction: row;
    align-items: center;
    gap: 12px;
    padding: 6px 20px 6px 8px;
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 9999px;
    box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.35);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);

    &:hover {
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.2);
      box-shadow: 0 6px 22px -2px rgba(0, 0, 0, 0.5);
    }
  }

  .stat-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    flex-shrink: 0;

    &.icon-blue {
      background: rgba(30, 58, 138, 0.28);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.38);
    }

    &.icon-purple {
      background: rgba(88, 28, 135, 0.28);
      color: #c084fc;
      border: 1px solid rgba(168, 85, 247, 0.38);
    }

    &.icon-cyan {
      background: rgba(19, 78, 74, 0.32);
      color: #2dd4bf;
      border: 1px solid rgba(20, 184, 166, 0.38);
    }

    &.icon-emerald {
      background: rgba(6, 78, 59, 0.32);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.38);
    }
  }

  .stat-text-col {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    min-width: 0;
  }

  .stat-val {
    font-size: 1.35rem;
    font-weight: 800;
    line-height: 1.1;
    color: #ffffff;
    font-family: var(--font-heading);
    letter-spacing: -0.01em;
  }

  .stat-lbl {
    font-size: 0.68rem;
    font-weight: 700;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-top: 2px;
    white-space: nowrap;
  }

  /* Light Theme Overrides for Stat Pill Cards */
  [data-theme='light'] &,
  :root[data-theme='light'] &,
  .light & {
    .stat-card {
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid rgba(0, 0, 0, 0.08);
      box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.06);

      &:hover {
        border-color: rgba(0, 0, 0, 0.16);
        box-shadow: 0 6px 20px -2px rgba(0, 0, 0, 0.1);
      }
    }

    .stat-val {
      color: #0f172a;
    }

    .stat-lbl {
      color: #64748b;
    }

    .stat-icon-wrap {
      &.icon-blue {
        background: #dbeafe;
        color: #1d4ed8;
        border-color: #bfdbfe;
      }
      &.icon-purple {
        background: #f3e8ff;
        color: #7e22ce;
        border-color: #e9d5ff;
      }
      &.icon-cyan {
        background: #ccfbf1;
        color: #0f766e;
        border-color: #99f6e4;
      }
      &.icon-emerald {
        background: #d1fae5;
        color: #065f46;
        border-color: #a7f3d0;
      }
    }
  }

  .controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 4px;
  }

  .results-count {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .match-active-tag {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #34d399;
    font-weight: 600;
    font-size: 0.8rem;
  }

  .toggle-saved-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    font-size: 0.82rem;
    font-weight: 600;
    transition: all 0.2s;

    &:hover {
      background: var(--border-subtle);
      color: var(--text-primary);
    }

    &.active {
      background: rgba(59, 130, 246, 0.15);
      border-color: rgba(59, 130, 246, 0.3);
      color: var(--primary);
    }
  }

  .jobs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 22px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 14px;
    padding: 60px 20px;

    .empty-icon { color: var(--text-muted); }
    h3 { font-size: 1.3rem; }
    p { color: var(--text-muted); max-width: 420px; font-size: 0.9rem; }
  }

  .reset-btn {
    padding: 9px 20px;
    background: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 0.85rem;
    border-radius: 10px;
    margin-top: 8px;
    transition: all 0.2s;

    &:hover { background: #1d4ed8; }
  }

  .pagination-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    margin-top: 20px;
  }

  .page-nav-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: var(--border-subtle);
    }
    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }

  .page-indicator {
    font-size: 0.88rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .unauth-profile {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 16px;
    padding: 60px 24px;
    max-width: 600px;
    margin: 40px auto;

    .sparkle-icon { color: #8b5cf6; }
    h2 { font-size: 1.6rem; }
    p { color: var(--text-muted); line-height: 1.6; }
  }

  .open-auth-btn {
    padding: 12px 28px;
    background: #2563eb;
    color: #ffffff;
    font-weight: 600;
    border-radius: 12px;
    margin-top: 10px;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    transition: all 0.2s;

    &:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
    }
  }

  .app-footer {
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-surface);
    padding: 22px 20px;
    margin-top: auto;
  }

  .footer-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .footer-brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .f-logo {
    width: 22px;
    height: 22px;
    object-fit: contain;
    filter: drop-shadow(0 0 6px rgba(0, 240, 255, 0.4));
  }

  .f-name {
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: -0.01em;
    color: var(--text-primary);
  }

  .f-tag {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-left: 6px;
  }

  .footer-links {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .footer-link-btn {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-secondary);
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    transition: color 0.15s ease;

    &:hover {
      color: var(--primary);
    }
  }

  .footer-dot {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  .footer-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    color: var(--text-muted);

    .f-shield {
      color: var(--accent-emerald);
      flex-shrink: 0;
    }
  }
`;

export default App;
