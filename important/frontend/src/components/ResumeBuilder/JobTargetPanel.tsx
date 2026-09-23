import React, { useState, useCallback } from 'react';
import {
  Target,
  Briefcase,
  Zap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  Loader2,
  Save,
  Download,
  FileText,
  Mail,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Activity,
  BookmarkPlus,
  ExternalLink,
  HelpCircle,
} from 'lucide-react';
import type {
  ExternalJobInput,
  JobTargetAnalysisResult,
  ResumeRecommendation,
  SupportedLanguage,
  ApplicationMaterial,
  MaterialType,
  ExportDocumentRequest,
  SaveTailoredFromJobTargetRequest,
} from '../../api/client';
import { api } from '../../api/client';
import { StageProgressList, useStageProgress } from '../common/StageProgressList';
import { useTranslation } from '../../i18n';
import './JobTargetPanel.css';

const IN_APP_ANALYZE_STAGES = [
  'Sending job details & requirements…',
  'Checking your active resume…',
  'Comparing skills & identifying gaps…',
  'Generating tailored suggestions & outreach…',
  'Done',
];

interface JobTargetPanelProps {
  resumeId: number;
  resumeTitle: string;
  onResumeSaved?: (newResumeId: number) => void;
  onPreviewRecommendations?: (acceptedRecs: ResumeRecommendation[]) => void;
  initialJobTarget?: { role: string; description: string; companyName: string } | null;
  onClearJobTarget?: () => void;
  onNavigateToApplications?: () => void;
}

type AnalysisStep = 'idle' | 'analyzing' | 'done' | 'error';
type ActiveTab = 'match' | 'recommendations' | 'email' | 'message' | 'letter' | 'interview';
type ExportFormat = 'pdf' | 'docx';
const LANG_LABELS: Record<SupportedLanguage, string> = {
  en: 'English',
  fr: 'Français',
  de: 'Deutsch',
  es: 'Español',
};

