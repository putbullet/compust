import { browserAPI } from '../lib/browserPolyfill';
import {
  getToken,
  setToken,
  removeToken,
  getUser,
  setUser,
  getSettings,
  saveSettings,
} from '../lib/auth';
import {
  checkBackendHealth,
  loginToBackend,
  quickAddAndAnalyzeJob,
  analyzeEphemeralJob,
  saveJobWithAction,
  extractJobFromHtml,
  trackJobApplication,
  fetchActiveResume,
  CompustApiError,
} from '../lib/api';
import { ExtensionMessage } from '../lib/types';

// Initialize background message listener
console.log('[Compust Background] Initializing...');
if (typeof browser !== 'undefined' && browser.permissions) {
  browser.permissions.getAll().then((p) => {
    console.log('[Compust Background] Active permissions in Firefox:', JSON.stringify(p));
  }).catch((err) => {
    console.warn('[Compust Background] Error getting permissions:', err);
  });
}

browserAPI.runtime.onMessage.addListener((message: ExtensionMessage, _sender, sendResponse) => {
  console.log('[Compust Background] Received message:', message.type);
  handleMessage(message)
    .then((result) => sendResponse(result))
    .catch((err) => {
      sendResponse({
        ok: false,
        error: err.message || 'An unexpected extension error occurred',
        status: err instanceof CompustApiError ? err.status : undefined,
        isNetworkError: err instanceof CompustApiError ? err.isNetworkError : false,
      });
    });
  // Return true to indicate asynchronous response in Chrome & Firefox
  return true;
});

async function handleMessage(message: ExtensionMessage): Promise<any> {
  const settings = await getSettings();

  switch (message.type) {
    case 'CHECK_STATUS': {
      const token = await getToken();
      const user = await getUser();
      const health = await checkBackendHealth(settings.backendUrl);
      let activeResume = null;
      if (token && health.ok) {
        activeResume = await fetchActiveResume(settings.backendUrl, token);
      }
      return {
        ok: true,
        isLoggedIn: !!token,
        user,
        backendConnected: health.ok,
        backendUrl: settings.backendUrl,
        activeResume,
      };
    }

    case 'GET_SETTINGS': {
      return { ok: true, settings };
    }

    case 'SAVE_SETTINGS': {
      await saveSettings(message.settings);
      const health = await checkBackendHealth(message.settings.backendUrl);
      return { ok: true, backendConnected: health.ok };
    }

    case 'TEST_CONNECTION': {
      const url = message.url || settings.backendUrl;
      const health = await checkBackendHealth(url);
      return health;
    }

    case 'LOGIN': {
      const { token, user } = await loginToBackend(
        settings.backendUrl,
        message.email,
        message.password
      );
      await setToken(token);
      await setUser(user);
      return { ok: true, user };
    }

    case 'LOGOUT': {
      await removeToken();
      return { ok: true };
    }

    case 'ANALYZE_EPHEMERAL_JOB': {
      const token = await getToken();
      if (!token) {
        return {
          ok: false,
          error: 'NOT_LOGGED_IN',
          message: 'Please log in to Compust to analyze jobs.',
        };
      }
      const data = await analyzeEphemeralJob(settings.backendUrl, token, message.payload);
      return { ok: true, data };
    }

    case 'SAVE_JOB_ACTION': {
      const token = await getToken();
      if (!token) {
        return {
          ok: false,
          error: 'NOT_LOGGED_IN',
          message: 'Please log in to Compust to save jobs.',
        };
      }
      const data = await saveJobWithAction(
        settings.backendUrl,
        token,
        message.payload,
        message.applicationStatus,
        message.resumeSuggestions
      );
      return { ok: true, data };
    }

    case 'EXTRACT_GENERIC_JOB': {
      const token = await getToken();
      if (!token) {
        return {
          ok: false,
          error: 'NOT_LOGGED_IN',
          message: 'Please log in to Compust to extract jobs.',
        };
      }
      const data = await extractJobFromHtml(settings.backendUrl, token, message.html, message.url);
      return { ok: true, data };
    }

    case 'CAPTURE_JOB': {
      const token = await getToken();
      if (!token) {
        return {
          ok: false,
          error: 'NOT_LOGGED_IN',
          message: 'Please log in to Compust to capture jobs.',
        };
      }
      const data = await quickAddAndAnalyzeJob(settings.backendUrl, token, message.payload);
      return { ok: true, data };
    }

    case 'TRACK_APPLICATION': {
      const token = await getToken();
      if (!token) {
        return {
          ok: false,
          error: 'NOT_LOGGED_IN',
          message: 'Please log in to Compust to track applications.',
        };
      }
      const data = await trackJobApplication(
        settings.backendUrl,
        token,
        message.jobId,
        message.status
      );
      return { ok: true, data };
    }

    case 'ACTIVATE_CAPTURE_ON_TAB': {
      await activateOnTab(message.tabId);
      return { ok: true };
    }

    default:
      return { ok: false, error: 'Unknown message type' };
  }
}

