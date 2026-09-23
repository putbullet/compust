import { JobPayload } from '../../lib/types';

export interface JobExtractor {
  siteName: string;
  canHandle(url: string, doc?: Document): boolean;
  extract(doc?: Document): JobPayload | null;
  extractAsync?(doc?: Document): Promise<JobPayload | null>;
}

export function cleanText(text: string | null | undefined): string | null {
  if (!text) return null;
  const cleaned = text
    .normalize('NFC')
    .replace(/\r\n/g, '\n')
    .replace(/\s+/g, ' ')
    .trim();
  return cleaned.length > 0 ? cleaned : null;
}

export function cleanEmployerName(text: string | null | undefined): string | null {
  if (!text) return null;
  let cleaned = cleanText(text) || '';
  // Remove trailing ratings e.g. "Google 4.4 ★" or "Company 4.2"
  cleaned = cleaned.replace(/\s*\d+(\.\d+)?\s*★.*$/i, '');
  cleaned = cleaned.replace(/\s+\d+\.\d+\s*$/, '');
  return cleaned.trim().length > 0 ? cleaned.trim() : null;
}

export function getCleanHtml(element: Element | null): string | null {
  if (!element) return null;
  const clone = element.cloneNode(true) as Element;
  // Remove script and style elements from cloned description
  clone.querySelectorAll('script, style, noscript, iframe').forEach((el) => el.remove());
  const html = clone.innerHTML.trim();
  return html.length > 0 ? html : null;
}

function isJobPostingType(type: any): boolean {
  if (!type) return false;
  if (typeof type === 'string') {
    return type.toLowerCase().includes('jobposting');
  }
  if (Array.isArray(type)) {
    return type.some((t) => typeof t === 'string' && t.toLowerCase().includes('jobposting'));
  }
  return false;
}

function findJobPostingInObject(obj: any): any | null {
  if (!obj || typeof obj !== 'object') return null;
  if (isJobPostingType(obj['@type'])) {
    return obj;
  }
  if (Array.isArray(obj)) {
    for (const item of obj) {
      const found = findJobPostingInObject(item);
      if (found) return found;
    }
  }
  if (Array.isArray(obj['@graph'])) {
    for (const item of obj['@graph']) {
      const found = findJobPostingInObject(item);
      if (found) return found;
    }
  }
  return null;
}

export function extractJsonLd(doc: Document): any | null {
  const scripts = doc.querySelectorAll('script[type="application/ld+json"]');
  for (const script of scripts) {
    try {
      const content = script.textContent?.trim();
      if (!content) continue;
      const data = JSON.parse(content);
      const posting = findJobPostingInObject(data);
      if (posting) return posting;
    } catch {
      // Ignore JSON parse errors in invalid JSON-LD blocks
    }
  }
  return null;
}

export interface PayloadValidationResult {
  isValid: boolean;
  missingError?: string;
}

export function validateJobPayload(payload: JobPayload | null): PayloadValidationResult {
  if (!payload) {
    return {
      isValid: false,
      missingError: 'Could not detect any job posting details on this page.',
    };
  }

  const hasTitle = Boolean(payload.title && payload.title.trim().length > 0);
  const hasCompany = Boolean(payload.company && payload.company.trim().length > 0);
  const hasDesc = Boolean(payload.description && payload.description.trim().length > 0);

  if (!hasTitle && !hasCompany && !hasDesc) {
    return {
      isValid: false,
      missingError: 'Could not detect a job posting on this page. Please make sure you are viewing an active job listing or details pane.',
    };
  }

  if (!hasTitle) {
    return {
      isValid: false,
      missingError: 'Found job information, but could not detect the job title on this page.',
    };
  }

  if (!hasCompany) {
    return {
      isValid: false,
      missingError: `Found job title ("${payload.title}"), but could not detect the company name on this page.`,
    };
  }

  if (!hasDesc) {
    return {
      isValid: false,
      missingError: `Found job title ("${payload.title}") and company ("${payload.company}"), but could not detect the job description on this page.`,
    };
  }

  return { isValid: true };
}

export function getCanonicalUrl(doc: Document, fallbackUrl: string): string {
  const canonical = doc.querySelector('link[rel="canonical"]')?.getAttribute('href');
  if (canonical && canonical.startsWith('http')) {
    return canonical;
  }
  // Strip tracking parameters
  try {
    const parsed = new URL(fallbackUrl);
    const trackingParams = ['utm_source', 'utm_medium', 'utm_campaign', 'refId', 'trackingId'];
    for (const p of trackingParams) {
      parsed.searchParams.delete(p);
    }
    return parsed.toString();
  } catch {
    return fallbackUrl;
  }
}

