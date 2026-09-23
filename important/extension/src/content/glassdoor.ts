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
 * Helper to programmatically expand collapsed job description on Glassdoor.
 * Unblurs the CSS and ensures any collapsed content is expanded.
 */
export function expandDescriptionIfCollapsed(doc: Document = document): boolean {
  try {
    const showMoreBtn =
      (doc.querySelector(
        'button[class*="ShowMore"], button[class*="showMore"], [class*="ShowMoreCTA"] button, [data-test="showMoreButton"], button[class*="showMoreButton"]'
      ) as HTMLButtonElement | null) ||
      (Array.from(doc.querySelectorAll('button')).find((b) => {
        const text = b.textContent?.trim().toLowerCase() || '';
        return (
          text.includes('show more') ||
          text.includes('discover more') ||
          text.includes('read more') ||
          text.includes('voir plus')
        );
      }) as HTMLButtonElement | null);

    if (showMoreBtn && typeof showMoreBtn.click === 'function') {
      showMoreBtn.click();
      return true;
    }
  } catch (e) {
    // Non-fatal if click is blocked by security context
  }
  return false;
}

/**
 * Wait for an element to appear in the DOM within a bounded timeout.
 */
export function waitForElement(
  predicate: (doc: Document) => Element | null,
  doc: Document = document,
  timeoutMs: number = 3000
): Promise<Element | null> {
  return new Promise((resolve) => {
    const immediate = predicate(doc);
    if (immediate) {
      resolve(immediate);
      return;
    }

    const observer = new MutationObserver(() => {
      const el = predicate(doc);
      if (el) {
        observer.disconnect();
        clearTimeout(timer);
        resolve(el);
      }
    });

    const timer = setTimeout(() => {
      observer.disconnect();
      resolve(predicate(doc));
    }, timeoutMs);

    observer.observe(doc.body || doc.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
    });
  });
}

/**
 * Extract Glassdoor Job Listing ID from URL or active job card.
 */
export function getGlassdoorJobId(urlStr: string, doc?: Document): string | null {
  try {
    const urlObj = new URL(urlStr, 'https://www.glassdoor.com');
    const paramJl = urlObj.searchParams.get('jl');
    if (paramJl) return paramJl;
    const match = urlObj.pathname.match(/-JV_IC(\d+)/) || urlObj.pathname.match(/-JL(\d+)/) || urlObj.pathname.match(/\/job\/.*_(\d+)\.htm/);
    if (match) return match[1];
  } catch {
    const m = urlStr.match(/jl=(\d+)/) || urlStr.match(/-JV_IC(\d+)/) || urlStr.match(/-JL(\d+)/);
    if (m) return m[1];
  }
  if (doc) {
    const selected = doc.querySelector('li[data-selected="true"], [data-test="jobListing"][data-selected="true"]');
    const attrId = selected?.getAttribute('data-job-id') || selected?.getAttribute('data-id');
    if (attrId) return attrId;
  }
  return null;
}

export class GlassdoorExtractor implements JobExtractor {
  siteName = 'Glassdoor';

  canHandle(url: string, doc?: Document): boolean {
    const isMatchingUrl =
      url.includes('glassdoor.com/Job/') ||
      url.includes('glassdoor.com/job-listing/') ||
      url.includes('glassdoor.com/job-detail');

    if (!isMatchingUrl) {
      return false;
    }

    if (doc) {
      const hasJsonLd = Boolean(extractJsonLd(doc));
      const hasJobDetailDom = Boolean(
        doc.querySelector(
          '[data-test="job-title"], [data-test="jobTitle"], [class*="heading_Heading"], [class*="JobDetails_jobTitle"], [data-test="employer-name"], [class*="EmployerProfile_employerName"], [class*="JobDetails_employerName"], #JobDescriptionContainer, [data-test="jobDescription"], [class*="JobDetails_jobDescription"], [class*="jobDescription"], [class*="TwoColumnLayout_jobDetailsContainer"]'
        )
      );
      return hasJsonLd || hasJobDetailDom;
    }

    return true;
  }

