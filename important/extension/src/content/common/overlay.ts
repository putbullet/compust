import {
  JobPayload,
  QuickAddAndAnalyzeResult,
  EphemeralAnalyzeResult,
  ResumeEditSuggestionItem,
  JobQuickAddResult,
} from '../../lib/types';
import { browserAPI } from '../../lib/browserPolyfill';
import { scanVisaAndWorkAuthorization } from './visaAnalysis';

export interface OverlayCallbacks {
  onCapture: () => Promise<void>;
  onTrack?: (jobId: number, status: 'applied' | 'saved') => Promise<void>;
  onSaveAction?: (
    payload: JobPayload,
    action: 'untracked' | 'saved' | 'applied',
    suggestions?: ResumeEditSuggestionItem[]
  ) => Promise<any>;
  onRetry: () => void;
}

export function formatErrorMessage(error: unknown): string {
  if (error === null || error === undefined) {
    return 'An unexpected error occurred.';
  }

  if (typeof error === 'string') {
    const trimmed = error.trim();
    if (!trimmed || trimmed === '[object Object]') {
      return 'An unexpected error occurred.';
    }
    return trimmed;
  }

  if (error instanceof Error) {
    return error.message || error.name || 'An unexpected error occurred.';
  }

  if (typeof error === 'object') {
    const obj = error as Record<string, any>;

    // 1. Direct message property
    if (typeof obj.message === 'string' && obj.message.trim() && obj.message !== '[object Object]') {
      return obj.message.trim();
    }

    // 2. Direct error property
    if (typeof obj.error === 'string' && obj.error.trim() && obj.error !== '[object Object]') {
      return obj.error.trim();
    }
    if (typeof obj.error === 'object' && obj.error !== null) {
      const nested = formatErrorMessage(obj.error);
      if (nested && nested !== '[object Object]') return nested;
    }

    // 3. FastAPI detail (string or array of validation errors)
    if (typeof obj.detail === 'string' && obj.detail.trim()) {
      return obj.detail.trim();
    }
    if (Array.isArray(obj.detail) && obj.detail.length > 0) {
      const messages = obj.detail
        .map((item: any) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            return item.msg || item.message || JSON.stringify(item);
          }
          return String(item);
        })
        .filter(Boolean);
      if (messages.length > 0) {
        return messages.join(', ');
      }
    }

    // 4. HTTP status text or description
    if (typeof obj.statusText === 'string' && obj.statusText.trim()) {
      return obj.statusText.trim();
    }

    // 5. Try JSON stringifying object properties safely
    try {
      const serialized = JSON.stringify(obj);
      if (serialized && serialized !== '{}' && serialized !== '[]') {
        return serialized;
      }
    } catch {
      // Ignore circular JSON errors
    }
  }

  const str = String(error);
  return str && str !== '[object Object]' ? str : 'An unexpected error occurred.';
}

// ── DOM helpers ──────────────────────────────────────────────────────────────

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  text?: string
): HTMLElementTagNameMap[K] {
  const elem = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    elem.setAttribute(k, v);
  }
  if (text !== undefined) elem.textContent = text;
  return elem;
}

function elStyle<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  cssText: string,
  text?: string
): HTMLElementTagNameMap[K] {
  const elem = el(tag, {}, text);
  elem.style.cssText = cssText;
  return elem;
}

function clearChildren(node: Element) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

// Build a chip span — safe text only
function chip(text: string, cls: string): HTMLSpanElement {
  const s = el('span', { class: cls });
  s.textContent = text;
  return s;
}

// ── SVG helpers (static markup only — never user data) ────────────────────────

