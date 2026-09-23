import React, { useState } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  ChevronDown,
  ChevronUp,
  Layers,
  UserCheck,
  TrendingUp,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  BehavioralPrepResponse,
  STAREvaluationResponse,
} from '../../api/client';

export const STAR_TARGET_SPLIT = {
  situation: 15,
  task: 10,
  action: 60,
  result: 15,
};

interface STARProportionBarProps {
  activeStep?: string | null;
  onSelectStep?: (step: string) => void;
}

export const STARProportionBar: React.FC<STARProportionBarProps> = ({
  activeStep,
  onSelectStep,
}) => {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);

  const stepDetails: Record<
    string,
    { pct: number; label: string; time: string; focus: string; color: string }
  > = {
    Situation: {
      pct: STAR_TARGET_SPLIT.situation,
      label: 'Situation',
      time: '~20–25s',
      focus: 'Set company context, constraints, and problem trigger without digressing.',
      color: '#38bdf8',
    },
    Task: {
      pct: STAR_TARGET_SPLIT.task,
      label: 'Task',
      time: '~15s',
      focus: 'Explicitly state your personal responsibility, scope, and objective.',
      color: '#818cf8',
    },
    Action: {
      pct: STAR_TARGET_SPLIT.action,
      label: 'Action (Dominant)',
      time: '~90–100s',
      focus: 'Architectural decisions, trade-offs weighed, code/infra implementation, and overcoming obstacles.',
      color: '#3b82f6',
    },
    Result: {
      pct: STAR_TARGET_SPLIT.result,
      label: 'Result',
      time: '~20–25s',
      focus: 'Quantified metrics (latency, revenue, uptime), retrospective learnings, and business impact.',
      color: '#10b981',
    },
  };

  const currentHover = hoveredStep || activeStep || 'Action';
  const detail = stepDetails[currentHover] || stepDetails.Action;

  return (
    <div className="star-proportion-section">
      <div className="proportion-header-row">
        <div className="proportion-title-group">
          <span className="proportion-label">Calibrated Delivery Split</span>
          <span className="proportion-badge">100% Behavioral Target</span>
        </div>
        <div className="proportion-tip">
          Click any segment to inspect timing & framing formulas
        </div>
      </div>

      <div className="star-proportion-bar" role="progressbar" aria-label="STAR Time Allocation">
        {Object.entries(stepDetails).map(([key, data]) => {
          const isSelected = activeStep === key;
          const isDominant = key === 'Action';
          return (
            <div
              key={key}
              className={`proportion-segment ${key.toLowerCase()} ${
                isSelected ? 'selected' : ''
              } ${isDominant ? 'dominant' : ''}`}
              style={{ width: `${data.pct}%` }}
              onClick={() => onSelectStep && onSelectStep(key)}
              onMouseEnter={() => setHoveredStep(key)}
              onMouseLeave={() => setHoveredStep(null)}
              role="button"
              tabIndex={0}
              title={`${data.label}: ${data.pct}%`}
            >
              <div className="segment-label-box">
                <span className="segment-name">{key[0]}</span>
                <span className="segment-pct">{data.pct}%</span>
              </div>
              {isDominant && <span className="dominant-glow-pill">Core Focus</span>}
            </div>
          );
        })}
      </div>

      {/* Dynamic Guideline Tooltip Banner */}
      <div className="proportion-guideline-banner">
        <div className="guideline-indicator" style={{ borderColor: detail.color }}>
          <strong style={{ color: detail.color }}>
            {detail.label} ({detail.pct}% · {detail.time})
          </strong>
          <span className="guideline-focus">{detail.focus}</span>
        </div>
      </div>
    </div>
  );
};

interface ExpandableSTARCardsProps {
  starGuide: BehavioralPrepResponse['star_guide'];
  expandedStep: string | null;
  onToggleStep: (step: string) => void;
}

