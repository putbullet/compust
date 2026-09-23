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
 * Extract Indeed job key (jk) from URL or active page element.
 */
export function getIndeedJobKey(urlStr: string, doc?: Document): string | null {
  try {
    const urlObj = new URL(urlStr, 'https://www.indeed.com');
    const jk = urlObj.searchParams.get('jk') || urlObj.searchParams.get('vjk');
    if (jk) return jk;
  } catch {
    const m = urlStr.match(/[?&]v?jk=([a-f0-9]+)/i);
    if (m) return m[1];
  }
  if (doc) {
    // Look for active/selected item or detail pane container first
    const selectedJk =
      doc.querySelector('#jobsearch-ViewjobPaneWrapper [data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('#vjs-container [data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('[aria-selected="true"] [data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('[aria-selected="true"][data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('.job_seen_beacon.selected [data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('.selected [data-jk]')?.getAttribute('data-jk') ||
      doc.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]')?.closest('[data-jk]')?.getAttribute('data-jk');
    if (selectedJk) return selectedJk;

    // Only if single-job viewjob page
    if (urlStr.includes('/viewjob') || urlStr.includes('/job/')) {
      const attrJk = doc.querySelector('[data-jk]')?.getAttribute('data-jk') || doc.querySelector('[data-job-id]')?.getAttribute('data-job-id');
      if (attrJk) return attrJk;
    }
  }
  return null;
}

export class IndeedExtractor implements JobExtractor {
  siteName = 'Indeed';

  canHandle(url: string, doc?: Document): boolean {
    const isMatchingUrl =
      url.includes('indeed.com/viewjob') ||
      url.includes('indeed.com/jobs') ||
      url.includes('indeed.com/job/');

    if (!isMatchingUrl) {
      return false;
    }

    if (doc) {
      const hasJobDetailDom = Boolean(
        doc.querySelector(
          '[data-testid="jobsearch-JobInfoHeader-title"], .jobsearch-JobInfoHeader-title, #jobDescriptionText, .jobsearch-jobDescriptionText'
        )
      );
      const hasJsonLd = Boolean(extractJsonLd(doc));
      return hasJobDetailDom || hasJsonLd;
    }

    return true;
  }

  extractFromApiResponse(apiData: any, targetUrl: string): JobPayload | null {
    if (!apiData) return null;
    const job = apiData?.data?.jobSearch?.results?.[0]?.job || apiData?.data?.job || apiData?.job;
    if (!job) return null;

    const title = cleanText(job.title);
    const company = cleanEmployerName(job.employer?.name || job.companyName);
    const location = cleanText(
      job.location?.formatted?.short ||
      job.location?.city ||
      (job.location?.city && job.location?.admin1Code ? `${job.location.city}, ${job.location.admin1Code}` : null)
    );
    const description = cleanText(job.description?.html) || getCleanHtml(job.description?.html) || cleanText(job.description);

    if (!title && !company && !description) return null;

    const isRemote =
      job.attributes?.some((a: any) => a.label?.toLowerCase().includes('remote')) ||
      (location?.toLowerCase().includes('remote') ?? false);

    return {
      title,
      company,
      location,
      description,
      employment_type: cleanText(job.attributes?.find((a: any) => a.key === 'jobType')?.label),
      remote_type: isRemote ? 'Remote' : null,
      url: targetUrl,
      source: 'extension:indeed',
    };
  }

  async extractAsync(doc: Document = document): Promise<JobPayload | null> {
    // 1. Always prioritize active detail pane DOM rendered right now at click time
    const domPayload = this.extract(doc);
    if (domPayload && domPayload.title && domPayload.description) {
      return domPayload;
    }

    // 2. If DOM detail pane was incomplete, try API fallback
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const jobKey = getIndeedJobKey(fallbackUrl, doc);

    if (jobKey) {
      const canonicalJobUrl = `https://www.indeed.com/viewjob?jk=${jobKey}`;
      try {
        console.log(`[Compust Indeed] Fetching structured job via Indeed GraphQL API for jobKey: ${jobKey}`);
        const query = `query GetJobData {
          job(key: "${jobKey}") {
            key
            title
            description { html }
            location { city admin1Code countryCode formatted { short long } }
            employer { name }
            attributes { key label }
          }
        }`;

        const res = await fetch('https://apis.indeed.com/graphql', {
          method: 'POST',
          headers: {
            'content-type': 'application/json',
            'indeed-api-key': '161092c2017b5bbab13edb12461a62d5a833871e7cad6d9d475304573de67ac8',
            'accept': 'application/json',
          },
          body: JSON.stringify({ query }),
        });

        if (res.ok) {
          const data = await res.json();
          const apiPayload = this.extractFromApiResponse(data, canonicalJobUrl);
          if (apiPayload && apiPayload.title && apiPayload.company && apiPayload.description) {
            console.log('[Compust Indeed] Successfully extracted job via GraphQL API');
            return apiPayload;
          }
        }
      } catch (err) {
        console.warn('[Compust Indeed] GraphQL API fetch failed, falling back to page extraction:', err);
      }
    }

    return domPayload;
  }