function svgNS(tag: string, attrs: Record<string, string>): Element {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

function makeSearchSvg(): SVGElement {
  const svg = svgNS('svg', { viewBox: '0 0 24 24' }) as unknown as SVGElement;
  svg.appendChild(svgNS('circle', { cx: '11', cy: '11', r: '8', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }));
  svg.appendChild(svgNS('line', { x1: '21', y1: '21', x2: '16.65', y2: '16.65', stroke: 'currentColor', 'stroke-width': '2' }));
  return svg;
}

function makeLogoSvg(): SVGElement {
  const svg = svgNS('svg', { width: '14', height: '14', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' }) as unknown as SVGElement;
  svg.appendChild(svgNS('polygon', { points: '12 2 2 7 12 12 22 7 12 2' }));
  svg.appendChild(svgNS('polyline', { points: '2 17 12 22 22 17' }));
  svg.appendChild(svgNS('polyline', { points: '2 12 12 17 22 12' }));
  return svg;
}

function makeSpinner(size = '14px', borderWidth = '2px'): HTMLDivElement {
  const d = el('div', { class: 'compust-spinner' });
  d.style.cssText = `width: ${size}; height: ${size}; border-width: ${borderWidth};`;
  return d;
}

// ── Main class ────────────────────────────────────────────────────────────────

export class CompustOverlay {
  private container: HTMLElement | null = null;
  private shadow: ShadowRoot | null = null;
  private isExpanded = false;
  private progressTimer: any = null;
  private currentGeneration = 0;
  private stages: string[] = [
    'Extracting job details…',
    'Connecting to Compust…',
    'Analyzing resume alignment & skill match…',
    'Drafting actionable resume-edit suggestions…',
    'Screening visa & work authorization…',
    'Done',
  ];

  constructor(private callbacks: OverlayCallbacks) {
    this.init();
  }

  public bumpGeneration(): number {
    this.currentGeneration++;
    console.log(`[CompustOverlay] Generation incremented to ${this.currentGeneration}`);
    return this.currentGeneration;
  }

  public getGeneration(): number {
    return this.currentGeneration;
  }

  public isCurrentGeneration(gen: number): boolean {
    return gen === this.currentGeneration;
  }

  public toggle() {
    if (this.isExpanded) {
      this.hidePanel();
    } else {
      this.callbacks.onCapture();
    }
  }

  private init() {
    if (document.getElementById('compust-capture-root')) {
      return;
    }

    const mount = () => {
      if (document.getElementById('compust-capture-root')) return;
      if (!document.body) return;

      this.container = document.createElement('div');
      this.container.id = 'compust-capture-root';
      this.shadow = this.container.attachShadow({ mode: 'open' });

      this.injectStyles();
      this.renderButton();
      document.body.appendChild(this.container);
      console.log('[Compust] CompustOverlay successfully mounted to document.body');
    };

    if (document.body) {
      mount();
    } else {
      document.addEventListener('DOMContentLoaded', () => mount(), { once: true });
      window.addEventListener('load', () => mount(), { once: true });
    }

    // Guard against SPA page transitions wiping body contents
    const observer = new MutationObserver(() => {
      if (!document.getElementById('compust-capture-root') && document.body) {
        mount();
      }
    });

    try {
      const targetNode = document.documentElement || document.body;
      if (targetNode) {
        observer.observe(targetNode, { childList: true, subtree: false });
      }
    } catch {
      // Ignore observer initialization errors in restricted contexts
    }
  }

  private injectStyles() {
    if (!this.shadow) return;
    const style = document.createElement('style');
    style.textContent = `
      :host {
        all: initial;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 14px;
        line-height: 1.4;
        color: #1e293b;
      }

      * {
        box-sizing: border-box;
      }

      .compust-fab {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 2147483647;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 50px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
        transition: transform 0.2s, box-shadow 0.2s;
        white-space: nowrap;
      }

      .compust-fab:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(99, 102, 241, 0.5);
      }

      .compust-fab svg {
        width: 16px;
        height: 16px;
        flex-shrink: 0;
      }

      .compust-panel {
        position: fixed;
        top: 0;
        right: 0;
        width: 360px;
        height: 100vh;
        background: #0f172a;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        z-index: 2147483647;
        display: flex;
        flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        overflow: hidden;
        box-shadow: -8px 0 32px rgba(0, 0, 0, 0.4);
      }

      .compust-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        background: rgba(15, 23, 42, 0.95);
        flex-shrink: 0;
      }

      .compust-brand {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.01em;
      }

      .compust-close-btn {
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        font-size: 16px;
        padding: 4px 8px;
        border-radius: 4px;
        transition: color 0.2s, background 0.2s;
      }

      .compust-close-btn:hover {
        color: #f8fafc;
        background: rgba(255, 255, 255, 0.08);
      }

      .compust-body {
        flex: 1;
        overflow-y: auto;
        padding: 0;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.1) transparent;
      }

      .compust-body::-webkit-scrollbar {
        width: 4px;
      }

      .compust-body::-webkit-scrollbar-track {
        background: transparent;
      }

      .compust-body::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.1);
        border-radius: 2px;
      }

      .compust-actions {
        padding: 12px 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.07);
        background: rgba(15, 23, 42, 0.98);
        flex-shrink: 0;
      }

      .compust-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 9px 14px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        text-align: center;
      }

      .compust-btn-primary {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
      }

      .compust-btn-primary:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
      }

      .compust-btn-secondary {
        background: rgba(255, 255, 255, 0.07);
        color: #cbd5e1;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }

      .compust-btn-secondary:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #f8fafc;
      }

      .compust-btn-ghost {
        background: transparent;
        color: #64748b;
        border: 1px solid rgba(255, 255, 255, 0.06);
      }

      .compust-btn-ghost:hover {
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.04);
      }

      .compust-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none !important;
      }

      .compust-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 100px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin: 16px 16px 0;
      }

      .compust-status-created {
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.3);
      }

      .compust-status-existing {
        background: rgba(148, 163, 184, 0.1);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.2);
      }

      .compust-status-ephemeral {
        background: rgba(245, 158, 11, 0.1);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
      }

      .compust-job-title {
        font-size: 16px;
        font-weight: 700;
        color: #f8fafc;
        margin: 10px 16px 4px;
        line-height: 1.3;
      }

      .compust-company-row {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #64748b;
        margin: 0 16px 12px;
      }

      .compust-score-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        background: rgba(99, 102, 241, 0.08);
        border-top: 1px solid rgba(99, 102, 241, 0.15);
        border-bottom: 1px solid rgba(99, 102, 241, 0.15);
      }

      .compust-score-num {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .compust-section-title {
        font-size: 11px;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 10px 16px 6px;
      }

      .compust-chips-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        padding: 0 16px 12px;
      }

      .compust-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 3px 9px;
        border-radius: 100px;
        font-size: 11px;
        font-weight: 600;
      }

      .compust-chip-demonstrated {
        background: rgba(34, 197, 94, 0.12);
        color: #86efac;
        border: 1px solid rgba(34, 197, 94, 0.2);
      }

      .compust-chip-missing {
        background: rgba(239, 68, 68, 0.1);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.2);
      }

      .compust-alert-box {
        margin: 8px 16px;
        padding: 10px 12px;
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 8px;
        color: #fca5a5;
        font-size: 12px;
        line-height: 1.5;
      }

      .compust-warning-box {
        margin: 8px 16px;
        padding: 9px 12px;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        border-radius: 8px;
        color: #fcd34d;
        font-size: 12px;
        line-height: 1.5;
      }

      .compust-success-banner {
        padding: 10px 12px;
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 8px;
        color: #86efac;
        font-size: 12px;
        font-weight: 600;
      }

      .compust-suggestion-card {
        margin: 0 16px 8px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px;
      }

      .compust-suggestion-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
      }

      .compust-badge-grounded {
        font-size: 9px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 100px;
        background: rgba(34, 197, 94, 0.15);
        color: #86efac;
        border: 1px solid rgba(34, 197, 94, 0.25);
        letter-spacing: 0.03em;
      }

      .compust-badge-ungrounded {
        font-size: 9px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 100px;
        background: rgba(245, 158, 11, 0.12);
        color: #fcd34d;
        border: 1px solid rgba(245, 158, 11, 0.25);
        letter-spacing: 0.03em;
      }

      .compust-suggestion-box {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        margin: 6px 0;
        padding: 7px 10px;
        background: rgba(99, 102, 241, 0.08);
        border-radius: 6px;
        border: 1px solid rgba(99, 102, 241, 0.15);
      }

      .compust-suggestion-text {
        flex: 1;
        font-size: 11px;
        color: #c7d2fe;
        font-style: italic;
        line-height: 1.5;
      }

      .compust-copy-btn {
        flex-shrink: 0;
        background: none;
        border: none;
        color: #6366f1;
        cursor: pointer;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 4px;
        border-radius: 3px;
        transition: color 0.2s;
      }

      .compust-copy-btn:hover {
        color: #a5b4fc;
      }

      .compust-suggestion-reason {
        font-size: 10px;
        color: #64748b;
        line-height: 1.4;
        margin-top: 3px;
      }

      .compust-bullet-list {
        list-style: disc;
        padding-left: 16px;
        margin: 4px 0 0;
        font-size: 11px;
        color: #fecaca;
      }

      .compust-spinner {
        width: 14px;
        height: 14px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-top-color: white;
        border-radius: 50%;
        animation: compust-spin 0.7s linear infinite;
        flex-shrink: 0;
      }

      @keyframes compust-spin {
        to { transform: rotate(360deg); }
      }

      .compust-stage-list {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .compust-stage-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        padding: 6px 10px;
        border-radius: 6px;
        transition: all 0.3s;
      }

      .compust-stage-completed {
        color: #4ade80;
        background: rgba(74, 222, 128, 0.05);
      }

      .compust-stage-active {
        color: #f8fafc;
        background: rgba(99, 102, 241, 0.1);
        font-weight: 600;
      }

      .compust-stage-pending {
        color: #475569;
      }

      .compust-stage-icon {
        width: 16px;
        text-align: center;
        font-size: 12px;
      }
    `;
    this.shadow.appendChild(style);
  }

  public renderButton() {
    if (!this.shadow) return;
    const existingFab = this.shadow.querySelector('.compust-fab');
    if (existingFab) existingFab.remove();

    const fab = document.createElement('button');
    fab.className = 'compust-fab';
    fab.id = 'compust-capture-trigger';
    fab.setAttribute('title', 'Analyse with Compust Career Platform');
    fab.appendChild(makeSearchSvg());
    const fabLabel = document.createElement('span');
    fabLabel.textContent = 'Analyse with Compust';
    fab.appendChild(fabLabel);
    fab.addEventListener('click', () => {
      this.callbacks.onCapture();
    });
    this.shadow.appendChild(fab);
  }

  public showLoading(generation?: number) {
    if (generation !== undefined && !this.isCurrentGeneration(generation)) {
      console.warn(`[CompustOverlay] showLoading ignored for stale generation ${generation} (current: ${this.currentGeneration})`);
      return;
    }
    this.ensurePanel();
    const body = this.shadow?.querySelector('.compust-body') as HTMLElement | null;
    const actions = this.shadow?.querySelector('.compust-actions') as HTMLElement | null;
    if (actions) clearChildren(actions);
    if (!body) return;

    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }

    let activeStage = 0;
    const renderStages = (currentStage: number) => {
      clearChildren(body);

      const wrapper = elStyle('div', 'display: flex; flex-direction: column; padding: 24px 18px; gap: 16px;');

      // Header row
      const header = elStyle('div', 'font-size: 13px; font-weight: 600; color: #f8fafc; display: flex; align-items: center; gap: 8px;');
      header.appendChild(makeSpinner('14px', '2px'));
      header.appendChild(document.createTextNode('Running Match & Guidance Analysis...'));
      wrapper.appendChild(header);

      // Stage list
      const stageList = el('div', { class: 'compust-stage-list' });
      this.stages.slice(0, 5).forEach((stage, idx) => {
        const isCompleted = idx < currentStage;
        const isActive = idx === currentStage;
        const cls = isCompleted ? 'compust-stage-item compust-stage-completed'
          : isActive ? 'compust-stage-item compust-stage-active'
          : 'compust-stage-item compust-stage-pending';

        const item = el('div', { class: cls });
        const icon = el('div', { class: 'compust-stage-icon' });
        icon.textContent = isCompleted ? '✓' : isActive ? '●' : '○';
        const label = el('div', { class: 'compust-stage-label' });
        label.textContent = stage;
        item.appendChild(icon);
        item.appendChild(label);
        stageList.appendChild(item);
      });
      wrapper.appendChild(stageList);
      body.appendChild(wrapper);
    };

    renderStages(activeStage);

    this.progressTimer = setInterval(() => {
      if (activeStage < 4) {
        activeStage++;
        renderStages(activeStage);
      }
    }, 450);
  }

  public showError(errorInput: unknown, isAuthError = false, isNetworkError = false, generation?: number) {
    if (generation !== undefined && !this.isCurrentGeneration(generation)) {
      console.warn(`[CompustOverlay] showError ignored for stale generation ${generation} (current: ${this.currentGeneration})`);
      return;
    }
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }

    this.ensurePanel();
    const body = this.shadow?.querySelector('.compust-body') as HTMLElement | null;
    const actions = this.shadow?.querySelector('.compust-actions') as HTMLElement | null;
    if (!body || !actions) return;

    const message = formatErrorMessage(errorInput);
    clearChildren(body);
    clearChildren(actions);

    if (isNetworkError || message.includes("isn't running") || message.toLowerCase().includes('failed to fetch')) {
      // Network error panel
      const box = el('div', { class: 'compust-alert-box' });
      const boxTitle = el('div', { style: 'font-weight: 600;' }, 'Backend Unreachable');
      const boxMsg = el('div', {}, "Compust isn't running — start the app and try again.");
      box.appendChild(boxTitle);
      box.appendChild(boxMsg);
      body.appendChild(box);

      const retryBtn = el('button', { class: 'compust-btn compust-btn-primary', id: 'compust-retry-btn' }, 'Retry Connection');
      retryBtn.addEventListener('click', () => this.callbacks.onRetry());
      actions.appendChild(retryBtn);

    } else if (isAuthError || message.toLowerCase().includes('log in') || message === 'NOT_LOGGED_IN') {
      // Auth error panel
      const alertBox = el('div', { class: 'compust-alert-box' });
      alertBox.style.cssText = 'background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); color: #93c5fd; margin-bottom: 12px;';
      const authTitle = el('div', { style: 'font-weight: 600;' }, 'Authentication Required');
      const authMsg = el('div', { style: 'font-size: 12px; margin-top: 2px;' }, 'Log in to your local Compust account to run match analyses and save jobs.');
      alertBox.appendChild(authTitle);
      alertBox.appendChild(authMsg);
      body.appendChild(alertBox);

      // Login form
      const form = el('form', {
        id: 'compust-inline-login-form',
        style: 'display: flex; flex-direction: column; gap: 8px;',
      });

      const errEl = el('div', {
        id: 'compust-inline-login-err',
        style: 'color: #f87171; font-size: 11px; display: none;',
      });
      form.appendChild(errEl);

      // Email field
      const emailWrap = el('div');
      const emailLabel = el('label', { style: 'display: block; font-size: 11px; color: #94a3b8; margin-bottom: 3px;' }, 'Email');
      const emailInput = el('input', {
        type: 'email',
        id: 'compust-inline-email',
        required: '',
        placeholder: 'user@compust.ma',
        style: 'width: 100%; box-sizing: border-box; padding: 7px 10px; border-radius: 6px; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; font-size: 12px;',
      });
      emailWrap.appendChild(emailLabel);
      emailWrap.appendChild(emailInput);
      form.appendChild(emailWrap);

      // Password field
      const pwWrap = el('div');
      const pwLabel = el('label', { style: 'display: block; font-size: 11px; color: #94a3b8; margin-bottom: 3px;' }, 'Password');
      const pwInput = el('input', {
        type: 'password',
        id: 'compust-inline-password',
        required: '',
        placeholder: '••••••••',
        style: 'width: 100%; box-sizing: border-box; padding: 7px 10px; border-radius: 6px; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; font-size: 12px;',
      });
      pwWrap.appendChild(pwLabel);
      pwWrap.appendChild(pwInput);
      form.appendChild(pwWrap);

      const submitBtn = el('button', {
        type: 'submit',
        class: 'compust-btn compust-btn-primary',
        id: 'compust-inline-submit-btn',
        style: 'margin-top: 4px; justify-content: center;',
      }, 'Log In & Analyse');
      form.appendChild(submitBtn);
      body.appendChild(form);

      // Dismiss button in actions
      const dismissBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-close-auth-btn' }, 'Dismiss');
      dismissBtn.addEventListener('click', () => this.hidePanel());
      actions.appendChild(dismissBtn);

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errEl.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';
        const emailVal = (body.querySelector('#compust-inline-email') as HTMLInputElement)?.value.trim();
        const passwordVal = (body.querySelector('#compust-inline-password') as HTMLInputElement)?.value;
        try {
          const res = await browserAPI.runtime.sendMessage({
            type: 'LOGIN',
            email: emailVal,
            password: passwordVal,
          });
          if (!res.ok) {
            errEl.textContent = res.error || 'Invalid credentials or server unreachable.';
            errEl.style.display = 'block';
          } else {
            this.callbacks.onCapture();
          }
        } catch (err: any) {
          errEl.textContent = err.message || 'Login failed';
          errEl.style.display = 'block';
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Log In & Analyse';
        }
      });

    } else {
      // Generic error panel
      const box = el('div', { class: 'compust-alert-box' });
      const boxTitle = el('div', { style: 'font-weight: 600;' }, 'Capture Error');
      const boxMsg = el('div');
      boxMsg.textContent = message;
      box.appendChild(boxTitle);
      box.appendChild(boxMsg);
      body.appendChild(box);

      const dismissBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-close-err-btn' }, 'Dismiss');
      dismissBtn.addEventListener('click', () => this.hidePanel());
      actions.appendChild(dismissBtn);
    }
  }

  private renderSectionSuggestions(title: string, items: ResumeEditSuggestionItem[]): DocumentFragment | null {
    if (!items || items.length === 0) return null;
    const frag = document.createDocumentFragment();

    const container = elStyle('div', 'margin-bottom: 12px;');

    // Section header
    const header = elStyle('div', 'font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; display: flex; align-items: center; gap: 4px;');
    const bullet = el('span');
    bullet.textContent = '•';
    const titleSpan = el('span');
    titleSpan.textContent = title;
    const countSpan = document.createTextNode(` (${items.length})`);
    header.appendChild(bullet);
    header.appendChild(document.createTextNode(' '));
    header.appendChild(titleSpan);
    header.appendChild(countSpan);
    container.appendChild(header);

    for (const item of items) {
      const card = el('div', { class: 'compust-suggestion-card' });

      // Card header row
      const cardHeader = el('div', { class: 'compust-suggestion-header' });
      const itemLabel = el('span', { style: 'font-weight: 600; color: #f8fafc; font-size: 12px;' });
      itemLabel.textContent = item.item_label;
      cardHeader.appendChild(itemLabel);

      const badge = item.grounded
        ? el('span', { class: 'compust-badge-grounded' }, '✓ Grounded')
        : el('span', { class: 'compust-badge-ungrounded' }, '⚠️ Verify Experience First');
      cardHeader.appendChild(badge);
      card.appendChild(cardHeader);

      // Placement
      const placement = elStyle('div', 'font-size: 11px; color: #94a3b8; margin-bottom: 4px;');
      placement.appendChild(document.createTextNode('📍 '));
      const strong = el('strong', {}, 'Placement:');
      placement.appendChild(strong);
      placement.appendChild(document.createTextNode(' ' + item.where));
      card.appendChild(placement);

      // Suggestion box with copy button
      const suggBox = el('div', { class: 'compust-suggestion-box' });
      const suggText = el('div', { class: 'compust-suggestion-text' });
      suggText.textContent = item.suggested_text;
      const copyBtn = el('button', { class: 'compust-copy-btn' }, 'Copy');
      // Store text to copy as a property (not attribute) to avoid escaping concerns
      (copyBtn as any)._copyText = item.suggested_text;
      copyBtn.addEventListener('click', async (e) => {
        const target = e.currentTarget as any;
        const textToCopy: string = target._copyText || '';
        try {
          await navigator.clipboard.writeText(textToCopy);
          const orig = target.textContent;
          target.textContent = 'Copied!';
          target.style.color = '#86efac';
          setTimeout(() => {
            target.textContent = orig;
            target.style.color = '';
          }, 2000);
        } catch {
          target.textContent = 'Error';
        }
      });
      suggBox.appendChild(suggText);
      suggBox.appendChild(copyBtn);
      card.appendChild(suggBox);

      // Reason
      const reason = el('div', { class: 'compust-suggestion-reason' });
      reason.appendChild(document.createTextNode('💡 ' + item.reason));
      card.appendChild(reason);

      container.appendChild(card);
    }

    frag.appendChild(container);
    return frag;
  }

  public showEphemeralResult(result: EphemeralAnalyzeResult, payload: JobPayload, generation?: number) {
    if (generation !== undefined && !this.isCurrentGeneration(generation)) {
      console.warn(`[CompustOverlay] showEphemeralResult ignored for stale generation ${generation} (current: ${this.currentGeneration})`);
      return;
    }
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }

    this.ensurePanel();
    const body = this.shadow?.querySelector('.compust-body') as HTMLElement | null;
    const actions = this.shadow?.querySelector('.compust-actions') as HTMLElement | null;
    if (!body || !actions) return;

    const score = result.match_score ?? null;
    const demonstrated = result.demonstrated_skills || [];
    const missing = result.missing_skills || [];
    const suggestions = result.resume_suggestions || [];

    // Group suggestions by section
    const bySection: Record<string, ResumeEditSuggestionItem[]> = {
      skills: [],
      experience: [],
      summary: [],
      projects: [],
    };
    for (const s of suggestions) {
      const sec = (s.section || 'experience').toLowerCase();
      if (bySection[sec]) {
        bySection[sec].push(s);
      } else {
        bySection.experience.push(s);
      }
    }

    const hasMissingFields = !payload.title || !payload.company;
    const visaResult = scanVisaAndWorkAuthorization(payload.description);

    clearChildren(body);

    // Status pill
    const pill = el('div', { class: 'compust-status-pill compust-status-ephemeral' });
    pill.textContent = '⚡ Analysis Preview • 0 Database Writes';
    body.appendChild(pill);

    // Job title + company
    const titleBlock = el('div');
    const jobTitle = el('h3', { class: 'compust-job-title' });
    jobTitle.textContent = result.title || payload.title || 'Untitled Position';
    titleBlock.appendChild(jobTitle);
    const companyRow = el('div', { class: 'compust-company-row' });
    const companySpan = el('span');
    companySpan.textContent = result.company || payload.company || 'Unknown Company';
    companyRow.appendChild(companySpan);
    if (payload.location) {
      const locSpan = el('span');
      locSpan.textContent = '• ' + payload.location;
      companyRow.appendChild(locSpan);
    }
    titleBlock.appendChild(companyRow);
    body.appendChild(titleBlock);

    // Missing fields warning
    if (hasMissingFields) {
      const warn = el('div', { class: 'compust-warning-box' });
      warn.textContent = '⚠️ Some posting fields were missing from the DOM. You can edit them after saving.';
      body.appendChild(warn);
    }

    // Extraction advisory message
    if (result.message) {
      const advisory = el('div', { class: 'compust-warning-box' });
      advisory.style.cssText = 'background: rgba(56, 189, 248, 0.08); border-color: rgba(56, 189, 248, 0.3); color: #7dd3fc; font-size: 12px;';
      advisory.textContent = 'ℹ️ ' + result.message;
      body.appendChild(advisory);
    }

    if (result.has_active_resume) {
      // Score card
      const scoreCard = el('div', { class: 'compust-score-card' });
      const scoreLeft = el('div');
      const scoreLabel = elStyle('div', 'font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;', 'Resume Match');
      const scoreSubLabel = elStyle('div', 'font-size: 12px; color: #cbd5e1;', 'Active Resume Alignment');
      scoreLeft.appendChild(scoreLabel);
      scoreLeft.appendChild(scoreSubLabel);
      const scoreNum = el('div', { class: 'compust-score-num' });
      scoreNum.textContent = score !== null ? `${score}%` : 'N/A';
      scoreCard.appendChild(scoreLeft);
      scoreCard.appendChild(scoreNum);
      body.appendChild(scoreCard);

      // Demonstrated skills
      const demTitle = el('div', { class: 'compust-section-title' });
      demTitle.textContent = `Demonstrated Skills (${demonstrated.length})`;
      body.appendChild(demTitle);
      const demChips = el('div', { class: 'compust-chips-wrap' });
      if (demonstrated.length > 0) {
        demonstrated.forEach((s) => demChips.appendChild(chip('✓ ' + s, 'compust-chip compust-chip-demonstrated')));
      } else {
        const none = elStyle('span', 'color: #64748b; font-size: 12px;', 'No matching skills detected');
        demChips.appendChild(none);
      }
      body.appendChild(demChips);

      // Missing skills
      const misTitle = el('div', { class: 'compust-section-title' });
      misTitle.textContent = `Missing or Weak Requirements (${missing.length})`;
      body.appendChild(misTitle);
      const misChips = el('div', { class: 'compust-chips-wrap' });
      if (missing.length > 0) {
        missing.forEach((s) => misChips.appendChild(chip('! ' + s, 'compust-chip compust-chip-missing')));
      } else {
        const none = elStyle('span', 'color: #64748b; font-size: 12px;', 'None detected');
        misChips.appendChild(none);
      }
      body.appendChild(misChips);

      // Resume suggestions
      const suggBlock = elStyle('div', 'margin-top: 10px;');
      const suggHeader = el('div', { class: 'compust-section-title' });
      suggHeader.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;';
      const suggTitle = el('span', {}, 'Actionable Resume Guidance');
      const suggCount = el('span', { style: 'font-size: 10px; color: #38bdf8; font-weight: 600;' });
      suggCount.textContent = `${suggestions.length} suggestions`;
      suggHeader.appendChild(suggTitle);
      suggHeader.appendChild(suggCount);
      suggBlock.appendChild(suggHeader);

      const secFrags: Array<DocumentFragment | null> = [
        this.renderSectionSuggestions('Skills Section', bySection.skills),
        this.renderSectionSuggestions('Work Experience Phrasing', bySection.experience),
        this.renderSectionSuggestions('Summary & Headline', bySection.summary),
        this.renderSectionSuggestions('Projects', bySection.projects),
      ];
      secFrags.forEach((f) => { if (f) suggBlock.appendChild(f); });
      body.appendChild(suggBlock);
    } else {
      // No active resume box
      const noResume = el('div', { class: 'compust-alert-box' });
      noResume.style.cssText = 'background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); color: #93c5fd;';
      const noResumeTitle = el('div', { style: 'font-weight: 600;' }, 'No Active Resume Set');
      const noResumeMsg = el('div', {}, 'Upload or activate a resume in Compust to see match scores and actionable resume edit guidance.');
      noResume.appendChild(noResumeTitle);
      noResume.appendChild(noResumeMsg);
      body.appendChild(noResume);
    }

    // Visa section
    const visaHeader = el('div', { class: 'compust-section-title' });
    visaHeader.style.cssText = 'margin-top: 14px; display: flex; align-items: center; justify-content: space-between;';
    const visaTitle = el('span', {}, 'Deep Analysis: Visa & Work Authorization');
    const visaStatus = el('span');
    visaStatus.style.cssText = `font-size: 10px; font-weight: 600; color: ${visaResult.hasRestriction ? '#f87171' : '#34d399'};`;
    visaStatus.textContent = visaResult.hasRestriction ? 'Restrictions Detected' : 'No Restrictions';
    visaHeader.appendChild(visaTitle);
    visaHeader.appendChild(visaStatus);
    body.appendChild(visaHeader);

    if (visaResult.hasRestriction) {
      const visaBox = el('div', { class: 'compust-alert-box' });
      visaBox.style.cssText = 'background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.25); color: #fca5a5;';
      const visaBoxTitle = elStyle('div', 'font-weight: 600; display: flex; align-items: center; gap: 6px;');
      visaBoxTitle.textContent = '⚠️ Work Authorization Restriction';
      visaBox.appendChild(visaBoxTitle);

      const visaChips = el('div', { class: 'compust-chips-wrap' });
      visaChips.style.marginTop = '4px';
      visaResult.restrictions.forEach((r) => {
        const c = el('span', { class: 'compust-chip compust-chip-missing' });
        c.style.fontSize = '11px';
        c.textContent = r.label;
        visaChips.appendChild(c);
      });
      visaBox.appendChild(visaChips);

      const evidenceBlock = elStyle('div', 'font-size: 11px; margin-top: 6px; color: #fecaca;');
      const evidenceLabel = el('strong', {}, 'Quoted Evidence:');
      evidenceBlock.appendChild(evidenceLabel);
      const ul = el('ul', { class: 'compust-bullet-list' });
      ul.style.marginTop = '4px';
      visaResult.triggerSentences.slice(0, 3).forEach((s) => {
        const li = el('li');
        const em = el('em');
        em.textContent = `"${s}"`;
        li.appendChild(em);
        ul.appendChild(li);
      });
      evidenceBlock.appendChild(ul);
      visaBox.appendChild(evidenceBlock);
      body.appendChild(visaBox);
    } else {
      const noVisa = el('div', { class: 'compust-warning-box' });
      noVisa.style.cssText = 'background: rgba(34, 197, 94, 0.08); border-color: rgba(34, 197, 94, 0.25); color: #86efac; font-size: 12px; display: flex; align-items: center; gap: 6px;';
      const checkSpan = el('span', {}, '✓');
      const noRestrMsg = el('span', {}, 'No restriction language detected.');
      noVisa.appendChild(checkSpan);
      noVisa.appendChild(noRestrMsg);
      body.appendChild(noVisa);
    }

    // ── Action buttons ────────────────────────────────────────────────────────
    clearChildren(actions);

    const actionsLabel = elStyle('div', 'font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;', 'Choose Action (Not yet saved)');
    actions.appendChild(actionsLabel);

    const btnGrid = elStyle('div', 'display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;');

    const addBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-action-add', title: 'Save to Opportunities directory only' });
    const addSpan = el('span', {}, '+ Add');
    const addSub = el('small', { style: 'display:block; font-size:9px; opacity:0.75; font-weight:400;' }, 'Opportunities');
    addBtn.appendChild(addSpan);
    addBtn.appendChild(addSub);

    const appliedBtn = el('button', { class: 'compust-btn compust-btn-primary', id: 'compust-action-applied', title: 'Save and mark as Applied in Kanban' });
    const appliedSpan = el('span', {}, '✓ Applied');
    const appliedSub = el('small', { style: 'display:block; font-size:9px; opacity:0.85; font-weight:400;' }, 'Mark Applied');
    appliedBtn.appendChild(appliedSpan);
    appliedBtn.appendChild(appliedSub);

    const saveBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-action-save', title: 'Save and mark as Interested in Kanban' });
    const saveSpan = el('span', {}, '★ Save');
    const saveSub = el('small', { style: 'display:block; font-size:9px; opacity:0.75; font-weight:400;' }, 'Interested');
    saveBtn.appendChild(saveSpan);
    saveBtn.appendChild(saveSub);

    btnGrid.appendChild(addBtn);
    btnGrid.appendChild(appliedBtn);
    btnGrid.appendChild(saveBtn);
    actions.appendChild(btnGrid);

    const dismissRow = elStyle('div', 'display: flex; gap: 6px; margin-top: 4px;');
    const dismissBtn = el('button', { class: 'compust-btn compust-btn-ghost', id: 'compust-action-dismiss', style: 'flex: 1; font-size: 11px; padding: 6px; color: #94a3b8;' }, '✕ Skip / Dismiss (0 Writes)');
    dismissRow.appendChild(dismissBtn);
    actions.appendChild(dismissRow);

    const handleSave = async (status: 'untracked' | 'saved' | 'applied', btn: HTMLButtonElement, label: string) => {
      btn.disabled = true;
      clearChildren(btn);
      btn.appendChild(makeSpinner('12px', '2px'));
      btn.appendChild(document.createTextNode(' Saving...'));
      try {
        if (this.callbacks.onSaveAction) {
          await this.callbacks.onSaveAction(payload, status, suggestions);
        }
        clearChildren(actions);
        const banner = el('div', { class: 'compust-success-banner' });
        banner.textContent = `✓ Job saved ${status === 'untracked' ? 'to Opportunities' : status === 'applied' ? 'and marked as Applied' : 'and marked as Interested'}!`;
        actions.appendChild(banner);

        const doneRow = elStyle('div', 'display: flex; gap: 8px; margin-top: 6px;');
        const openBtn = el('button', { class: 'compust-btn compust-btn-primary', id: 'compust-open-app-btn', style: 'flex: 1;' }, 'Open in Compust');
        const closeBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-close-done-btn', style: 'flex: 1;' }, 'Close');
        openBtn.addEventListener('click', () => browserAPI.tabs.create({ url: 'http://localhost:8000' }));
        closeBtn.addEventListener('click', () => this.hidePanel());
        doneRow.appendChild(openBtn);
        doneRow.appendChild(closeBtn);
        actions.appendChild(doneRow);
      } catch (saveErr: any) {
        btn.disabled = false;
        clearChildren(btn);
        btn.textContent = label;
        // Render error inline — avoids CSP-blocked alert() and keeps UX inside panel
        const errMsg = saveErr?.message || 'Failed to save job';
        const errBanner = el('div', { class: 'compust-alert-box' });
        errBanner.style.cssText = 'font-size: 12px; margin-top: 6px; padding: 8px 10px;';
        errBanner.textContent = `⚠ Save failed: ${errMsg}`;
        actions.appendChild(errBanner);
        setTimeout(() => errBanner.remove(), 5000);
      }
    };

    addBtn.addEventListener('click', () => handleSave('untracked', addBtn, '+ Add'));
    appliedBtn.addEventListener('click', () => handleSave('applied', appliedBtn, '✓ Applied'));
    saveBtn.addEventListener('click', () => handleSave('saved', saveBtn, '★ Save'));
    dismissBtn.addEventListener('click', () => this.hidePanel());
  }

  public showResult(result: QuickAddAndAnalyzeResult, payload: JobPayload) {
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }

    this.ensurePanel();
    const body = this.shadow?.querySelector('.compust-body') as HTMLElement | null;
    const actions = this.shadow?.querySelector('.compust-actions') as HTMLElement | null;
    if (!body || !actions) return;

    const isDuplicate = result.is_duplicate;
    const score = result.score_breakdown?.overall_score ?? null;
    const demonstrated = result.match_analysis?.already_demonstrated || [];
    const missing = result.match_analysis?.missing_or_weak || [];

    const hasMissingFields = !payload.title || !payload.company || !payload.description;
    const visaResult = scanVisaAndWorkAuthorization(payload.description);

    clearChildren(body);

    // Status pill
    const pill = el('div', { class: `compust-status-pill ${isDuplicate ? 'compust-status-existing' : 'compust-status-created'}` });
    pill.textContent = isDuplicate ? 'Previously Analyzed • In Directory' : 'Analysis Complete • Stored in Directory';
    body.appendChild(pill);

    // Title + company
    const titleBlock = el('div');
    const jobTitle = el('h3', { class: 'compust-job-title' });
    jobTitle.textContent = result.job.title || payload.title || 'Untitled Position';
    titleBlock.appendChild(jobTitle);
    const companyRow = el('div', { class: 'compust-company-row' });
    const companySpan = el('span');
    companySpan.textContent = result.job.company || payload.company || 'Unknown Company';
    companyRow.appendChild(companySpan);
    if (payload.location) {
      const locSpan = el('span');
      locSpan.textContent = '• ' + payload.location;
      companyRow.appendChild(locSpan);
    }
    titleBlock.appendChild(companyRow);
    body.appendChild(titleBlock);

    if (hasMissingFields) {
      const warn = el('div', { class: 'compust-warning-box' });
      warn.textContent = '⚠️ Some posting fields were missing from the DOM. You may edit them in Compust.';
      body.appendChild(warn);
    }

    if (result.has_active_resume) {
      // Score card
      const scoreCard = el('div', { class: 'compust-score-card' });
      const scoreLeft = el('div');
      const scoreLabel = elStyle('div', 'font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;', 'Resume Match');
      const scoreSubLabel = elStyle('div', 'font-size: 12px; color: #cbd5e1;', 'Active Resume Alignment');
      scoreLeft.appendChild(scoreLabel);
      scoreLeft.appendChild(scoreSubLabel);
      const scoreNum = el('div', { class: 'compust-score-num' });
      scoreNum.textContent = score !== null ? `${score}%` : 'N/A';
      scoreCard.appendChild(scoreLeft);
      scoreCard.appendChild(scoreNum);
      body.appendChild(scoreCard);

      // Demonstrated
      const demTitle = el('div', { class: 'compust-section-title' });
      demTitle.textContent = `Demonstrated Skills (${demonstrated.length})`;
      body.appendChild(demTitle);
      const demChips = el('div', { class: 'compust-chips-wrap' });
      if (demonstrated.length > 0) {
        demonstrated.forEach((s) => demChips.appendChild(chip('✓ ' + s, 'compust-chip compust-chip-demonstrated')));
      } else {
        demChips.appendChild(elStyle('span', 'color: #64748b; font-size: 12px;', 'No matching skills found'));
      }
      body.appendChild(demChips);

      // Missing
      const misTitle = el('div', { class: 'compust-section-title' });
      misTitle.textContent = `Missing or Weak Requirements (${missing.length})`;
      body.appendChild(misTitle);
      const misChips = el('div', { class: 'compust-chips-wrap' });
      if (missing.length > 0) {
        missing.forEach((s) => misChips.appendChild(chip('! ' + s, 'compust-chip compust-chip-missing')));
      } else {
        misChips.appendChild(elStyle('span', 'color: #64748b; font-size: 12px;', 'None detected'));
      }
      body.appendChild(misChips);
    } else {
      const noResume = el('div', { class: 'compust-alert-box' });
      noResume.style.cssText = 'background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); color: #93c5fd;';
      const t = el('div', { style: 'font-weight: 600;' }, 'No Active Resume');
      const m = el('div', {}, 'Job stored in directory. Set an active resume in Compust to see automatic gap analysis and match scores.');
      noResume.appendChild(t);
      noResume.appendChild(m);
      body.appendChild(noResume);
    }

    clearChildren(actions);
    const actRow = elStyle('div', 'display: flex; gap: 8px;');
    const openBtn = el('button', { class: 'compust-btn compust-btn-primary', id: 'compust-open-app', style: 'flex: 1;' }, 'Open in Compust');
    const closeBtn = el('button', { class: 'compust-btn compust-btn-secondary', id: 'compust-dismiss-btn', style: 'flex: 1;' }, 'Dismiss');
    openBtn.addEventListener('click', () => browserAPI.tabs.create({ url: 'http://localhost:8000' }));
    closeBtn.addEventListener('click', () => this.hidePanel());
    actRow.appendChild(openBtn);
    actRow.appendChild(closeBtn);
    actions.appendChild(actRow);
  }

  private ensurePanel() {
    if (!this.shadow) return;
    this.isExpanded = true;
    let panel = this.shadow.querySelector('.compust-panel') as HTMLElement | null;
    if (!panel) {
      panel = el('div', { class: 'compust-panel' });

      // Header
      const header = el('div', { class: 'compust-header' });
      const brand = el('div', { class: 'compust-brand' });
      brand.appendChild(makeLogoSvg());
      brand.appendChild(document.createTextNode('Compust Capture'));
      const closeBtn = el('button', { class: 'compust-close-btn', id: 'compust-panel-close' }, '✕');
      closeBtn.addEventListener('click', () => this.hidePanel());
      header.appendChild(brand);
      header.appendChild(closeBtn);

      const bodyDiv = el('div', { class: 'compust-body' });
      const actionsDiv = el('div', { class: 'compust-actions' });

      panel.appendChild(header);
      panel.appendChild(bodyDiv);
      panel.appendChild(actionsDiv);

      this.shadow.appendChild(panel);
    }
  }

  public hidePanel() {
    this.isExpanded = false;
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }
    const panel = this.shadow?.querySelector('.compust-panel');
    if (panel) panel.remove();
  }

  private escapeHtml(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}
