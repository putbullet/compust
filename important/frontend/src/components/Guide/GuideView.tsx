import React, { useState, useMemo, useCallback, useEffect } from 'react';
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
  Puzzle,
  GraduationCap,
  Target,
  BookOpen,
} from 'lucide-react';
import {
  GITHUB_REPO_URL,
  GITHUB_ISSUES_URL,
  GITHUB_DISCUSSIONS_URL,
  GOOGLE_DRIVE_DEMO_URL,
  DEMO_PREVIEW_IMAGE_PATH,
  GUIDE_SECTIONS,
  GUIDE_SECTION_GROUPS,
} from '../../config/guideConfig';
import type { GuideSectionGroup } from '../../config/guideConfig';
import { useTranslation } from '../../i18n';
import { GuideDiagram } from './GuideDiagram';

import './GuideView.css';

// ─── Diagram definitions ─────────────────────────────────────────────────────

const SYSTEM_OVERVIEW_DIAGRAM = `
flowchart LR
  subgraph Sources["Career Sources"]
    A[Career Portals<br/>& ATS Sites]
    B[Browser Extension<br/>LinkedIn · Indeed · Glassdoor]
  end

  subgraph Engine["Compust Backend"]
    C[7-Layer<br/>Scraper Pipeline]
    D[Match Engine<br/>5-Factor Scoring]
    DB[(MySQL<br/>Database)]
  end

  subgraph Studio["Resume Studio"]
    E[Resume Editor<br/>A4 Preview]
    F[ATS Checker]
    G[Deep Analysis<br/>Job Target Panel]
  end

  subgraph Tracking["Application Tracking"]
    H[Kanban Board<br/>& Funnel Analytics]
  end

  A --> C
  B --> D
  C --> DB
  DB --> D
  D --> H
  E --> F
  E --> G
  G --> H
`;

const EXTENSION_FLOW_DIAGRAM = `
flowchart TD
  A([Browse LinkedIn · Indeed<br/>Glassdoor · WTTJ]) --> B{Extension<br/>Detects Job Page?}
  B -- No --> Z([Keep Browsing])
  B -- Yes --> C[Overlay Appears<br/>Auto-Analyse Begins]
  C --> D[quickAddAndAnalyze<br/>API Call]
  D --> E{Has Active<br/>Resume?}
  E -- No --> F[Show Job Info<br/>No Score]
  E -- Yes --> G[Show Match Score<br/>Skills · Gaps · Visa Check]
  F --> H{User Action}
  G --> H
  H -- "＋ Add" --> I[Save to Opportunities<br/>No Kanban Status]
  H -- "✓ Applied" --> J[Save + Mark Applied<br/>in Kanban]
  H -- "★ Save" --> K[Save + Mark Interested<br/>in Kanban]
  H -- "✕ Skip" --> Z
`;

const RESUME_STUDIO_DIAGRAM = `
flowchart LR
  A([Upload PDF<br/>or Start Fresh]) --> B[Deterministic<br/>Text Extraction]
  B --> C[Resume Editor<br/>Structured Sections]
  C --> D[A4 Live Preview<br/>RenderCV Style]
  D --> E{Action}
  E --> F[Export PDF / DOCX]
  E --> G[ATS Checker<br/>6-Pillar Audit]
  E --> H[Job Target Panel<br/>Deep Analysis]
  H --> I[Tailored Recs<br/>Email · Message<br/>Cover Letter<br/>Interview Prep]
  H --> J[Save Tailored Copy<br/>to Kanban]
`;

