import { describe, it, expect, beforeEach } from 'vitest';
import { JSDOM } from 'jsdom';
import { formatErrorMessage, CompustOverlay } from '../../src/content/common/overlay';

describe('Global Overlay Error Handling (Bug 2 Regression Suite)', () => {
  beforeEach(() => {
    const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'https://www.glassdoor.com/job-listing/test.htm',
    });
    (global as any).document = dom.window.document;
    (global as any).window = dom.window;
    (global as any).HTMLElement = dom.window.HTMLElement;
    (global as any).MutationObserver = dom.window.MutationObserver;
  });

  describe('formatErrorMessage()', () => {
    it('formats plain string errors properly and prevents [object Object]', () => {
      expect(formatErrorMessage('Failed to capture vacancy')).toBe('Failed to capture vacancy');
      expect(formatErrorMessage('[object Object]')).toBe('An unexpected error occurred.');
      expect(formatErrorMessage('')).toBe('An unexpected error occurred.');
    });

    it('formats plain Error instances and preserves error.message', () => {
      const plainError = new Error('Database connection reset during capture');
      expect(formatErrorMessage(plainError)).toBe('Database connection reset during capture');
    });

    it('formats non-Error object rejections with message or error fields', () => {
      const nonErrorRejection1 = { message: 'Token has expired', code: 401 };
      expect(formatErrorMessage(nonErrorRejection1)).toBe('Token has expired');

      const nonErrorRejection2 = { error: 'Service temporarily unavailable', status: 503 };
      expect(formatErrorMessage(nonErrorRejection2)).toBe('Service temporarily unavailable');
    });

    it('formats FastAPI validation error dictionaries with detail array', () => {
      const fastApiValidationError = {
        detail: [
          { loc: ['body', 'title'], msg: 'Title is required', type: 'value_error.missing' },
          { loc: ['body', 'company'], msg: 'Company is required', type: 'value_error.missing' },
        ],
      };
      const formatted = formatErrorMessage(fastApiValidationError);
      expect(formatted).toContain('Title is required');
      expect(formatted).toContain('Company is required');
      expect(formatted).not.toContain('[object Object]');
    });

    it('formats arbitrary non-Error objects into string representations without [object Object]', () => {
      const rawObject = { code: 'INTERNAL_ERR', retryable: false };
      const formatted = formatErrorMessage(rawObject);
      expect(formatted).toContain('INTERNAL_ERR');
      expect(formatted).not.toContain('[object Object]');
    });

    it('handles null and undefined gracefully', () => {
      expect(formatErrorMessage(null)).toBe('An unexpected error occurred.');
      expect(formatErrorMessage(undefined)).toBe('An unexpected error occurred.');
    });
  });

  describe('CompustOverlay.showError() DOM Rendering', () => {
    it('renders readable text and NEVER renders [object Object] when passed a plain Error', () => {
      const overlay = new CompustOverlay({
        onCapture: async () => {},
        onTrack: async () => {},
        onRetry: () => {},
      });

      const root = document.getElementById('compust-capture-root');
      expect(root).not.toBeNull();
      const shadow = root?.shadowRoot;

      const plainError = new Error('Glassdoor DOM parse exception');
      overlay.showError(plainError);

      const alertBox = shadow?.querySelector('.compust-alert-box');
      expect(alertBox).not.toBeNull();
      const content = alertBox?.innerHTML || '';

      expect(content).toContain('Glassdoor DOM parse exception');
      expect(content).not.toContain('[object Object]');
    });

    it('renders readable text and NEVER renders [object Object] when passed a non-Error rejection object', () => {
      const overlay = new CompustOverlay({
        onCapture: async () => {},
        onTrack: async () => {},
        onRetry: () => {},
      });

      const root = document.getElementById('compust-capture-root');
      const shadow = root?.shadowRoot;

      const nonErrorRejection = {
        error: 'Backend request failed with status 502',
        statusCode: 502,
      };
      overlay.showError(nonErrorRejection);

      const alertBox = shadow?.querySelector('.compust-alert-box');
      expect(alertBox).not.toBeNull();
      const content = alertBox?.innerHTML || '';

      expect(content).toContain('Backend request failed with status 502');
      expect(content).not.toContain('[object Object]');
    });
  });
});
