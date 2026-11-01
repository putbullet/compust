import React, { useState, useEffect, useId } from 'react';
import { Copy, Check, Loader2, Info, AlertCircle, CheckCircle2, X } from 'lucide-react';
import { api, getStoredToken, type ResumePromptResponse } from '../../api/client';
import { useTranslation } from '../../i18n';
import './CopyAsPromptControl.css';

const STORAGE_KEY_INCLUDE_CONTACT = 'compust_resume_prompt_include_contact';

export interface CopyAsPromptControlProps {
  jobId: number | string;
  jobTitle?: string;
  companyName?: string;
  variant?: 'modal' | 'card' | 'table';
  className?: string;
  onRequireAuth?: () => void;
  onNavigateToProfile?: () => void;
  children?: React.ReactNode;
}

export const CopyAsPromptControl: React.FC<CopyAsPromptControlProps> = ({
  jobId,
  jobTitle: _jobTitle,
  companyName: _companyName,
  variant = 'modal',
  className = '',
  onRequireAuth,
  onNavigateToProfile,
  children,
}) => {
  const { t } = useTranslation();
  const tooltipId = useId();

  // Remember contact details preference per user
  const [includeContact, setIncludeContact] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_INCLUDE_CONTACT);
      return stored !== null ? stored === 'true' : true;
    } catch {
      return true;
    }
  });

  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState<{
    title: string;
    body: string;
    isWarning?: boolean;
    showProfileLink?: boolean;
  } | null>(null);
  const [missingProfileWarning, setMissingProfileWarning] = useState<string | null>(null);

  // Sync preference to localStorage
  const handleToggleContact = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.checked;
    setIncludeContact(val);
    try {
      localStorage.setItem(STORAGE_KEY_INCLUDE_CONTACT, String(val));
    } catch {
      // Ignore storage errors in sandboxed contexts
    }
  };

  // Auto-dismiss toast
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => {
      setToastMessage(null);
    }, 4500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const copyToClipboard = async (text: string): Promise<boolean> => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (err) {
        console.warn('navigator.clipboard.writeText failed, falling back:', err);
      }
    }
    // Fallback using textarea execCommand
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-999999px';
      textarea.style.top = '-999999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textarea);
      return success;
    } catch (fallbackErr) {
      console.error('Fallback copy failed:', fallbackErr);
      return false;
    }
  };

  const handleCopyPrompt = async () => {
    // 1. Session / Auth check
    const token = getStoredToken() || localStorage.getItem('token');
    if (!token) {
      if (onRequireAuth) {
        onRequireAuth();
      } else {
        setToastMessage({
          title: 'Authentication Required',
          body: t.copyPrompt.authRequired,
        });
      }
      return;
    }

    setLoading(true);
    setCopied(false);

    try {
      const res: ResumePromptResponse = await api.getJobResumePrompt(jobId, includeContact);

      // Check if user has no profile data
      if (!res.has_profile) {
        setMissingProfileWarning(res.error || t.copyPrompt.missingProfileMsg);
        setLoading(false);
        return;
      }

      // Perform copy
      const copyOk = await copyToClipboard(res.prompt);

      if (copyOk) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2400);

        const sourceTitle = res.source_resume_title || 'Active Resume';
        const roles = res.counts?.roles ?? 0;
        const education = res.counts?.education ?? 0;
        const skills = res.counts?.skills ?? 0;
        const chars = res.char_count ? res.char_count.toLocaleString() : String(res.prompt.length);

        let body = t.copyPrompt.copiedToastWithResume
          .replace('{title}', sourceTitle)
          .replace('{roles}', String(roles))
          .replace('{education}', String(education))
          .replace('{skills}', String(skills))
          .replace('{chars}', chars);

        const hasExp = res.has_experience ?? (roles > 0);
        if (!hasExp) {
          body += '\n\n⚠️ ' + t.copyPrompt.noExperienceWarning;
        }

        setToastMessage({
          title: t.copyPrompt.buttonCopied,
          body,
          isWarning: !hasExp,
          showProfileLink: !hasExp,
        });
      } else {
        setToastMessage({
          title: 'Copy Failed',
          body: t.copyPrompt.copyError,
        });
      }
    } catch (err: any) {
      console.error('Error fetching tailored resume prompt:', err);
      if (err?.status === 401 || err?.message?.includes('401') || err?.message?.includes('credentials')) {
        if (onRequireAuth) {
          onRequireAuth();
        } else {
          setToastMessage({
            title: 'Authentication Required',
            body: t.copyPrompt.authRequired,
          });
        }
      } else {
        setToastMessage({
          title: 'Error',
          body: err?.message || t.copyPrompt.copyError,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className={`copy-as-prompt-container variant-${variant} ${className}`}>
        {/* Buttons Row */}
        <div className="copy-prompt-actions-row">
          <button
            type="button"
            className={`copy-as-prompt-btn ${copied ? 'copied' : ''}`}
            onClick={handleCopyPrompt}
            disabled={loading}
            aria-label={t.copyPrompt.buttonLabel}
            aria-describedby={tooltipId}
          >
            {loading ? (
              <>
                <Loader2 size={13} className="copy-icon spin" />
                <span>{t.copyPrompt.generating}</span>
              </>
            ) : copied ? (
              <>
                <Check size={13} className="copy-icon" />
                <span>{t.copyPrompt.buttonCopied}</span>
              </>
            ) : (
              <>
                <Copy size={13} className="copy-icon" />
                <span>{t.copyPrompt.buttonLabel}</span>
              </>
            )}
          </button>
          {children}
        </div>

        {/* Contact Details Toggle Pill */}
        <div className={`copy-prompt-toggle-wrap ${includeContact ? 'active' : ''}`}>
          <label className="copy-prompt-toggle-label" title={t.copyPrompt.contactNote}>
            <input
              type="checkbox"
              checked={includeContact}
              onChange={handleToggleContact}
              className="copy-prompt-checkbox"
              aria-label={t.copyPrompt.includeContact}
            />
            <span className="copy-prompt-toggle-text">{t.copyPrompt.includeContact}</span>
          </label>
          <span title={t.copyPrompt.contactNote} className="copy-prompt-info-wrap">
            <Info
              size={12}
              className="copy-prompt-info-icon"
              aria-label={t.copyPrompt.contactNote}
            />
          </span>
        </div>

        {/* Hover / Keyboard Tooltip Popover */}
        <div id={tooltipId} role="tooltip" className="copy-prompt-tooltip-popover">
          {t.copyPrompt.tooltip}
        </div>
      </div>

      {/* Floating Success / Error Toast */}
      {toastMessage && (
        <div className={`copy-prompt-floating-toast ${toastMessage.isWarning ? 'has-warning' : ''}`} role="status" aria-live="polite">
          <div className="toast-icon-wrap" style={{ color: toastMessage.isWarning ? '#f59e0b' : '#10b981' }}>
            {toastMessage.isWarning ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          </div>
          <div className="toast-content-wrap">
            <div className="toast-title">{toastMessage.title}</div>
            <div className="toast-body">{toastMessage.body}</div>
            {toastMessage.showProfileLink && onNavigateToProfile && (
              <button
                type="button"
                className="toast-action-btn"
                onClick={() => {
                  setToastMessage(null);
                  onNavigateToProfile();
                }}
              >
                {t.copyPrompt.viewProfile} &rarr;
              </button>
            )}
          </div>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setToastMessage(null)}
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Missing Profile Alert Modal */}
      {missingProfileWarning && (
        <>
          <div className="alert-dialog-backdrop" onClick={() => setMissingProfileWarning(null)} />
          <div className="copy-prompt-alert-dialog" role="alertdialog" aria-modal="true">
            <div className="alert-dialog-header">
              <AlertCircle size={22} className="alert-dialog-icon" />
              <h4 className="alert-dialog-title">{t.copyPrompt.missingProfileTitle}</h4>
            </div>
            <div className="alert-dialog-body">
              {missingProfileWarning}
            </div>
            <div className="alert-dialog-actions">
              <button
                type="button"
                className="alert-action-secondary"
                onClick={() => setMissingProfileWarning(null)}
              >
                {t.common.close}
              </button>
              {onNavigateToProfile && (
                <button
                  type="button"
                  className="alert-action-primary"
                  onClick={() => {
                    setMissingProfileWarning(null);
                    onNavigateToProfile();
                  }}
                >
                  {t.copyPrompt.uploadResumeAction}
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
};
