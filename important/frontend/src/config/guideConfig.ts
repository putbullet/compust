/**
 * Centralized Configuration for Compust Documentation & In-App Guide
 */

export const GITHUB_REPO_URL = 'https://github.com/putbullet/compust';

export const GITHUB_ISSUES_URL = 'https://github.com/putbullet/compust/issues';

export const GITHUB_DISCUSSIONS_URL = 'https://github.com/putbullet/compust/discussions';

/**
 * Google Drive link for full product walkthrough video.
 */
export const GOOGLE_DRIVE_DEMO_URL = 'https://drive.google.com/file/d/1V1UkAwfKErwvKLdZK2VN0cH_suhf8MGZ/view';

/**
 * Public preview image path displaying "Click here to see the demo".
 */
export const DEMO_PREVIEW_IMAGE_PATH = '/DEMO_COMPUST.png';

/**
 * Local public path or external URL for product demo video.
 */
export const DEMO_VIDEO_PATH = GOOGLE_DRIVE_DEMO_URL;

/**
 * Official project donation / support URL.
 * Configured via environment variable VITE_DONATE_URL if set.
 * When empty, the UI displays a graceful community sponsorship dialog.
 */
export const DONATE_URL = import.meta.env.VITE_DONATE_URL || '';

export interface GuideSectionMeta {
  id: string;
  title: string;
  badge?: string;
  description: string;
  group: string;
  /** Terms users may search for when the topic title does not contain them. */
  keywords?: string[];
}

export interface GuideSectionGroup {
  id: string;
  label: string;
}

export const GUIDE_SECTION_GROUPS: GuideSectionGroup[] = [
  { id: 'getting-started', label: 'Getting Started' },
  { id: 'resume-studio', label: 'Resume Studio' },
  { id: 'browser-extension', label: 'Browser Extension' },
  { id: 'job-discovery', label: 'Job Discovery' },
  { id: 'application-tracking', label: 'Application Tracking' },
  { id: 'data-supervision', label: 'Data Supervision & Scraping' },
  { id: 'developer', label: 'Developer Guide' },
  { id: 'help', label: 'Help & FAQ' },
];