  extractFromApiResponse(apiData: any, targetUrl: string): JobPayload | null {
    if (!apiData) return null;
    const resObj = Array.isArray(apiData) ? apiData[0] : apiData;
    const jobview = resObj?.data?.jobview;
    if (!jobview) return null;

    const header = jobview.header || {};
    const job = jobview.job || {};

    const title = cleanText(header.jobTitleText || job.jobTitleText);
    const company = cleanEmployerName(header.employerNameFromSearch);
    const location = cleanText(header.locationName);
    const description = cleanText(job.description) || getCleanHtml(job.description);

    if (!title && !company && !description) return null;

    const isRemote = header.locationType === 'S' || (location?.toLowerCase().includes('remote') ?? false);

    return {
      title,
      company,
      location,
      description,
      employment_type: null,
      remote_type: isRemote ? 'Remote' : null,
      url: targetUrl,
      source: 'extension:glassdoor',
    };
  }

  async extractAsync(doc: Document = document): Promise<JobPayload | null> {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const url = getCanonicalUrl(doc, fallbackUrl);
    const jobId = getGlassdoorJobId(fallbackUrl, doc) || getGlassdoorJobId(url, doc);

    if (jobId) {
      try {
        console.log(`[Compust Glassdoor] Fetching structured job via JobSpy GraphQL endpoint for job ID: ${jobId}`);
        const body = [
          {
            operationName: 'JobDetailQuery',
            variables: {
              jl: parseInt(jobId, 10) || jobId,
              queryString: 'q',
              pageTypeEnum: 'SERP',
            },
            query: `query JobDetailQuery($jl: Long!, $queryString: String, $pageTypeEnum: PageTypeEnum) {
              jobview: jobView(
                listingId: $jl
                contextHolder: {queryString: $queryString, pageTypeEnum: $pageTypeEnum}
              ) {
                header {
                  jobTitleText
                  employerNameFromSearch
                  locationName
                  locationType
                  payCurrency
                  payPeriod
                  payPeriodAdjustedPay {
                    p10
                    p50
                    p90
                  }
                }
                job {
                  listingId
                  jobTitleText
                  description
                }
              }
            }`,
          },
        ];

        const res = await fetch('https://www.glassdoor.com/graph', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'apollographql-client-name': 'job-search-next',
            'apollographql-client-version': '4.65.5',
          },
          credentials: 'same-origin',
          body: JSON.stringify(body),
        });

        if (res.ok) {
          const json = await res.json();
          const apiPayload = this.extractFromApiResponse(json, url);
          if (apiPayload && apiPayload.title && apiPayload.company && apiPayload.description) {
            console.log('[Compust Glassdoor] Successfully extracted job via GraphQL API');
            return apiPayload;
          }
        } else {
          console.warn(`[Compust Glassdoor] GraphQL API returned status ${res.status}, falling back to DOM.`);
        }
      } catch (err) {
        console.warn('[Compust Glassdoor] GraphQL API fetch failed, falling back to DOM:', err);
      }
    }

    // Fallback path: JSON-LD and DOM selectors
    return this.extract(doc);
  }

  extract(doc: Document = document): JobPayload | null {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const url = getCanonicalUrl(doc, fallbackUrl);

    // 1. Try JSON-LD structured data first (most stable)
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
        source: 'extension:glassdoor',
      };
    }

    // 2. Expand collapsed description if toggle exists
    expandDescriptionIfCollapsed(doc);

    // Scope search within job details container if present (e.g. split-pane search view)
    const container =
      doc.querySelector('div[class*="jobDetailsContainer"]') ||
      doc.querySelector('div[class*="TwoColumnLayout_jobDetailsContainer"]') ||
      doc;

    // 3. DOM extraction with comprehensive fallback selectors
    const titleEl =
      container.querySelector('[data-test="job-title"]') ||
      container.querySelector('[data-test="jobTitle"]') ||
      container.querySelector('[class*="JobDetails_jobTitle"]') ||
      container.querySelector('header[class*="JobDetails_jobDetailsHeader"] h1') ||
      container.querySelector('h1[class*="heading_Heading"]') ||
      container.querySelector('h1.heading_Heading__x_DqB') ||
      container.querySelector('.JobDetails_jobTitle__w1gH_') ||
      container.querySelector('h1');
    const title = cleanText(titleEl?.textContent);

    const companyEl =
      container.querySelector('[data-test="employer-name"]') ||
      container.querySelector('[data-test="employerName"]') ||
      container.querySelector('[class*="EmployerProfile_employerNameHeading"]') ||
      container.querySelector('[class*="EmployerProfile_employerName"]') ||
      container.querySelector('[class*="JobDetails_employerName"]') ||
      container.querySelector('.EmployerProfile_employerName__8A_sf') ||
      container.querySelector('.JobDetails_employerName__qIIL_') ||
      container.querySelector('[class*="EmployerProfile_employerInfo"] h4');
    const company = cleanEmployerName(companyEl?.textContent);

    const locationEl =
      container.querySelector('[data-test="location"]') ||
      container.querySelector('[data-test="job-location"]') ||
      container.querySelector('[class*="JobDetails_location"]') ||
      container.querySelector('.JobDetails_location__mSg5h') ||
      container.querySelector('[data-test="job-location-link"]');
    const location = cleanText(locationEl?.textContent);

    const descEl =
      container.querySelector('[class*="JobDetails_jobDescription"]') ||
      container.querySelector('[class*="jobDescription"]') ||
      container.querySelector('[class*="JobDescription"]') ||
      container.querySelector('[data-test="jobDescription"]') ||
      container.querySelector('#JobDescriptionContainer') ||
      container.querySelector('.jobDescriptionContent') ||
      container.querySelector('.JobDetails_jobDescription__uWShared') ||
      container.querySelector('[class*="JobDetails_description"]') ||
      container.querySelector('article[class*="jobDescription"]') ||
      container.querySelector('section[class*="jobDescription"]');
    const description = getCleanHtml(descEl);

    const employmentEl =
      container.querySelector('[data-test="job-type"]') ||
      container.querySelector('[class*="JobDetails_jobType"] span') ||
      container.querySelector('[data-test="job-detail-type"]');
    const employment_type = cleanText(employmentEl?.textContent);

    return {
      title,
      company,
      location,
      description,
      employment_type,
      remote_type: location?.toLowerCase().includes('remote') ? 'Remote' : null,
      url,
      source: 'extension:glassdoor',
    };
  }
}

