import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  X,
  ExternalLink,
  MapPin,
  Building2,
  Calendar,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Globe,
  ShieldCheck,
  Loader2,
  FileSearch,
  CheckCheck,
  Check,
  FileText,
  Download,
  Wand2,
  Copy,
  RefreshCw,
} from 'lucide-react';
import {
  api,
  type JobDetail,
  type JobTranslationItem,
  type ResumeSuggestion,
  type CustomizedResumeItem,
  type ResumeEditSuggestionItem,
} from '../api/client';
import { ResumeTailorDrawer } from './ResumeBuilder/ResumeTailorDrawer';
import { StageProgressList, useStageProgress } from './common/StageProgressList';

const RESUME_SUGGESTION_STAGES = [
  'Reading target job requirements…',
  'Checking active resume…',
  'Analyzing skill alignment & ATS formatting…',
  'Generating tailored suggestions…',
  'Done',
];

interface JobDetailModalProps {
  job: JobDetail | null;
  companyName: string;
  onClose: () => void;
  isAppliedInitially?: boolean;
  onApplicationStatusChanged?: (jobId: number, status: string) => void;
  onTargetJob?: (jobData: { role: string; description: string; companyName: string }) => void;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  companyName,
  onClose,
  isAppliedInitially = false,
  onApplicationStatusChanged,
  onTargetJob,
}) => {
  const [translations, setTranslations] = useState<JobTranslationItem[]>([]);
  const [selectedLang, setSelectedLang] = useState<string>('original');
  const [loadingTranslation, setLoadingTranslation] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Resume suggestions state
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<ResumeSuggestion | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const suggestionStage = useStageProgress(RESUME_SUGGESTION_STAGES, loadingSuggestions, 450);

  // Resume customization state
  const [customizedResume, setCustomizedResume] = useState<CustomizedResumeItem | null>(null);
  const [recreationError, setRecreationError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'docx' | null>(null);
  const [showTailorDrawer, setShowTailorDrawer] = useState(false);

  // Feature 2: Attached Actionable Resume Edit Guidance
  const [attachedSuggestions, setAttachedSuggestions] = useState<ResumeEditSuggestionItem[]>([]);
  const [refreshingAttached, setRefreshingAttached] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [attachedError, setAttachedError] = useState<string | null>(null);

  useEffect(() => {
    if (!job) return;
    const raw = job.resume_suggestions;
    const list = Array.isArray(raw) ? raw : (Array.isArray(raw?.suggestions) ? raw.suggestions : []);
    setAttachedSuggestions(list);
    setAttachedError(null);
  }, [job]);

  const handleRefreshAttached = async () => {
    if (!job || refreshingAttached) return;
    try {
      setRefreshingAttached(true);
      setAttachedError(null);
      const updatedJob = await api.refreshJobResumeSuggestions(job.id);
      const raw = updatedJob.resume_suggestions;
      const list = Array.isArray(raw) ? raw : (Array.isArray(raw?.suggestions) ? raw.suggestions : []);
      setAttachedSuggestions(list);
    } catch (err: any) {
      setAttachedError(err.message || 'Failed to refresh resume suggestions.');
    } finally {
      setRefreshingAttached(false);
    }
  };

  const handleCopySuggestion = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 1600);
  };

  const sectionsGrouped = React.useMemo(() => {
    const groups: { [key: string]: ResumeEditSuggestionItem[] } = {
      Skills: [],
      Experience: [],
      Summary: [],
    };
    const other: ResumeEditSuggestionItem[] = [];

    attachedSuggestions.forEach((item) => {
      const sec = (item.section || '').trim();
      if (/skill/i.test(sec)) groups.Skills.push(item);
      else if (/exp|work|employ/i.test(sec)) groups.Experience.push(item);
      else if (/summary|profile|objective/i.test(sec)) groups.Summary.push(item);
      else other.push(item);
    });

    if (other.length > 0) {
      groups.Other = other;
    }
    return groups;
  }, [attachedSuggestions]);

  const handleDownloadCustomizedResume = async (format: 'pdf' | 'docx') => {
    if (!customizedResume || downloadingFormat) return;
    setDownloadingFormat(format);
    try {
      const defaultName = format === 'pdf'
        ? (customizedResume.pdf_filename || `resume_${customizedResume.id}.pdf`)
        : (customizedResume.docx_filename || `resume_${customizedResume.id}.docx`);
      await api.downloadCustomizedResume(customizedResume.id, format, defaultName);
    } catch (err: any) {
      alert(err.message || 'Failed to download customized resume');
    } finally {
      setTimeout(() => setDownloadingFormat(null), 1200);
    }
  };

  // Application tracking state
  const [isApplied, setIsApplied] = useState(isAppliedInitially);
  const [markingApplied, setMarkingApplied] = useState(false);

  useEffect(() => {
    if (!job) return;
    setSelectedLang('original');
    setErrorMsg(null);
    setShowSuggestions(false);
    setCustomizedResume(null);
    setRecreationError(null);
    setSuggestions(null);
    setSuggestionError(null);
    setIsApplied(isAppliedInitially);

    api.getJobTranslations(job.id)
      .then((items) => setTranslations(items))
      .catch(() => setTranslations([]));
  }, [job, isAppliedInitially]);

  const handleMarkAsApplied = async () => {
    if (!job || isApplied || markingApplied) return;
    try {
      setMarkingApplied(true);
      await api.trackApplication(job.id, {
        status: 'applied',
        notes: 'Applied via official company portal',
      });
      setIsApplied(true);
      if (onApplicationStatusChanged) {
        onApplicationStatusChanged(job.id, 'applied');
      }
    } catch (err) {
      console.error('Failed to mark as applied:', err);
    } finally {
      setMarkingApplied(false);
    }
  };

  const handleFetchResumeSuggestions = async () => {
    if (!job) return;
    setShowSuggestions(true);
    if (suggestions) return; // already fetched

    try {
      setLoadingSuggestions(true);
      setSuggestionError(null);
      const data = await api.getResumeSuggestions(job.id);
      setSuggestions(data);
    } catch (err: any) {
      setSuggestionError(
        err.message || 'Unable to generate resume suggestions. Please ensure you have uploaded a resume in your profile.'
      );
    } finally {
      setLoadingSuggestions(false);
    }
  };


  if (!job) return null;

  const handleSelectLanguage = async (lang: string) => {
    setSelectedLang(lang);
    setErrorMsg(null);

    if (lang === 'original') return;

    const existing = translations.find((t) => t.language.toLowerCase() === lang.toLowerCase());
    if (existing) return;

    // Request on-demand auto-translation
    setLoadingTranslation(true);
    try {
      const generated = await api.requestJobTranslation(job.id, { language: lang });
      setTranslations((prev) => [...prev.filter((p) => p.language !== lang), generated]);
    } catch (err: any) {
      setErrorMsg('Translation could not be loaded at this moment.');
    } finally {
      setLoadingTranslation(false);
    }
  };

  const currentTranslation = selectedLang !== 'original'
    ? translations.find((t) => t.language.toLowerCase() === selectedLang.toLowerCase())
    : null;

  const displayTitle = currentTranslation?.title || job.title;
  const displayDescription = currentTranslation?.description !== undefined
    ? currentTranslation?.description
    : job.description;

  return (
    <StyledModalBackdrop onClick={onClose}>
      <div className="modal-container glass-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="title-block">
            <div className="company-line">
              <Building2 size={18} className="icon" />
              <span className="company">{companyName}</span>
              {job.location && (
                <>
                  <span className="dot">•</span>
                  <MapPin size={16} className="icon" />
                  <span>{job.location}</span>
                </>
              )}
            </div>
            <h2 className="job-title">{displayTitle}</h2>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Translation Bar */}
        <div className="translation-bar">
          <div className="lang-switcher">
            <Globe size={15} className="lang-icon" />
            <span className="lang-label">View Language:</span>
            <div className="pill-group">
              <button
                className={`pill-btn ${selectedLang === 'original' ? 'active' : ''}`}
                onClick={() => handleSelectLanguage('original')}
              >
                Original (Employer)
              </button>
              <button
                className={`pill-btn ${selectedLang === 'en' ? 'active' : ''}`}
                onClick={() => handleSelectLanguage('en')}
                disabled={loadingTranslation}
              >
                {loadingTranslation && selectedLang === 'en' ? (
                  <Loader2 size={12} className="spin" />
                ) : null}
                English
              </button>
              <button
                className={`pill-btn ${selectedLang === 'fr' ? 'active' : ''}`}
                onClick={() => handleSelectLanguage('fr')}
                disabled={loadingTranslation}
              >
                {loadingTranslation && selectedLang === 'fr' ? (
                  <Loader2 size={12} className="spin" />
                ) : null}
                Français
              </button>
            </div>
          </div>

          <div className="truth-badge">
            <ShieldCheck size={14} className="shield-icon" />
            <span>Employer source text preserved unmodified</span>
          </div>
        </div>

        {errorMsg && (
          <div className="translation-error">
            <AlertCircle size={14} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Content Body */}
        <div className="modal-body">
          {/* Match Score Banner */}
          {job.match_score !== undefined && job.match_score !== null && (
            <div className="match-panel">
              <div className="match-score-header">
                <div className="score-badge">
                  <Sparkles size={16} />
                  <span>{job.match_score}% Match</span>
                </div>
                <span className="score-desc">Calculated against your career profile and skills</span>
              </div>

              {job.category_scores && Object.keys(job.category_scores).length > 0 && (
                <div className="category-scores-grid">
                  {Object.entries(job.category_scores).map(([category, score]) => (
                    <div key={category} className="cat-score-item">
                      <div className="cat-score-label">
                        <span className="cat-name">{category.charAt(0).toUpperCase() + category.slice(1)}</span>
                        <span className="cat-val">{score}%</span>
                      </div>
                      <div className="cat-progress-bar">
                        <div
                          className={`cat-progress-fill ${
                            score >= 75 ? 'high' : score >= 50 ? 'med' : 'low'
                          }`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {job.positive_factors && job.positive_factors.length > 0 && (
                <div className="factors-group positive">
                  {job.positive_factors.map((f, i) => (
                    <div key={i} className="factor-item">
                      <CheckCircle2 size={14} className="factor-icon" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              )}

              {job.missing_factors && job.missing_factors.length > 0 && (
                <div className="factors-group missing">
                  {job.missing_factors.map((f, i) => (
                    <div key={i} className="factor-item">
                      <AlertCircle size={14} className="factor-icon" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Metadata Row */}
          <div className="meta-grid">
            {job.employment_type && (
              <div className="meta-item">
                <span className="label">Contract</span>
                <span className="val">{job.employment_type}</span>
              </div>
            )}
            {job.remote_type && (
              <div className="meta-item">
                <span className="label">Work Mode</span>
                <span className="val">{job.remote_type}</span>
              </div>
            )}
            {job.department && (
              <div className="meta-item">
                <span className="label">Department</span>
                <span className="val">{job.department}</span>
              </div>
            )}
            {job.posted_at && (
              <div className="meta-item">
                <span className="label">Posted Date</span>
                <span className="val">
                  <Calendar size={13} style={{ display: 'inline', marginRight: '4px' }} />
                  {new Date(job.posted_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>

          {/* Required Skills */}
          {job.skills && job.skills.length > 0 && (
            <div className="skills-section">
              <h4 className="section-title">Required / Detected Skills</h4>
              <div className="skills-chips">
                {job.skills.map((skill, idx) => (
                  <span key={idx} className="skill-chip">{skill}</span>
                ))}
              </div>
            </div>
          )}

          {/* Full Job Description */}
          <div className="description-section">
            <div className="description-header">
              <h4 className="section-title">Job Description</h4>
              {selectedLang !== 'original' && (
                <span className="translation-indicator">
                  Translated view ({selectedLang.toUpperCase()})
                </span>
              )}
            </div>
            {displayDescription ? (
              <div
                className="description-content"
                dangerouslySetInnerHTML={{ __html: displayDescription }}
              />
            ) : (
              <p className="no-desc">No detailed description was provided by the job source.</p>
            )}
          </div>

          {/* AI Resume & Career Assistant Banner */}
          <div className="studio-tailor-banner active" style={{ borderColor: 'var(--accent, #6366f1)', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.05) 100%)' }}>
            <div className="studio-tailor-info">
              <Sparkles size={20} className="studio-tailor-icon" style={{ color: '#818cf8' }} />
              <div>
                <div className="banner-title-row">
                  <h4>Local AI Career Assistant — Target this Vacancy</h4>
                  <span className="coming-soon-badge" style={{ background: '#10b981', color: '#fff' }}>Active</span>
                </div>
                <p>Run 5-stage career analysis with local AI: match scoring, bullet tailoring, cover letter, cold outreach, and STAR interview prep.</p>
              </div>
            </div>
            <button
              type="button"
              className="studio-tailor-btn"
              style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)', color: '#fff', cursor: 'pointer' }}
              onClick={() => {
                if (job && onTargetJob) {
                  onTargetJob({
                    role: job.title,
                    description: job.description || '',
                    companyName: companyName,
                  });
                }
              }}
              title="Open in Career Assistant"
            >
              <Sparkles size={15} />
              <span>Target in Career Assistant</span>
            </button>
          </div>

          {/* Feature 2: Attached Actionable Resume Guidance */}
          <div className="attached-guidance-panel">
            <div className="guidance-panel-header">
              <div className="guidance-header-left">
                <Sparkles size={18} className="guidance-icon" />
                <div>
                  <h4 className="guidance-title">Actionable Resume Edit Guidance</h4>
                  <p className="guidance-subtitle">
                    Section-grouped edits tailored for this vacancy. Missing skills flagged for verification.
                  </p>
                </div>
              </div>
              <div className="guidance-header-right">
                {attachedSuggestions.length > 0 && (
                  <span className="guidance-count-pill">
                    {attachedSuggestions.length} suggestions
                  </span>
                )}
                <button
                  type="button"
                  className="refresh-guidance-btn"
                  onClick={handleRefreshAttached}
                  disabled={refreshingAttached}
                  title="Recalculate suggestions against your active resume"
                >
                  <RefreshCw size={13} className={refreshingAttached ? 'spin' : ''} />
                  <span>{refreshingAttached ? 'Refreshing…' : 'Refresh Guidance'}</span>
                </button>
              </div>
            </div>

            {attachedError && (
              <div className="guidance-error">
                <AlertCircle size={14} />
                <span>{attachedError}</span>
              </div>
            )}

            {attachedSuggestions.length === 0 ? (
              <div className="guidance-empty">
                <p>No resume edit guidance attached to this job record yet.</p>
                <button
                  type="button"
                  className="generate-guidance-btn"
                  onClick={handleRefreshAttached}
                  disabled={refreshingAttached}
                >
                  {refreshingAttached ? <Loader2 size={13} className="spin" /> : <Sparkles size={13} />}
                  <span>{refreshingAttached ? 'Generating suggestions…' : 'Generate Suggestions Now'}</span>
                </button>
              </div>
            ) : (
              <div className="guidance-sections-list">
                {Object.entries(sectionsGrouped).map(([sectionName, items]) => {
                  if (!items || items.length === 0) return null;
                  return (
                    <div key={sectionName} className="guidance-section-block">
                      <h5 className="section-group-heading">
                        <span>{sectionName}</span>
                        <span className="section-count">({items.length})</span>
                      </h5>
                      <div className="guidance-cards-grid">
                        {items.map((item, idx) => {
                          const globalIdx = idx + sectionName.charCodeAt(0) * 100;
                          return (
                            <div key={idx} className={`guidance-card ${!item.grounded ? 'unverified' : 'grounded'}`}>
                              <div className="card-top-bar">
                                <div className="location-tag">
                                  <span>{item.target_location || item.section}</span>
                                </div>
                                <div className="grounding-status">
                                  {item.grounded ? (
                                    <span className="badge-grounded">
                                      <CheckCircle2 size={11} />
                                      Grounded in Profile
                                    </span>
                                  ) : (
                                    <span className="badge-unverified" title="Missing from your profile. Add only if you have genuine experience.">
                                      <AlertCircle size={11} />
                                      ⚠️ Verify Experience First
                                    </span>
                                  )}
                                </div>
                              </div>

                              <p className="guidance-rationale">{item.rationale}</p>

                              {(!item.grounded || item.warning) && (
                                <div className="unverified-warning-banner">
                                  <AlertCircle size={12} className="warning-icon" />
                                  <span>{item.warning || 'Add this only if you actually have this experience — never invent qualifications.'}</span>
                                </div>
                              )}

                              {item.original_text && (
                                <div className="original-box">
                                  <span className="orig-label">Original:</span>
                                  <span className="orig-val">{item.original_text}</span>
                                </div>
                              )}

                              <div className="suggested-box">
                                <div className="suggested-text">{item.suggested_text}</div>
                                <button
                                  type="button"
                                  className="copy-suggestion-btn"
                                  onClick={() => handleCopySuggestion(item.suggested_text, globalIdx)}
                                  title="Copy to clipboard"
                                >
                                  {copiedIndex === globalIdx ? (
                                    <>
                                      <Check size={12} />
                                      <span>Copied</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy size={12} />
                                      <span>Copy</span>
                                    </>
                                  )}
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Phase 20: Resume Customization Panel */}
          {showSuggestions && (
            <div className="resume-customization-panel">
              <div className="panel-header">
                <div className="panel-title-row">
                  <FileSearch size={18} className="panel-icon" />
                  <span className="panel-title">Resume Customization & Gap Analysis</span>
                </div>
                {suggestions && (
                  <span className={`req-badge ${suggestions.requirements_status === 'COMPLETE' ? 'complete' : 'incomplete'}`}>
                    Requirements: {suggestions.requirements_status}
                  </span>
                )}
              </div>

              {loadingSuggestions ? (
                <StageProgressList
                  title="Analyzing Vacancy Requirements Against Your Resume…"
                  stages={RESUME_SUGGESTION_STAGES}
                  currentStage={suggestionStage}
                  className="modal-stage-progress"
                />
              ) : suggestionError ? (
                <div className="suggestions-error">
                  <AlertCircle size={16} />
                  <span>{suggestionError}</span>
                </div>
              ) : suggestions ? (
                <div className="suggestions-content">
                  {/* Already Demonstrated */}
                  <div className="factor-box demonstrated">
                    <div className="box-title">
                      <CheckCircle2 size={14} />
                      <span>Already Demonstrated in Resume ({suggestions.already_demonstrated.length})</span>
                    </div>
                    <div className="tags-row">
                      {suggestions.already_demonstrated.length > 0 ? (
                        suggestions.already_demonstrated.map((s, idx) => (
                          <span key={idx} className="match-tag demonstrated">{s}</span>
                        ))
                      ) : (
                        <span className="none-text">No direct skills matched yet.</span>
                      )}
                    </div>
                  </div>

                  {/* Missing or Weak Requirements */}
                  <div className="factor-box missing">
                    <div className="box-title">
                      <AlertCircle size={14} />
                      <span>Missing or Weakly Highlighted ({suggestions.missing_or_weak.length})</span>
                    </div>
                    <div className="tags-row">
                      {suggestions.missing_or_weak.length > 0 ? (
                        suggestions.missing_or_weak.map((s, idx) => (
                          <span key={idx} className="match-tag missing">{s}</span>
                        ))
                      ) : (
                        <span className="none-text">All extracted skills are demonstrated!</span>
                      )}
                    </div>
                  </div>

                  {/* Actionable Suggestions */}
                  <div className="actionable-suggestions">
                    <div className="box-title">
                      <Sparkles size={14} />
                      <span>Actionable Advice & Recommendations</span>
                    </div>
                    <ul className="advice-list">
                      {suggestions.suggestions.map((sug, idx) => (
                        <li key={idx}>{sug}</li>
                      ))}
                    </ul>
                  </div>

                  {/* ATS Formatting Improvements */}
                  {suggestions.ats_improvements && suggestions.ats_improvements.length > 0 && (
                    <div className="factor-box ats-box">
                      <div className="box-title">
                        <FileText size={14} />
                        <span>ATS Compatibility Improvements</span>
                      </div>
                      <ul className="advice-list">
                        {suggestions.ats_improvements.map((imp, idx) => (
                          <li key={idx}>{imp}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Detailed Section Recommendations */}
                  {suggestions.actionable_recommendations && suggestions.actionable_recommendations.length > 0 && (
                    <div className="detailed-recs">
                      <div className="box-title">
                        <Wand2 size={14} />
                        <span>Targeted Section Enhancements ({suggestions.actionable_recommendations.length})</span>
                      </div>
                      <div className="rec-cards-list">
                        {suggestions.actionable_recommendations.map((rec, idx) => (
                          <div key={idx} className="rec-card">
                            <div className="rec-header">
                              <span className="rec-req">{rec.requirement}</span>
                              <span className="rec-loc">{rec.location}</span>
                            </div>
                            <p className="rec-weak">{rec.weakness}</p>
                            <p className="rec-act"><strong>Suggested action:</strong> {rec.suggested_action}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recreated Resume Ready Drawer */}
                  {customizedResume && (
                    <div className="customized-ready-box">
                      <div className="ready-header">
                        <CheckCircle2 size={18} className="ready-icon" />
                        <div>
                          <h4 className="ready-title">Job-Specific Customized Resume Ready</h4>
                          <span className="ready-sub">Version {customizedResume.version} • Validated structure & layout</span>
                        </div>
                      </div>
                      <div className="download-buttons">
                        <button
                          type="button"
                          disabled={downloadingFormat !== null}
                          onClick={() => handleDownloadCustomizedResume('pdf')}
                          className={`download-btn pdf-btn ${downloadingFormat === 'pdf' ? 'loading' : ''}`}
                        >
                          {downloadingFormat === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                          <span>{downloadingFormat === 'pdf' ? 'Downloading...' : 'Download PDF'}</span>
                        </button>
                        <button
                          type="button"
                          disabled={downloadingFormat !== null}
                          onClick={() => handleDownloadCustomizedResume('docx')}
                          className={`download-btn docx-btn ${downloadingFormat === 'docx' ? 'loading' : ''}`}
                        >
                          {downloadingFormat === 'docx' ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                          <span>{downloadingFormat === 'docx' ? 'Downloading...' : 'Download Word (DOCX)'}</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {recreationError && (
                    <div className="suggestions-error">
                      <AlertCircle size={15} />
                      <span>{recreationError}</span>
                    </div>
                  )}

                  {/* Recreate Resume Action Bar (Disabled - Coming Soon) */}
                  <div className="recreate-action-bar disabled-tailor-bar">
                    <div className="tailor-coming-soon-notice">
                      <Sparkles size={15} className="cs-icon" />
                      <span>AI resume tailoring is coming soon.</span>
                    </div>
                    <button
                      type="button"
                      className="recreate-btn disabled"
                      disabled
                      aria-disabled="true"
                      title="AI resume tailoring is coming soon."
                    >
                      <Wand2 size={15} />
                      <span>AI resume tailoring is coming soon</span>
                    </button>
                  </div>

                  <div className="ethics-notice">
                    COMPUST AI advisory only. Never invent experience.
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="modal-footer">
          <button className="secondary-btn" onClick={onClose}>Close</button>

          {/* AI Resume Studio Tailor Button (Coming Soon) */}
          <button
            type="button"
            className="studio-tailor-footer-btn disabled"
            disabled
            aria-disabled="true"
            title="AI resume tailoring is coming soon."
          >
            <Sparkles size={15} />
            <span>AI Tailoring (Coming Soon)</span>
          </button>

          {/* Suggest Resume Customization Button */}
          <button
            type="button"
            className={`suggestion-btn ${showSuggestions ? 'active' : ''}`}
            onClick={handleFetchResumeSuggestions}
          >
            <FileSearch size={15} />
            <span>{showSuggestions ? 'Refresh Suggestions' : 'Suggest Resume Customization'}</span>
          </button>

          {/* Mark as Applied Action */}
          <button
            type="button"
            className={`applied-btn ${isApplied ? 'applied' : ''}`}
            onClick={handleMarkAsApplied}
            disabled={isApplied || markingApplied}
          >
            {isApplied ? (
              <>
                <Check size={15} />
                <span>Marked as Applied</span>
              </>
            ) : (
              <>
                <CheckCheck size={15} />
                <span>{markingApplied ? 'Updating...' : 'Mark as Applied'}</span>
              </>
            )}
          </button>

          {/* External Genuine Portal Link */}
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="primary-btn"
          >
            <span>Apply on Official Portal</span>
            <ExternalLink size={16} />
          </a>
        </div>
      </div>

      {showTailorDrawer && (
        <ResumeTailorDrawer
          job={job}
          onClose={() => setShowTailorDrawer(false)}
        />
      )}
    </StyledModalBackdrop>
  );
};

const StyledModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;

  .modal-container {
    width: 100%;
    max-width: 760px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .modal-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 24px 28px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .company-line {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
    color: #94a3b8;
    margin-bottom: 6px;

    .icon {
      color: #60a5fa;
    }
    .dot {
      color: #475569;
    }
  }

  .job-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
    line-height: 1.3;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 6px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      color: #f8fafc;
      background: rgba(255, 255, 255, 0.08);
    }
  }

  .translation-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    padding: 10px 28px;
    background: rgba(30, 41, 59, 0.45);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .lang-switcher {
    display: flex;
    align-items: center;
    gap: 8px;

    .lang-icon {
      color: #38bdf8;
    }

    .lang-label {
      font-size: 0.8rem;
      font-weight: 600;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }

  .pill-group {
    display: flex;
    gap: 6px;
    background: rgba(15, 23, 42, 0.6);
    padding: 3px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .pill-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.06);
    }

    &.active {
      background: #2563eb;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
    }

    &:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .spin {
      animation: spin 1s linear infinite;
    }
  }

  .truth-badge {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.76rem;
    color: #10b981;
    background: rgba(16, 185, 129, 0.08);
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid rgba(16, 185, 129, 0.2);

    .shield-icon {
      color: #10b981;
    }
  }

  .translation-error {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 28px;
    background: rgba(239, 68, 68, 0.1);
    color: #f87171;
    font-size: 0.82rem;
    border-bottom: 1px solid rgba(239, 68, 68, 0.2);
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .match-panel {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(124, 58, 237, 0.12));
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 12px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .match-score-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .score-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #2563eb;
    color: #ffffff;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 4px 10px;
    border-radius: 20px;
    box-shadow: 0 2px 10px rgba(37, 99, 235, 0.4);
  }

  .score-desc {
    font-size: 0.85rem;
    color: #94a3b8;
  }

  .category-scores-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 8px;
    padding: 10px 12px;
    background: rgba(15, 23, 42, 0.4);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .cat-score-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .cat-score-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.74rem;
    font-weight: 600;
    color: #cbd5e1;

    .cat-val {
      color: #93c5fd;
    }
  }

  .cat-progress-bar {
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
  }

  .cat-progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;

    &.high {
      background: linear-gradient(90deg, #10b981, #34d399);
    }
    &.med {
      background: linear-gradient(90deg, #3b82f6, #60a5fa);
    }
    &.low {
      background: linear-gradient(90deg, #f59e0b, #fbbf24);
    }
  }

  .factors-group {
    display: flex;
    flex-direction: column;
    gap: 6px;

    .factor-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
    }

    &.positive {
      color: #34d399;
      .factor-icon { color: #10b981; }
    }

    &.missing {
      color: #fbbf24;
      .factor-icon { color: #f59e0b; }
    }
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    padding: 14px 18px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
  }

  .meta-item {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .label {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #64748b;
    }

    .val {
      font-size: 0.9rem;
      font-weight: 500;
      color: #e2e8f0;
    }
  }

  .section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 10px;
  }

  .description-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;

    .section-title {
      margin-bottom: 0;
    }

    .translation-indicator {
      font-size: 0.75rem;
      font-weight: 600;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(56, 189, 248, 0.25);
    }
  }

  .skills-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .skill-chip {
    padding: 5px 12px;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 16px;
    color: #93c5fd;
    font-size: 0.82rem;
    font-weight: 500;
  }

  .description-content {
    font-size: 0.95rem;
    color: #cbd5e1;
    line-height: 1.7;

    p { margin-bottom: 12px; }
    ul, ol { margin-left: 24px; margin-bottom: 12px; }
    li { margin-bottom: 6px; }
    h2, h3, h4 { margin-top: 16px; margin-bottom: 8px; color: #ffffff; }
    a { color: #60a5fa; text-decoration: underline; }
  }

  .no-desc {
    color: #64748b;
    font-style: italic;
  }

  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    padding: 18px 28px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(10, 15, 26, 0.9);
  }

  .secondary-btn {
    padding: 10px 20px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.05);
    transition: all 0.2s;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }
  }

  .primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 22px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    color: #ffffff;
    background: #2563eb;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    transition: all 0.2s;

    &:hover {
      background: #1d4ed8;
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.55);
      transform: translateY(-1px);
    }
  }

  .studio-tailor-footer-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.88rem;
    color: #ffffff;
    background: linear-gradient(135deg, #8b5cf6, #ec4899);
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);
    transition: all 0.2s;

    &:hover {
      filter: brightness(1.1);
      box-shadow: 0 6px 18px rgba(139, 92, 246, 0.55);
      transform: translateY(-1px);
    }

    &.disabled {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #94a3b8;
      cursor: not-allowed;
      box-shadow: none;
      filter: none;
      transform: none;

      &:hover {
        filter: none;
        transform: none;
        background: rgba(255, 255, 255, 0.06);
        color: #94a3b8;
        box-shadow: none;
      }
    }
  }

  .suggestion-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.85rem;
    color: #93c5fd;
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.25);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(59, 130, 246, 0.22);
      color: #ffffff;
    }

    &.active {
      background: rgba(59, 130, 246, 0.25);
      border-color: #3b82f6;
      color: #ffffff;
    }
  }

  .applied-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.85rem;
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.3);
      color: #34d399;
    }

    &.applied {
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.35);
      color: #34d399;
      cursor: default;
    }
  }

  /* Resume Customization Panel */
  .resume-customization-panel {
    margin-top: 24px;
    background: rgba(10, 15, 26, 0.7);
    border: 1px solid rgba(59, 130, 246, 0.25);
    border-radius: 16px;
    padding: 18px;

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .panel-title-row {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #f8fafc;
      font-weight: 700;
      font-size: 0.95rem;

      .panel-icon {
        color: #3b82f6;
      }
    }

    .req-badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 8px;

      &.complete {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
      }

      &.incomplete {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
      }
    }

    .suggestions-loading {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 20px;
      color: #94a3b8;
      font-size: 0.85rem;
      justify-content: center;
    }

    .suggestions-error {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: 10px;
      color: #fde68a;
      font-size: 0.82rem;
    }

    .suggestions-content {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .factor-box {
      padding: 12px;
      border-radius: 12px;

      &.demonstrated {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        .box-title { color: #34d399; }
      }

      &.missing {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        .box-title { color: #fbbf24; }
      }

      .box-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 8px;
      }

      .tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .match-tag {
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;

        &.demonstrated {
          background: rgba(16, 185, 129, 0.15);
          color: #6ee7b7;
        }

        &.missing {
          background: rgba(245, 158, 11, 0.15);
          color: #fcd34d;
        }
      }

      .none-text {
        font-size: 0.78rem;
        color: #94a3b8;
        font-style: italic;
      }
    }

    .actionable-suggestions {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 12px;

      .box-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #93c5fd;
        margin-bottom: 8px;
      }

      .advice-list {
        margin: 0;
        padding-left: 20px;
        font-size: 0.8rem;
        color: #cbd5e1;
        line-height: 1.5;

        li {
          margin-bottom: 6px;
        }
      }

      .ethics-notice {
        margin-top: 8px;
        font-size: 0.7rem;
        color: #64748b;
        font-style: italic;
      }
    }

    .ats-box {
      background: rgba(147, 51, 234, 0.08);
      border: 1px solid rgba(147, 51, 234, 0.2);
      .box-title { color: #c084fc; }
    }

    .detailed-recs {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 12px;

      .box-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #60a5fa;
        margin-bottom: 10px;
      }

      .rec-cards-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .rec-card {
        padding: 10px;
        border-radius: 8px;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);

        .rec-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;

          .rec-req {
            font-size: 0.82rem;
            font-weight: 700;
            color: #f8fafc;
          }

          .rec-loc {
            font-size: 0.72rem;
            color: #94a3b8;
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 6px;
            border-radius: 4px;
          }
        }

        .rec-weak {
          font-size: 0.78rem;
          color: #fca5a5;
          margin-bottom: 4px;
        }

        .rec-act {
          font-size: 0.78rem;
          color: #93c5fd;
          line-height: 1.4;
        }
      }
    }

    .customized-ready-box {
      padding: 14px;
      border-radius: 12px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.35);

      .ready-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;

        .ready-icon {
          color: #34d399;
          flex-shrink: 0;
        }

        .ready-title {
          font-size: 0.9rem;
          font-weight: 700;
          color: #f8fafc;
          margin: 0;
        }

        .ready-sub {
          font-size: 0.75rem;
          color: #6ee7b7;
        }
      }

      .download-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;

        .download-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-size: 0.8rem;
          font-weight: 600;
          text-decoration: none;
          transition: all 0.2s;

          &:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          &.pdf-btn {
            background: #ef4444;
            color: #ffffff;
            &:hover:not(:disabled) { background: #dc2626; }
          }

          &.docx-btn {
            background: #2563eb;
            color: #ffffff;
            &:hover:not(:disabled) { background: #1d4ed8; }
          }
        }
      }
    }

    .attached-guidance-panel {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 14px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);

      .guidance-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;

        .guidance-header-left {
          display: flex;
          align-items: center;
          gap: 10px;

          .guidance-icon {
            color: #60a5fa;
            flex-shrink: 0;
          }

          .guidance-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0 0 2px;
          }

          .guidance-subtitle {
            font-size: 0.78rem;
            color: #94a3b8;
            margin: 0;
          }
        }

        .guidance-header-right {
          display: flex;
          align-items: center;
          gap: 8px;

          .guidance-count-pill {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(59, 130, 246, 0.15);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.3);
          }

          .refresh-guidance-btn {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #cbd5e1;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;

            &:hover:not(:disabled) {
              background: rgba(59, 130, 246, 0.15);
              border-color: rgba(59, 130, 246, 0.4);
              color: #60a5fa;
            }

            &:disabled {
              opacity: 0.6;
              cursor: not-allowed;
            }

            .spin {
              animation: spin 1s linear infinite;
            }
          }
        }
      }

      .guidance-error {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border-radius: 8px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        color: #fca5a5;
        font-size: 0.78rem;
      }

      .guidance-empty {
        padding: 16px;
        text-align: center;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        border: 1px dashed rgba(255, 255, 255, 0.1);

        p {
          font-size: 0.82rem;
          color: #94a3b8;
          margin-bottom: 8px;
        }

        .generate-guidance-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 6px;
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          border: none;
          color: #fff;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;

          .spin {
            animation: spin 1s linear infinite;
          }
        }
      }

      .guidance-sections-list {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }

      .guidance-section-block {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .section-group-heading {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #93c5fd;
        margin: 0 0 4px;

        .section-count {
          color: #64748b;
          font-weight: 500;
        }
      }

      .guidance-cards-grid {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .guidance-card {
        background: rgba(2, 6, 23, 0.6);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        transition: border-color 0.2s;

        &.unverified {
          border-color: rgba(245, 158, 11, 0.35);
          background: rgba(30, 20, 10, 0.35);
        }

        &.grounded {
          border-color: rgba(16, 185, 129, 0.25);
        }

        .card-top-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;

          .location-tag {
            font-size: 0.75rem;
            font-weight: 600;
            color: #cbd5e1;
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 8px;
            border-radius: 4px;
          }

          .badge-grounded {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            color: #34d399;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 2px 6px;
            border-radius: 4px;
          }

          .badge-unverified {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            color: #fbbf24;
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
          }
        }

        .guidance-rationale {
          font-size: 0.8rem;
          color: #94a3b8;
          line-height: 1.4;
          margin: 0;
        }

        .unverified-warning-banner {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 5px 8px;
          border-radius: 6px;
          background: rgba(245, 158, 11, 0.1);
          border: 1px solid rgba(245, 158, 11, 0.25);
          color: #fde68a;
          font-size: 0.72rem;

          .warning-icon {
            color: #fbbf24;
            flex-shrink: 0;
          }
        }

        .original-box {
          font-size: 0.75rem;
          color: #64748b;
          background: rgba(0, 0, 0, 0.2);
          padding: 6px 10px;
          border-radius: 6px;
          border-left: 2px solid #64748b;

          .orig-label {
            font-weight: 600;
            margin-right: 4px;
          }
        }

        .suggested-box {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          background: rgba(15, 23, 42, 0.9);
          border: 1px solid rgba(59, 130, 246, 0.25);
          border-radius: 8px;
          padding: 10px 12px;

          .suggested-text {
            font-family: 'JetBrains Mono', monospace, ui-monospace;
            font-size: 0.82rem;
            color: #e2e8f0;
            line-height: 1.45;
            flex: 1;
            white-space: pre-wrap;
            word-break: break-word;
          }

          .copy-suggestion-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 5px;
            background: rgba(59, 130, 246, 0.2);
            border: 1px solid rgba(59, 130, 246, 0.35);
            color: #93c5fd;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            flex-shrink: 0;
            transition: all 0.15s;

            &:hover {
              background: rgba(59, 130, 246, 0.35);
              color: #fff;
            }
          }
        }
      }
    }

    .studio-tailor-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 16px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(139, 92, 246, 0.18));
      border: 1px solid rgba(139, 92, 246, 0.35);
      margin-top: 10px;
      box-shadow: 0 4px 16px rgba(139, 92, 246, 0.1);

      &.coming-soon {
        background: rgba(148, 163, 184, 0.05);
        border: 1px dashed rgba(148, 163, 184, 0.25);
        box-shadow: none;

        .studio-tailor-icon {
          color: #94a3b8;
        }

        .banner-title-row {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 2px;
        }
      }

      .studio-tailor-info {
        display: flex;
        align-items: center;
        gap: 12px;

        .studio-tailor-icon {
          color: #a855f7;
          flex-shrink: 0;
        }

        h4 {
          font-size: 0.88rem;
          font-weight: 700;
          color: #f1f5f9;
          margin-bottom: 2px;
        }

        p {
          font-size: 0.78rem;
          color: #94a3b8;
          line-height: 1.45;
        }
      }

      .studio-tailor-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 9px 16px;
        border-radius: 10px;
        font-size: 0.82rem;
        font-weight: 700;
        color: #ffffff;
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        border: none;
        cursor: pointer;
        white-space: nowrap;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35);
        transition: all 0.2s;

        &:hover {
          filter: brightness(1.1);
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(139, 92, 246, 0.45);
        }

        &.disabled {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: #94a3b8;
          cursor: not-allowed;
          box-shadow: none;
          filter: none;
          transform: none;

          &:hover {
            filter: none;
            transform: none;
            background: rgba(255, 255, 255, 0.06);
            color: #94a3b8;
            box-shadow: none;
          }
        }
      }
    }

    .recreate-action-bar {
      margin-top: 10px;

      &.disabled-tailor-bar {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .tailor-coming-soon-notice {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px dashed rgba(148, 163, 184, 0.25);
          border-radius: 10px;
          color: #cbd5e1;
          font-size: 0.82rem;

          .cs-icon {
            color: #60a5fa;
            flex-shrink: 0;
          }
        }
      }

      .recreate-btn {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 12px;
        border-radius: 10px;
        font-size: 0.85rem;
        font-weight: 700;
        color: #ffffff;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border: none;
        cursor: pointer;
        transition: all 0.2s;

        &:hover:not(:disabled) {
          filter: brightness(1.1);
          transform: translateY(-1px);
        }

        &.disabled {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #94a3b8;
          cursor: not-allowed;
          box-shadow: none;
          filter: none;
          transform: none;

          &:hover {
            filter: none;
            transform: none;
          }
        }
      }
    }
  }

  /* Responsive Text and Layout Adjustments */
  @media (max-width: 680px) {
    padding: 12px;

    .modal-container {
      max-height: 94vh;
      border-radius: 16px;
    }

    .modal-header {
      padding: 18px 18px 12px;
    }

    .job-title {
      font-size: 1.25rem;
    }

    .translation-bar {
      padding: 10px 18px;
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }

    .modal-body {
      padding: 16px 18px;
      gap: 18px;
    }

    .meta-grid {
      grid-template-columns: repeat(2, 1fr);
      padding: 10px 12px;
    }

    .studio-tailor-banner {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;

      .studio-tailor-btn {
        width: 100%;
        justify-content: center;
      }
    }

    .modal-footer {
      padding: 14px 18px;
      flex-direction: column-reverse;
      align-items: stretch;
      gap: 8px;

      button, a {
        width: 100%;
        justify-content: center;
      }
    }
  }

  @keyframes modalIn {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
