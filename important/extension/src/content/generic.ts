import { CompustOverlay } from './common/overlay';
import { JobPayload } from '../lib/types';
import { browserAPI } from '../lib/browserPolyfill';

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  if ((window as any).__COMPUST_GENERIC_LOADED__) {
    console.log('[Compust Generic] Script already injected, toggling overlay.');
    const existingOverlay = (window as any).__COMPUST_OVERLAY_INSTANCE__;
    if (existingOverlay) {
      existingOverlay.toggle();
    }
  } else {
    (window as any).__COMPUST_GENERIC_LOADED__ = true;
    console.log('[Compust Generic] Script initializing on:', window.location.href);

    let overlay: CompustOverlay | null = null;

    overlay = new CompustOverlay({
      onCapture: async () => {
        if (!overlay) return;
        const currentGen = overlay.getGeneration();
        overlay.showLoading(currentGen);

        try {
          // 1. Extract job posting from raw HTML using backend generic extraction (adapters + JSON-LD + 73k taxonomy)
          const extractRes = await browserAPI.runtime.sendMessage({
            type: 'EXTRACT_GENERIC_JOB',
            html: document.documentElement.outerHTML,
            url: window.location.href,
          });

          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust Generic] Discarding stale extraction: generation changed during extraction');
            return;
          }

          if (!extractRes.ok) {
            overlay.showError(
              extractRes.message || extractRes.error || 'Failed to extract job posting',
              extractRes.error === 'NOT_LOGGED_IN',
              extractRes.isNetworkError,
              currentGen
            );
            return;
          }

          const extracted = extractRes.data;

          // Surface extraction confidence to the user:
          // - 'high': platform adapter or JSON-LD match with title corpus confirmation — no warning needed
          // - 'medium': partial match — warn that the title may not be fully recognized
          // - 'low': no title corpus match — strong advisory to review fields before saving
          const confidence: 'high' | 'medium' | 'low' = extracted.confidence || 'low';
          const extractionAdvisory: string | null =
            confidence === 'low'
              ? extracted.message ||
                `Extraction confidence is low for this site — please review the job title and details before saving. ${extracted.normalized_title ? `Closest recognized title: "${extracted.normalized_title}".` : ''}`
              : confidence === 'medium'
              ? extracted.message ||
                (extracted.normalized_title
                  ? `Title matched as "${extracted.normalized_title}" — verify this is correct before saving.`
                  : null)
              : null;

          const payload: JobPayload = {
            title: extracted.title || document.title || 'Untitled Position',
            company: extracted.company || 'Company',
            location: extracted.location,
            description: extracted.description || document.body.innerText.slice(0, 1500),
            employment_type: extracted.employment_type,
            remote_type: extracted.remote_type,
            url: window.location.href,
            source: 'extension:generic',
          };

          // 2. Run Ephemeral Match & Guidance Analysis (zero DB writes)
          const analyzeRes = await browserAPI.runtime.sendMessage({
            type: 'ANALYZE_EPHEMERAL_JOB',
            payload,
          });

          if (!overlay.isCurrentGeneration(currentGen)) {
            console.log('[Compust Generic] Discarding stale response: generation changed during analysis');
            return;
          }

          if (!analyzeRes.ok) {
            overlay.showError(
              analyzeRes.message || analyzeRes.error || 'Failed to analyze job',
              analyzeRes.error === 'NOT_LOGGED_IN',
              analyzeRes.isNetworkError,
              currentGen
            );
            return;
          }

          // Merge extraction advisory into the result message so it appears in the overlay
          const resultData = analyzeRes.data;
          if (extractionAdvisory && !resultData.message) {
            resultData.message = extractionAdvisory;
          } else if (extractionAdvisory && resultData.message) {
            resultData.message = `${extractionAdvisory}\n\n${resultData.message}`;
          }

          overlay.showEphemeralResult(resultData, payload, currentGen);
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

    (window as any).__COMPUST_OVERLAY_INSTANCE__ = overlay;

    // Trigger analysis immediately on manual activation
    overlay.toggle();

    // Listen for subsequent toggle events from toolbar icon or shortcut
    browserAPI.runtime.onMessage.addListener((message: any, _sender: any, sendResponse: any) => {
      if (message.type === 'TOGGLE_CAPTURE_PANEL') {
        overlay?.toggle();
        sendResponse({ ok: true });
      }
      return true;
    });
  }
}
