import React, { useState, useMemo } from 'react';
import {
  Search,
  ExternalLink,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  Database,
  Briefcase,
  UserCheck,
  FileText,
  FolderKanban,
  HelpCircle,
  Code2,
  Activity,
  Zap,
  Globe,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Sliders,
  Sparkles,
  Info,
} from 'lucide-react';
import {
  GITHUB_REPO_URL,
  GITHUB_ISSUES_URL,
  GITHUB_DISCUSSIONS_URL,
  DEMO_VIDEO_PATH,
  GUIDE_SECTIONS,
} from '../../config/guideConfig';

import './GuideView.css';

export const GuideView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('welcome');
  const [videoError, setVideoError] = useState(false);
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);
  const [openFaqIndices, setOpenFaqIndices] = useState<Set<number>>(new Set([0, 1]));

  const handleCopyCode = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCodeId(id);
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const toggleFaq = (index: number) => {
    setOpenFaqIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return GUIDE_SECTIONS;
    const q = searchQuery.toLowerCase();
    return GUIDE_SECTIONS.filter(
      (s) => s.title.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  return (
    <div className="guide-container">
      {/* Search and Quick Action Header */}
      <header className="guide-header-bar">
        <div className="guide-search-wrapper">
          <Search size={18} className="guide-search-icon" />
          <input
            type="text"
            className="guide-search-input"
            placeholder="Search documentation, scrapers, matching, database, FAQ..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search Compust Guide"
          />
          {searchQuery && (
            <button
              className="guide-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="guide-quick-links">
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="guide-external-repo-btn"
          >
            <Code2 size={16} />
            <span>GitHub Repository</span>
            <ExternalLink size={13} />
          </a>
          <a
            href={GITHUB_ISSUES_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="guide-external-repo-btn"
          >
            <ShieldAlert size={16} />
            <span>Report Issue</span>
          </a>
          <a
            href={GITHUB_DISCUSSIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="guide-external-repo-btn"
          >
            <HelpCircle size={16} />
            <span>Discussions</span>
          </a>
        </div>

      </header>

      {/* Main Layout: Sticky Sidebar TOC + Content */}
      <div className="guide-layout">
        {/* Sticky Sidebar Navigation */}
        <aside className="guide-sidebar">
          <div className="guide-sidebar-title">Table of Contents</div>
          <nav className="guide-toc-nav" aria-label="Guide Navigation">
            {filteredSections.map((sec) => (
              <a
                key={sec.id}
                href={`#${sec.id}`}
                className={`guide-toc-link ${activeSection === sec.id ? 'active' : ''}`}
                onClick={() => setActiveSection(sec.id)}
              >
                <span>{sec.title}</span>
                {sec.badge && (
                  <span className={`guide-toc-badge ${sec.badge.toLowerCase()}`}>
                    {sec.badge}
                  </span>
                )}
              </a>
            ))}
          </nav>
        </aside>

        {/* Content Area */}
        <main className="guide-content">
          {/* 1. Welcome to Compust */}
          <section id="welcome" className="guide-section guide-hero">
            <div className="guide-hero-badge">
              <Sparkles size={14} />
              <span>Official Compust Documentation</span>
            </div>
            <h1>Welcome to Compust</h1>
            <p>
              Compust is an open-source, local-first career intelligence and employment opportunity platform.
              It unites ethical career portal ingestion, deterministic resume profiling, an explainable 5-factor matching engine,
              and full application lifecycle management—giving candidates complete transparency over their job search.
            </p>

            <div className="guide-hero-stats">
              <div className="guide-stat-card">
                <span className="guide-stat-value">7-Layer</span>
                <span className="guide-stat-label">Universal Parser</span>
              </div>
              <div className="guide-stat-card">
                <span className="guide-stat-value">73,380</span>
                <span className="guide-stat-label">Title Intelligence Index</span>
              </div>
              <div className="guide-stat-card">
                <span className="guide-stat-value">Headless</span>
                <span className="guide-stat-label">Playwright Fallback</span>
              </div>
              <div className="guide-stat-card">
                <span className="guide-stat-value">Explainable</span>
                <span className="guide-stat-label">5-Factor Matching</span>
              </div>
            </div>
          </section>

          {/* 2. Critical Pre-Use Notice */}
          <section id="important-notice" className="guide-section">
            <div className="guide-notice-card">
              <div className="notice-header">
                <ShieldAlert size={26} color="#f59e0b" />
                <h3>Please read this before using Compust</h3>
              </div>

              <div className="notice-grid">
                <div className="notice-item pos">
                  <h4>
                    <CheckCircle2 size={16} /> What Compust IS
                  </h4>
                  <p>
                    A specialized career discovery and career intelligence engine designed to help you ingest,
                    diagnose, and centralize opportunities directly from verified company portals, evaluate match
                    fidelity, tailor resumes, and track applications through interview stages.
                  </p>
                </div>

                <div className="notice-item neg">
                  <h4>
                    <AlertTriangle size={16} /> What Compust IS NOT
                  </h4>
                  <p>
                    Compust is <strong>NOT</strong> a full replacement for LinkedIn, Indeed, Glassdoor, professional
                    recruiters, or company career boards. It complements traditional job searches. Compust does not
                    claim to host every vacancy on the internet.
                  </p>
                </div>

                <div className="notice-item warn">
                  <h4>
                    <Info size={16} /> Why Some Jobs May Be Missing
                  </h4>
                  <p>
                    Whether an opening appears depends on whether its source portal can be accessed, detected, parsed,
                    and normalized. <strong>Not seeing a job in Compust does NOT mean the company does not have that opening available.</strong> Always check primary company career sites directly.
                  </p>
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <h4 style={{ color: '#f8fafc', fontSize: '0.98rem', marginBottom: '8px' }}>
                  Current Project Limitations & Known Challenges:
                </h4>
                <ul className="notice-limitations-list">
                  <li>
                    <strong>Cloudflare & WAF Protection:</strong> Some corporate career portals enforce Cloudflare Bot Management or Turnstile challenge gates. Compust strictly respects robots.txt and site restrictions; it does <em>not</em> attempt to bypass anti-bot, CAPTCHA, or rate-limiting controls.
                  </li>
                  <li>
                    <strong>Client-Rendered SPA Shells:</strong> Modern career portals often serve empty <code>&lt;div id="root"&gt;&lt;/div&gt;</code> shells. Compust uses an automated Playwright headless browser fallback to hydrate these applications, but heavily guarded client widgets may require direct ATS subdomain URLs (e.g. <code>jobs.ashbyhq.com/org</code> instead of <code>org.com/careers</code>).
                  </li>
                  <li>
                    <strong>Partial Discovery:</strong> Dynamic infinite scroll or complex multi-tier category filters may discover a subset of available openings.
                  </li>
                  <li>
                    <strong>Manual Extraction Validation:</strong> Completed HTTP requests must always be verified by inspecting returned titles to ensure general site headers (e.g. "Careers", "About", "Services") are not mistaken for job titles.
                  </li>
                </ul>
              </div>

              <div style={{ marginTop: '20px', padding: '12px 16px', background: 'rgba(56, 189, 248, 0.08)', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                <p style={{ margin: 0, fontSize: '0.88rem', color: '#93c5fd' }}>
                  <strong>Project Status:</strong> Compust is an evolving, open-source work in progress. Community contributions are warmly welcome, but contribution is entirely optional—you may freely use Compust as an end-user or develop private parsers for personal use.
                </p>
              </div>
            </div>
          </section>

          {/* 3. Product Demo Video */}
          <section id="demo-video" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Play size={24} color="#38bdf8" />
                See Compust in Action
              </h2>
              <p className="guide-section-subtitle">
                Watch an end-to-end product walkthrough demonstrating portal ingestion, diagnostics, matching, and application tracking.
              </p>
            </div>

            <div className="guide-video-frame-container">
              <div className="guide-video-frame">
                {/* Decorative Window Top Bar */}
                <div className="video-frame-browser-bar">
                  <div className="browser-dots">
                    <span className="browser-dot red" />
                    <span className="browser-dot yellow" />
                    <span className="browser-dot green" />
                  </div>
                  <span className="browser-title">Compust Platform Demo • Local In-App Playback</span>
                  <span className="browser-badge">Native HTML5</span>
                </div>

                <div className="video-wrapper">
                  {!videoError ? (
                    <video
                      className="guide-html5-video"
                      controls
                      playsInline
                      preload="metadata"
                      onError={() => setVideoError(true)}
                      aria-label="Compust Interactive Walkthrough Video"
                    >
                      <source src={DEMO_VIDEO_PATH} type="video/mp4" />
                      Your browser does not support the video tag.
                    </video>
                  ) : (
                    <div className="video-fallback-card">
                      <AlertTriangle size={36} color="#f59e0b" />
                      <h4>Product Demo Video Unavailable</h4>
                      <p>
                        The local video asset could not be loaded. Please refer to the written step-by-step
                        walkthroughs below to explore portal configuration and scraping workflows.
                      </p>
                      <a href="#getting-started" className="step-action-tag">
                        Jump to Getting Started Guide
                      </a>
                    </div>
                  )}
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '10px', textAlign: 'center' }}>
                Note: The video above is an embedded developer placeholder demonstrating application workflows. You can easily replace it by updating <code>public/demo.mp4</code>.
              </p>
            </div>
          </section>

          {/* 4. How Compust Works */}
          <section id="how-it-works" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Layers size={24} color="#818cf8" />
                How Compust Works
              </h2>
              <p className="guide-section-subtitle">
                Understanding the unified data flow across the Compust platform ecosystem.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6', marginBottom: '20px' }}>
                Compust establishes a strict, clean lifecycle separating company entities from individual job vacancies:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#38bdf8', margin: '0 0 8px 0' }}>Company vs. Job Country</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    A <strong>Company</strong> (e.g., Orange or Capgemini) can operate across multiple countries (Morocco, France, etc.). However, a <strong>Job</strong> has its own specific normalized country and location where the position is stationed.
                  </p>
                </div>

                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#818cf8', margin: '0 0 8px 0' }}>Scrape Targets & Runs</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Each company maintains one or more <strong>Scrape Targets</strong> (Careers URL or ATS portal). When a crawl runs, a timestamped <strong>Scraping Run</strong> records jobs found, added, updated, and detailed telemetry errors.
                  </p>
                </div>

                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#34d399', margin: '0 0 8px 0' }}>Matching & Pipeline</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Discovered vacancies are evaluated by the deterministic 5-factor match engine against your active structured resume, flowing into your Kanban applications board and funnel analytics.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 5. Scraper Architecture & Live Pipeline */}
          <section id="scraper-architecture" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Activity size={24} color="#34d399" />
                Scraper Architecture & Live Data-Flow
              </h2>
              <p className="guide-section-subtitle">
                How Compust crawls, detects, parses, and persists vacancies with animated live flow indicators.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="arch-flow-diagram" role="img" aria-label="Compust Scraper Pipeline Architecture Diagram">
                <div className="arch-node">
                  <div className="arch-node-icon blue"><Globe size={20} /></div>
                  <div className="arch-node-title">Target Portal</div>
                  <div className="arch-node-desc">Careers URL or ATS Endpoint</div>
                </div>

                <div className="arch-arrow-container">
                  <svg className="guide-flow-arrow" viewBox="0 0 44 24"><path d="M2 12 L36 12 M30 6 L38 12 L30 18" /></svg>
                </div>

                <div className="arch-node">
                  <div className="arch-node-icon amber"><ShieldAlert size={20} /></div>
                  <div className="arch-node-title">Compliance Gate</div>
                  <div className="arch-node-desc">Robots.txt & Polite Delay</div>
                </div>

                <div className="arch-arrow-container">
                  <svg className="guide-flow-arrow" viewBox="0 0 44 24"><path d="M2 12 L36 12 M30 6 L38 12 L30 18" /></svg>
                </div>

                <div className="arch-node">
                  <div className="arch-node-icon indigo"><Layers size={20} /></div>
                  <div className="arch-node-title">Parsing Layers 1-7</div>
                  <div className="arch-node-desc">Adapters + Title Intelligence</div>
                </div>

                <div className="arch-arrow-container">
                  <svg className="guide-flow-arrow" viewBox="0 0 44 24"><path d="M2 12 L36 12 M30 6 L38 12 L30 18" /></svg>
                </div>

                <div className="arch-node">
                  <div className="arch-node-icon purple"><Zap size={20} /></div>
                  <div className="arch-node-title">Browser Fallback</div>
                  <div className="arch-node-desc">Playwright Chromium for SPAs</div>
                </div>

                <div className="arch-arrow-container">
                  <svg className="guide-flow-arrow" viewBox="0 0 44 24"><path d="M2 12 L36 12 M30 6 L38 12 L30 18" /></svg>
                </div>

                <div className="arch-node">
                  <div className="arch-node-icon emerald"><Database size={20} /></div>
                  <div className="arch-node-title">Persistence Engine</div>
                  <div className="arch-node-desc">Deduplication & MySQL Storage</div>
                </div>
              </div>

              <div style={{ marginTop: '28px' }}>
                <h4 style={{ color: '#f8fafc', fontSize: '1.05rem', marginBottom: '14px' }}>
                  The 7-Layer Universal Fallback System:
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Layer 1: ATS Platform Adapters</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Auto-detects Ashby, Workable, Greenhouse, Lever, SmartRecruiters, Workday, Teamtailor, Orange, Capgemini, Inwi, and Deloitte.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Layer 2: Direct JSON APIs</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Parses structured JSON payloads when targets return direct REST or GraphQL endpoints.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Layer 3: Schema.org JSON-LD</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Extracts standardized <code>JobPosting</code> microdata embedded in page markup.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Layer 4: Embedded Next.js State</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Inspects <code>__NEXT_DATA__</code> and <code>window.__initial_state__</code> scripts.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Layers 5 & 6: Semantic HTML Cards</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Evaluates repeated card classes, grid layouts, and semantic heading cards (h1-h4).
                    </p>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#34d399' }}>Layer 7: Job Title Intelligence</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '6px 0 0 0' }}>
                      Context-aware DOM clustering against the local 73,380-title dictionary when prior layers discover 0 jobs.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 6. Getting Started: A-to-Z Workflow */}
          <section id="getting-started" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <CheckCircle2 size={24} color="#38bdf8" />
                Getting Started: A-to-Z Workflow
              </h2>
              <p className="guide-section-subtitle">
                Follow these 20 practical steps from first-time setup to active application tracking.
              </p>
            </div>

            <div className="steps-timeline">
              <div className="step-card">
                <div className="step-number-badge">01</div>
                <div className="step-body">
                  <div className="step-title">Configure MySQL Database</div>
                  <div className="step-desc">
                    Ensure MySQL 8.0+ is running. Set your database credentials in <code>important/.env</code> (e.g., <code>DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/compust</code>).
                  </div>
                  <span className="step-action-tag">Database Configuration</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">02</div>
                <div className="step-body">
                  <div className="step-title">Run Alembic Database Migrations</div>
                  <div className="step-desc">
                    Apply all schema migrations to create the required tables: <code>alembic upgrade head</code>.
                  </div>
                  <span className="step-action-tag">Schema Setup</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">03</div>
                <div className="step-body">
                  <div className="step-title">Start Backend & Frontend Servers</div>
                  <div className="step-desc">
                    Launch the FastAPI server with <code>uvicorn src.app.main:app --reload</code> and start the React client with <code>npm run dev</code> in <code>important/frontend</code>.
                  </div>
                  <span className="step-action-tag">Service Execution</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">04</div>
                <div className="step-body">
                  <div className="step-title">Set Up Candidate Profile & Upload Resume</div>
                  <div className="step-desc">
                    Navigate to <strong>Profile</strong>. Fill in technical skills, experience history, and upload your PDF resume for deterministic text extraction.
                  </div>
                  <span className="step-action-tag">Profile View</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">05</div>
                <div className="step-body">
                  <div className="step-title">Find an Employer's Official Careers Portal</div>
                  <div className="step-desc">
                    Visit the company website, locate their "Careers" or "Jobs" link, and copy the actual listing URL (e.g. <code>https://boards.greenhouse.io/company</code>).
                  </div>
                  <span className="step-action-tag">Portal Identification</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">06</div>
                <div className="step-body">
                  <div className="step-title">Open Data Supervision & Run Scraper Diagnostics</div>
                  <div className="step-desc">
                    Switch to <strong>Data Supervision ➔ Scraper Test Diagnostic</strong>. Paste the careers URL and click <strong>Run Diagnostic Test</strong>.
                  </div>
                  <span className="step-action-tag">Data Supervision View</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">07</div>
                <div className="step-body">
                  <div className="step-title">Inspect Diagnostic Telemetry & Discovered Jobs</div>
                  <div className="step-desc">
                    Verify the HTTP status (200), rendering mode, platform detected, confidence score, and inspect sample jobs to ensure real vacancies were extracted.
                  </div>
                  <span className="step-action-tag">Validation Step</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">08</div>
                <div className="step-body">
                  <div className="step-title">Add Company in Companies & Sources</div>
                  <div className="step-desc">
                    Open <strong>Companies & Sources</strong>, click <strong>+ Add Company</strong>, enter the name, website, Careers URL, and assign operating countries.
                  </div>
                  <span className="step-action-tag">Companies View</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">09</div>
                <div className="step-body">
                  <div className="step-title">Execute "Run Now" to Synchronize Vacancies</div>
                  <div className="step-desc">
                    Expand the company row and click <strong>Run Now</strong>. The scraper verifies robots.txt compliance, crawls the portal, and records a Scraping Run.
                  </div>
                  <span className="step-action-tag">Ingestion Run</span>
                </div>
              </div>

              <div className="step-card">
                <div className="step-number-badge">10</div>
                <div className="step-body">
                  <div className="step-title">Explore Matched Opportunities & Apply</div>
                  <div className="step-desc">
                    Visit <strong>Opportunities</strong> to filter vacancies by country, inspect match scores and missing skill gaps, tailor your resume, and track applications in the Kanban board.
                  </div>
                  <span className="step-action-tag">Opportunity Pipeline</span>
                </div>
              </div>
            </div>
          </section>

          {/* 7. Testing a Career Portal */}
          <section id="testing-career-sites" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Sliders size={24} color="#38bdf8" />
                Testing a Career Portal
              </h2>
              <p className="guide-section-subtitle">
                How to dry-run and inspect scraper behavior without writing to the database.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                Compust includes a built-in diagnostic testing suite located under <strong>Data Supervision ➔ Scraper Test Diagnostic</strong>.
                This allows you to test any URL in isolation:
              </p>

              <div style={{ marginTop: '16px' }}>
                <h4 style={{ color: '#f8fafc', marginBottom: '10px' }}>What to look for in the Diagnostic Report:</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#38bdf8' }}>Status & Confidence</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
                      <code>SUCCESS</code> with confidence ≥ 0.70 indicates high-fidelity extraction.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#818cf8' }}>Rendering Mode</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
                      Identifies whether static HTML was sufficient or client-side SPA hydration was triggered.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#34d399' }}>Discovery Method</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
                      Reports which strategy (platform adapter, JSON-LD, title intelligence, etc.) won.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <strong style={{ color: '#f59e0b' }}>Diagnostic Errors</strong>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
                      Detailed audit logs explain reasons for rejections, rejected headings, or timeouts.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 8. Diagnosing Results & Failures */}
          <section id="success-vs-failure" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <AlertTriangle size={24} color="#f59e0b" />
                Diagnosing Results & Failures
              </h2>
              <p className="guide-section-subtitle">
                Understanding why a scraper returns 0 jobs, 1 job, or restricted responses.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '12px', padding: '16px' }}>
                  <h4 style={{ color: '#f87171', margin: '0 0 6px 0' }}>Problem: 0 Jobs Discovered</h4>
                  <p style={{ fontSize: '0.88rem', color: '#cbd5e1', margin: 0, lineHeight: 1.5 }}>
                    <strong>Cause:</strong> The page might be an unhydrated SPA, behind Cloudflare WAF, or the URL entered is a corporate home page rather than the careers subportal.<br />
                    <strong>Solution:</strong> Look for the direct ATS link (e.g. <code>jobs.lever.co/company</code>) in the page network tab or check if the browser fallback option was active.
                  </p>
                </div>

                <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '12px', padding: '16px' }}>
                  <h4 style={{ color: '#fbbf24', margin: '0 0 6px 0' }}>Problem: Only 1 Job or Partial Openings Found</h4>
                  <p style={{ fontSize: '0.88rem', color: '#cbd5e1', margin: 0, lineHeight: 1.5 }}>
                    <strong>Cause:</strong> The portal uses dynamic infinite scrolling or client-side cursor pagination that static crawling cannot paginate.<br />
                    <strong>Solution:</strong> Check if an unpaginated JSON endpoint or specific country filter URL is available.
                  </p>
                </div>

                <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '12px', padding: '16px' }}>
                  <h4 style={{ color: '#38bdf8', margin: '0 0 6px 0' }}>Problem: HTTP 403 Forbidden / Cloudflare Challenge</h4>
                  <p style={{ fontSize: '0.88rem', color: '#cbd5e1', margin: 0, lineHeight: 1.5 }}>
                    <strong>Cause:</strong> The target server blocks non-browser User-Agent headers or serves a Cloudflare challenge page.<br />
                    <strong>Solution:</strong> Compust automatically retries 403s with browser-grade headers and Playwright headless rendering. If the domain enforces strict Turnstile challenges, configure a direct public ATS subdomain.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 9. Developer & Contributor Guide */}
          <section id="contributor-guide" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Code2 size={24} color="#c084fc" />
                Developer & Contributor Guide
              </h2>
              <p className="guide-section-subtitle">
                How to implement, test, and contribute new portal adapters and scraping strategies.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                Adding support for a new career portal is modular and follows Compust's strategy design pattern:
              </p>

              <div className="guide-code-box">
                <div className="guide-code-header">
                  <span>src/app/scraper/platforms/my_platform.py</span>
                  <button
                    className="guide-code-copy-btn"
                    onClick={() => handleCopyCode('adapter-code', `from bs4 import BeautifulSoup\nfrom ..http_client import FetchedSource\nfrom ..orange_parser import JobCandidate, ParseResult\n\nclass MyPlatformAdapter:\n    name = "my_platform"\n\n    def can_handle(self, source: FetchedSource) -> bool:\n        return "myplatform.com" in source.requested_url.lower()\n\n    def parse(self, source: FetchedSource) -> ParseResult:\n        soup = BeautifulSoup(source.body, "html.parser")\n        jobs: list[JobCandidate] = []\n        # Extract vacancies and return ParseResult\n        return ParseResult(jobs=jobs, errors=[])`)}
                  >
                    {copiedCodeId === 'adapter-code' ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                    <span>{copiedCodeId === 'adapter-code' ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="guide-code-pre">
{`from bs4 import BeautifulSoup
from ..http_client import FetchedSource
from ..orange_parser import JobCandidate, ParseResult

class MyPlatformAdapter:
    name = "my_platform"

    def can_handle(self, source: FetchedSource) -> bool:
        return "myplatform.com" in source.requested_url.lower()

    def parse(self, source: FetchedSource) -> ParseResult:
        soup = BeautifulSoup(source.body, "html.parser")
        jobs: list[JobCandidate] = []
        for card in soup.select("div.job-listing"):
            title = card.select_one("h3").get_text(strip=True)
            link = card.select_one("a")["href"]
            jobs.append(JobCandidate(title=title, job_url=link))
        return ParseResult(jobs=jobs, errors=[])`}
                </pre>
              </div>

              <div style={{ marginTop: '16px' }}>
                <h4 style={{ color: '#f8fafc', marginBottom: '10px' }}>Contributor Step Checklist:</h4>
                <ol style={{ color: '#cbd5e1', fontSize: '0.88rem', lineHeight: '1.7', paddingLeft: '20px', margin: 0 }}>
                  <li>Create your platform adapter in <code>src/app/scraper/platforms/</code>.</li>
                  <li>Register the adapter in <code>src/app/scraper/registry.py</code> under <code>_PLATFORM_STRATEGIES</code>.</li>
                  <li>Add a deterministic test HTML fixture under <code>important/tests/fixtures/</code>.</li>
                  <li>Write unit tests ensuring candidates parse correctly without synthetic URLs.</li>
                  <li>Execute the full test suite with <code>pytest</code> to ensure zero regressions.</li>
                  <li>Submit your Pull Request to the official repository at <code>https://github.com/putbullet/compust</code>.</li>
                </ol>
              </div>
            </div>
          </section>

          {/* 10. Opportunities & Job Catalog */}
          <section id="opportunities" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Briefcase size={24} color="#38bdf8" />
                Opportunities & Job Catalog
              </h2>
              <p className="guide-section-subtitle">
                Navigating curated vacancies, country filtering, work modes, and job details.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                The <strong>Opportunities</strong> directory provides a live, curated catalog of verified openings:
              </p>
              <ul style={{ color: '#cbd5e1', fontSize: '0.88rem', lineHeight: '1.7', paddingLeft: '20px' }}>
                <li><strong>Multi-Country Filtering:</strong> Switch between countries using URL query synchronization (<code>?country_id=...</code>) or view all international openings.</li>
                <li><strong>Work Modes:</strong> Filter by Remote, Hybrid, or On-site positions.</li>
                <li><strong>Opportunity Detail Modal:</strong> Inspect full job descriptions, required skills, and instant match analysis.</li>
                <li><strong>Saved Jobs:</strong> Bookmark vacancies to review later with client-side persistence.</li>
              </ul>
            </div>
          </section>

          {/* 11. Explainable Match Engine */}
          <section id="matching-engine" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Sparkles size={24} color="#38bdf8" />
                Explainable Match Engine
              </h2>
              <p className="guide-section-subtitle">
                Deterministic, mathematically explainable scoring without black-box hallucination.
              </p>
            </div>

            <div className="guide-notice-card" style={{ borderColor: 'rgba(56, 189, 248, 0.4)', borderLeftColor: '#38bdf8' }}>
              <h3 style={{ color: '#38bdf8', marginTop: 0 }}>Deterministic 5-Factor Scoring (100% Total)</h3>
              <p style={{ color: '#cbd5e1', fontSize: '0.92rem', lineHeight: '1.6' }}>
                Compust does not generate arbitrary percentages. Match scores are strictly computed via <code>src/app/matching/matcher.py</code> across five explicit categories:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px' }}>
                  <div style={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '1.2rem' }}>35%</div>
                  <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.86rem' }}>Skills Match</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.76rem' }}>Direct & synonym matching from profile & active resume.</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px' }}>
                  <div style={{ color: '#818cf8', fontWeight: 'bold', fontSize: '1.2rem' }}>25%</div>
                  <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.86rem' }}>Experience Duration</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.76rem' }}>Evaluated work history months and title relevance.</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px' }}>
                  <div style={{ color: '#34d399', fontWeight: 'bold', fontSize: '1.2rem' }}>15%</div>
                  <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.86rem' }}>Education Level</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.76rem' }}>Degree level, field of study, and academic alignment.</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px' }}>
                  <div style={{ color: '#fbbf24', fontWeight: 'bold', fontSize: '1.2rem' }}>15%</div>
                  <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.86rem' }}>Location & Country</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.76rem' }}>Matches preferred countries or remote availability.</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '10px' }}>
                  <div style={{ color: '#f43f5e', fontWeight: 'bold', fontSize: '1.2rem' }}>10%</div>
                  <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.86rem' }}>Languages</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.76rem' }}>Verified multilingual competencies.</div>
                </div>
              </div>

              <p style={{ color: '#94a3b8', fontSize: '0.84rem', marginTop: '16px', marginBottom: 0 }}>
                Every match produces human-readable <code>positive_factors</code> and <code>missing_factors</code> pills so candidates know exactly why they scored what they scored.
              </p>
            </div>
          </section>

          {/* 12. Profile & Candidate Preferences */}
          <section id="profile-management" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <UserCheck size={24} color="#34d399" />
                Profile & Candidate Preferences
              </h2>
              <p className="guide-section-subtitle">
                Manage your technical competencies, work history, education, and target countries.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                Your candidate profile feeds directly into the matching engine and application tracking:
              </p>
              <ul style={{ color: '#cbd5e1', fontSize: '0.88rem', lineHeight: '1.7', paddingLeft: '20px' }}>
                <li><strong>Skills Catalog:</strong> Add competencies with proficiency levels.</li>
                <li><strong>Experience History:</strong> Record past roles, dates, and responsibilities.</li>
                <li><strong>Education & Languages:</strong> Detail degrees, institutions, and multilingual proficiencies.</li>
                <li><strong>Target Countries:</strong> Select which countries you are authorized and willing to work in.</li>
              </ul>
            </div>
          </section>

          {/* 13. Resume Builder & Tailoring */}
          <section id="resume-builder" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <FileText size={24} color="#38bdf8" />
                Resume Builder & Tailoring
              </h2>
              <p className="guide-section-subtitle">
                Zero-OCR PDF extraction, customizable templates, document export, and vacancy tailoring.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#38bdf8', margin: '0 0 8px 0' }}>Zero-OCR Deterministic Extraction</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Extracts text layers from uploaded PDFs with 100% fidelity, eliminating AI hallucinations and misread formatting.
                  </p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#818cf8', margin: '0 0 8px 0' }}>Templates & One-Click Export</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Choose between Modern, Classic, Minimal, and Technical layouts with direct PDF and Word (.docx) export.
                  </p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <h4 style={{ color: '#34d399', margin: '0 0 8px 0' }}>Job-Specific Tailoring Suggestions</h4>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Generates tailored summary and experience refinement recommendations for specific vacancies, saving tailored copies without overwriting your master resume.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 14. Applications Tracker & Kanban */}
          <section id="applications-tracker" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <FolderKanban size={24} color="#818cf8" />
                Applications Tracker & Kanban
              </h2>
              <p className="guide-section-subtitle">
                Manage your job application lifecycle from Saved to Offer or Terminal status.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                The <strong>My Applications</strong> board organizes your recruitment pipelines into fluid columns:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', margin: '14px 0' }}>
                {['Saved', 'Applied', 'No Answer', '1st Interview', '2nd Interview', '3rd Interview', 'Final Interview', 'Offer', 'Accepted', 'Rejected', 'Withdrawn'].map((status) => (
                  <span key={status} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '8px', padding: '6px 12px', fontSize: '0.8rem', color: '#e2e8f0' }}>
                    {status}
                  </span>
                ))}
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.86rem', lineHeight: '1.5', margin: 0 }}>
                Track external applications manually (e.g. roles found on LinkedIn or direct recruiter contacts), log interview dates, expected salaries, and recruiter notes.
              </p>
            </div>
          </section>

          {/* 15. Application Pipeline & Funnel (Sankey) */}
          <section id="pipeline-analytics" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Activity size={24} color="#34d399" />
                Application Pipeline & Funnel (Sankey)
              </h2>
              <p className="guide-section-subtitle">
                Visualize interview progression, conversion rates, and outcome drop-offs.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p style={{ color: '#cbd5e1', fontSize: '0.94rem', lineHeight: '1.6' }}>
                The built-in <strong>Sankey Pipeline Chart</strong> renders your actual interview flows dynamically:
              </p>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', margin: '12px 0' }}>
                <code style={{ color: '#38bdf8', fontSize: '0.86rem' }}>
                  Total Applications ➔ 1st Interview ➔ 2nd Interview ➔ Final Interview ➔ Offers ➔ Accepted
                </code>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.86rem', lineHeight: '1.5', margin: 0 }}>
                Accurately reveals where applications drop off, identifying whether resume optimization, initial screening, or technical interview performance requires focus.
              </p>
            </div>
          </section>

          {/* 16. Frequently Asked Questions */}
          <section id="faq" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <HelpCircle size={24} color="#38bdf8" />
                Frequently Asked Questions
              </h2>
              <p className="guide-section-subtitle">
                Instant answers to common questions about Compust, scraping, matching, and setup.
              </p>
            </div>

            <div className="faq-list">
              {[
                {
                  q: 'Is Compust a replacement for LinkedIn or Indeed?',
                  a: 'No. Compust is a companion career intelligence tool. It helps you discover vacancies directly from verified employer career portals, match them against your resume deterministically, and organize your applications. Always continue using traditional channels like LinkedIn and recruiter networks.',
                },
                {
                  q: 'Why did my scraper return zero jobs for a company?',
                  a: 'Several factors can cause 0 jobs: the page may require client-side JavaScript rendering (handled by our Playwright fallback), Cloudflare WAF bot protection may be active, or the URL entered might be a marketing page rather than the actual job board. Try using the direct ATS URL (e.g. jobs.ashbyhq.com/company).',
                },
                {
                  q: 'How does Compust handle client-rendered SPA websites?',
                  a: 'Compust integrates an automated headless Chromium fallback using Playwright. When static HTTP requests return empty containers (like <div id="root"></div>), Playwright launches in the background, aborts images and fonts for speed, executes the client-side JavaScript, and feeds the hydrated DOM into the 7-layer universal parser.',
                },
                {
                  q: 'What is the Job Title Intelligence fallback?',
                  a: 'Compust bundles an in-memory index of 73,380 real-world job titles. If standard JSON-LD, metadata, and CSS card heuristics discover 0 jobs, the Job Title Intelligence layer scans the DOM for clusters of recognizable job titles to locate hidden opportunity containers.',
                },
                {
                  q: 'Can a company have multiple countries assigned?',
                  a: 'Yes! In Compust, companies can operate across multiple countries through a many-to-many relationship (company_countries). However, each individual vacancy has its own normalized location and country where the job is based.',
                },
                {
                  q: 'How is the match score calculated?',
                  a: 'Matching is 100% deterministic and explainable: Skills (35%), Experience (25%), Education (15%), Location & Country Preferences (15%), and Languages (10%). Positive factors and missing factors are displayed in full transparency.',
                },
                {
                  q: 'Can I track applications for jobs I found outside Compust?',
                  a: 'Yes. In the Applications view, click "+ Add Application" to track external applications with custom company names, roles, recruiter contact information, follow-up dates, and salary notes.',
                },
                {
                  q: 'How can I contribute a new scraper or parser?',
                  a: 'You can implement a custom platform adapter in src/app/scraper/platforms/, register it in registry.py, add a test HTML fixture under tests/fixtures/, run pytest, and submit a Pull Request on GitHub!',
                },
              ].map((item, idx) => {
                const isOpen = openFaqIndices.has(idx);
                return (
                  <div key={idx} className={`faq-item ${isOpen ? 'open' : ''}`}>
                    <button
                      className="faq-question"
                      onClick={() => toggleFaq(idx)}
                      aria-expanded={isOpen}
                    >
                      <span>{item.q}</span>
                      {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                    {isOpen && (
                      <div className="faq-answer">
                        <p>{item.a}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};
