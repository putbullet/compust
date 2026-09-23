import {
  JobExtractor,
  cleanText,
  cleanEmployerName,
  getCleanHtml,
  extractJsonLd,
  getCanonicalUrl,
  validateJobPayload,
} from './common/jobExtractor';
import { CompustOverlay } from './common/overlay';
import { JobPayload } from '../lib/types';
import { browserAPI } from '../lib/browserPolyfill';

/**
 * Extract Job ID from either a direct URL (/jobs/view/<id>/)
 * or a split-pane search URL (?currentJobId=<id>).
 */
export function getLinkedInJobId(urlStr: string): string | null {
  try {
    const urlObj = new URL(urlStr, 'https://www.linkedin.com');
    const paramId = urlObj.searchParams.get('currentJobId');
    if (paramId) return paramId;

    const match = urlObj.pathname.match(/\/jobs\/view\/(\d+)/);
    if (match) return match[1];
  } catch {
    const m = urlStr.match(/currentJobId=(\d+)/) || urlStr.match(/\/jobs\/view\/(\d+)/);
    if (m) return m[1];
  }
  return null;
}

export class LinkedInExtractor implements JobExtractor {
  siteName = 'LinkedIn';

  canHandle(url: string, doc?: Document): boolean {
    const isMatchingUrl =
      url.includes('linkedin.com/jobs/view') ||
      url.includes('linkedin.com/jobs/collections') ||
      url.includes('linkedin.com/jobs/search') ||
      url.includes('linkedin.com/jobs/search-results') ||
      url.includes('linkedin.com/jobs');

    if (!isMatchingUrl) {
      return false;
    }

    // (a) ID present in path (/jobs/view/<id>/) or (b) currentJobId in query params on ANY path
    const jobIdFromUrl = getLinkedInJobId(url);
    if (jobIdFromUrl) {
      return true;
    }

    // When document is provided and URL alone doesn't have an ID, check if job-detail DOM is rendered
    if (doc) {
      const docJobId = doc.querySelector('[data-job-id]')?.getAttribute('data-job-id');
      if (docJobId) return true;

      const hasJsonLd = Boolean(extractJsonLd(doc));
      const hasJobDetailDom = Boolean(
        doc.querySelector(
          'section.two-pane-serp-page__detail-view, .details-pane, .jobs-search__job-details, .jobs-search-results-list__detail-pane, #job-details, .jobs-details__main-content, .job-details-jobs-unified-top-card, .jobs-unified-top-card, .jobs-description__content, h1.top-card-layout__title, .topcard__title, .top-card-layout'
        )
      );
      return hasJsonLd || hasJobDetailDom;
    }

    return false;
  }