export const ExpandableSTARCards: React.FC<ExpandableSTARCardsProps> = ({
  starGuide,
  expandedStep,
  onToggleStep,
}) => {
  const formulas: Record<string, { formula: string; signal: string }> = {
    Situation: {
      formula: '"While working at [Company/Org], our [System/Team] faced [Specific Bottleneck/Crisis] under [Scale/Constraint]..."',
      signal: 'Conciseness & situational awareness without irrelevant tangents.',
    },
    Task: {
      formula: '"My direct ownership was to [Lead/Design/Deliver] [Target Deliverable] within [Timeline], aiming to reduce [Risk/Metric]..."',
      signal: 'Individual accountability, scope clarity, and goal setting.',
    },
    Action: {
      formula: '"I first investigated [Root Cause via Profiling/Logs]. I evaluated Option A vs Option B, choosing [Decision] because of [Trade-off]. When [Obstacle] arose, I adapted by [Solution]..."',
      signal: 'Engineering depth, agency, trade-off analysis, and resilience.',
    },
    Result: {
      formula: '"As a result, [Metric] improved by [X% / $Y], reducing incidents by [Z]. The team adopted my [Pattern/Doc], and in retrospect, I learned to [Future Optimization]..."',
      signal: 'Business impact, metrics quantification, and reflective growth.',
    },
  };

  return (
    <div className="star-expandable-cards-grid">
      {starGuide.steps.map((step) => {
        const isExpanded = expandedStep === step.step;
        const meta = formulas[step.step] || {
          formula: 'Frame with clarity, individual ownership, and concrete evidence.',
          signal: 'Direct communication and structured thought.',
        };
        const isAction = step.step === 'Action';

        return (
          <div
            key={step.step}
            className={`star-step-card glass-panel ${isExpanded ? 'expanded' : ''} ${
              isAction ? 'is-action-highlight' : ''
            }`}
          >
            <div
              className="step-card-header"
              onClick={() => onToggleStep(step.step)}
              role="button"
              tabIndex={0}
              aria-expanded={isExpanded}
            >
              <div className="step-badge-left">
                <span className="step-letter-pill">{step.step[0]}</span>
                <div>
                  <h4 className="step-name-title">{step.step}</h4>
                  <span className="step-pct-tag">
                    {step.step === 'Situation' ? '15%' : step.step === 'Task' ? '10%' : step.step === 'Action' ? '60%' : '15%'} Target
                  </span>
                </div>
              </div>
              <div className="step-toggle-icon">
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </div>

            <p className="step-definition-text">{step.definition}</p>

            {isExpanded && (
              <div className="step-expanded-details">
                <div className="detail-row formula">
                  <span className="detail-tag">Recommended Framing Formula:</span>
                  <p className="formula-text">{meta.formula}</p>
                </div>

                <div className="detail-row signal">
                  <span className="detail-tag">Evaluator Core Signal:</span>
                  <p className="signal-text">{meta.signal}</p>
                </div>

                <div className="detail-row example">
                  <span className="detail-tag">Sample Excerpt:</span>
                  <blockquote className="example-quote">"{step.example}"</blockquote>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export const StoryThemeCoverageMatrix: React.FC = () => {
  const archetypes = [
    {
      id: 's1',
      title: 'Story 1: High-Concurrency Bottleneck',
      subtitle: 'Kafka/Redis latency spike resolution',
      leadership: 'High',
      conflict: 'Medium',
      scale: 'Critical',
      failure: 'Low',
      ambiguity: 'Medium',
    },
    {
      id: 's2',
      title: 'Story 2: Production Outage Postmortem',
      subtitle: 'Database connection pool exhaustion',
      leadership: 'High',
      conflict: 'Low',
      scale: 'High',
      failure: 'Critical',
      ambiguity: 'High',
    },
    {
      id: 's3',
      title: 'Story 3: Architectural Migration',
      subtitle: 'Monolith to decoupled microservices',
      leadership: 'Critical',
      conflict: 'High',
      scale: 'High',
      failure: 'Low',
      ambiguity: 'High',
    },
    {
      id: 's4',
      title: 'Story 4: Disagreement on Technical Standard',
      subtitle: 'GraphQL vs gRPC team consensus',
      leadership: 'High',
      conflict: 'Critical',
      scale: 'Low',
      failure: 'Low',
      ambiguity: 'Medium',
    },
    {
      id: 's5',
      title: 'Story 5: Zero-to-One Prototype Delivery',
      subtitle: 'Greenfield vector retrieval ingestion',
      leadership: 'High',
      conflict: 'Medium',
      scale: 'Medium',
      failure: 'Medium',
      ambiguity: 'Critical',
    },
  ];

  return (
    <section className="story-theme-matrix-section glass-panel">
      <div className="matrix-head-row">
        <div className="matrix-title-box">
          <Layers size={20} className="text-primary" />
          <div>
            <h3>Story ↔ Behavioral Theme Coverage Matrix</h3>
            <p className="matrix-subtitle">
              Verify your 5 core engineering stories cover all high-frequency behavioral dimensions so you never scramble for an example.
            </p>
          </div>
        </div>
        <span className="matrix-full-coverage-pill">Recommended: 5 Anchors</span>
      </div>

      <div className="matrix-table-scroll">
        <table className="story-matrix-table">
          <thead>
            <tr>
              <th className="th-story">Candidate Story Anchor</th>
              <th>System Scale</th>
              <th>Crisis / Recovery</th>
              <th>Technical Conflict</th>
              <th>Leadership / Standards</th>
              <th>Ambiguity / Zero-to-One</th>
            </tr>
          </thead>
          <tbody>
            {archetypes.map((row) => (
              <tr key={row.id}>
                <td className="td-story-name">
                  <strong>{row.title}</strong>
                  <span className="story-subtitle">{row.subtitle}</span>
                </td>
                <td>
                  <span className={`coverage-pill ${row.scale.toLowerCase()}`}>
                    {row.scale}
                  </span>
                </td>
                <td>
                  <span className={`coverage-pill ${row.failure.toLowerCase()}`}>
                    {row.failure}
                  </span>
                </td>
                <td>
                  <span className={`coverage-pill ${row.conflict.toLowerCase()}`}>
                    {row.conflict}
                  </span>
                </td>
                <td>
                  <span className={`coverage-pill ${row.leadership.toLowerCase()}`}>
                    {row.leadership}
                  </span>
                </td>
                <td>
                  <span className={`coverage-pill ${row.ambiguity.toLowerCase()}`}>
                    {row.ambiguity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

interface STAREvaluatorWidgetProps {
  prepLanguage: string;
  questionTitle?: string;
}

export const STAREvaluatorWidget: React.FC<STAREvaluatorWidgetProps> = ({
  prepLanguage,
  questionTitle,
}) => {
  const [draft, setDraft] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<STAREvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleEvaluate = async () => {
    if (!draft.trim()) return;
    setEvaluating(true);
    setError(null);
    try {
      const res = await api.evaluateSTARDraft({
        draft_answer: draft.trim(),
        question_title: questionTitle,
        language: prepLanguage,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Evaluation request failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const handleLoadSample = () => {
    setDraft(
      'At my previous fintech role, our transaction settlement service began experiencing a 15% timeout rate during the Black Friday surge, risking $350k in delayed transfers. As the lead backend engineer, my direct task was to isolate the database bottleneck and stabilize p99 latency to under 200ms within 48 hours. I profiled the slow queries using pg_stat_statements and identified an unindexed composite join on settlement_batches. I decided to implement an asynchronous batch queue using Redis streams and added a partition index. When team members raised concerns about eventual consistency, I built a synthetic reconciliation check to prove zero data loss. Consequently, our p99 dropped from 3.2s to 140ms, the timeout rate fell to 0.01%, and the settlement engine processed 1.2M transactions with zero dropped funds.'
    );
  };

  return (
    <section className="star-evaluator-card glass-panel">
      <div className="evaluator-header">
        <div className="eval-title-group">
          <Sparkles size={20} className="text-primary" />
          <div>
            <h3>AI STAR Draft Story Evaluator</h3>
            <p className="eval-desc">
              Test your draft response against the calibrated 60% Action threshold, quantified metrics detection, and "I" vs "We" ownership ratio.
            </p>
          </div>
        </div>
        <button
          type="button"
          className="load-sample-btn"
          onClick={handleLoadSample}
          title="Load a calibrated sample STAR answer"
        >
          Load High-Score Sample
        </button>
      </div>

      <div className="evaluator-input-container">
        <textarea
          className="star-draft-textarea"
          rows={6}
          placeholder="Paste or write your STAR story draft here. Mention your specific role, technical decisions, trade-offs, and measurable outcomes..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />

        <div className="evaluator-action-row">
          <span className="word-counter">
            {draft.trim() ? `${draft.trim().split(/\s+/).length} words` : '0 words'}
          </span>
          <button
            type="button"
            className="evaluate-submit-btn"
            onClick={handleEvaluate}
            disabled={evaluating || !draft.trim()}
          >
            {evaluating ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                <span>Evaluating Story...</span>
              </>
            ) : (
              <>
                <Send size={14} />
                <span>Evaluate My STAR Story</span>
              </>
            )}
          </button>
        </div>

        {error && <div className="eval-error-banner">{error}</div>}
      </div>

      {result && (
        <div className="eval-results-dashboard glass-panel">
          <div className="results-overview-row">
            {/* STAR Coverage */}
            <div className="overview-card coverage">
              <span className="overview-title">STAR Quadrant Coverage</span>
              <div className="coverage-pills-row">
                <span className={`cov-pill ${result.star_coverage.situation ? 'valid' : 'missing'}`}>
                  {result.star_coverage.situation ? '✓ Situation' : '✕ Situation'}
                </span>
                <span className={`cov-pill ${result.star_coverage.task ? 'valid' : 'missing'}`}>
                  {result.star_coverage.task ? '✓ Task' : '✕ Task'}
                </span>
                <span className={`cov-pill ${result.star_coverage.action ? 'valid' : 'missing'}`}>
                  {result.star_coverage.action ? '✓ Action' : '✕ Action'}
                </span>
                <span className={`cov-pill ${result.star_coverage.result ? 'valid' : 'missing'}`}>
                  {result.star_coverage.result ? '✓ Result' : '✕ Result'}
                </span>
              </div>
            </div>

            {/* Action Proportion Gauge */}
            <div className="overview-card action-gauge">
              <span className="overview-title">Action Share Estimate</span>
              <div className="gauge-display">
                <span className="gauge-number">{result.action_proportion_estimate}%</span>
                <span className="gauge-target">Target: 60%</span>
              </div>
              <div className="gauge-track">
                <div
                  className="gauge-fill"
                  style={{
                    width: `${Math.min(100, result.action_proportion_estimate)}%`,
                    backgroundColor:
                      result.action_proportion_estimate >= 50
                        ? '#10b981'
                        : result.action_proportion_estimate >= 35
                        ? '#f59e0b'
                        : '#ef4444',
                  }}
                />
              </div>
            </div>

            {/* Quantified Metrics */}
            <div className="overview-card metrics">
              <span className="overview-title">Metrics & Impact Score</span>
              <div className="metrics-score-display">
                <span className="metrics-score">{result.quantified_metrics_score} / 10</span>
                <TrendingUp size={16} className="text-emerald" />
              </div>
              <div className="detected-metrics-tags">
                {result.metrics_detected.length > 0 ? (
                  result.metrics_detected.map((m, idx) => (
                    <span key={idx} className="metric-chip">
                      {m}
                    </span>
                  ))
                ) : (
                  <span className="no-metrics-warn">No specific numbers or % detected</span>
                )}
              </div>
            </div>

            {/* Ownership Ratio */}
            <div className="overview-card ownership">
              <span className="overview-title">Ownership Agency ("I" vs "We")</span>
              <div className="ownership-ratio-display">
                <UserCheck size={16} className="text-primary" />
                <span>
                  {result.ownership_ratio.i_count} "I" · {result.ownership_ratio.we_count} "We" ({result.ownership_ratio.i_percentage}%)
                </span>
              </div>
              <p className="ownership-hint">
                {result.ownership_ratio.i_percentage < 40
                  ? 'Clarify your individual contributions. Overusing "We" hides your personal impact.'
                  : 'Great personal agency without dismissing team collaboration.'}
              </p>
            </div>
          </div>

          {/* Feedback Lists */}
          <div className="feedback-columns-split">
            {result.strengths.length > 0 && (
              <div className="fb-col strengths">
                <h5>✓ Standout Strengths</h5>
                <ul>
                  {result.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.missing_elements.length > 0 && (
              <div className="fb-col missing">
                <h5>⚠ Gaps & Missing Elements</h5>
                <ul>
                  {result.missing_elements.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.recommendations.length > 0 && (
              <div className="fb-col recommendations">
                <h5>💡 Specific Recommendations</h5>
                <ul>
                  {result.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};
