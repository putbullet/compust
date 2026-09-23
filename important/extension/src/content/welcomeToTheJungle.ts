import {
  BaseJobExtractor,
  ExtractorConfig,
  validateJobPayload,
  extractJsonLd,
} from './common/jobExtractor';
import { CompustOverlay } from './common/overlay';
import { browserAPI } from '../lib/browserPolyfill';

export const welcomeToTheJungleConfig: ExtractorConfig = {
  siteName: 'Welcome to the Jungle',
  sourceIdentifier: 'extension:welcometothejungle',
  urlPatterns: [
    'welcometothejungle.com',
  ],
  detailDomSelectors: [
    '[data-testid="job-page-content"]',
    '[data-testid="job-section-description"]',
    'h1[data-testid="job-header-title"]',
    'h1[data-testid="job-title"]',
    '#job-details',
    'main h1',
  ],
  titleSelectors: [
    'h1[data-testid="job-header-title"]',
    'h1[data-testid="job-title"]',
    'header h1',
    'main h1',
    'h1',
  ],
  companySelectors: [
    '[data-testid="job-company-name"]',
    'a[href*="/companies/"] h4',
    'a[href*="/companies/"] span',
    'a[href*="/companies/"]',
    'header a[href*="/companies/"]',
  ],
  locationSelectors: [
    '[data-testid="job-location"]',
    'i[name="location"] + span',
    '[data-testid="job-header-location"]',
    'span[class*="location"]',
  ],
  descriptionSelectors: [
    '[data-testid="job-section-description"]',
    '#job-details',
    '[data-testid="job-description"]',
    'section[class*="description"]',
  ],
  employmentSelectors: [
    '[data-testid="job-contract-type"]',
    '[data-testid="job-summary"]',
  ],
};

export class WelcomeToTheJungleExtractor extends BaseJobExtractor {
  constructor() {
    super(welcomeToTheJungleConfig);
  }

  /**
   * Strictly target actual job postings (e.g. /companies/<company>/jobs/<slug>).
   * Directory listing pages (e.g. /en/companies, /en/jobs) are deliberately excluded.
   */
  override canHandle(url: string, doc?: Document): boolean {
    const isJobPostingUrl =
      url.includes('welcometothejungle.com') &&
      url.includes('/companies/') &&
      url.includes('/jobs/') &&
      !url.endsWith('/companies') &&
      !url.endsWith('/companies/') &&
      !url.endsWith('/jobs') &&
      !url.endsWith('/jobs/');

    if (!isJobPostingUrl) {
      return false;
    }

    if (doc) {
      const hasJsonLd = Boolean(extractJsonLd(doc));
      const hasDetailDom = Boolean(
        doc.querySelector(
          '[data-testid="job-page-content"], [data-testid="job-section-description"], h1[data-testid="job-header-title"], h1[data-testid="job-title"], #job-details, main h1'
        )
      );
      return hasJsonLd || hasDetailDom;
    }

    return true;
  }
}