  extractFromApiResponse(htmlText: string, targetUrl: string, parsedDoc?: Document): JobPayload | null {
    if (!htmlText && !parsedDoc) return null;
    let apiDoc: Document | null = parsedDoc || null;
    if (!apiDoc && typeof DOMParser !== 'undefined') {
      apiDoc = new DOMParser().parseFromString(htmlText, 'text/html');
    }
    if (!apiDoc) return null;

    // 1. Try JSON-LD if present in the response
    const jsonLd = extractJsonLd(apiDoc);
    if (jsonLd) {
      const title = cleanText(jsonLd.title);
      const company = cleanEmployerName(jsonLd.hiringOrganization?.name);
      const description = jsonLd.description ? cleanText(jsonLd.description) : null;
      if (title && company && description) {
        return {
          title,
          company,
          location: cleanText(jsonLd.jobLocation?.address?.addressLocality || jsonLd.jobLocation?.address?.addressRegion),
          description,
          employment_type: cleanText(jsonLd.employmentType),
          remote_type: jsonLd.jobLocationType === 'TELECOMMUTE' ? 'Remote' : null,
          url: targetUrl,
          source: 'extension:linkedin',
        };
      }
    }

    // 2. Structured HTML tags returned by LinkedIn guest jobPosting endpoint
    // Title
    const titleEl =
      apiDoc.querySelector('.topcard__title') ||
      apiDoc.querySelector('.top-card-layout__title') ||
      apiDoc.querySelector('h2') ||
      apiDoc.querySelector('h1');
    const title = cleanText(titleEl?.textContent);

    // Company
    const companyEl =
      apiDoc.querySelector('.topcard__org-name-link') ||
      apiDoc.querySelector('.topcard__flavor--black-link') ||
      apiDoc.querySelector('.topcard__flavor') ||
      apiDoc.querySelector('.top-card-layout__first-subline a');
    const company = cleanEmployerName(companyEl?.textContent);

    // Location
    const locationEl =
      apiDoc.querySelector('.topcard__flavor--bullet') ||
      apiDoc.querySelector('.top-card-layout__first-subline .topcard__flavor:not(.topcard__org-name-link)') ||
      apiDoc.querySelector('.top-card-layout__first-subline span');
    const location = cleanText(locationEl?.textContent);

    // Description
    const descEl =
      apiDoc.querySelector('.show-more-less-html__markup') ||
      apiDoc.querySelector('#job-details') ||
      apiDoc.querySelector('.description__text');
    const description = getCleanHtml(descEl);

    // Criteria (Employment type, seniority)
    let employment_type: string | null = null;
    const criteriaItems = apiDoc.querySelectorAll('.description__job-criteria-item');
    for (const item of Array.from(criteriaItems)) {
      const subheader = item.querySelector('.description__job-criteria-subheader')?.textContent || '';
      if (subheader.toLowerCase().includes('employment type')) {
        const val = item.querySelector('.description__job-criteria-text')?.textContent;
        employment_type = cleanText(val);
        break;
      }
    }

    if (!title && !company && !description) {
      return null;
    }

    return {
      title,
      company,
      location,
      description,
      employment_type,
      remote_type: location?.toLowerCase().includes('remote') ? 'Remote' : null,
      url: targetUrl,
      source: 'extension:linkedin',
    };
  }

  async extractAsync(doc: Document = document): Promise<JobPayload | null> {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const url = getCanonicalUrl(doc, fallbackUrl);
    const jobId = getLinkedInJobId(fallbackUrl) || getLinkedInJobId(url) || doc.querySelector('[data-job-id]')?.getAttribute('data-job-id');

    if (jobId) {
      try {
        console.log(`[Compust LinkedIn] Fetching structured job via JobSpy endpoint for job ID: ${jobId}`);
        const apiUrl = `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/${jobId}`;
        const res = await fetch(apiUrl, {
          headers: {
            'Accept': 'text/html,application/xhtml+xml',
          },
          credentials: 'same-origin',
        });
        if (res.ok) {
          const html = await res.text();
          const apiPayload = this.extractFromApiResponse(html, url);
          if (apiPayload && apiPayload.title && apiPayload.company && apiPayload.description) {
            console.log('[Compust LinkedIn] Successfully extracted job via API endpoint');
            return apiPayload;
          }
        } else {
          console.warn(`[Compust LinkedIn] API endpoint returned status ${res.status}, falling back to DOM.`);
        }
      } catch (err) {
        console.warn('[Compust LinkedIn] API endpoint fetch failed, falling back to DOM:', err);
      }
    }

    // Fallback path: JSON-LD and DOM selectors
    return this.extract(doc);
  }