// -------------------------------------------------------------
// Manual Activation: Toolbar icon click, Context Menu, Shortcuts
// -------------------------------------------------------------
async function activateOnTab(tabId?: number, url?: string) {
  if (!tabId) {
    const [activeTab] = await browserAPI.tabs.query({ active: true, currentWindow: true });
    if (!activeTab || !activeTab.id) return;
    tabId = activeTab.id;
    url = activeTab.url;
  }

  // Guard against internal browser pages
  if (url && (url.startsWith('chrome://') || url.startsWith('about:') || url.startsWith('edge://') || url.startsWith('chrome-extension://') || url.startsWith('moz-extension://'))) {
    console.log('[Compust Background] Cannot activate on internal browser page:', url);
    return;
  }

  try {
    // Check if an overlay is already injected on the tab
    const res = await browserAPI.tabs.sendMessage(tabId, { type: 'TOGGLE_CAPTURE_PANEL' });
    if (res && res.ok) {
      return;
    }
  } catch {
    // If sendMessage failed, content script was not loaded yet (generic site like Workday, Greenhouse)
    console.log('[Compust Background] Content script not detected on tab', tabId, '— injecting generic content script...');
    try {
      const scriptingApi = (browserAPI as any).scripting || (chrome as any)?.scripting;
      if (scriptingApi?.executeScript) {
        await scriptingApi.executeScript({
          target: { tabId },
          files: ['src/content/generic.js'],
        });
      }
    } catch (injErr) {
      console.warn('[Compust Background] Failed to inject generic content script:', injErr);
    }
  }
}

// 1. Toolbar action click listener
const actionApi = (browserAPI as any).action || (chrome as any)?.action;
if (actionApi?.onClicked) {
  actionApi.onClicked.addListener((tab: any) => {
    activateOnTab(tab.id, tab.url);
  });
}

// 2. Keyboard shortcut command listener
const commandsApi = (browserAPI as any).commands || (chrome as any)?.commands;
if (commandsApi?.onCommand) {
  commandsApi.onCommand.addListener((command: string) => {
    if (command === 'toggle-capture') {
      activateOnTab();
    }
  });
}

// 3. Context Menu setup & click listener
const contextMenusApi = (browserAPI as any).contextMenus || (chrome as any)?.contextMenus;
if (contextMenusApi) {
  try {
    const onInstalledApi = browserAPI.runtime?.onInstalled || (chrome as any)?.runtime?.onInstalled;
    if (onInstalledApi?.addListener) {
      onInstalledApi.addListener(() => {
        try {
          contextMenusApi.create({
            id: 'compust-capture-menu',
            title: 'Analyse Job with Compust',
            contexts: ['page', 'selection'],
          });
        } catch {
          // ignore duplicate create error
        }
      });
    } else {
      contextMenusApi.create({
        id: 'compust-capture-menu',
        title: 'Analyse Job with Compust',
        contexts: ['page', 'selection'],
      });
    }
  } catch (err) {
    console.warn('[Compust Background] Context menu init note:', err);
  }

  contextMenusApi.onClicked?.addListener((info: any, tab: any) => {
    if (info.menuItemId === 'compust-capture-menu' && tab) {
      activateOnTab(tab.id, tab.url);
    }
  });
}

