export interface ChangelogEntry {
  title: string;
  details?: string[];
}

export interface ChangelogGroup {
  type: 'Added' | 'Changed' | 'Fixed' | 'Performance';
  items: ChangelogEntry[];
}

export interface ChangelogRelease {
  version: string;
  date: string;
  isCurrent?: boolean;
  isUnreleased?: boolean;
  groups: ChangelogGroup[];
}

export const GITHUB_RELEASES_URL = 'https://github.com/putbullet/compust/releases';
export const CURRENT_INSTALLED_VERSION = '1.0.4';

export const CHANGELOG_RELEASES: ChangelogRelease[] = [
  {
    version: 'Unreleased',
    date: 'In Development',
    isUnreleased: true,
    groups: [
      {
        type: 'Fixed',
        items: [
          {
            title: 'MySQL Foreign Key Schema Parity',
            details: [
              'Aligned unsigned integer IDs across SQLAlchemy models and migrations, resolving MySQL errno 150.',
              'Eliminated 500 Internal Server Errors on user sign-up and sign-in when connected to MySQL/MariaDB.',
            ],
          },
          {
            title: 'Database Startup Migrations',
            details: [
              'Automated schema migrations at application startup for both MySQL and SQLite.',
              'Fails loudly with actionable diagnostics if migrations cannot be applied.',
            ],
          },
          {
            title: 'HTTP Status Codes on Auth Endpoints',
            details: [
              'Returns 409 Conflict with friendly message on duplicate email registration.',
              'Returns 401 Unauthorized on invalid sign-in credentials.',
              'Returns 503 Service Unavailable when the database is unreachable.',
            ],
          },
          {
            title: 'Opportunities Stat Pills Hover Removal',
            details: [
              'Removed unrequested hover transforms, shadows, and cursor effects on Opportunities stat pills.',
              'Maintained exact approved visual layout and styling.',
            ],
          },
          {
            title: 'Internships Stat Pills Structure & Layout',
            details: [
              'Consolidated stat elements into a shared StatPill component with responsive flex-wrap and gap spacing.',
              'Eliminated text squeeze, border overflow, and poor padding.',
            ],
          },
        ],
      },
      {
        type: 'Changed',
        items: [
          {
            title: 'Navbar AI Panel Instantaneous Loading',
            details: [
              'Panel renders immediately (<150ms) using locally cached provider settings.',
              'Non-blocking background probes update provider status chips progressively.',
              'Short 1.0s timeout for local Ollama daemon and zero cloud network calls for status display.',
            ],
          },
          {
            title: 'Documentation Diagram Viewer',
            details: [
              'Replaced static shrunken diagrams with an interactive, zoomable, and pannable DiagramViewer.',
              'Features Ctrl+wheel zoom, fit-to-width, reset, and portal modal expansion.',
            ],
          },
        ],
      },
    ],
  },
  {
    version: '1.0.4',
    date: '2026-10-23',
    isCurrent: true,
    groups: [
      {
        type: 'Added',
        items: [
          {
            title: 'Functional "Explain with AI" with Safe SVG Diagrams',
            details: [
              'Deep concept breakdowns powered by unified AIGateway (Gemini 3.8 Flash, local Ollama, smart fallback).',
              'Server-side sanitized SVG vector diagrams parsed via ElementTree and sanitized via Bleach.',
              'Multi-stage generation progress indicator and model-keyed database caching.',
              'Interactive Regenerate button bypassing cache.',
            ],
          },
          {
            title: 'Opportunities Stat-Card Pill Redesign',
            details: [
              'Restructured 4 opportunity metrics cards into modern horizontal pill containers.',
              'High-contrast SVG icons and responsive flexbox wrapping across desktop and laptop viewports.',
            ],
          },
        ],
      },
      {
        type: 'Changed',
        items: [
          {
            title: 'Extension Package Updates (v1.0.3)',
            details: [
              'Bumped Chrome and Firefox manifests to 1.0.3.',
              'Packaged Mozilla Add-ons (AMO) source archive with build instructions.',
            ],
          },
        ],
      },
      {
        type: 'Fixed',
        items: [
          {
            title: 'Sync Now Button Spacing & Text Collision',
            details: [
              'Resolved visual collision between Sync Now button and last sync timestamp text.',
              'Enforced flex-row layout with gap: 0.75rem and nowrap behavior.',
            ],
          },
        ],
      },
    ],
  },
  {
    version: '1.0.3',
    date: '2026-10-20',
    groups: [
      {
        type: 'Added',
        items: [
          {
            title: 'Compust Capture Extension v1.0.2',
            details: [
              'Enhanced job extraction heuristics for modern LinkedIn, Indeed, Glassdoor, and WTTJ layouts.',
              'Background token synchronization and instant match score badges.',
            ],
          },
        ],
      },
      {
        type: 'Changed',
        items: [
          {
            title: 'Gemini AI Quota & Rate-Limit Handling',
            details: [
              'Exponential backoff and retry handling for HTTP 429 quota exhaustion.',
              'Optimized prompt token lengths to reduce API usage.',
            ],
          },
        ],
      },
      {
        type: 'Fixed',
        items: [
          {
            title: 'Resume Customization Contrast',
            details: [
              'Resolved low-contrast text on dark backgrounds in Suggest Resume Customization view.',
            ],
          },
          {
            title: 'Modal Stacking Context',
            details: [
              'Fixed z-index layering where schedule settings modals appeared behind main content.',
            ],
          },
        ],
      },
    ],
  },
  {
    version: '1.0.2',
    date: '2026-10-18',
    groups: [
      {
        type: 'Added',
        items: [
          {
            title: 'Windows DPAPI Key Encryption',
            details: [
              'Secure encryption at rest for Google Gemini API keys using Windows CryptProtectData.',
            ],
          },
          {
            title: 'Stepped Gemini Setup Wizard',
            details: [
              'Guided 4-stage configuration wizard with live latency testing and consent verification.',
            ],
          },
          {
            title: 'Guided Data Migration & Portable Backup',
            details: [
              'Auto-discovery of legacy MySQL and development SQLite databases.',
              'One-click portable zip backup and restore preserving data fidelity.',
            ],
          },
          {
            title: 'Hardened Offline Internships Dataset',
            details: [
              'Bundled 4,283 pre-indexed positions (4,021 active) for offline operation.',
            ],
          },
        ],
      },
      {
        type: 'Changed',
        items: [
          {
            title: 'Bootstrap Technical Documentation Redesign',
            details: [
              'Clean 3-column layout, collapsible sidebar, sticky table of contents, and quick search.',
              'Monochrome dark-mode compatible Mermaid architecture diagrams.',
            ],
          },
        ],
      },
      {
        type: 'Fixed',
        items: [
          {
            title: 'Relative API Paths & CORS',
            details: [
              'Converted frontend API calls to relative paths (/api/v1).',
              'Hardened loopback CORS policy for browser extensions.',
            ],
          },
        ],
      },
    ],
  },
  {
    version: '1.0.1',
    date: '2026-10-14',
    groups: [
      {
        type: 'Added',
        items: [
          {
            title: 'Compust Capture Browser Extension',
            details: [
              'Manifest V3 browser extension for LinkedIn, Indeed, Glassdoor, and WTTJ.',
              'Overlay with automatic job analysis and quick actions.',
            ],
          },
          {
            title: 'RenderCV Typst Resume Studio',
            details: [
              'Integrated Typst-based resume compiler with deterministic A4 live preview.',
              '6-pillar ATS audit engine evaluating structure, keywords, and typography.',
            ],
          },
          {
            title: 'Playwright Headless Browser Fallback',
            details: [
              'Headless Chromium rendering fallback for dynamic SPA career portals.',
            ],
          },
          {
            title: 'Job Title Intelligence',
            details: [
              'DOM clustering against local 73,380-title dictionary for fallback job detection.',
            ],
          },
        ],
      },
      {
        type: 'Fixed',
        items: [
          {
            title: 'Application Funnel Progression',
            details: [
              'Fixed application pipeline progression logic in Kanban view.',
              'Prevented ribbon collisions in conversion analytics.',
            ],
          },
        ],
      },
    ],
  },
  {
    version: '1.0.0',
    date: '2026-10-10',
    groups: [
      {
        type: 'Added',
        items: [
          {
            title: 'Initial Standalone Platform Release',
            details: [
              'Windows Inno Setup installer and portable zip package.',
              'Dual-mode database engine (MySQL with automatic SQLite fallback).',
              '7-layer scraper pipeline with adapter auto-detection.',
              'Job directory, 5-stage Kanban application tracker, AI interview prep, and contacts manager.',
            ],
          },
        ],
      },
    ],
  },
];