  extract(doc: Document = document): JobPayload | null {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const url = getCanonicalUrl(doc, fallbackUrl);

    // 1. Target the right-hand job detail pane specifically if present (split-pane search/collections view)
    const detailPane =
      doc.querySelector('section.two-pane-serp-page__detail-view') ||
      doc.querySelector('.details-pane') ||
      doc.querySelector('.jobs-search__job-details') ||
      doc.querySelector('.jobs-search-results-list__detail-pane') ||
      doc.querySelector('.jobs-details__main-content') ||
      doc.querySelector('.job-view-layout') ||
      doc.querySelector('.top-card-layout') ||
      doc;

    // 2. Try JSON-LD structured data first (most stable against DOM updates)
    const jsonLd = extractJsonLd(doc);
    if (jsonLd) {
      return {
        title: cleanText(jsonLd.title),
        company: cleanEmployerName(jsonLd.hiringOrganization?.name),
        location: cleanText(jsonLd.jobLocation?.address?.addressLocality || jsonLd.jobLocation?.address?.addressRegion),
        description: jsonLd.description ? cleanText(jsonLd.description) : null,
        employment_type: cleanText(jsonLd.employmentType),
        remote_type: jsonLd.jobLocationType === 'TELECOMMUTE' ? 'Remote' : null,
        url,
        source: 'extension:linkedin',
      };
    }

    // 3. DOM extraction strictly scoped within the detail pane so search result list cards are not picked
    const titleEl =
      detailPane.querySelector('.job-details-jobs-unified-top-card__job-title') ||
      detailPane.querySelector('h2.job-details-jobs-unified-top-card__job-title') ||
      detailPane.querySelector('.jobs-search__job-details h2') ||
      detailPane.querySelector('.jobs-search__job-details h1') ||
      detailPane.querySelector('.jobs-unified-top-card__job-title') ||
      detailPane.querySelector('h1.top-card-layout__title') ||
      detailPane.querySelector('a.topcard__link h2') ||
      detailPane.querySelector('h2.topcard__title') ||
      detailPane.querySelector('.topcard__title') ||
      detailPane.querySelector('h1');
    const title = cleanText(titleEl?.textContent);

    const companyEl =
      detailPane.querySelector('.job-details-jobs-unified-top-card__company-name') ||
      detailPane.querySelector('.jobs-unified-top-card__company-name') ||
      detailPane.querySelector('.topcard__org-name-link') ||
      detailPane.querySelector('.topcard__flavor--black-link') ||
      detailPane.querySelector('.jobs-unified-top-card__subtitle-primary-grouping a') ||
      detailPane.querySelector('a.job-details-jobs-unified-top-card__company-name-link') ||
      detailPane.querySelector('a[href*="/company/"]');
    const company = cleanEmployerName(companyEl?.textContent);

    const locationEl =
      detailPane.querySelector('.job-details-jobs-unified-top-card__primary-description-container .tvm__text') ||
      detailPane.querySelector('.topcard__flavor-row .topcard__flavor') ||
      detailPane.querySelector('.job-details-jobs-unified-top-card__bullet') ||
      detailPane.querySelector('.jobs-unified-top-card__bullet') ||
      detailPane.querySelector('.topcard__flavor--bullet') ||
      detailPane.querySelector('.jobs-unified-top-card__primary-description span') ||
      detailPane.querySelector('.jobs-search__job-details .jobs-unified-top-card__primary-description');
    const location = cleanText(locationEl?.textContent);

    const descEl =
      detailPane.querySelector('.show-more-less-html__markup') ||
      detailPane.querySelector('#job-details') ||
      detailPane.querySelector('.jobs-description__content') ||
      detailPane.querySelector('.jobs-description-content__text') ||
      detailPane.querySelector('.description__text') ||
      detailPane.querySelector('article.jobs-description__container') ||
      detailPane.querySelector('.jobs-box__html-content') ||
      detailPane.querySelector('.jobs-description');
    const description = getCleanHtml(descEl);

    const employmentEl =
      detailPane.querySelector('.job-details-jobs-unified-top-card__job-insight') ||
      detailPane.querySelector('.jobs-unified-top-card__job-insight') ||
      detailPane.querySelector('li.jobs-unified-top-card__job-insight') ||
      detailPane.querySelector('.topcard__flavor-row');
    const employment_type = cleanText(employmentEl?.textContent);

    return {
      title,
      company,
      location,
      description,
      employment_type,
      remote_type: location?.toLowerCase().includes('remote') ? 'Remote' : null,
      url,
      source: 'extension:linkedin',
    };
  }
}