export const JobTargetPanel: React.FC<JobTargetPanelProps> = ({
  resumeId,
  resumeTitle,
  onResumeSaved,
  onPreviewRecommendations,
  initialJobTarget,
  onClearJobTarget,
  onNavigateToApplications,
}) => {
  const { language: globalLang } = useTranslation();
  // Input state
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [language, setLanguage] = useState<SupportedLanguage>(() => {
    return (globalLang === 'fr' ? 'fr' : 'en') as SupportedLanguage;
  });

  // Keep synced with global switcher changes unless user manually changed
  React.useEffect(() => {
    if (globalLang === 'fr' || globalLang === 'en') {
      setLanguage(globalLang as SupportedLanguage);
    }
  }, [globalLang]);
  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false);

  // Analysis state
  const [step, setStep] = useState<AnalysisStep>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobTargetAnalysisResult | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<ActiveTab>('match');
  const [acceptedRecIds, setAcceptedRecIds] = useState<Set<string>>(new Set());
  const [rejectedRecIds, setRejectedRecIds] = useState<Set<string>>(new Set());
  const [copyTitleValue, setCopyTitleValue] = useState('');
  const [savingCopy, setSavingCopy] = useState(false);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const [exportingLetter, setExportingLetter] = useState(false);
  const analyzeStage = useStageProgress(IN_APP_ANALYZE_STAGES, step === 'analyzing', 500);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('pdf');
  const [regeneratingMaterial, setRegeneratingMaterial] = useState<Record<string, boolean>>({});

  // Application tracker state
  const [trackingApp, setTrackingApp] = useState(false);
  const [trackedSuccess, setTrackedSuccess] = useState<string | null>(null);

  // Auto-fill from incoming directory target
  React.useEffect(() => {
    if (initialJobTarget) {
      if (initialJobTarget.role) setRole(initialJobTarget.role);
      if (initialJobTarget.description) setDescription(initialJobTarget.description);
      if (initialJobTarget.companyName) {
        setAdditionalInfo(initialJobTarget.companyName);
        setShowAdditionalInfo(true);
      }
      setTimeout(() => {
        const el = document.getElementById('resume-job-target-section');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 300);
      onClearJobTarget?.();
    }
  }, [initialJobTarget, onClearJobTarget]);

  const handleTrackApplication = async () => {
    if (!role.trim()) return;
    setTrackingApp(true);
    setTrackedSuccess(null);
    try {
      const summaryText = result ? [
        `Target Role: ${role.trim()}`,
        `Deterministic Score: ${result.deterministic_score.overall}/10 (Tech: ${result.deterministic_score.technical_skills}, Exp: ${result.deterministic_score.experience_alignment})`,
        result.cold_email.body ? `\n--- Cold Outreach Email ---\n${result.cold_email.body}` : '',
        result.motivation_letter.body ? `\n--- Motivation Letter ---\n${result.motivation_letter.body}` : '',
      ].filter(Boolean).join('\n') : `Job Description: ${description.slice(0, 500)}`;

      await api.createManualApplication({
        job_title: role.trim(),
        company_name: additionalInfo.trim() || 'Targeted Employer',
        status: 'preparing',
        notes: summaryText,
      });
      setTrackedSuccess(`Application for "${role.trim()}" successfully added to your Applications Tracker!`);
    } catch (err: any) {
      setTrackedSuccess(`Error tracking application: ${err.message || 'Failed'}`);
    } finally {
      setTrackingApp(false);
    }
  };

  const handleRegenerateMaterial = async (mtype: MaterialType) => {
    if (!role.trim() || description.length < 50) return;
    setRegeneratingMaterial((prev) => ({ ...prev, [mtype]: true }));
    try {
      const updated = await api.regenerateApplicationMaterial(resumeId, {
        material_type: mtype,
        target_role: role.trim(),
        job_description: description,
        additional_information: additionalInfo,
        language: language,
      });
      setResult((prev) => {
        if (!prev) return prev;
        if (mtype === 'cold_email') return { ...prev, cold_email: updated };
        if (mtype === 'short_message') return { ...prev, short_message: updated };
        if (mtype === 'motivation_letter') return { ...prev, motivation_letter: updated };
        return prev;
      });
    } catch (err: any) {
      console.error('Failed to regenerate material', err);
    } finally {
      setRegeneratingMaterial((prev) => ({ ...prev, [mtype]: false }));
    }
  };

  // Derived state
  const acceptedRecs = result?.resume_recommendations.filter(
    (r) => acceptedRecIds.has(r.id) && r.rec_type !== 'missing'
  ) ?? [];

  // ---------------------------------------------------------------------------
  // Analyze
  // ---------------------------------------------------------------------------
  const handleAnalyze = useCallback(async () => {
    if (!role.trim() || description.length < 50) return;
    setStep('analyzing');
    setError(null);
    setResult(null);
    setAcceptedRecIds(new Set());
    setRejectedRecIds(new Set());
    setCopySuccess(null);

    try {
      const input: ExternalJobInput = {
        target_role: role.trim(),
        job_description: description,
        additional_information: additionalInfo,
        language,
      };
      const res = await api.analyzeJobTarget(resumeId, input);
      setResult(res);
      setStep('done');
      setCopyTitleValue(`${role.trim()} — Tailored`);
      setActiveTab('match');
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Check your connection and try again.');
      setStep('error');
    }
  }, [role, description, additionalInfo, language, resumeId]);

  // ---------------------------------------------------------------------------
  // Accept / reject recommendations
  // ---------------------------------------------------------------------------
  const toggleAccept = (id: string) => {
    setAcceptedRecIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setRejectedRecIds((prevR) => { const nr = new Set(prevR); nr.delete(id); return nr; });
      }
      return next;
    });
  };

  const toggleReject = (id: string) => {
    setRejectedRecIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setAcceptedRecIds((prevA) => { const na = new Set(prevA); na.delete(id); return na; });
      }
      return next;
    });
  };

  // ---------------------------------------------------------------------------
  // Save tailored copy
  // ---------------------------------------------------------------------------
  const handleSaveCopy = async () => {
    if (!result || !copyTitleValue.trim()) return;
    setSavingCopy(true);
    setCopySuccess(null);
    try {
      const payload: SaveTailoredFromJobTargetRequest = {
        new_title: copyTitleValue.trim(),
        accepted_recommendation_ids: [...acceptedRecIds],
        accepted_recommendations: acceptedRecs,
      };
      const newResume = await api.saveTailoredCopyFromJobTarget(resumeId, payload);
      setCopySuccess(`Saved "${newResume.title}" — your master resume is unchanged.`);
      onResumeSaved?.(newResume.id);
    } catch (err: any) {
      setCopySuccess(`Error: ${err.message}`);
    } finally {
      setSavingCopy(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Export application material
  // ---------------------------------------------------------------------------
  const handleExportLetter = async (material: ApplicationMaterial, filename: string) => {
    if (!material.body) return;
    setExportingLetter(true);
    try {
      const req: ExportDocumentRequest = {
        content: material.body,
        file_format: exportFormat,
        suggested_filename: filename,
      };
      await api.exportMotivationLetter(resumeId, req, `${filename}.${exportFormat}`);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setExportingLetter(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Score ring
  // ---------------------------------------------------------------------------
  const ScoreRing = ({ value, label }: { value: number; label: string }) => {
    const pct = Math.round((value / 10) * 100);
    const color = pct >= 70 ? '#22c55e' : pct >= 45 ? '#f59e0b' : '#ef4444';
    return (
      <div className="jtp-score-ring" title={`${label}: ${value.toFixed(1)}/10`}>
        <svg viewBox="0 0 36 36" className="jtp-ring-svg">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#ffffff0a" strokeWidth="2.5" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="2.5"
            strokeDasharray={`${pct} 100`}
            strokeLinecap="round"
            transform="rotate(-90 18 18)"
          />
        </svg>
        <span className="jtp-ring-value" style={{ color }}>{value.toFixed(1)}</span>
        <span className="jtp-ring-label">{label}</span>
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Recommendation card
  // ---------------------------------------------------------------------------
  const RecCard = ({ rec }: { rec: ResumeRecommendation }) => {
    const accepted = acceptedRecIds.has(rec.id);
    const rejected = rejectedRecIds.has(rec.id);
    const isMissing = rec.rec_type === 'missing';

    const badgeColor = {
      emphasize: '#a78bfa', rewrite: '#60a5fa', keep: '#22c55e',
      move: '#fb923c', add: '#34d399', missing: '#f87171',
      verify: '#fbbf24', reduce: '#94a3b8', remove: '#f87171',
    }[rec.rec_type] || '#94a3b8';

    return (
      <div className={`jtp-rec-card ${accepted ? 'accepted' : ''} ${rejected ? 'rejected' : ''} ${isMissing ? 'missing' : ''}`}>
        <div className="jtp-rec-header">
          <span className="jtp-rec-badge" style={{ background: badgeColor + '22', color: badgeColor, border: `1px solid ${badgeColor}44` }}>
            {rec.rec_type.toUpperCase()}
          </span>
          <span className="jtp-rec-section">{rec.section}{rec.item_label ? ` → ${rec.item_label}` : ''}</span>
          {!isMissing && (
            <div className="jtp-rec-actions">
              <button
                id={`accept-rec-${rec.id}`}
                className={`jtp-rec-btn accept ${accepted ? 'active' : ''}`}
                onClick={() => toggleAccept(rec.id)}
                title={accepted ? 'Remove from accepted' : 'Accept this recommendation'}
              >
                <CheckCircle2 size={14} />
                {accepted ? 'Accepted' : 'Accept'}
              </button>
              <button
                id={`reject-rec-${rec.id}`}
                className={`jtp-rec-btn reject ${rejected ? 'active' : ''}`}
                onClick={() => toggleReject(rec.id)}
                title="Reject this recommendation"
              >
                <XCircle size={14} />
              </button>
            </div>
          )}
        </div>
        {rec.current_text && (
          <div className="jtp-rec-current">
            <span className="jtp-label-muted">Current:</span> {rec.current_text.slice(0, 180)}{rec.current_text.length > 180 ? '…' : ''}
          </div>
        )}
        {rec.suggested_text && !isMissing && (
          <div className="jtp-rec-suggested">
            <span className="jtp-label-muted">Suggested:</span> {rec.suggested_text.slice(0, 300)}{rec.suggested_text.length > 300 ? '…' : ''}
          </div>
        )}
        <div className="jtp-rec-reason">{rec.reason}</div>
        {!rec.grounded && (
          <div className="jtp-rec-verify-notice">
            <AlertCircle size={12} /> AI suggested content — please verify before applying
          </div>
        )}
        {rec.evidence_sources.length > 0 && (
          <div className="jtp-rec-evidence">
            {rec.evidence_sources.map((src, i) => (
              <span key={i} className="jtp-evidence-chip">{src}</span>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Application material card
  // ---------------------------------------------------------------------------
  const MaterialCard = ({
    material,
    filename,
    icon,
    onRegenerate,
    isRegenerating,
  }: {
    material: ApplicationMaterial;
    filename: string;
    icon: React.ReactNode;
    onRegenerate?: () => void;
    isRegenerating?: boolean;
  }) => {
    const [bodyText, setBodyText] = useState(material.body);
    const [subjectText, setSubjectText] = useState(material.subject);
    const [copied, setCopied] = useState(false);
    const [expanded, setExpanded] = useState(true);
    const [phInputs, setPhInputs] = useState<Record<string, string>>({});

    React.useEffect(() => {
      setBodyText(material.body);
      setSubjectText(material.subject);
      setPhInputs({});
    }, [material.body, material.subject]);

    const isModified = bodyText !== material.body || subjectText !== material.subject;

    // Detect bracketed placeholders like [RECRUITER NAME], [COMPANY], etc.
    const allPlaceholders = React.useMemo(() => {
      const phSet = new Set<string>(material.placeholders || []);
      const matches = (material.body + ' ' + (material.subject || '')).match(/\[[A-Z0-9_\s]{2,}\]/g);
      if (matches) {
        matches.forEach((m) => phSet.add(m));
      }
      return Array.from(phSet);
    }, [material.body, material.subject, material.placeholders]);

    const handleApplyPlaceholder = (placeholder: string, replacement: string) => {
      const nextInputs = { ...phInputs, [placeholder]: replacement };
      setPhInputs(nextInputs);
      let updatedBody = material.body;
      let updatedSubject = material.subject;
      for (const [ph, rep] of Object.entries(nextInputs)) {
        if (rep) {
          updatedBody = updatedBody.split(ph).join(rep);
          if (updatedSubject) {
            updatedSubject = updatedSubject.split(ph).join(rep);
          }
        }
      }
      setBodyText(updatedBody);
      setSubjectText(updatedSubject);
    };

    const handleRestore = () => {
      setBodyText(material.body);
      setSubjectText(material.subject);
      setPhInputs({});
    };

    const getFullContent = () => {
      if (subjectText) {
        return `Subject: ${subjectText}\n\n${bodyText}`;
      }
      return bodyText;
    };

    const handleCopy = () => {
      navigator.clipboard.writeText(getFullContent()).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    };

    if (!material.generated && material.error) {
      return (
        <div className="jtp-material-unavailable">
          <AlertCircle size={16} />
          <span>{material.error}</span>
          {onRegenerate && (
            <button
              className="jtp-action-pill"
              style={{ marginLeft: 'auto' }}
              onClick={onRegenerate}
              disabled={isRegenerating}
              title="Generate this material using local AI"
            >
              {isRegenerating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
              {isRegenerating ? 'Generating...' : 'Try Generating'}
            </button>
          )}
        </div>
      );
    }

    return (
      <div className="jtp-material-card">
        <div className="jtp-material-header">
          <div className="jtp-material-title-row">
            {icon}
            {isModified && <span className="jtp-modified-chip">Edited</span>}
          </div>
          <button className="jtp-collapse-btn" onClick={() => setExpanded(!expanded)} aria-label="Toggle section">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {expanded && (
          <>
            {material.subject !== undefined && (
              <div className="jtp-subject-group">
                <label className="jtp-mini-label" htmlFor={`subject-${filename}`}>Subject:</label>
                <input
                  id={`subject-${filename}`}
                  className="jtp-input jtp-subject-input"
                  value={subjectText}
                  onChange={(e) => setSubjectText(e.target.value)}
                  placeholder="Subject line..."
                />
              </div>
            )}

            {allPlaceholders.length > 0 && (
              <div className="jtp-placeholders-box">
                <div className="jtp-placeholders-header">
                  <Info size={13} />
                  <span>Detected Placeholders — Quick Fill:</span>
                </div>
                <div className="jtp-placeholder-grid">
                  {allPlaceholders.slice(0, 6).map((ph) => (
                    <div key={ph} className="jtp-placeholder-pill">
                      <span className="jtp-ph-label" title={ph}>{ph}</span>
                      <input
                        type="text"
                        className="jtp-ph-input"
                        placeholder="Replace..."
                        value={phInputs[ph] || ''}
                        onChange={(e) => handleApplyPlaceholder(ph, e.target.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="jtp-editor-area">
              <label className="jtp-mini-label" htmlFor={`body-${filename}`}>Content (Editable):</label>
              <textarea
                id={`body-${filename}`}
                className="jtp-textarea jtp-material-textarea"
                rows={12}
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                placeholder="Content..."
              />
            </div>

            <div className="jtp-material-actions">
              <div className="jtp-material-left-actions">
                <button className="jtp-action-pill" onClick={handleCopy} title="Copy to clipboard">
                  {copied ? <CheckCircle2 size={13} /> : <FileText size={13} />}
                  {copied ? 'Copied!' : 'Copy text'}
                </button>
                {isModified && (
                  <button className="jtp-action-pill secondary" onClick={handleRestore} title="Revert edits back to original AI generation">
                    Restore AI Original
                  </button>
                )}
                {onRegenerate && (
                  <button
                    className="jtp-action-pill"
                    onClick={onRegenerate}
                    disabled={isRegenerating}
                    title="Regenerate this specific material using AI"
                  >
                    {isRegenerating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                    {isRegenerating ? 'Regenerating…' : 'Regenerate'}
                  </button>
                )}
              </div>

              <div className="jtp-export-row">
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                  className="jtp-format-select"
                  aria-label="Export format"
                >
                  <option value="pdf">PDF</option>
                  <option value="docx">DOCX</option>
                </select>
                <button
                  className="jtp-action-pill export"
                  onClick={() => handleExportLetter({ ...material, body: getFullContent() }, filename)}
                  disabled={exportingLetter}
                  title={`Export as ${exportFormat.toUpperCase()}`}
                >
                  {exportingLetter ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                  Export {exportFormat.toUpperCase()}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="jtp-root">
      {/* Header */}
      <div className="jtp-header">
        <div className="jtp-header-icon">
          <Target size={18} />
        </div>
        <div>
          <h2 className="jtp-title">Job Targeting Assistant</h2>
          <p className="jtp-subtitle">Paste any job description → get AI analysis, match score & application materials</p>
        </div>
      </div>

      {/* Input Form */}
      <div className="jtp-form">
        <div className="jtp-form-row">
          <div className="jtp-field">
            <label className="jtp-label" htmlFor="jtp-role">Target Role *</label>
            <input
              id="jtp-role"
              className="jtp-input"
              placeholder="e.g. Senior Python Engineer"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              maxLength={300}
              disabled={step === 'analyzing'}
            />
          </div>
          <div className="jtp-field jtp-field-lang">
            <label className="jtp-label" htmlFor="jtp-lang">Output Language</label>
            <select
              id="jtp-lang"
              className="jtp-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
              disabled={step === 'analyzing'}
            >
              {(Object.keys(LANG_LABELS) as SupportedLanguage[]).map((l) => (
                <option key={l} value={l}>{LANG_LABELS[l]}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="jtp-field">
          <label className="jtp-label" htmlFor="jtp-desc">
            Job Description * <span className="jtp-char-count">{description.length}/12000</span>
          </label>
          <textarea
            id="jtp-desc"
            className="jtp-textarea"
            placeholder="Paste the full job description here…"
            rows={8}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={12000}
            disabled={step === 'analyzing'}
          />
        </div>

        <button
          className="jtp-toggle-info"
          type="button"
          onClick={() => setShowAdditionalInfo(!showAdditionalInfo)}
        >
          {showAdditionalInfo ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showAdditionalInfo ? 'Hide' : 'Add'} context (company, recruiter, notes…)
        </button>

        {showAdditionalInfo && (
          <div className="jtp-field">
            <textarea
              id="jtp-extra"
              className="jtp-textarea jtp-textarea-sm"
              placeholder="Optional: company name, recruiter name, job source, notes…"
              rows={3}
              value={additionalInfo}
              onChange={(e) => setAdditionalInfo(e.target.value)}
              maxLength={2000}
              disabled={step === 'analyzing'}
            />
          </div>
        )}

        <button
          id="jtp-analyze-btn"
          className="jtp-analyze-btn"
          onClick={handleAnalyze}
          disabled={step === 'analyzing' || !role.trim() || description.length < 50}
        >
          {step === 'analyzing' ? (
            <><Loader2 size={16} className="animate-spin" /> Analyzing…</>
          ) : (
            <><Zap size={16} /> Analyze for This Job</>
          )}
        </button>

        {step === 'analyzing' && (
          <div className="jtp-analyzing-progress-wrap">
            <StageProgressList
              title="Running In-App Job Targeting Analysis…"
              stages={IN_APP_ANALYZE_STAGES}
              currentStage={analyzeStage}
              className="jtp-stage-progress"
            />
          </div>
        )}

        {step === 'error' && error && (
          <div className="jtp-error-banner">
            <AlertCircle size={14} /> {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && step === 'done' && (
        <div className="jtp-results">
          {/* Status bar */}
          <div className="jtp-status-bar">
            <span className="jtp-status-role">
              <Briefcase size={13} /> {result.target_role}
            </span>
            {result.ollama_used ? (
              <span className="jtp-status-ai on"><Sparkles size={12} /> AI Active ({result.ollama_model})</span>
            ) : (
              <span className="jtp-status-ai off"><AlertCircle size={12} /> AI Offline — deterministic analysis only</span>
            )}
            {result.data_conflicts.length > 0 && (
              <span className="jtp-status-conflicts">
                <AlertCircle size={12} /> {result.data_conflicts.length} data conflict{result.data_conflicts.length > 1 ? 's' : ''} detected
              </span>
            )}
            <button
              id="jtp-track-app-btn"
              type="button"
              className="jtp-track-btn"
              onClick={handleTrackApplication}
              disabled={trackingApp}
              title="Add this vacancy to your Unified Applications Tracker"
            >
              {trackingApp ? <Loader2 size={13} className="animate-spin" /> : <BookmarkPlus size={13} />}
              <span>{trackingApp ? 'Tracking…' : 'Track Application'}</span>
            </button>
          </div>

          {trackedSuccess && (
            <div className={`jtp-tracked-notification ${trackedSuccess.startsWith('Error') ? 'error' : 'success'}`}>
              <CheckCircle2 size={15} />
              <span>{trackedSuccess}</span>
              {onNavigateToApplications && !trackedSuccess.startsWith('Error') && (
                <button
                  type="button"
                  className="jtp-link-btn"
                  onClick={onNavigateToApplications}
                >
                  View in Tracker <ExternalLink size={12} />
                </button>
              )}
            </div>
          )}

          {result.partial_failure && result.partial_failure_detail && (
            <div className="jtp-partial-warning">
              <Info size={13} /> {result.partial_failure_detail}
            </div>
          )}

          {/* Score Panel */}
          <div className="jtp-score-panel">
            <div className="jtp-overall-score">
              <span className="jtp-overall-value">{result.deterministic_score.overall.toFixed(1)}</span>
              <span className="jtp-overall-label">/ 10 Overall Match</span>
            </div>
            <div className="jtp-score-rings">
              <ScoreRing value={result.deterministic_score.technical_skills} label="Tech" />
              <ScoreRing value={result.deterministic_score.experience_alignment} label="Exp." />
              <ScoreRing value={result.deterministic_score.education} label="Edu." />
              <ScoreRing value={result.deterministic_score.languages} label="Lang." />
              <ScoreRing value={result.deterministic_score.ats_keywords} label="ATS" />
            </div>
          </div>

          {/* Tab navigation */}
          <div className="jtp-tabs" role="tablist">
            <button
              role="tab"
              id="jtp-tab-match"
              className={`jtp-tab ${activeTab === 'match' ? 'active' : ''}`}
              onClick={() => setActiveTab('match')}
            >
              <Activity size={13} />
              Match ({(result.match_analysis.strong_matches?.length ?? 0) + (result.match_analysis.partial_matches?.length ?? 0)}/{result.job_requirements.length})
            </button>
            <button
              role="tab"
              id="jtp-tab-recs"
              className={`jtp-tab ${activeTab === 'recommendations' ? 'active' : ''}`}
              onClick={() => setActiveTab('recommendations')}
            >
              <FileText size={13} />
              Recommendations ({result.resume_recommendations.filter(r => r.rec_type !== 'missing').length})
            </button>
            <button
              role="tab"
              id="jtp-tab-email"
              className={`jtp-tab ${activeTab === 'email' ? 'active' : ''}`}
              onClick={() => setActiveTab('email')}
            >
              <Mail size={13} /> Cold Email
            </button>
            <button
              role="tab"
              id="jtp-tab-msg"
              className={`jtp-tab ${activeTab === 'message' ? 'active' : ''}`}
              onClick={() => setActiveTab('message')}
            >
              <MessageSquare size={13} /> DM / Message
            </button>
            <button
              role="tab"
              id="jtp-tab-letter"
              className={`jtp-tab ${activeTab === 'letter' ? 'active' : ''}`}
              onClick={() => setActiveTab('letter')}
            >
              <FileText size={13} /> Cover Letter
            </button>
            <button
              role="tab"
              id="jtp-tab-interview"
              className={`jtp-tab ${activeTab === 'interview' ? 'active' : ''}`}
              onClick={() => setActiveTab('interview')}
            >
              <HelpCircle size={13} /> Interview Prep (STAR)
              {result.interview_prep?.questions?.length ? (
                <span className="jtp-tab-counter">{result.interview_prep.questions.length}</span>
              ) : null}
            </button>
          </div>

          {/* Tab content */}
          <div className="jtp-tab-content">
            {/* Match Analysis */}
            {activeTab === 'match' && (
              <div className="jtp-match-panel">
                {result.match_analysis.strong_matches.length > 0 && (
                  <div className="jtp-match-group">
                    <h4 className="jtp-match-group-title strong">
                      <CheckCircle2 size={14} /> Strong Matches ({result.match_analysis.strong_matches.length})
                    </h4>
                    {result.match_analysis.strong_matches.map((m, i) => (
                      <div key={i} className="jtp-match-item strong">
                        <span className="jtp-match-req">{m.requirement}</span>
                        {m.evidence_sources.map((src, j) => (
                          <span key={j} className="jtp-evidence-chip">{src}</span>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
                {result.match_analysis.partial_matches.length > 0 && (
                  <div className="jtp-match-group">
                    <h4 className="jtp-match-group-title partial">
                      <AlertCircle size={14} /> Partial Matches ({result.match_analysis.partial_matches.length})
                    </h4>
                    {result.match_analysis.partial_matches.map((m, i) => (
                      <div key={i} className="jtp-match-item partial">
                        <span className="jtp-match-req">{m.requirement}</span>
                        {m.note && <span className="jtp-match-note">{m.note}</span>}
                      </div>
                    ))}
                  </div>
                )}
                {result.match_analysis.missing_or_unconfirmed.length > 0 && (
                  <div className="jtp-match-group">
                    <h4 className="jtp-match-group-title missing">
                      <XCircle size={14} /> Not Found in Your Data ({result.match_analysis.missing_or_unconfirmed.length})
                    </h4>
                    <p className="jtp-match-disclaimer">
                      These requirements were not found in your Compust profile. Only add skills you genuinely have.
                    </p>
                    {result.match_analysis.missing_or_unconfirmed.map((m, i) => (
                      <div key={i} className="jtp-match-item missing">
                        <span className="jtp-match-req">{m.requirement}</span>
                      </div>
                    ))}
                  </div>
                )}
                {result.match_analysis.verify_items.length > 0 && (
                  <div className="jtp-match-group">
                    <h4 className="jtp-match-group-title verify">
                      <Info size={14} /> Needs Verification ({result.match_analysis.verify_items.length})
                    </h4>
                    {result.match_analysis.verify_items.map((m, i) => (
                      <div key={i} className="jtp-match-item verify">
                        <span className="jtp-match-req">{m.requirement}</span>
                        {m.note && <span className="jtp-match-note">{m.note}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Recommendations */}
            {activeTab === 'recommendations' && (
              <div className="jtp-recs-panel">
                <p className="jtp-recs-note">
                  <Info size={12} /> Accept recommendations to include in your tailored copy.
                  Rejected or unreviewed items will not be applied. <strong>Your master resume is never changed.</strong>
                </p>
                {result.resume_recommendations.filter(r => r.rec_type !== 'missing').map((rec) => (
                  <RecCard key={rec.id} rec={rec} />
                ))}
                {result.resume_recommendations.filter(r => r.rec_type === 'missing').length > 0 && (
                  <div className="jtp-missing-section">
                    <h4 className="jtp-match-group-title missing">
                      <XCircle size={14} /> Skills Not In Your Data — Do Not Auto-Add
                    </h4>
                    {result.resume_recommendations.filter(r => r.rec_type === 'missing').map((rec) => (
                      <RecCard key={rec.id} rec={rec} />
                    ))}
                  </div>
                )}

                {acceptedRecs.length > 0 && (
                  <div className="jtp-save-copy-panel">
                    <div className="jtp-save-header-row">
                      <h4 className="jtp-save-title">
                        <Save size={14} /> Save Tailored Copy ({acceptedRecs.length} change{acceptedRecs.length > 1 ? 's' : ''} accepted)
                      </h4>
                      {onPreviewRecommendations && (
                        <button
                          id="jtp-preview-draft-btn"
                          type="button"
                          className="jtp-action-pill preview-draft-btn"
                          onClick={() => onPreviewRecommendations(acceptedRecs)}
                          title="Apply accepted recommendations directly to the editor draft to see Before -> After in WYSIWYG preview"
                        >
                          <Sparkles size={13} />
                          Preview in Live Editor (Draft)
                        </button>
                      )}
                    </div>
                    <p className="jtp-save-note">Your master resume "{resumeTitle}" will remain unchanged.</p>
                    <div className="jtp-save-row">
                      <input
                        id="jtp-copy-title"
                        className="jtp-input"
                        placeholder="Title for tailored copy…"
                        value={copyTitleValue}
                        onChange={(e) => setCopyTitleValue(e.target.value)}
                      />
                      <button
                        id="jtp-save-copy-btn"
                        className="jtp-save-btn"
                        onClick={handleSaveCopy}
                        disabled={savingCopy || !copyTitleValue.trim()}
                      >
                        {savingCopy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                        Save Copy
                      </button>
                    </div>
                    {copySuccess && (
                      <div className={`jtp-copy-status ${copySuccess.startsWith('Error') ? 'error' : 'success'}`}>
                        {copySuccess.startsWith('Error') ? <AlertCircle size={13} /> : <CheckCircle2 size={13} />}
                        {copySuccess}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Cold Email */}
            {activeTab === 'email' && (
              <MaterialCard
                material={result.cold_email}
                filename="cold_email"
                icon={<><Mail size={15} /> <strong>Cold Email</strong></>}
                onRegenerate={() => handleRegenerateMaterial('cold_email')}
                isRegenerating={!!regeneratingMaterial['cold_email']}
              />
            )}

            {/* Short Message */}
            {activeTab === 'message' && (
              <MaterialCard
                material={result.short_message}
                filename="linkedin_message"
                icon={<><MessageSquare size={15} /> <strong>Short Message / DM</strong></>}
                onRegenerate={() => handleRegenerateMaterial('short_message')}
                isRegenerating={!!regeneratingMaterial['short_message']}
              />
            )}

            {/* Motivation Letter */}
            {activeTab === 'letter' && (
              <MaterialCard
                material={result.motivation_letter}
                filename="motivation_letter"
                icon={<><FileText size={15} /> <strong>Motivation Letter</strong></>}
                onRegenerate={() => handleRegenerateMaterial('motivation_letter')}
                isRegenerating={!!regeneratingMaterial['motivation_letter']}
              />
            )}

            {/* Interview Prep Tab */}
            {activeTab === 'interview' && (
              <div className="jtp-interview-panel">
                {result.interview_prep?.confidence_tip && (
                  <div className="jtp-interview-tip glass-panel">
                    <Sparkles size={18} className="jtp-tip-icon" />
                    <div>
                      <strong>Executive Coach Tip:</strong>
                      <p>{result.interview_prep.confidence_tip}</p>
                    </div>
                  </div>
                )}

                {result.interview_prep?.key_focus_areas && result.interview_prep.key_focus_areas.length > 0 && (
                  <div className="jtp-focus-areas">
                    <span className="jtp-focus-label">Key Preparation Focus Areas:</span>
                    <div className="jtp-focus-chips">
                      {result.interview_prep.key_focus_areas.map((fa, i) => (
                        <span key={i} className="jtp-focus-chip">{fa}</span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="jtp-questions-list">
                  {result.interview_prep?.questions?.map((q, i) => (
                    <div key={q.id || i} className="jtp-question-card">
                      <div className="jtp-question-header">
                        <span className={`jtp-qtype-badge ${q.question_type}`}>
                          {q.question_type === 'qualification_gap' ? 'Gap Strategy' : q.question_type.toUpperCase()}
                        </span>
                        {q.category && <span className="jtp-qcat-badge">{q.category}</span>}
                      </div>

                      <h4 className="jtp-question-text">{q.question}</h4>
                      {q.context_reason && (
                        <p className="jtp-question-context">
                          <Info size={12} /> <em>Why interviewers ask this:</em> {q.context_reason}
                        </p>
                      )}

                      {q.handling_missing_skill && (
                        <div className="jtp-gap-advice">
                          <AlertCircle size={14} />
                          <span><strong>Honest Gap Strategy:</strong> {q.handling_missing_skill}</span>
                        </div>
                      )}

                      {q.suggested_star && (q.suggested_star.situation || q.suggested_star.action) && (
                        <div className="jtp-star-framework">
                          <div className="jtp-star-header">
                            <Sparkles size={13} />
                            <span>Recommended STAR Response Framework:</span>
                          </div>
                          <div className="jtp-star-grid">
                            <div className="jtp-star-item s">
                              <span className="jtp-star-letter">S</span>
                              <div className="jtp-star-body">
                                <strong>Situation:</strong> {q.suggested_star.situation}
                              </div>
                            </div>
                            <div className="jtp-star-item t">
                              <span className="jtp-star-letter">T</span>
                              <div className="jtp-star-body">
                                <strong>Task:</strong> {q.suggested_star.task}
                              </div>
                            </div>
                            <div className="jtp-star-item a">
                              <span className="jtp-star-letter">A</span>
                              <div className="jtp-star-body">
                                <strong>Action:</strong> {q.suggested_star.action}
                              </div>
                            </div>
                            <div className="jtp-star-item r">
                              <span className="jtp-star-letter">R</span>
                              <div className="jtp-star-body">
                                <strong>Result:</strong> {q.suggested_star.result}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