export const GUIDE_SECTIONS: GuideSectionMeta[] = [
  // ── Getting Started ──────────────────────────────────────────────────────────
  {
    id: 'welcome',
    title: 'Welcome to Compust',
    description: 'Overview and high-transparency employment intelligence.',
    group: 'getting-started',
    keywords: ['overview', 'platform', 'career intelligence', 'local first'],
  },
  {
    id: 'important-notice',
    title: 'Please Read Before Using',
    badge: 'Critical',
    description: 'Essential expectations, non-replacement of job boards, and current limitations.',
    group: 'getting-started',
    keywords: ['limitations', 'cloudflare', 'robots', 'missing jobs'],
  },
  {
    id: 'demo-video',
    title: 'See Compust in Action',
    badge: 'Demo',
    description: 'Interactive product walkthrough demonstration on Google Drive.',
    group: 'getting-started',
    keywords: ['video', 'walkthrough', 'demo'],
  },
  {
    id: 'how-it-works',
    title: 'How Compust Works',
    description: 'System overview: data flow from company source to matched application.',
    group: 'getting-started',
    keywords: ['architecture', 'data flow', 'database', 'scraper', 'matching'],
  },
  {
    id: 'getting-started',
    title: 'A-to-Z Setup Workflow',
    description: 'Step-by-step from first-time setup to active job tracking.',
    group: 'getting-started',
    keywords: ['setup', 'profile', 'resume', 'company', 'sync'],
  },

  // ── Resume Studio ─────────────────────────────────────────────────────────────
  {
    id: 'resume-studio',
    title: 'Resume Studio Overview',
    description: 'RenderCV-style A4 resume builder, multi-template, PDF/DOCX export.',
    group: 'resume-studio',
    keywords: ['resume', 'CV', 'A4', 'pagination', 'RenderCV', 'PDF', 'DOCX'],
  },
  {
    id: 'deep-analysis',
    title: 'Job Targeting & Deep Analysis',
    description: 'Match score, tailored suggestions, outreach email, cover letter, and interview prep.',
    group: 'resume-studio',
    keywords: ['job target', 'tailor', 'deep analysis', 'cover letter', 'email'],
  },
  {
    id: 'ats-checker',
    title: 'ATS Checker',
    badge: 'AI',
    description: 'Six-pillar ATS audit with actionable recommendations and deterministic fallback.',
    group: 'resume-studio',
    keywords: ['ATS', 'parseability', 'keywords', 'formatting', 'audit'],
  },

  // ── Browser Extension ─────────────────────────────────────────────────────────
  {
    id: 'extension-install',
    title: 'Install & Setup',
    description: 'Download, extract, and load the Compust Capture extension in your browser.',
    group: 'browser-extension',
    keywords: ['Chrome', 'Firefox', 'Edge', 'install', 'manual activation'],
  },
  {
    id: 'extension-sites',
    title: 'Auto-Detected Sites',
    description: 'LinkedIn, Indeed, Glassdoor, and Welcome to the Jungle — auto-captured on page load.',
    group: 'browser-extension',
    keywords: ['LinkedIn', 'Indeed', 'Glassdoor', 'Welcome to the Jungle', 'automatic'],
  },
  {
    id: 'extension-capture-flow',
    title: 'Capture Flow: Add / Applied / Save / Skip',
    description: 'How the overlay analyze → action flow works after the extension detects a job.',
    group: 'browser-extension',
    keywords: ['analyze', 'Add', 'Applied', 'Save', 'Interested', 'Skip', 'untracked'],
  },

  // ── Job Discovery ─────────────────────────────────────────────────────────────
  {
    id: 'opportunities',
    title: 'Opportunities & Job Catalog',
    description: 'Catalog navigation, multi-country filtering, work modes, and vacancy inspection.',
    group: 'job-discovery',
    keywords: ['jobs', 'country', 'remote', 'hybrid', 'onsite'],
  },
  {
    id: 'internships',
    title: 'Internships',
    description: 'GitHub-synced curated tech internship listings with visa/sponsorship filters.',
    group: 'job-discovery',
    keywords: ['internship', 'GitHub', 'visa', 'sponsorship', 'curated'],
  },
  {
    id: 'matching-engine',
    title: 'Explainable Match Engine',
    description: 'Deterministic 5-factor scoring: Skills 35%, Experience 25%, Education 15%, Location 15%, Languages 10%.',
    group: 'job-discovery',
    keywords: ['score', 'skills', 'experience', 'education', 'location', 'languages'],
  },

  // ── Application Tracking ──────────────────────────────────────────────────────
  {
    id: 'profile-management',
    title: 'Profile & Candidate Preferences',
    description: 'Skills, work experience, education, and multi-country preferences.',
    group: 'application-tracking',
    keywords: ['profile', 'preferences', 'education', 'experience', 'languages'],
  },
  {
    id: 'applications-tracker',
    title: 'Applications Tracker & Kanban',
    description: 'Managing interview stages, follow-up dates, recruiters, and notes.',
    group: 'application-tracking',
    keywords: ['kanban', 'applications', 'interviews', 'follow-up', 'recruiter'],
  },
  {
    id: 'pipeline-analytics',
    title: 'Application Pipeline & Funnel',
    description: 'Interactive Sankey diagram of interview progress and terminal conversion states.',
    group: 'application-tracking',
    keywords: ['funnel', 'analytics', 'Sankey', 'pipeline'],
  },

  // ── Data Supervision & Scraping ───────────────────────────────────────────────
  {
    id: 'scraper-architecture',
    title: 'Scraper Architecture & Pipeline',
    description: 'Animated data-flow diagram of the 7-layer fallback scraping system.',
    group: 'data-supervision',
    keywords: ['scraper', 'parser', 'fallback', 'JSON-LD', 'Playwright'],
  },
  {
    id: 'testing-career-sites',
    title: 'Testing a Career Portal',
    description: 'How to diagnose career pages using the Scraper Test Diagnostic tool.',
    group: 'data-supervision',
    keywords: ['diagnostic', 'dry run', 'confidence', 'rendering'],
  },
  {
    id: 'success-vs-failure',
    title: 'Diagnosing Results & Failures',
    description: 'What to do with 0 jobs, 1 job, SPA shells, and Cloudflare WAF challenges.',
    group: 'data-supervision',
    keywords: ['errors', 'zero jobs', '403', 'WAF', 'SPA'],
  },
  {
    id: 'scraper-diagnostics-ai',
    title: 'Scraper Diagnostics AI Assistant',
    badge: 'AI',
    description: 'Ask the AI to explain scraper results and apply suggested URL corrections.',
    group: 'data-supervision',
    keywords: ['AI', 'explain', 'correct URL', 'apply correction'],
  },

  // ── Developer Guide ───────────────────────────────────────────────────────────
  {
    id: 'contributor-guide',
    title: 'Developer & Contributor Guide',
    badge: 'Developers',
    description: 'How to test, build, and register custom scrapers and platform adapters.',
    group: 'developer',
  },

  // ── Help & FAQ ────────────────────────────────────────────────────────────────
  {
    id: 'faq',
    title: 'Frequently Asked Questions',
    description: 'Comprehensive FAQ covering scraping, matching, the extension, and contributing.',
    group: 'help',
  },
];
