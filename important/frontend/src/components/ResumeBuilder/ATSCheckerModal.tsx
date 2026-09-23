import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCircle2,
  RefreshCw,
  Cpu,
  Layers,
  Sparkles,
  Search,
  Check,
} from 'lucide-react';
import type {
  StructuredResumeData,
  ATSCheckResult,
} from '../../api/client';
import { api } from '../../api/client';
import { StageProgressList, useStageProgress } from '../common/StageProgressList';
import './ATSCheckerModal.css';

interface ATSCheckerModalProps {
  isOpen: boolean;
  onClose: () => void;
  resumeId: number;
  resumeTitle: string;
  structuredData: StructuredResumeData;
  initialRole?: string;
  initialField?: string;
}

const ATS_STAGES = [
  'Extracting Plain-Text Search Layer & Identity...',
  'Standardizing Sections Across Locales (EN, FR, DE)...',
  'Auditing Quantifiable Metrics & Action Verbs...',
  'Checking ATS Typography, Hierarchy & Length Norms...',
  'Scoring ATS Pillars & Synthesizing Recommendations...',
];

export const ATSCheckerModal: React.FC<ATSCheckerModalProps> = ({
  isOpen,
  onClose,
  resumeId,
  resumeTitle,
  structuredData,
  initialRole = '',
  initialField = '',
}) => {
  const [targetRole, setTargetRole] = useState(
    initialRole || structuredData.profile?.headline || ''
  );
  const [targetField, setTargetField] = useState(initialField || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ATSCheckResult | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'critical' | 'warning' | 'tip' | 'pass'>('all');

  const stageProgress = useStageProgress(ATS_STAGES, loading, 400);

  // Sync role when props change
  useEffect(() => {
    if (initialRole) {
      setTargetRole(initialRole);
    } else if (structuredData.profile?.headline && !targetRole) {
      setTargetRole(structuredData.profile.headline);
    }
  }, [initialRole, structuredData.profile?.headline]);

  // Execute ATS check
  const handleRunAudit = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.runResumeATSCheck(resumeId, {
        target_role: targetRole.trim() || undefined,
        target_field: targetField.trim() || undefined,
        structured_data: structuredData,
      });
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to complete ATS audit.');
    } finally {
      setLoading(false);
    }
  };

  // Run automatically on first open if no result yet
  useEffect(() => {
    if (isOpen && !result && !loading) {
      handleRunAudit();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredFeedback = (result?.feedback || []).filter((item) => {
    if (activeFilter === 'all') return true;
    return item.severity === activeFilter;
  });

  const getScoreColorClass = (score: number) => {
    if (score >= 85) return 'score-excellent';
    if (score >= 70) return 'score-good';
    if (score >= 50) return 'score-warning';
    return 'score-danger';
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertOctagon size={16} className="text-danger" />;
      case 'warning':
        return <AlertTriangle size={16} className="text-warning" />;
      case 'pass':
        return <CheckCircle2 size={16} className="text-success" />;
      default:
        return <Info size={16} className="text-info" />;
    }
  };

  return (
    <div className="ats-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ats-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <header className="ats-modal-header">
          <div className="ats-header-title-block">
            <div className="ats-title-icon-wrap">
              <ShieldCheck size={22} className="ats-header-icon" />
            </div>
            <div>
              <h2 className="ats-modal-title">ATS Compatibility Engine &mdash; {resumeTitle}</h2>
              <p className="ats-modal-subtitle">
                Grounded in 6 corporate ATS scoring pillars (Workday, Taleo, Greenhouse, Lever)
              </p>
            </div>
          </div>
          <button
            type="button"
            className="ats-close-btn"
            onClick={onClose}
            aria-label="Close ATS audit"
          >
            <X size={20} />
          </button>
        </header>

        {/* Target Profile Controls Bar */}
        <div className="ats-controls-bar">
          <div className="ats-input-group">
            <label htmlFor="ats-target-role">Target Role</label>
            <div className="ats-input-wrapper">
              <Search size={14} className="ats-input-icon" />
              <input
                id="ats-target-role"
                type="text"
                placeholder="e.g. Senior Software Engineer, Cybersecurity Analyst"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
              />
            </div>
          </div>

          <div className="ats-input-group">
            <label htmlFor="ats-target-field">Industry / Domain</label>
            <div className="ats-input-wrapper">
              <Layers size={14} className="ats-input-icon" />
              <input
                id="ats-target-field"
                type="text"
                placeholder="e.g. Cloud Infrastructure, FinTech, Defense"
                value={targetField}
                onChange={(e) => setTargetField(e.target.value)}
              />
            </div>
          </div>

          <button
            type="button"
            className="ats-recheck-btn"
            disabled={loading}
            onClick={handleRunAudit}
            title="Re-run ATS Audit with updated targets"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Auditing...' : 'Run Audit'}</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="ats-modal-body">
          {error && (
            <div className="ats-error-banner">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="ats-loading-state">
              <StageProgressList
                stages={ATS_STAGES}
                currentStage={stageProgress}
                title="Running ATS Audit..."
              />
            </div>
          ) : result ? (
            <div className="ats-results-container">
              {/* Score Hero Banner */}
              <div className={`ats-score-hero ${getScoreColorClass(result.overall_score)}`}>
                <div className="ats-hero-gauge-col">
                  <div className="ats-score-gauge-ring">
                    <svg className="ats-gauge-svg" viewBox="0 0 100 100">
                      <circle
                        className="ats-gauge-bg"
                        cx="50"
                        cy="50"
                        r="42"
                      />
                      <circle
                        className="ats-gauge-fill"
                        cx="50"
                        cy="50"
                        r="42"
                        strokeDasharray="264"
                        strokeDashoffset={264 - (264 * result.overall_score) / 100}
                      />
                    </svg>
                    <div className="ats-gauge-number-wrap">
                      <span className="ats-gauge-number">{result.overall_score}</span>
                      <span className="ats-gauge-denom">/100</span>
                    </div>
                  </div>
                </div>

                <div className="ats-hero-info-col">
                  <div className="ats-hero-top-row">
                    <span className="ats-verdict-tag">{result.verdict}</span>
                    <div className="ats-provider-tag" title="Execution Engine">
                      <Cpu size={12} />
                      <span>
                        {result.provider === 'ollama'
                          ? `Local LLM (${result.model || 'active'})`
                          : 'Deterministic ATS Engine'}
                      </span>
                    </div>
                  </div>

                  <p className="ats-hero-desc">
                    {result.overall_score >= 85
                      ? 'Exceptional parseability and alignment. Your resume is well-structured to bypass automated screening filters and reach hiring managers.'
                      : result.overall_score >= 70
                      ? 'Solid competitive foundation. Addressing the keyword gaps and metric recommendations below will elevate your application to top-tier percentile.'
                      : result.overall_score >= 50
                      ? 'Noticeable ATS obstacles detected. Missing standard sections, weak action verbs, or lack of metrics may cause applicant filtering.'
                      : 'High risk of ATS parse failure or low relevance ranking. Immediate structural improvements and contact verification are required.'}
                  </p>

                  <div className="ats-hero-stat-pills">
                    <span className="ats-stat-pill">
                      <strong>{result.keywords_found.length}</strong> Keywords Found
                    </span>
                    <span className="ats-stat-pill">
                      <strong>{result.keywords_missing.length}</strong> Missing Targets
                    </span>
                    <span className="ats-stat-pill">
                      <strong>{result.feedback.filter((f) => f.severity === 'critical').length}</strong> Critical Issues
                    </span>
                  </div>
                </div>
              </div>

              {/* 6 Category Breakdown Grid */}
              <div className="ats-categories-section">
                <h3 className="ats-section-heading">ATS Pillar Breakdown</h3>
                <div className="ats-categories-grid">
                  {result.categories.map((cat) => (
                    <div
                      key={cat.category}
                      className={`ats-category-card cat-status-${cat.status}`}
                    >
                      <div className="ats-category-top">
                        <span className="ats-category-name">{cat.name}</span>
                        <span className="ats-category-score">
                          {cat.score}
                          <small>/{cat.max_score}</small>
                        </span>
                      </div>
                      <div className="ats-category-progress-track">
                        <div
                          className="ats-category-progress-bar"
                          style={{ width: `${Math.min(100, Math.max(0, cat.score))}%` }}
                        />
                      </div>
                      <p className="ats-category-notes">{cat.notes}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Keywords & Verbs Clouds */}
              <div className="ats-keywords-section">
                <div className="ats-kw-column">
                  <h4 className="ats-subheading">
                    <Check size={14} className="text-success" />
                    <span>Matched Keywords ({result.keywords_found.length})</span>
                  </h4>
                  <div className="ats-chips-cloud">
                    {result.keywords_found.length > 0 ? (
                      result.keywords_found.map((kw, i) => (
                        <span key={i} className="ats-chip matched">
                          {kw}
                        </span>
                      ))
                    ) : (
                      <span className="ats-chips-empty">No target keywords detected in text.</span>
                    )}
                  </div>
                </div>

                <div className="ats-kw-column">
                  <h4 className="ats-subheading">
                    <AlertTriangle size={14} className="text-warning" />
                    <span>Missing Target Keywords ({result.keywords_missing.length})</span>
                  </h4>
                  <div className="ats-chips-cloud">
                    {result.keywords_missing.length > 0 ? (
                      result.keywords_missing.map((kw, i) => (
                        <span key={i} className="ats-chip missing">
                          +{kw}
                        </span>
                      ))
                    ) : (
                      <span className="ats-chips-empty">No missing core keywords identified.</span>
                    )}
                  </div>
                </div>

                {result.recommended_action_verbs && result.recommended_action_verbs.length > 0 && (
                  <div className="ats-kw-column verbs-col">
                    <h4 className="ats-subheading">
                      <Sparkles size={14} className="text-primary" />
                      <span>Recommended Action Verbs</span>
                    </h4>
                    <div className="ats-chips-cloud">
                      {result.recommended_action_verbs.map((verb, i) => (
                        <span key={i} className="ats-chip verb">
                          {verb}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actionable Feedback List */}
              <div className="ats-feedback-section">
                <div className="ats-feedback-header-row">
                  <h3 className="ats-section-heading">
                    Grounded Findings & Recommendations ({result.feedback.length})
                  </h3>
                  <div className="ats-filter-pills">
                    {(['all', 'critical', 'warning', 'tip', 'pass'] as const).map((filter) => {
                      const count =
                        filter === 'all'
                          ? result.feedback.length
                          : result.feedback.filter((f) => f.severity === filter).length;
                      return (
                        <button
                          key={filter}
                          type="button"
                          className={`ats-filter-pill ${activeFilter === filter ? 'active' : ''}`}
                          onClick={() => setActiveFilter(filter)}
                        >
                          {filter.toUpperCase()} ({count})
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="ats-feedback-list">
                  {filteredFeedback.length > 0 ? (
                    filteredFeedback.map((item) => (
                      <div
                        key={item.id}
                        className={`ats-feedback-card severity-${item.severity}`}
                      >
                        <div className="ats-feedback-icon-col">
                          {getSeverityIcon(item.severity)}
                        </div>
                        <div className="ats-feedback-content-col">
                          <div className="ats-feedback-card-title-row">
                            <h4 className="ats-feedback-card-title">{item.title}</h4>
                            <span className={`ats-severity-badge ${item.severity}`}>
                              {item.severity}
                            </span>
                          </div>
                          <p className="ats-feedback-message">{item.message}</p>

                          {item.grounded_quote && (
                            <div className="ats-grounded-quote">
                              <span className="ats-quote-label">Excerpt:</span>
                              <code className="ats-quote-text">
                                &ldquo;{item.grounded_quote}&rdquo;
                              </code>
                            </div>
                          )}

                          <div className="ats-feedback-rec-box">
                            <span className="ats-rec-label">Recommendation:</span>
                            <span className="ats-rec-text">{item.recommendation}</span>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="ats-empty-feedback">
                      <CheckCircle2 size={24} className="text-success" />
                      <p>No issues found for the &ldquo;{activeFilter}&rdquo; filter.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="ats-idle-state">
              <p>Click &ldquo;Run Audit&rdquo; to analyze your resume against ATS criteria.</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <footer className="ats-modal-footer">
          <button
            type="button"
            className="action-btn secondary"
            onClick={onClose}
          >
            Back to Resume Editor
          </button>
          <button
            type="button"
            className="action-btn primary"
            onClick={handleRunAudit}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Re-Audit Resume</span>
          </button>
        </footer>
      </div>
    </div>
  );
};
