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
import { AISettingsModal } from './components/AISettingsModal';
import { AIAssistantWidget } from './components/AIAssistantWidget';
import { Loader } from './components/Loader';
import { Sparkles, Layers, ShieldCheck, ChevronLeft, ChevronRight, Bookmark } from 'lucide-react';
import { useTranslation } from './i18n';

export const App: React.FC = () => {
  const { t } = useTranslation();

  // Navigation & View
  const [activeTab, setActiveTab] = useState<'directory' | 'profile' | 'scraper' | 'applications' | 'companies' | 'supervision'>('directory');
  const [isAISettingsOpen, setIsAISettingsOpen] = useState(false);

  // Metadata
  const [countries, setCountries] = useState<Country[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCountry, setSelectedCountry] = useState<number | null>(null);
  const [selectedRemote, setSelectedRemote] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

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
              const ids = userApps.map((a) => a.job_id);
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
  }, [searchTerm, selectedCountry, selectedRemote, currentPage, user]);

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

      <main className="main-content">
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
              <div className="stats-ribbon">
                <div className="stat-card">
                  <span className="stat-val">{totalJobs}</span>
                  <span className="stat-lbl">Active Vacancies</span>
                </div>
                <div className="stat-sep" />
                <div className="stat-card">
                  <span className="stat-val">{companies.length || 3}</span>
                  <span className="stat-lbl">Direct Sources</span>
                </div>
                <div className="stat-sep" />
                <div className="stat-card">
                  <span className="stat-val">{countries.length || 2}</span>
                  <span className="stat-lbl">Countries</span>
                </div>
                <div className="stat-sep" />
                <div className="stat-card">
                  <span className="stat-val">100%</span>
                  <span className="stat-lbl">XSS Sanitized</span>
                </div>
              </div>

              {/* Search & Filter Bar */}
              <SearchBar
                searchTerm={searchTerm}
                onSearchChange={(val) => { setSearchTerm(val); setCurrentPage(1); }}
                selectedCountry={selectedCountry}
                onSelectCountry={(cId) => { setSelectedCountry(cId); setCurrentPage(1); }}
                countries={countries}
                selectedRemote={selectedRemote}
                onSelectRemote={(r) => { setSelectedRemote(r); setCurrentPage(1); }}
              />
            </section>

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
              <ProfileView user={user} onUpdate={(updated) => setUser(updated)} />
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

        {/* VIEW 4: SCRAPER DASHBOARD */}
        {activeTab === 'scraper' && (
          <ScraperDashboard companies={companies} />
        )}

        {/* VIEW 5: COMPANY & SOURCE MANAGEMENT */}
        {activeTab === 'companies' && (
          <CompanyManagementView
            countries={countries}
            onRefreshCountries={async () => {
              const cList = await api.getCountries();
              setCountries(cList);
            }}
          />
        )}

        {/* VIEW 6: DATA SUPERVISION */}
        {activeTab === 'supervision' && (
          <MyDataSupervisionView />
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
          <div className="footer-compliance">
            <ShieldCheck size={16} />
            <span>Robots.txt Enforced • Bleach HTML Sanitized • Zero AI Hallucination</span>
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
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={(newUser) => setUser(newUser)}
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
    margin-top: 20px;
  }

  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 20px;
    color: #60a5fa;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .hero-title {
    font-size: clamp(2rem, 4vw, 3.2rem);
    line-height: 1.15;
    max-width: 850px;
  }

  .gradient-text {
    background: linear-gradient(135deg, #60a5fa 20%, #c084fc 80%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    max-width: 680px;
    line-height: 1.6;
  }

  .stats-ribbon {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
    padding: 12px 28px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    margin: 8px 0 16px;
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .stat-val {
    font-size: 1.25rem;
    font-weight: 800;
    color: #ffffff;
    font-family: var(--font-heading);
  }

  .stat-lbl {
    font-size: 0.75rem;
    color: #64748b;
  }

  .stat-sep {
    width: 1px;
    height: 28px;
    background: rgba(255, 255, 255, 0.08);
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
    color: #94a3b8;
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
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #94a3b8;
    font-size: 0.82rem;
    font-weight: 600;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #ffffff;
    }

    &.active {
      background: rgba(59, 130, 246, 0.15);
      border-color: rgba(59, 130, 246, 0.3);
      color: #60a5fa;
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

    .empty-icon { color: #64748b; }
    h3 { font-size: 1.3rem; }
    p { color: #94a3b8; max-width: 420px; font-size: 0.9rem; }
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
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #f8fafc;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.12);
    }
    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }

  .page-indicator {
    font-size: 0.88rem;
    color: #94a3b8;
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
    p { color: #94a3b8; line-height: 1.6; }
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
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(8, 12, 20, 0.9);
    padding: 24px 20px;
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
    width: 20px;
    height: 20px;
    object-fit: contain;
    filter: drop-shadow(0 0 6px rgba(0, 240, 255, 0.4));
  }

  .f-name {
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 1rem;
    letter-spacing: -0.01em;
    color: #ffffff;
  }

  .f-tag {
    font-size: 0.8rem;
    color: #64748b;
    margin-left: 6px;
  }

  .footer-compliance {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: #64748b;
  }
`;

export default App;