  extract(doc: Document = document): JobPayload | null {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const jobKey = getIndeedJobKey(fallbackUrl, doc);
    const targetUrl = jobKey
      ? `https://www.indeed.com/viewjob?jk=${jobKey}`
      : getCanonicalUrl(doc, fallbackUrl);

    // Identify active detail pane container in list+detail layout
    const detailContainer =
      doc.querySelector('#jobsearch-ViewjobPaneWrapper') ||
      doc.querySelector('.jobsearch-RightPane') ||
      doc.querySelector('#vjs-container') ||
      doc;

    // 1. DOM extraction from active rendered detail pane
    const titleEl =
      detailContainer.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]') ||
      detailContainer.querySelector('h1.jobsearch-JobInfoHeader-title') ||
      detailContainer.querySelector('.jobsearch-JobInfoHeader-title') ||
      detailContainer.querySelector('h1');
    const title = cleanText(titleEl?.textContent);

    const companyEl =
      detailContainer.querySelector('[data-testid="inlineHeader-companyName"]') ||
      detailContainer.querySelector('.jobsearch-CompanyInfoContainer a') ||
      detailContainer.querySelector('.jobsearch-JobInfoHeader-companyName') ||
      detailContainer.querySelector('[data-company-name="true"]');
    const company = cleanEmployerName(companyEl?.textContent);

    const locationEl =
      detailContainer.querySelector('[data-testid="inlineHeader-companyLocation"]') ||
      detailContainer.querySelector('[data-testid="job-location"]') ||
      detailContainer.querySelector('.jobsearch-JobInfoHeader-companyLocation') ||
      detailContainer.querySelector('#jobLocationText');
    const location = cleanText(locationEl?.textContent);

    const descEl =
      detailContainer.querySelector('#jobDescriptionText') ||
      detailContainer.querySelector('.jobsearch-jobDescriptionText');
    const description = getCleanHtml(descEl);

    const employmentEl =
      detailContainer.querySelector('[data-testid="jobsearch-JobInfoHeader-jobType"]') ||
      detailContainer.querySelector('#salaryInfoAndJobType') ||
      detailContainer.querySelector('[data-testid="jobsearch-JobDescriptionSection-item"]') ||
      detailContainer.querySelector('.jobsearch-JobDescriptionSection-item');
    const employment_type = cleanText(employmentEl?.textContent);

    // If detail DOM yielded a job, return it fresh!
    if (title || description) {
      return {
        title,
        company,
        location,
        description,
        employment_type,
        remote_type: location?.toLowerCase().includes('remote') ? 'Remote' : null,
        url: targetUrl,
        source: 'extension:indeed',
      };
    }

    // 2. Fallback to JSON-LD structured data if no active detail pane elements were found
    const jsonLd = extractJsonLd(doc);
    if (jsonLd) {
      return {
        title: cleanText(jsonLd.title),
        company: cleanEmployerName(jsonLd.hiringOrganization?.name),
        location: cleanText(jsonLd.jobLocation?.address?.addressLocality || jsonLd.jobLocation?.address?.addressRegion),
        description: jsonLd.description ? cleanText(jsonLd.description) : null,
        employment_type: cleanText(jsonLd.employmentType),
        remote_type: jsonLd.jobLocationType === 'TELECOMMUTE' ? 'Remote' : null,
        url: targetUrl,
        source: 'extension:indeed',
      };
    }

    return {
      title,
      company,
      location,
      description,
      employment_type,
      remote_type: location?.toLowerCase().includes('remote') ? 'Remote' : null,
      url: targetUrl,
      source: 'extension:indeed',
    };
  }
}

export const indeedExtractor = new IndeedExtractor();

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  console.log('[Compust Indeed] Content script active at:', window.location.href);
  let overlay: CompustOverlay | null = null;
  let activeJobKey: string | null = getIndeedJobKey(window.location.href, document);

  const initOverlayIfMatching = () => {
    const currentUrl = window.location.href;
    const canHandleUrl = indeedExtractor.canHandle(currentUrl);
    if (!canHandleUrl) return;

    const newJobKey = getIndeedJobKey(currentUrl, document);
    console.log('[Compust Indeed] URL check:', currentUrl, 'JobKey:', newJobKey);

    // If job changed in Single Page App split-pane view, reset overlay state to avoid stale job captures
    if (overlay && newJobKey && newJobKey !== activeJobKey) {
      console.log(`[Compust Indeed] Job selection changed (${activeJobKey} -> ${newJobKey}). Resetting overlay.`);
      activeJobKey = newJobKey;
      overlay.bumpGeneration();
      overlay.hidePanel();
      overlay.renderButton();
    } else if (!activeJobKey && newJobKey) {
      activeJobKey = newJobKey;
    }

    // Create overlay eagerly on URL match — don't wait for detail pane DOM to render.
    // onCapture() reads the DOM fresh at click time so there is no stale-data risk.
    if (!overlay) {
      console.log('[Compust Indeed] Initializing overlay on page (URL match, eager creation)');
      overlay = new CompustOverlay({
        onCapture: async () => {
          if (!overlay) return;
          const currentGen = overlay.getGeneration();
          overlay.showLoading(currentGen);
          const payload = (await indeedExtractor.extractAsync?.(document)) || indeedExtractor.extract(document);
          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust Indeed] Discarding stale extraction: user navigated away during DOM extraction');
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
              console.log('[Compust Indeed] Discarding stale response: user navigated away during API call');
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
    const currentKey = getIndeedJobKey(window.location.href, document);
    if (!overlay || (currentKey && currentKey !== activeJobKey)) {
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