export const glassdoorExtractor = new GlassdoorExtractor();

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  console.log('[Compust Glassdoor] Content script active at:', window.location.href);
  let overlay: CompustOverlay | null = null;
  let activeJobId: string | null = getGlassdoorJobId(window.location.href, document);

  const initOverlayIfMatching = () => {
    const currentUrl = window.location.href;
    const canHandleUrl = glassdoorExtractor.canHandle(currentUrl);
    if (!canHandleUrl) return;

    const newJobId = getGlassdoorJobId(currentUrl, document);
    console.log('[Compust Glassdoor] URL check:', currentUrl, 'JobId:', newJobId);

    // If job changed in Single Page App split-pane view, reset overlay state to avoid stale job captures
    if (overlay && newJobId && newJobId !== activeJobId) {
      console.log(`[Compust Glassdoor] Job selection changed (${activeJobId} -> ${newJobId}). Resetting overlay.`);
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
      console.log('[Compust Glassdoor] Initializing overlay on page (URL match, eager creation)');
      overlay = new CompustOverlay({
        onCapture: async () => {
          if (!overlay) return;
          const currentGen = overlay.getGeneration();
          overlay.showLoading(currentGen);

          // 1. Try JobSpy GraphQL API first via extractAsync, then fall back to DOM
          let payload = (await glassdoorExtractor.extractAsync?.(document)) || glassdoorExtractor.extract(document);
          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust Glassdoor] Discarding stale extraction: user navigated away during API extraction');
            return;
          }

          if (payload && !payload.description) {
            expandDescriptionIfCollapsed(document);
            await waitForElement(
              (doc) =>
                doc.querySelector(
                  '[class*="JobDetails_jobDescription"], [class*="jobDescription"], #JobDescriptionContainer, [data-test="jobDescription"]'
                ),
              document,
              2000
            );
            if (!overlay.isCurrentGeneration(currentGen)) {
              console.log('[Compust Glassdoor] Discarding stale extraction: user navigated away while waiting for description');
              return;
            }
            payload = glassdoorExtractor.extract(document);
          }

          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust Glassdoor] Discarding stale extraction: user navigated away before validation');
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
              console.log('[Compust Glassdoor] Discarding stale response: user navigated away during API call');
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
    const currentId = getGlassdoorJobId(window.location.href, document);
    if (!overlay || (currentId && currentId !== activeJobId)) {
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