export function getWTTJJobSlug(urlStr: string): string | null {
  try {
    const urlObj = new URL(urlStr, 'https://www.welcometothejungle.com');
    const match = urlObj.pathname.match(/\/companies\/[^/]+\/jobs\/([^/?#]+)/);
    if (match) return match[1];
  } catch {
    const m = urlStr.match(/\/companies\/[^/]+\/jobs\/([^/?#]+)/);
    if (m) return m[1];
  }
  return null;
}

export const welcomeToTheJungleExtractor = new WelcomeToTheJungleExtractor();

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  console.log('[Compust WTTJ] Content script active at:', window.location.href);
  let overlay: CompustOverlay | null = null;
  let activeJobSlug: string | null = getWTTJJobSlug(window.location.href);

  const initOverlayIfMatching = () => {
    const currentUrl = window.location.href;
    const canHandleUrl = welcomeToTheJungleExtractor.canHandle(currentUrl);
    if (!canHandleUrl) return;

    const newJobSlug = getWTTJJobSlug(currentUrl);

    // If job changed in Single Page App view, reset overlay state to avoid stale job captures
    if (overlay && newJobSlug && newJobSlug !== activeJobSlug) {
      console.log(`[Compust WTTJ] Job selection changed (${activeJobSlug} -> ${newJobSlug}). Resetting overlay.`);
      activeJobSlug = newJobSlug;
      overlay.bumpGeneration();
      overlay.hidePanel();
      overlay.renderButton();
    } else if (!activeJobSlug && newJobSlug) {
      activeJobSlug = newJobSlug;
    }

    // Create overlay eagerly on URL match — don't wait for detail pane DOM to render.
    // onCapture() reads the DOM fresh at click time so there is no stale-data risk.
    if (!overlay) {
      console.log('[Compust WTTJ] Initializing overlay on page (URL match, eager creation)');
      overlay = new CompustOverlay({
        onCapture: async () => {
          if (!overlay) return;
          const currentGen = overlay.getGeneration();
          overlay.showLoading(currentGen);
          const payload = welcomeToTheJungleExtractor.extract(document);
          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust WTTJ] Discarding stale extraction: user navigated away during DOM extraction');
            return;
          }
          const validation = validateJobPayload(payload);
          if (!validation.isValid) {
            overlay.showError(validation.missingError!, false, false, currentGen);
            return;
          }

          try {
            const res = await browserAPI.runtime.sendMessage({
              type: 'ANALYZE_EPHEMERAL_JOB',
              payload: payload!,
            });

            if (!overlay.isCurrentGeneration(currentGen)) {
              console.log('[Compust WTTJ] Discarding stale response: user navigated away during API call');
              return;
            }

            if (!res.ok) {
              overlay.showError(
                res.message || res.error || 'Failed to analyze job',
                res.error === 'NOT_LOGGED_IN',
                res.isNetworkError,
                currentGen
              );
              return;
            }

            overlay.showEphemeralResult(res.data, payload!, currentGen);
          } catch (err: any) {
            if (overlay.isCurrentGeneration(currentGen)) {
              overlay.showError(err, false, true, currentGen);
            }
          }
        },
        onSaveAction: async (payload, status, suggestions) => {
          const res = await browserAPI.runtime.sendMessage({
            type: 'SAVE_JOB_ACTION',
            payload,
            applicationStatus: status,
            resumeSuggestions: suggestions,
          });
          if (!res.ok) {
            throw new Error(res.message || res.error || 'Failed to save job');
          }
          return res.data;
        },
        onRetry: () => {
          overlay?.renderButton();
          overlay?.hidePanel();
        },
      });
    }
  };

  browserAPI.runtime.onMessage.addListener((message: any, _sender: any, sendResponse: any) => {
    if (message.type === 'TOGGLE_CAPTURE_PANEL') {
      if (overlay) {
        overlay.toggle();
      } else {
        initOverlayIfMatching();
        overlay?.toggle();
      }
      sendResponse({ ok: true });
    }
    return true;
  });

  // Intercept history.pushState and replaceState to catch SPA routing immediately
  const patchHistoryMethod = (method: 'pushState' | 'replaceState') => {
    const original = history[method];
    history[method] = function (...args) {
      const result = original.apply(this, args);
      window.dispatchEvent(new Event('compust:locationchange'));
      return result;
    };
  };
  patchHistoryMethod('pushState');
  patchHistoryMethod('replaceState');

  initOverlayIfMatching();
  window.addEventListener('popstate', initOverlayIfMatching);
  window.addEventListener('compust:locationchange', initOverlayIfMatching);

  // Poll fallback for URL changes (DOM check removed — overlay created eagerly on URL match)
  let lastUrl = window.location.href;
  const urlCheckTimer = setInterval(() => {
    if (window.location.href !== lastUrl || !overlay) {
      lastUrl = window.location.href;
      initOverlayIfMatching();
    }
  }, 500);

  // MutationObserver on body to detect: (a) detail pane swaps for job-switch tracking,
  // (b) SPA body replacement that removes the overlay element.
  let debounceTimeout: any = null;
  const detailObserver = new MutationObserver(() => {
    const currentSlug = getWTTJJobSlug(window.location.href);
    if (!overlay || (currentSlug && currentSlug !== activeJobSlug)) {
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        initOverlayIfMatching();
      }, 200);
    }
  });

  if (document.body) {
    detailObserver.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      if (document.body) {
        detailObserver.observe(document.body, { childList: true, subtree: true });
      }
      initOverlayIfMatching();
    });
  }

  window.addEventListener('unload', () => {
    clearInterval(urlCheckTimer);
    if (debounceTimeout) clearTimeout(debounceTimeout);
    detailObserver.disconnect();
  }, { once: true });
}
