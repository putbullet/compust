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
}

export const GUIDE_SECTIONS: GuideSectionMeta[] = [
  { id: 'welcome', title: 'Welcome to Compust', description: 'Overview and high-transparency employment intelligence.' },
  { id: 'important-notice', title: 'Please Read Before Using', badge: 'Critical', description: 'Essential expectations, non-replacement of job boards, and current limitations.' },
  { id: 'demo-video', title: 'See Compust in Action', badge: 'Demo', description: 'Interactive product walkthrough demonstration on Google Drive.' },
  { id: 'how-it-works', title: 'How Compust Works', description: 'Data flow from company source down to matched application.' },
  { id: 'scraper-architecture', title: 'Scraper Architecture & Live Pipeline', description: 'Interactive diagram with animated data-flow arrows and fallback layers.' },
  { id: 'getting-started', title: 'Getting Started: A-to-Z Workflow', description: '20 practical steps from zero to active job opportunities.' },
  { id: 'testing-career-sites', title: 'Testing a Career Portal', description: 'How to diagnose career pages using Data Supervision Scraper Diagnostics.' },
  { id: 'success-vs-failure', title: 'Diagnosing Results & Failures', description: 'What to do on 0 jobs, 1 job, SPA shells, and Cloudflare WAF challenges.' },
  { id: 'contributor-guide', title: 'Developer & Contributor Guide', badge: 'Developers', description: 'How to test, build, and register custom scrapers and platform adapters.' },
  { id: 'opportunities', title: 'Opportunities & Job Catalog', description: 'Catalog navigation, multi-country filtering, and vacancy inspection.' },
  { id: 'matching-engine', title: 'Explainable Match Engine', description: 'Deterministic 5-factor scoring (Skills 35%, Experience 25%, Education 15%, Location 15%, Languages 10%).' },
  { id: 'profile-management', title: 'Profile & Candidate Preferences', description: 'Skills, work experience history, education, and multi-country preferences.' },
  { id: 'resume-builder', title: 'Resume Builder & Tailoring', description: 'Zero-OCR PDF extraction, templates, document export, and vacancy tailoring.' },
  { id: 'applications-tracker', title: 'Applications Tracker & Kanban', description: 'Managing interview stages, follow-up dates, recruiters, and notes.' },
  { id: 'pipeline-analytics', title: 'Application Pipeline & Funnel', description: 'Interactive Sankey diagram of interview progress and terminal conversion states.' },
  { id: 'faq', title: 'Frequently Asked Questions', description: 'Comprehensive FAQ covering database, scraping, matching, and contributing.' },
];