export const linkedInExtractor = new LinkedInExtractor();

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  console.log('[Compust LinkedIn] Content script active at:', window.location.href);
  let overlay: CompustOverlay | null = null;
  let activeJobId: string | null = getLinkedInJobId(window.location.href);

  const initOrUpdateOverlay = () => {
    const currentUrl = window.location.href;
    const canHandleUrl = linkedInExtractor.canHandle(currentUrl);
    if (!canHandleUrl) return;

    const newJobId = getLinkedInJobId(currentUrl);

    console.log('[Compust LinkedIn] URL check:', currentUrl, 'JobId:', newJobId);

    // If job changed in Single Page App split-pane view, reset overlay state to avoid stale job captures
    if (overlay && newJobId && newJobId !== activeJobId) {
      console.log(`[Compust LinkedIn] Job selection changed (${activeJobId} -> ${newJobId}). Resetting overlay.`);
      activeJobId = newJobId;
      overlay.bumpGeneration();
      overlay.hidePanel();
      overlay.renderButton();
    } else if (!activeJobId && newJobId) {
      activeJobId = newJobId;
    }

    // Create overlay eagerly on URL match — don't wait for detail pane DOM to render.
    // onCapture() reads the DOM fresh at click time so there is no stale-data risk.
    if (!overlay) {
      console.log('[Compust LinkedIn] Initializing overlay on page (URL match, eager creation)');
      overlay = new CompustOverlay({
        onCapture: async () => {
          if (!overlay) return;
          const currentGen = overlay.getGeneration();
          overlay.showLoading(currentGen);
          const payload = (await linkedInExtractor.extractAsync?.(document)) || linkedInExtractor.extract(document);
          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust LinkedIn] Discarding stale extraction: user navigated away during DOM extraction');
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
              console.log('[Compust LinkedIn] Discarding stale response: user navigated away during API call');
              return;
            }

            if (!res.ok) {
              overlay.showError(res.message || res.error || 'Failed to analyze job', res.error === 'NOT_LOGGED_IN', res.isNetworkError, currentGen);
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

  // Toggle message listener for manual activation
  browserAPI.runtime.onMessage.addListener((message: any, _sender: any, sendResponse: any) => {
    if (message.type === 'TOGGLE_CAPTURE_PANEL') {
      if (overlay) {
        overlay.toggle();
      } else {
        initOrUpdateOverlay();
        overlay?.toggle();
      }
      sendResponse({ ok: true });
    }
    return true;
  });

  // Immediate check on load
  initOrUpdateOverlay();

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

  window.addEventListener('popstate', initOrUpdateOverlay);
  window.addEventListener('compust:locationchange', initOrUpdateOverlay);

  // Poll fallback for URL changes (DOM check removed — overlay created eagerly on URL match)
  let lastUrl = window.location.href;
  const urlCheckTimer = setInterval(() => {
    if (window.location.href !== lastUrl || !overlay) {
      lastUrl = window.location.href;
      initOrUpdateOverlay();
    }
  }, 500);

  // MutationObserver on body to detect: (a) detail pane swaps for job-switch tracking,
  // (b) SPA body replacement that removes the overlay element.
  let debounceTimeout: any = null;
  const detailObserver = new MutationObserver(() => {
    const currentId = getLinkedInJobId(window.location.href);
    // Re-init if overlay is gone OR if job changed (always call to track activeJobId changes)
    if (!overlay || (currentId && currentId !== activeJobId)) {
      if (debounceTimeout) clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        initOrUpdateOverlay();
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
      initOrUpdateOverlay();
    });
  }

  window.addEventListener('unload', () => {
    clearInterval(urlCheckTimer);
    if (debounceTimeout) clearTimeout(debounceTimeout);
    detailObserver.disconnect();
  }, { once: true });
}