export interface ExtractorConfig {
  siteName: string;
  sourceIdentifier: string;
  urlPatterns: (string | RegExp)[];
  detailDomSelectors: string[];
  titleSelectors: string[];
  companySelectors: string[];
  locationSelectors: string[];
  descriptionSelectors: string[];
  employmentSelectors?: string[];
}

export function extractLocationFromJsonLd(jobLocation: any): string | null {
  if (!jobLocation) return null;
  const loc = Array.isArray(jobLocation) ? jobLocation[0] : jobLocation;
  if (!loc) return null;
  const addr = loc.address || loc;
  const locality = addr.addressLocality || addr.addressRegion || addr.addressCountry;
  if (locality) return cleanText(locality);
  if (typeof addr === 'string') return cleanText(addr);
  if (typeof loc.name === 'string') return cleanText(loc.name);
  return null;
}

export class BaseJobExtractor implements JobExtractor {
  siteName: string;
  sourceIdentifier: string;
  protected config: ExtractorConfig;

  constructor(config: ExtractorConfig) {
    this.config = config;
    this.siteName = config.siteName;
    this.sourceIdentifier = config.sourceIdentifier;
  }

  canHandle(url: string, doc?: Document): boolean {
    const isMatchingUrl = this.config.urlPatterns.some((pattern) => {
      if (typeof pattern === 'string') {
        return url.includes(pattern);
      }
      return pattern.test(url);
    });

    if (!isMatchingUrl) {
      return false;
    }

    if (doc) {
      const hasJsonLd = Boolean(extractJsonLd(doc));
      const hasDetailDom = this.config.detailDomSelectors.some((sel) => Boolean(doc.querySelector(sel)));
      return hasJsonLd || hasDetailDom;
    }

    return true;
  }

  extract(doc: Document = document): JobPayload | null {
    const fallbackUrl = (typeof window !== 'undefined' ? window.location?.href : doc.defaultView?.location?.href) || '';
    const url = getCanonicalUrl(doc, fallbackUrl);

    // 1. Prioritize JSON-LD structured data
    const jsonLd = extractJsonLd(doc);
    if (jsonLd) {
      const title = cleanText(jsonLd.title);
      const company = cleanEmployerName(jsonLd.hiringOrganization?.name);
      const description = jsonLd.description ? cleanText(jsonLd.description) : null;
      if (title && company && description) {
        return {
          title,
          company,
          location: extractLocationFromJsonLd(jsonLd.jobLocation),
          description,
          employment_type: cleanText(jsonLd.employmentType),
          remote_type: jsonLd.jobLocationType === 'TELECOMMUTE' ? 'Remote' : null,
          url,
          source: this.sourceIdentifier,
        };
      }
    }

    // 2. DOM selector extraction
    const queryFirst = (selectors: string[]): Element | null => {
      for (const sel of selectors) {
        const el = doc.querySelector(sel);
        if (el) return el;
      }
      return null;
    };

    const titleEl = queryFirst(this.config.titleSelectors);
    const companyEl = queryFirst(this.config.companySelectors);
    const locationEl = queryFirst(this.config.locationSelectors);
    const descEl = queryFirst(this.config.descriptionSelectors);
    const empEl = this.config.employmentSelectors ? queryFirst(this.config.employmentSelectors) : null;

    const title = cleanText(titleEl?.textContent) || (jsonLd ? cleanText(jsonLd.title) : null);
    const company = cleanEmployerName(companyEl?.textContent) || (jsonLd ? cleanEmployerName(jsonLd.hiringOrganization?.name) : null);
    const location = cleanText(locationEl?.textContent) || (jsonLd ? extractLocationFromJsonLd(jsonLd.jobLocation) : null);
    const description = getCleanHtml(descEl) || (jsonLd?.description ? cleanText(jsonLd.description) : null);
    const employment_type = cleanText(empEl?.textContent) || (jsonLd ? cleanText(jsonLd.employmentType) : null);

    const locLower = (location || '').toLowerCase();
    const isRemote =
      locLower.includes('remote') ||
      locLower.includes('télétravail') ||
      locLower.includes('teletravail') ||
      locLower.includes('homeoffice');

    return {
      title,
      company,
      location,
      description,
      employment_type,
      remote_type: isRemote ? 'Remote' : null,
      url,
      source: this.sourceIdentifier,
    };
  }

  async extractAsync(doc: Document = document): Promise<JobPayload | null> {
    return this.extract(doc);
  }
}