const GUIDE_TITLE_TRANSLATIONS: Record<string, Record<string, string>> = {
  fr: {
    welcome: 'Bienvenue dans Compust', 'important-notice': 'A lire avant utilisation', 'demo-video': 'Voir Compust en action',
    'how-it-works': 'Fonctionnement de Compust', 'getting-started': 'Configuration de A a Z', 'resume-studio': 'Vue d\u2019ensemble de Resume Studio',
    'deep-analysis': 'Ciblage de poste et analyse approfondie', 'ats-checker': 'Verificateur ATS', 'extension-install': 'Installation et configuration',
    'extension-sites': 'Sites detectes automatiquement', 'extension-capture-flow': 'Flux de capture : Ajouter / Candidature / Enregistrer / Ignorer',
    opportunities: 'Opportunites et catalogue', internships: 'Stages', 'matching-engine': 'Moteur de correspondance explicable',
    'profile-management': 'Profil et preferences candidat', 'applications-tracker': 'Suivi des candidatures et Kanban', 'pipeline-analytics': 'Pipeline et entonnoir des candidatures',
    'scraper-architecture': 'Architecture et pipeline du scraper', 'testing-career-sites': 'Tester un portail carriere', 'success-vs-failure': 'Diagnostiquer les resultats et erreurs',
    'scraper-diagnostics-ai': 'Assistant IA de diagnostic du scraper', 'contributor-guide': 'Guide developpeur et contributeur', faq: 'Questions frequentes',
  },
  nl: {
    welcome: 'Welkom bij Compust', 'important-notice': 'Lees dit voor gebruik', 'demo-video': 'Compust in actie',
    'how-it-works': 'Hoe Compust werkt', 'getting-started': 'Installatie van A tot Z', 'resume-studio': 'Overzicht van Resume Studio',
    'deep-analysis': 'Jobtargeting en diepgaande analyse', 'ats-checker': 'ATS-checker', 'extension-install': 'Installatie en configuratie',
    'extension-sites': 'Automatisch gedetecteerde sites', 'extension-capture-flow': 'Captureflow: Toevoegen / Toegepast / Opslaan / Overslaan',
    opportunities: 'Kansen en vacaturecatalogus', internships: 'Stages', 'matching-engine': 'Uitlegbaar matchingmechanisme',
    'profile-management': 'Profiel en kandidaatvoorkeuren', 'applications-tracker': 'Sollicitatietracker en Kanban', 'pipeline-analytics': 'Sollicitatiepipeline en funnel',
    'scraper-architecture': 'Scraperarchitectuur en pipeline', 'testing-career-sites': 'Een carriereportaal testen', 'success-vs-failure': 'Resultaten en fouten diagnosticeren',
    'scraper-diagnostics-ai': 'AI-assistent voor scraperdiagnose', 'contributor-guide': 'Handleiding voor ontwikkelaars en bijdragers', faq: 'Veelgestelde vragen',
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

export const GuideView: React.FC = () => {
  const { t, language } = useTranslation();

  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('welcome');
  const [videoError, setVideoError] = useState(false);
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);
  const [openFaqIndices, setOpenFaqIndices] = useState<Set<number>>(new Set([0, 1]));

  const localizedSections = useMemo(
    () => GUIDE_SECTIONS.map((section) => ({
      ...section,
      title: GUIDE_TITLE_TRANSLATIONS[language]?.[section.id] ?? section.title,
    })),
    [language]
  );

  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash && localizedSections.some((section) => section.id === hash)) {
      setActiveSection(hash);
      requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView({ block: 'start' }));
    }

    const sections = localizedSections
      .map((section) => document.getElementById(section.id))
      .filter((section): section is HTMLElement => Boolean(section));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveSection(visible.target.id);
      },
      { rootMargin: '-96px 0px -65% 0px', threshold: [0.05, 0.25, 0.6] }
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [localizedSections]);

  const handleCopyCode = useCallback((id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCodeId(id);
    setTimeout(() => setCopiedCodeId(null), 2000);
  }, []);

  const toggleFaq = useCallback((index: number) => {
    setOpenFaqIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return localizedSections;
    const q = searchQuery.trim().toLowerCase();
    return localizedSections.filter(
      (s) => [s.title, s.description, ...(s.keywords ?? [])]
        .some((value) => value.toLowerCase().includes(q))
    );
  }, [localizedSections, searchQuery]);

  // Map group id → translated label
  const groupLabel = useCallback(
    (groupId: string): string => {
      const map: Record<string, string> = {
        'getting-started': t.guide.groupGettingStarted,
        'resume-studio': t.guide.groupResumeStudio,
        'browser-extension': t.guide.groupBrowserExtension,
        'job-discovery': t.guide.groupJobDiscovery,
        'application-tracking': t.guide.groupApplicationTracking,
        'data-supervision': t.guide.groupDataSupervision,
        'developer': t.guide.groupDeveloper,
        'help': t.guide.groupHelp,
      };
      return map[groupId] ?? groupId;
    },
    [t]
  );

  // Build grouped sidebar items from filtered results
  const groupedSidebar = useMemo(() => {
    const seen = new Set<string>();
    const groups: { group: GuideSectionGroup; sections: typeof filteredSections }[] = [];
    for (const grp of GUIDE_SECTION_GROUPS) {
      const secs = filteredSections.filter((s) => s.group === grp.id);
      if (secs.length > 0 && !seen.has(grp.id)) {
        seen.add(grp.id);
        groups.push({ group: grp, sections: secs });
      }
    }
    return groups;
  }, [filteredSections]);

  const handleNavClick = useCallback((id: string) => {
    setActiveSection(id);
    window.history.replaceState(null, '', `#${id}`);
  }, []);

  return (
    <div className="guide-container">
      {/* Search and Quick Action Header */}
      <header className="guide-header-bar">
        <div className="guide-search-wrapper">
          <Search size={18} className="guide-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="guide-search-input"
            placeholder={t.guide.searchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label={language === 'fr' ? 'Rechercher dans le guide Compust' : language === 'nl' ? 'Compust-gids doorzoeken' : 'Search Compust Guide'}
          />
          {searchQuery && (
            <button
              className="guide-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label={language === 'fr' ? 'Effacer la recherche' : language === 'nl' ? 'Zoekopdracht wissen' : 'Clear search'}
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
            <Code2 size={16} aria-hidden="true" />
            <span>{t.guide.githubRepo}</span>
            <ExternalLink size={13} aria-hidden="true" />
          </a>
          <a
            href={GITHUB_ISSUES_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="guide-external-repo-btn"
          >
            <ShieldAlert size={16} aria-hidden="true" />
            <span>{t.guide.reportIssue}</span>
          </a>
          <a
            href={GITHUB_DISCUSSIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="guide-external-repo-btn"
          >
            <HelpCircle size={16} aria-hidden="true" />
            <span>{t.guide.discussions}</span>
          </a>
        </div>
      </header>

      {/* Main Layout: Sticky Sidebar TOC + Content */}
      <div className="guide-layout">
        {/* Sticky Sidebar Navigation */}
        <aside className="guide-sidebar">
          <div className="guide-sidebar-title">{t.guide.tableOfContents}</div>
          <nav className="guide-toc-nav" aria-label={language === 'fr' ? 'Navigation du guide' : language === 'nl' ? 'Gidsnavigatie' : 'Guide Navigation'}>
            {groupedSidebar.length === 0 ? (
              <p className="guide-toc-empty">{t.guide.searchNoResults}</p>
            ) : (
              groupedSidebar.map(({ group, sections }) => (
                <div key={group.id} className="guide-toc-group">
                  <div className="guide-toc-group-label">{groupLabel(group.id)}</div>
                  {sections.map((sec) => (
                    <a
                      key={sec.id}
                      href={`#${sec.id}`}
                      className={`guide-toc-link ${activeSection === sec.id ? 'active' : ''}`}
                      onClick={() => handleNavClick(sec.id)}
                    >
                      <span>{sec.title}</span>
                      {sec.badge && (
                        <span className={`guide-toc-badge ${sec.badge.toLowerCase()}`}>
                          {sec.badge}
                        </span>
                      )}
                    </a>
                  ))}
                </div>
              ))
            )}
          </nav>
        </aside>

        {/* Content Area */}
        <main className="guide-content">

          {/* ── 1. Welcome ─────────────────────────────────────────────────── */}
          <section id="welcome" className="guide-section guide-hero">
            <div className="guide-hero-badge">
              <Sparkles size={14} aria-hidden="true" />
              <span>Official Compust Documentation</span>
            </div>
            <h1>Welcome to Compust</h1>
            <p>
              Compust is an open-source, local-first career intelligence and employment
              opportunity platform. It unites ethical career portal ingestion, deterministic
              resume profiling, an explainable 5-factor matching engine, browser-extension
              capture from major job boards, and full application lifecycle management—giving
              candidates complete transparency over their job search.
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
                <span className="guide-stat-value">4 Sites</span>
                <span className="guide-stat-label">Extension Auto-Capture</span>
              </div>
              <div className="guide-stat-card">
                <span className="guide-stat-value">Explainable</span>
                <span className="guide-stat-label">5-Factor Matching</span>
              </div>
            </div>
          </section>

          {/* ── 2. Critical Pre-Use Notice ─────────────────────────────────── */}
          <section id="important-notice" className="guide-section">
            <div className="guide-notice-card">
              <div className="notice-header">
                <ShieldAlert size={26} aria-hidden="true" className="notice-icon-warn" />
                <h3>Please read this before using Compust</h3>
              </div>

              <div className="notice-grid">
                <div className="notice-item pos">
                  <h4>
                    <CheckCircle2 size={16} aria-hidden="true" /> What Compust IS
                  </h4>
                  <p>
                    A specialized career discovery and career intelligence engine designed to
                    help you ingest, diagnose, and centralize opportunities directly from
                    verified company portals, evaluate match fidelity, tailor resumes, and
                    track applications through interview stages.
                  </p>
                </div>

                <div className="notice-item neg">
                  <h4>
                    <AlertTriangle size={16} aria-hidden="true" /> What Compust IS NOT
                  </h4>
                  <p>
                    Compust is <strong>NOT</strong> a full replacement for LinkedIn, Indeed,
                    Glassdoor, professional recruiters, or company career boards. It
                    complements traditional job searches. Compust does not claim to host every
                    vacancy on the internet.
                  </p>
                </div>

                <div className="notice-item warn">
                  <h4>
                    <Info size={16} aria-hidden="true" /> Why Some Jobs May Be Missing
                  </h4>
                  <p>
                    Whether an opening appears depends on whether its source portal can be
                    accessed, detected, parsed, and normalized.{' '}
                    <strong>
                      Not seeing a job in Compust does NOT mean the company does not have that
                      opening.
                    </strong>{' '}
                    Always check primary company career sites directly.
                  </p>
                </div>
              </div>

              <div className="notice-limitations-block">
                <h4 className="notice-limitations-title">
                  Current Project Limitations &amp; Known Challenges:
                </h4>
                <ul className="notice-limitations-list">
                  <li>
                    <strong>Cloudflare &amp; WAF Protection:</strong> Some corporate career
                    portals enforce Cloudflare Bot Management or Turnstile challenge gates.
                    Compust strictly respects robots.txt and site restrictions; it does{' '}
                    <em>not</em> attempt to bypass anti-bot, CAPTCHA, or rate-limiting
                    controls.
                  </li>
                  <li>
                    <strong>Client-Rendered SPA Shells:</strong> Modern career portals often
                    serve empty <code>&lt;div id="root"&gt;&lt;/div&gt;</code> shells. Compust
                    uses an automated Playwright headless browser fallback to hydrate these
                    applications, but heavily guarded client widgets may require direct ATS
                    subdomain URLs (e.g. <code>jobs.ashbyhq.com/org</code> instead of{' '}
                    <code>org.com/careers</code>).
                  </li>
                  <li>
                    <strong>Partial Discovery:</strong> Dynamic infinite scroll or complex
                    multi-tier category filters may discover a subset of available openings.
                  </li>
                  <li>
                    <strong>Manual Extraction Validation:</strong> Completed HTTP requests
                    must always be verified by inspecting returned titles to ensure general
                    site headers are not mistaken for job titles.
                  </li>
                </ul>
              </div>

              <div className="notice-project-status">
                <p>
                  <strong>Project Status:</strong> Compust is an evolving, open-source work
                  in progress. Community contributions are warmly welcome, but contribution is
                  entirely optional—you may freely use Compust as an end-user or develop
                  private parsers for personal use.
                </p>
              </div>
            </div>
          </section>

          {/* ── 3. Product Demo Video ──────────────────────────────────────── */}
          <section id="demo-video" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Play size={24} aria-hidden="true" className="icon-cyan" />
                See Compust in Action
              </h2>
              <p className="guide-section-subtitle">
                Watch an end-to-end product walkthrough demonstrating portal ingestion,
                diagnostics, matching, and application tracking.
              </p>
            </div>

            <div className="guide-video-frame-container">
              <div className="guide-video-frame">
                <div className="video-frame-browser-bar">
                  <div className="browser-dots">
                    <span className="browser-dot red" />
                    <span className="browser-dot yellow" />
                    <span className="browser-dot green" />
                  </div>
                  <span className="browser-title">
                    Compust Platform Demo • Interactive Walkthrough
                  </span>
                  <span className="browser-badge">Google Drive Demo</span>
                </div>

                <div className="video-wrapper">
                  {!videoError ? (
                    <a
                      href={GOOGLE_DRIVE_DEMO_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="guide-demo-preview-link"
                      aria-label="Open Compust demo video on Google Drive in a new tab"
                    >
                      <img
                        src={DEMO_PREVIEW_IMAGE_PATH}
                        alt="Compust Walkthrough Demo — Click to watch"
                        className="guide-demo-preview-img"
                        onError={() => setVideoError(true)}
                      />
                      <div className="guide-demo-overlay-badge">
                        <Play size={16} fill="#ffffff" color="#ffffff" aria-hidden="true" />
                        <span>{t.guide.watchDemo}</span>
                        <ExternalLink size={14} aria-hidden="true" />
                      </div>
                    </a>
                  ) : (
                    <div className="video-fallback-card">
                      <AlertTriangle size={36} aria-hidden="true" className="icon-amber" />
                      <h4>Product Demo Video</h4>
                      <p>Click below to watch the complete product walkthrough on Google Drive.</p>
                      <a
                        href={GOOGLE_DRIVE_DEMO_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="step-action-tag"
                      >
                        Watch on Google Drive
                      </a>
                    </div>
                  )}
                </div>
              </div>
              <p className="guide-video-caption">
                Click the preview image above to watch the full HD Compust walkthrough on
                Google Drive.
              </p>
            </div>
          </section>

          {/* ── 4. How Compust Works — System Overview ─────────────────────── */}
          <section id="how-it-works" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Layers size={24} aria-hidden="true" className="icon-purple" />
                How Compust Works
              </h2>
              <p className="guide-section-subtitle">
                Understanding the unified data flow across the Compust platform ecosystem.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Compust establishes a clean lifecycle separating company entities from
                individual job vacancies, and connects scraping, matching, resume tooling, and
                application tracking into one coherent pipeline:
              </p>

              <GuideDiagram
                definition={SYSTEM_OVERVIEW_DIAGRAM}
                ariaLabel="Compust System Overview: Career sources feed the scraper pipeline into the database and match engine, which flows into the kanban tracker. Resume Studio connects to ATS Checker and Job Target Panel, which also feeds the kanban."
              />

              <div className="guide-info-grid">
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Company vs. Job Country</h4>
                  <p className="info-card-body">
                    A <strong>Company</strong> (e.g., Google, Capgemini, Siemens) can operate
                    across multiple countries. However, a <strong>Job</strong> has its own
                    specific normalized country and location.
                  </p>
                </div>

                <div className="guide-info-card">
                  <h4 className="info-card-title purple">Scrape Targets &amp; Runs</h4>
                  <p className="info-card-body">
                    Each company maintains one or more <strong>Scrape Targets</strong> (Careers
                    URL or ATS portal). When a crawl runs, a timestamped{' '}
                    <strong>Scraping Run</strong> records jobs found, added, updated, and
                    detailed telemetry errors.
                  </p>
                </div>

                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">Matching &amp; Pipeline</h4>
                  <p className="info-card-body">
                    Discovered vacancies are evaluated by the deterministic 5-factor match
                    engine against your active structured resume, flowing into your Kanban
                    applications board and funnel analytics.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 5. A-to-Z Setup Workflow ───────────────────────────────────── */}
          <section id="getting-started" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <CheckCircle2 size={24} aria-hidden="true" className="icon-cyan" />
                A-to-Z Setup Workflow
              </h2>
              <p className="guide-section-subtitle">
                Follow these practical steps from first-time setup to active application
                tracking.
              </p>
            </div>

            <div className="steps-timeline">
              {[
                {
                  n: '01', title: 'Configure MySQL Database', tag: 'Database Configuration',
                  desc: <>Ensure MySQL 8.0+ is running. Set credentials in <code>important/.env</code> (e.g., <code>DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/compust</code>).</>,
                },
                {
                  n: '02', title: 'Run Alembic Database Migrations', tag: 'Schema Setup',
                  desc: <>Apply all schema migrations: <code>alembic upgrade head</code>.</>,
                },
                {
                  n: '03', title: 'Start Backend & Frontend Servers', tag: 'Service Execution',
                  desc: <>Launch FastAPI: <code>uvicorn src.app.main:app --reload</code> and the React client: <code>npm run dev</code> in <code>important/frontend</code>.</>,
                },
                {
                  n: '04', title: 'Set Up Candidate Profile & Upload Resume', tag: 'Profile View',
                  desc: <>Navigate to <strong>Match Profile</strong>. Fill in technical skills, experience history, education, and upload your PDF resume.</>,
                },
                {
                  n: '05', title: 'Find an Employer\'s Official Careers Portal', tag: 'Portal Identification',
                  desc: <>Visit the company website, locate their "Careers" link, and copy the actual listing URL (e.g. <code>https://boards.greenhouse.io/company</code>).</>,
                },
                {
                  n: '06', title: 'Run Scraper Test Diagnostic', tag: 'Data Supervision View',
                  desc: <>Switch to <strong>Data Supervision → Scraper Test Diagnostic</strong>. Paste the careers URL and click <strong>Run Diagnostic Test</strong> to verify extractability without writing to the database.</>,
                },
                {
                  n: '07', title: 'Inspect Diagnostic Telemetry & Discovered Jobs', tag: 'Validation Step',
                  desc: <>Verify the HTTP status (200), rendering mode, platform detected, confidence score, and inspect sample jobs to ensure real vacancies were extracted.</>,
                },
                {
                  n: '08', title: 'Add Company in Companies & Sources', tag: 'Companies View',
                  desc: <>Open <strong>Company Intel</strong>, click <strong>+ Add Company</strong>, enter the name, website, Careers URL, and assign operating countries.</>,
                },
                {
                  n: '09', title: 'Execute "Run Now" to Synchronize Vacancies', tag: 'Ingestion Run',
                  desc: <>Expand the company row and click <strong>Run Now</strong>. The scraper verifies robots.txt compliance, crawls the portal, and records a Scraping Run.</>,
                },
                {
                  n: '10', title: 'Explore Matched Opportunities & Apply', tag: 'Opportunity Pipeline',
                  desc: <>Visit <strong>Opportunities</strong> to filter vacancies by country, inspect match scores and missing skill gaps, tailor your resume, and track applications in the Kanban board.</>,
                },
              ].map((step) => (
                <div key={step.n} className="step-card">
                  <div className="step-number-badge">{step.n}</div>
                  <div className="step-body">
                    <div className="step-title">{step.title}</div>
                    <div className="step-desc">{step.desc}</div>
                    <span className="step-action-tag">{step.tag}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── 6. Resume Studio ───────────────────────────────────────────── */}
          <section id="resume-studio" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <FileText size={24} aria-hidden="true" className="icon-cyan" />
                Resume Studio
              </h2>
              <p className="guide-section-subtitle">
                RenderCV-style A4 resume editor with structured sections, live preview,
                per-language localization, and one-click PDF/DOCX export.
              </p>
            </div>

            <div className="guide-architecture-board">
              <GuideDiagram
                definition={RESUME_STUDIO_DIAGRAM}
                ariaLabel="Resume Studio workflow: Upload PDF or start fresh, deterministic extraction, structured editor, A4 live preview, then export or run ATS Checker or Job Target Deep Analysis."
              />

              <div className="guide-info-grid" style={{ marginTop: '24px' }}>
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Structured Sections</h4>
                  <p className="info-card-body">
                    Edit Profile, Experience, Education, Skills, Projects, Certifications,
                    Languages, and custom sections. Drag-and-drop section reordering,
                    show/hide per section, and custom section heading titles per language.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title purple">Templates &amp; Styling</h4>
                  <p className="info-card-body">
                    Switch between <strong>modern</strong> and <strong>classic</strong>
                    &nbsp;templates with an accent colour picker, font family selector, and
                    font-size control. Real-time A4 preview with correct pagination.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">Export &amp; Localization</h4>
                  <p className="info-card-body">
                    Export to <strong>PDF</strong> or <strong>DOCX</strong>. Choose the
                    resume language (English, French, German, Spanish) to automatically
                    translate section headings and date labels for international applications.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title amber">Multiple Resume Copies</h4>
                  <p className="info-card-body">
                    Maintain multiple resumes simultaneously. Set one as your{' '}
                    <strong>default (active)</strong> resume — this is what the match engine
                    and browser extension score against. Tailored copies can be saved without
                    overwriting your master.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 7. Deep Analysis ───────────────────────────────────────────── */}
          <section id="deep-analysis" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Target size={24} aria-hidden="true" className="icon-purple" />
                Job Targeting &amp; Deep Analysis
              </h2>
              <p className="guide-section-subtitle">
                Paste a job description to get a full match analysis, resume suggestions,
                outreach materials, and interview preparation — all powered by your configured
                AI provider.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Inside <strong>Resume Studio</strong>, select a resume and open the{' '}
                <strong>Job Target</strong> panel. Paste or enter the target role and job
                description. After analysis, six tabs are available:
              </p>

              <div className="guide-tab-showcase">
                {[
                  { label: 'Match', icon: <Sparkles size={16} aria-hidden="true" />, desc: 'Overall match score, demonstrated strengths, and identified skill gaps for the target role.' },
                  { label: 'Recommendations', icon: <CheckCircle2 size={16} aria-hidden="true" />, desc: 'Specific bullet-level resume edit suggestions organized by section (Experience, Skills, Summary, Projects).' },
                  { label: 'Email', icon: <Code2 size={16} aria-hidden="true" />, desc: 'A tailored outreach/networking email draft referencing the specific role and your matching strengths.' },
                  { label: 'Message', icon: <Activity size={16} aria-hidden="true" />, desc: 'A concise LinkedIn-style connection request message calibrated to the target position.' },
                  { label: 'Cover Letter', icon: <FileText size={16} aria-hidden="true" />, desc: 'A structured cover letter in your chosen language — English, French, German, or Spanish — with export to PDF or DOCX.' },
                  { label: 'Interview', icon: <GraduationCap size={16} aria-hidden="true" />, desc: 'Predicted interview questions tailored to the job description with suggested answer frameworks.' },
                ].map((tab) => (
                  <div key={tab.label} className="guide-tab-card">
                    <div className="guide-tab-card-header">
                      {tab.icon}
                      <strong>{tab.label}</strong>
                    </div>
                    <p>{tab.desc}</p>
                  </div>
                ))}
              </div>

              <div className="guide-callout info">
                <Info size={16} aria-hidden="true" />
                <p>
                  After reviewing recommendations you can <strong>Save a Tailored Copy</strong>
                  &nbsp;of the resume to your kanban board directly from the panel, keeping
                  your master resume untouched.
                </p>
              </div>
            </div>
          </section>

          {/* ── 8. ATS Checker ─────────────────────────────────────────────── */}
          <section id="ats-checker" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <ShieldAlert size={24} aria-hidden="true" className="icon-amber" />
                ATS Checker
              </h2>
              <p className="guide-section-subtitle">
                A structured ATS audit that evaluates six scoring pillars and produces
                prioritized, actionable recommendations. It uses the configured AI provider
                when available and has a deterministic fallback.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Open any resume in <strong>Resume Studio</strong> and click the{' '}
                <strong>ATS Check</strong> button. Optionally enter a target role and field
                to focus the audit.
              </p>

              <div className="guide-ats-stages">
                <h4 className="guide-subsection-heading">The 5 Analysis Stages:</h4>
                <ol className="guide-stage-list">
                  {[
                    'Extracting Plain-Text Search Layer & Identity',
                    'Standardizing Sections Across Locales (EN, FR, DE)',
                    'Auditing Quantifiable Metrics & Action Verbs',
                    'Checking ATS Typography, Hierarchy & Length Norms',
                    'Scoring ATS Pillars & Synthesizing Recommendations',
                  ].map((stage, i) => (
                    <li key={i} className="guide-stage-item">
                      <span className="guide-stage-num">{i + 1}</span>
                      <span>{stage}</span>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="guide-info-grid" style={{ marginTop: '20px' }}>
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Result Categories</h4>
                  <p className="info-card-body">
                    Each finding is classified as <strong>Critical</strong> (blocks ATS
                    parsing), <strong>Warning</strong> (reduces score), <strong>Tip</strong>
                    (best-practice suggestion), or <strong>Pass</strong> (already compliant).
                    Filter by category to focus on highest-impact fixes first.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">What Gets Audited</h4>
                  <p className="info-card-body">
                    Contact info completeness, section heading recognition, quantifiable
                    achievements presence, action verb usage, keyword density, document
                    length, and formatting cleanliness across EN/FR/DE locales.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 9. Extension Install ────────────────────────────────────────── */}
          <section id="extension-install" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Puzzle size={24} aria-hidden="true" className="icon-cyan" />
                Browser Extension — Install &amp; Setup
              </h2>
              <p className="guide-section-subtitle">
                Compust Capture is a developer-mode browser extension that connects directly
                to your local Compust backend — no cloud accounts, no Web Store required.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="guide-callout warn">
                <ShieldAlert size={16} aria-hidden="true" />
                <p>
                  <strong>Local developer-mode install only.</strong> Compust Capture is
                  not published to the Chrome Web Store or Firefox Add-ons. It must be
                  loaded as an unpacked extension — this takes under 60 seconds.
                </p>
              </div>

              <div className="steps-timeline" style={{ marginTop: '20px' }}>
                {[
                  {
                    n: '1',
                    title: 'Navigate to Browser Extension tab',
                    desc: <>Click <strong>Browser Extension</strong> in the top navigation bar. Select your browser (Chrome, Edge, Brave, or Firefox) to see tailored instructions.</>,
                  },
                  {
                    n: '2',
                    title: 'Download & Extract the Extension Package',
                    desc: <>Click the Download ZIP button and extract the archive into a <strong>permanent</strong> folder on your machine (e.g., inside your Documents or Compust directory). Do not move this folder after loading.</>,
                  },
                  {
                    n: '3',
                    title: 'Open Extension Manager & Enable Developer Mode',
                    desc: <>For Chromium-based browsers: navigate to <code>chrome://extensions</code> (or <code>edge://extensions</code>), toggle <strong>Developer Mode</strong> on in the top-right corner.</>,
                  },
                  {
                    n: '4',
                    title: 'Load Unpacked',
                    desc: <>Click <strong>Load unpacked</strong>, then select the extracted folder from Step 2. The Compust Capture extension will appear in your toolbar.</>,
                  },
                  {
                    n: '5',
                    title: 'Log In via the Extension Popup',
                    desc: <>Click the Compust icon in the browser toolbar. Log in with your local Compust account credentials. The popup will confirm connection to your backend and show your active resume.</>,
                  },
                ].map((step) => (
                  <div key={step.n} className="step-card">
                    <div className="step-number-badge">{step.n}</div>
                    <div className="step-body">
                      <div className="step-title">{step.title}</div>
                      <div className="step-desc">{step.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ── 10. Extension Auto-Detected Sites ─────────────────────────── */}
          <section id="extension-sites" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Globe size={24} aria-hidden="true" className="icon-emerald" />
                Auto-Detected Sites
              </h2>
              <p className="guide-section-subtitle">
                These platforms are automatically recognized by the extension's content
                scripts — no manual activation needed when you visit a job listing page.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="guide-sites-grid">
                {[
                  { name: 'LinkedIn', domain: 'linkedin.com', note: 'Job detail pages and search results' },
                  { name: 'Indeed', domain: 'indeed.com', note: 'View job pages, search results with detail pane' },
                  { name: 'Glassdoor', domain: 'glassdoor.com', note: 'Job listing and overview pages' },
                  { name: 'Welcome to the Jungle', domain: 'welcometothejungle.com', note: 'Individual job offer pages' },
                ].map((site) => (
                  <div key={site.name} className="guide-site-card">
                    <div className="guide-site-name">{site.name}</div>
                    <div className="guide-site-domain">{site.domain}</div>
                    <div className="guide-site-note">{site.note}</div>
                  </div>
                ))}
              </div>

              <div className="guide-callout info" style={{ marginTop: '20px' }}>
                <Globe size={16} aria-hidden="true" />
                <p>
                  <strong>Other job boards:</strong> For any site not listed above, visit the
                  job posting, then click the Compust Capture icon in your toolbar to
                  manually trigger capture via the popup's <strong>generic extractor</strong>.
                </p>
              </div>
            </div>
          </section>

          {/* ── 11. Extension Capture Flow ─────────────────────────────────── */}
          <section id="extension-capture-flow" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Zap size={24} aria-hidden="true" className="icon-amber" />
                Capture Flow: Add / Applied / Save / Skip
              </h2>
              <p className="guide-section-subtitle">
                How the extension overlay analyze → action flow works after detecting a job
                listing on an auto-detected site.
              </p>
            </div>

            <div className="guide-architecture-board">
              <GuideDiagram
                definition={EXTENSION_FLOW_DIAGRAM}
                ariaLabel="Extension capture flow: browse site, extension detects job page and overlay appears, quickAddAndAnalyze API call runs, match score and skills shown, user chooses Add (Opportunities), Applied (Kanban), Save (Interested), or Skip."
              />

              <div className="guide-action-pills">
                <h4 className="guide-subsection-heading">The Four Actions Explained:</h4>
                <div className="guide-action-grid">
                  <div className="guide-action-card add">
                    <strong>＋ Add</strong>
                    <p>Saves the job to your Opportunities directory only. No Kanban status assigned — useful when you want to review it later without committing to a status.</p>
                  </div>
                  <div className="guide-action-card applied">
                    <strong>✓ Applied</strong>
                    <p>Saves the job <em>and</em> immediately marks it as <strong>Applied</strong> in your Kanban board. Use when you have already submitted an application.</p>
                  </div>
                  <div className="guide-action-card save">
                    <strong>★ Save</strong>
                    <p>Saves the job <em>and</em> marks it as <strong>Interested / Saved</strong> in your Kanban. Use when you plan to apply but haven't yet.</p>
                  </div>
                  <div className="guide-action-card skip">
                    <strong>✕ Skip</strong>
                    <p>Closes the overlay with <strong>zero database writes</strong> — the job is not saved anywhere. Use when the role isn't a fit.</p>
                  </div>
                </div>
              </div>

              <div className="guide-callout info">
                <Info size={16} aria-hidden="true" />
                <p>
                  The overlay also includes a <strong>Visa &amp; Work Authorization</strong>
                  &nbsp;analysis that flags restriction language (e.g., "US Citizens Only",
                  "Must be authorized to work in…") with the source text quoted as evidence.
                </p>
              </div>
            </div>
          </section>

          {/* ── 12. Opportunities & Job Catalog ────────────────────────────── */}
          <section id="opportunities" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Briefcase size={24} aria-hidden="true" className="icon-cyan" />
                Opportunities &amp; Job Catalog
              </h2>
              <p className="guide-section-subtitle">
                Navigating curated vacancies, country filtering, work modes, and job details.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                The <strong>Opportunities</strong> directory provides a live, curated catalog
                of verified openings from all your configured company targets:
              </p>
              <ul className="guide-feature-list">
                <li><strong>Multi-Country Filtering:</strong> Switch between countries using URL query synchronization (<code>?country_id=...</code>) or view all international openings at once.</li>
                <li><strong>Work Modes:</strong> Filter by Remote, Hybrid, or On-site positions.</li>
                <li><strong>Opportunity Detail Modal:</strong> Inspect full job descriptions, required skills, work authorization info, and instant match analysis with positive/missing factor pills.</li>
                <li><strong>Saved Jobs:</strong> Bookmark vacancies to review later with client-side persistence.</li>
                <li><strong>Tailoring Shortcut:</strong> Click "Tailor Resume" inside the detail modal to pre-load the job directly into Resume Studio's Job Target Panel.</li>
              </ul>
            </div>
          </section>

          {/* ── 13. Internships ────────────────────────────────────────────── */}
          <section id="internships" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <GraduationCap size={24} aria-hidden="true" className="icon-emerald" />
                Internships
              </h2>
              <p className="guide-section-subtitle">
                GitHub-synced curated tech internship listings from top community repositories
                with visa/sponsorship filters and direct application links.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="guide-info-grid">
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Community GitHub Sources</h4>
                  <p className="info-card-body">
                    Internship data is parsed directly from well-maintained community GitHub
                    repositories that track tech internship openings. Click{' '}
                    <strong>Sync with GitHub</strong> to fetch the latest listings.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title purple">Visa &amp; Sponsorship Filter</h4>
                  <p className="info-card-body">
                    Filter by work authorization status: <em>Sponsors Visa</em>,{' '}
                    <em>No Sponsorship</em>, <em>US Citizens Only</em>,{' '}
                    <em>Canada Eligible</em>, or <em>Not Specified</em> — to quickly identify
                    roles you're eligible for.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">Views &amp; Filters</h4>
                  <p className="info-card-body">
                    Switch between Grid and Table views. Filter by repository source, category,
                    and show active-only or all listings including closed ones. Full-text
                    search across company, role, and location fields.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 14. Match Engine ───────────────────────────────────────────── */}
          <section id="matching-engine" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Sparkles size={24} aria-hidden="true" className="icon-cyan" />
                Explainable Match Engine
              </h2>
              <p className="guide-section-subtitle">
                Deterministic, mathematically explainable scoring — no black-box
                hallucination.
              </p>
            </div>

            <div className="guide-notice-card guide-match-card">
              <h3 className="match-card-title">Deterministic 5-Factor Scoring (100% Total)</h3>
              <p className="guide-arch-intro">
                Compust does not generate arbitrary percentages. Match scores are strictly
                computed across five explicit categories:
              </p>
              <div className="guide-match-grid">
                {[
                  { pct: '35%', label: 'Skills Match', color: 'cyan', desc: 'Direct & synonym matching from profile & active resume.' },
                  { pct: '25%', label: 'Experience Duration', color: 'purple', desc: 'Evaluated work history months and title relevance.' },
                  { pct: '15%', label: 'Education Level', color: 'emerald', desc: 'Degree level, field of study, and academic alignment.' },
                  { pct: '15%', label: 'Location & Country', color: 'amber', desc: 'Matches preferred countries or remote availability.' },
                  { pct: '10%', label: 'Languages', color: 'rose', desc: 'Verified multilingual competencies.' },
                ].map((f) => (
                  <div key={f.label} className="guide-match-factor">
                    <div className={`match-pct ${f.color}`}>{f.pct}</div>
                    <div className="match-label">{f.label}</div>
                    <div className="match-desc">{f.desc}</div>
                  </div>
                ))}
              </div>
              <p className="guide-match-note">
                Every match produces human-readable <code>positive_factors</code> and{' '}
                <code>missing_factors</code> pills so candidates know exactly why they scored
                what they scored.
              </p>
            </div>
          </section>

          {/* ── 15. Profile & Candidate Preferences ────────────────────────── */}
          <section id="profile-management" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <UserCheck size={24} aria-hidden="true" className="icon-emerald" />
                Profile &amp; Candidate Preferences
              </h2>
              <p className="guide-section-subtitle">
                Manage your technical competencies, work history, education, and target
                countries.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Your candidate profile feeds directly into the matching engine and application
                tracking:
              </p>
              <ul className="guide-feature-list">
                <li><strong>Skills Catalog:</strong> Add technical competencies. The match engine uses these directly for the Skills (35%) scoring factor.</li>
                <li><strong>Experience History:</strong> Record past roles, dates, and responsibilities. Used for Experience Duration (25%) scoring.</li>
                <li><strong>Education &amp; Languages:</strong> Detail degrees, institutions, and multilingual proficiencies for Education (15%) and Languages (10%) scoring.</li>
                <li><strong>Target Countries:</strong> Select countries you are authorized and willing to work in — feeds the Location & Country (15%) scoring factor.</li>
                <li><strong>Resume Upload:</strong> Upload a PDF resume for deterministic zero-OCR text extraction that populates your structured Resume Studio profile.</li>
              </ul>
            </div>
          </section>

          {/* ── 16. Applications Tracker ───────────────────────────────────── */}
          <section id="applications-tracker" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <FolderKanban size={24} aria-hidden="true" className="icon-purple" />
                Applications Tracker &amp; Kanban
              </h2>
              <p className="guide-section-subtitle">
                Manage your job application lifecycle from Saved to Offer or Terminal status.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                The <strong>My Applications</strong> board organizes your recruitment pipelines
                into fluid Kanban columns:
              </p>
              <div className="guide-status-chips">
                {[
                  'Saved', 'Applied', 'No Answer', '1st Interview',
                  '2nd Interview', '3rd Interview', 'Final Interview',
                  'Offer', 'Accepted', 'Rejected', 'Withdrawn',
                ].map((status) => (
                  <span key={status} className="guide-status-chip">{status}</span>
                ))}
              </div>
              <ul className="guide-feature-list" style={{ marginTop: '16px' }}>
                <li><strong>External Application Tracking:</strong> Click "+ Add Application" to track applications from external sources (LinkedIn, recruiters, direct apply) with custom company names, roles, and notes.</li>
                <li><strong>Recruiter Notes:</strong> Log recruiter name, follow-up dates, and expected salaries per application.</li>
                <li><strong>Extension Integration:</strong> Applications captured via the browser extension with "Applied" or "Save" actions appear here automatically.</li>
              </ul>
            </div>
          </section>

          {/* ── 17. Pipeline Funnel ────────────────────────────────────────── */}
          <section id="pipeline-analytics" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Activity size={24} aria-hidden="true" className="icon-emerald" />
                Application Pipeline &amp; Funnel
              </h2>
              <p className="guide-section-subtitle">
                Visualize interview progression, conversion rates, and outcome drop-offs.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                The built-in <strong>Sankey Pipeline Chart</strong> renders your actual
                interview flows dynamically:
              </p>
              <div className="guide-pipeline-flow">
                <code>
                  Total Applications → 1st Interview → 2nd Interview → Final Interview → Offers → Accepted
                </code>
              </div>
              <p className="guide-arch-note">
                Accurately reveals where applications drop off, identifying whether resume
                optimization, initial screening, or technical interview performance requires
                the most focus.
              </p>
            </div>
          </section>

          {/* ── 18. Scraper Architecture ───────────────────────────────────── */}
          <section id="scraper-architecture" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Activity size={24} aria-hidden="true" className="icon-emerald" />
                Scraper Architecture &amp; Live Data-Flow
              </h2>
              <p className="guide-section-subtitle">
                How Compust crawls, detects, parses, and persists vacancies through the
                7-layer universal fallback system.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="arch-flow-diagram" role="img" aria-label="Compust Scraper Pipeline Architecture Diagram">
                {[
                  { icon: <Globe size={20} aria-hidden="true" />, color: 'blue', title: 'Target Portal', desc: 'Careers URL or ATS Endpoint' },
                  { icon: <ShieldAlert size={20} aria-hidden="true" />, color: 'amber', title: 'Compliance Gate', desc: 'Robots.txt & Polite Delay' },
                  { icon: <Layers size={20} aria-hidden="true" />, color: 'indigo', title: 'Parsing Layers 1–7', desc: 'Adapters + Title Intelligence' },
                  { icon: <Zap size={20} aria-hidden="true" />, color: 'purple', title: 'Browser Fallback', desc: 'Playwright Chromium for SPAs' },
                  { icon: <Database size={20} aria-hidden="true" />, color: 'emerald', title: 'Persistence Engine', desc: 'Deduplication & MySQL Storage' },
                ].map((node, i, arr) => (
                  <React.Fragment key={node.title}>
                    <div className="arch-node">
                      <div className={`arch-node-icon ${node.color}`}>{node.icon}</div>
                      <div className="arch-node-title">{node.title}</div>
                      <div className="arch-node-desc">{node.desc}</div>
                    </div>
                    {i < arr.length - 1 && (
                      <div className="arch-arrow-container">
                        <svg className="guide-flow-arrow" viewBox="0 0 44 24" aria-hidden="true">
                          <path d="M2 12 L36 12 M30 6 L38 12 L30 18" />
                        </svg>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>

              <div style={{ marginTop: '28px' }}>
                <h4 className="guide-subsection-heading">The 7-Layer Universal Fallback System:</h4>
                <div className="guide-info-grid">
                  {[
                    { title: 'Layer 1: ATS Platform Adapters', color: 'cyan', body: 'Auto-detects Ashby, Workable, Greenhouse, Lever, SmartRecruiters, Workday, Teamtailor, Orange, Capgemini, Inwi, and Deloitte.' },
                    { title: 'Layer 2: Direct JSON APIs', color: 'cyan', body: 'Parses structured JSON payloads when targets return direct REST or GraphQL endpoints.' },
                    { title: 'Layer 3: Schema.org JSON-LD', color: 'cyan', body: 'Extracts standardized JobPosting microdata embedded in page markup.' },
                    { title: 'Layer 4: Embedded Next.js State', color: 'cyan', body: 'Inspects __NEXT_DATA__ and window.__initial_state__ scripts for hydrated job data.' },
                    { title: 'Layers 5 & 6: Semantic HTML Cards', color: 'cyan', body: 'Evaluates repeated card classes, grid layouts, and semantic heading cards (h1–h4).' },
                    { title: 'Layer 7: Job Title Intelligence', color: 'emerald', body: 'Context-aware DOM clustering against the local 73,380-title dictionary when prior layers discover 0 jobs.' },
                  ].map((layer) => (
                    <div key={layer.title} className="guide-info-card">
                      <h4 className={`info-card-title ${layer.color}`}>{layer.title}</h4>
                      <p className="info-card-body">{layer.body}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ── 19. Testing a Career Portal ────────────────────────────────── */}
          <section id="testing-career-sites" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Sliders size={24} aria-hidden="true" className="icon-cyan" />
                Testing a Career Portal
              </h2>
              <p className="guide-section-subtitle">
                Dry-run and inspect scraper behavior without writing to the database.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Navigate to <strong>Data Supervision → Scraper Test Diagnostic</strong>. Paste
                any careers URL and click <strong>Run Diagnostic Test</strong> — no database
                writes occur during a test run.
              </p>

              <h4 className="guide-subsection-heading">What to look for in the Diagnostic Report:</h4>
              <div className="guide-info-grid">
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Status &amp; Confidence</h4>
                  <p className="info-card-body"><code>SUCCESS</code> with confidence ≥ 0.70 indicates high-fidelity extraction. Lower scores suggest partial parsing or SPA hydration issues.</p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title purple">Rendering Mode</h4>
                  <p className="info-card-body">Identifies whether static HTML was sufficient or client-side SPA hydration via Playwright was triggered.</p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">Discovery Method</h4>
                  <p className="info-card-body">Reports which strategy (platform adapter, JSON-LD, title intelligence, etc.) succeeded and which layers were attempted.</p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title amber">Diagnostic Errors</h4>
                  <p className="info-card-body">Detailed audit logs explain reasons for rejections, rejected heading candidates, or network timeouts.</p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 20. Diagnosing Results & Failures ──────────────────────────── */}
          <section id="success-vs-failure" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <AlertTriangle size={24} aria-hidden="true" className="icon-amber" />
                Diagnosing Results &amp; Failures
              </h2>
              <p className="guide-section-subtitle">
                Understanding why a scraper returns 0 jobs, 1 job, or restricted responses.
              </p>
            </div>

            <div className="guide-architecture-board">
              <div className="guide-diag-list">
                <div className="guide-diag-card error">
                  <h4>Problem: 0 Jobs Discovered</h4>
                  <p><strong>Cause:</strong> The page might be an unhydrated SPA, behind Cloudflare WAF, or the URL entered is a corporate home page rather than the careers subportal.</p>
                  <p><strong>Solution:</strong> Look for the direct ATS link (e.g. <code>jobs.lever.co/company</code>) in the page network tab or check if the browser fallback option was active during the test.</p>
                </div>
                <div className="guide-diag-card warn">
                  <h4>Problem: Only 1 Job or Partial Openings Found</h4>
                  <p><strong>Cause:</strong> The portal uses dynamic infinite scrolling or client-side cursor pagination that static crawling cannot paginate.</p>
                  <p><strong>Solution:</strong> Check if an unpaginated JSON endpoint or specific country/category filter URL is available.</p>
                </div>
                <div className="guide-diag-card info">
                  <h4>Problem: HTTP 403 Forbidden / Cloudflare Challenge</h4>
                  <p><strong>Cause:</strong> The target server blocks non-browser User-Agent headers or serves a Cloudflare challenge page.</p>
                  <p><strong>Solution:</strong> Compust automatically retries 403s with browser-grade headers and Playwright headless rendering. If the domain enforces strict Turnstile challenges, configure a direct public ATS subdomain.</p>
                </div>
              </div>
            </div>
          </section>

          {/* ── 21. Scraper Diagnostics AI Assistant ───────────────────────── */}
          <section id="scraper-diagnostics-ai" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Sparkles size={24} aria-hidden="true" className="icon-purple" />
                Scraper Diagnostics AI Assistant
              </h2>
              <p className="guide-section-subtitle">
                Ask the AI to explain a scraper diagnostic result in plain language and
                automatically apply suggested URL corrections.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                After running a Scraper Test Diagnostic, an <strong>Explain with AI</strong>
                &nbsp;option becomes available. The AI assistant analyzes the full diagnostic
                telemetry — HTTP status, rendering mode, discovery layers attempted,
                confidence score, and error log — and responds with:
              </p>

              <div className="guide-info-grid">
                <div className="guide-info-card">
                  <h4 className="info-card-title purple">Plain-Language Explanation</h4>
                  <p className="info-card-body">
                    A human-readable summary of why the scraper succeeded or failed, written
                    for non-technical users — e.g., "The site uses a JavaScript-rendered SPA
                    and the Playwright browser fallback was required to discover 12 jobs."
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title cyan">Corrected URL Suggestion</h4>
                  <p className="info-card-body">
                    If the AI identifies that a better URL exists (e.g., a direct ATS
                    subdomain rather than the company's marketing careers page), it suggests a
                    replacement URL with a rationale.
                  </p>
                </div>
                <div className="guide-info-card">
                  <h4 className="info-card-title emerald">Apply Decision</h4>
                  <p className="info-card-body">
                    Click <strong>Apply Correction</strong> to automatically update the scrape
                    target's URL in the database — no manual editing of company records
                    required.
                  </p>
                </div>
              </div>

              <div className="guide-callout info">
                <Info size={16} aria-hidden="true" />
                <p>
                  This feature requires an AI provider to be configured. Navigate to{' '}
                  <strong>AI Settings</strong> in the top navigation to connect your preferred
                  provider (OpenAI, Anthropic, Ollama, or compatible API).
                </p>
              </div>
            </div>
          </section>

          {/* ── 22. Developer & Contributor Guide ──────────────────────────── */}
          <section id="contributor-guide" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <Code2 size={24} aria-hidden="true" className="icon-purple-light" />
                Developer &amp; Contributor Guide
              </h2>
              <p className="guide-section-subtitle">
                How to implement, test, and contribute new portal adapters and scraping
                strategies.
              </p>
            </div>

            <div className="guide-architecture-board">
              <p className="guide-arch-intro">
                Adding support for a new career portal follows Compust's strategy design
                pattern. Each adapter is a small, self-contained class:
              </p>

              <div className="guide-code-box">
                <div className="guide-code-header">
                  <span>src/app/scraper/platforms/my_platform.py</span>
                  <button
                    className="guide-code-copy-btn"
                    onClick={() =>
                      handleCopyCode(
                        'adapter-code',
                        `from bs4 import BeautifulSoup\nfrom ..http_client import FetchedSource\nfrom ..orange_parser import JobCandidate, ParseResult\n\nclass MyPlatformAdapter:\n    name = "my_platform"\n\n    def can_handle(self, source: FetchedSource) -> bool:\n        return "myplatform.com" in source.requested_url.lower()\n\n    def parse(self, source: FetchedSource) -> ParseResult:\n        soup = BeautifulSoup(source.body, "html.parser")\n        jobs: list[JobCandidate] = []\n        for card in soup.select("div.job-listing"):\n            title = card.select_one("h3").get_text(strip=True)\n            link = card.select_one("a")["href"]\n            jobs.append(JobCandidate(title=title, job_url=link))\n        return ParseResult(jobs=jobs, errors=[])`
                      )
                    }
                    aria-label="Copy code"
                  >
                    {copiedCodeId === 'adapter-code' ? (
                      <Check size={14} aria-hidden="true" />
                    ) : (
                      <Copy size={14} aria-hidden="true" />
                    )}
                    <span>
                      {copiedCodeId === 'adapter-code' ? t.guide.copied : t.guide.copyCode}
                    </span>
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
                <h4 className="guide-subsection-heading">Contributor Step Checklist:</h4>
                <ol className="guide-ol">
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

          {/* ── 23. FAQ ────────────────────────────────────────────────────── */}
          <section id="faq" className="guide-section">
            <div className="guide-section-header">
              <h2 className="guide-section-title">
                <HelpCircle size={24} aria-hidden="true" className="icon-cyan" />
                Frequently Asked Questions
              </h2>
              <p className="guide-section-subtitle">
                Instant answers to common questions about Compust, the extension, scraping,
                matching, and setup.
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
                  a: 'Several factors can cause 0 jobs: the page may require client-side JavaScript rendering (handled by our Playwright fallback), Cloudflare WAF bot protection may be active, or the URL entered might be a marketing page rather than the actual job board. Try using the direct ATS URL (e.g. jobs.ashbyhq.com/company). Run the Scraper Test Diagnostic first to get a detailed report.',
                },
                {
                  q: 'How does the browser extension work?',
                  a: 'The Compust Capture extension auto-detects job listing pages on LinkedIn, Indeed, Glassdoor, and Welcome to the Jungle. It extracts the job title, company, description, and location, then calls your local Compust backend to run a match analysis against your active resume. You then choose what to do: Add to Opportunities, mark as Applied, Save as Interested, or Skip (zero database writes).',
                },
                {
                  q: 'What does the ATS Checker actually check?',
                  a: 'The ATS Checker runs five visible analysis stages and scores six ATS pillars: parseability and text extraction, keyword alignment, section standardization, quantified impact and action verbs, formatting and length, and contact or identity detectability. It uses a configured AI provider when available and falls back to deterministic analysis.',
                },
                {
                  q: 'Can I use the Job Target Panel without an AI provider?',
                  a: 'The Job Target Panel (Deep Analysis) and ATS Checker require an AI provider to be configured in AI Settings. The rule-based match engine, resume editing, and export features work offline without any AI configuration.',
                },
                {
                  q: 'How does Compust handle client-rendered SPA websites?',
                  a: 'Compust integrates an automated headless Chromium fallback using Playwright. When static HTTP requests return empty containers (like <div id="root"></div>), Playwright launches in the background, aborts images and fonts for speed, executes the client-side JavaScript, and feeds the hydrated DOM into the 7-layer universal parser.',
                },
                {
                  q: 'How is the match score calculated?',
                  a: 'Matching is 100% deterministic and explainable: Skills (35%), Experience Duration (25%), Education Level (15%), Location & Country Preferences (15%), and Languages (10%). Positive factors and missing factors are displayed in full transparency — no black-box AI scoring.',
                },
                {
                  q: 'Can I track applications for jobs I found outside Compust?',
                  a: 'Yes. In the Applications view, click "+ Add Application" to track external applications with custom company names, roles, recruiter contact information, follow-up dates, and salary notes.',
                },
                {
                  q: 'Can I maintain multiple resumes for different role types?',
                  a: 'Yes. Resume Studio supports an unlimited number of named resume copies. Set one as your default (active) resume — this is what the match engine and browser extension score against. Tailored copies generated by the Job Target Panel are saved separately without overwriting your master.',
                },
                {
                  q: 'How can I contribute a new scraper or parser?',
                  a: 'Implement a custom platform adapter in src/app/scraper/platforms/, register it in registry.py, add a test HTML fixture under tests/fixtures/, run pytest, and submit a Pull Request on GitHub.',
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
                      {isOpen ? (
                        <ChevronUp size={18} aria-hidden="true" />
                      ) : (
                        <ChevronDown size={18} aria-hidden="true" />
                      )}
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

          {/* ── Footer: Open-Source Notice ─────────────────────────────────── */}
          <div className="guide-footer">
            <BookOpen size={18} aria-hidden="true" />
            <p>
              Compust is open-source. The source code, issue tracker, and discussions are
              available on{' '}
              <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">
                GitHub ↗
              </a>
              . For deep technical detail, see{' '}
              <code>COMPUS_DEVELOPER_GUIDE.md</code> in the repository root.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
};
