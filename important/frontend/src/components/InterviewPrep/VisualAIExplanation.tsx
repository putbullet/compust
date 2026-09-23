import React, { useState } from 'react';
import {
  Sparkles,
  Globe,
  Terminal,
  Check,
  Copy,
  CheckCircle2,
  AlertTriangle,
  Award,
  Layers,
  ShieldAlert,
  Server,
  Database,
  User,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
} from 'lucide-react';
import type {
  StructuredAIExplanationPayload,
  Actor,
  ScenarioStep,
  ScenarioVariant,
  QuestionAIExplainResponse,
} from '../../api/client';

interface VisualAIExplanationProps {
  result: QuestionAIExplainResponse;
  renderMarkdown: (markdown: string) => React.ReactNode;
}

export const VisualAIExplanation: React.FC<VisualAIExplanationProps> = ({
  result,
  renderMarkdown,
}) => {
  const [copiedCode, setCopiedCode] = useState(false);
  const [activeVariantIndex, setActiveVariantIndex] = useState(0);
  const [currentPlaybackStep, setCurrentPlaybackStep] = useState(0);
  const [showAllSteps, setShowAllSteps] = useState(true);

  // If there is no structured payload, fall back seamlessly to formatted text
  if (!result.structured_payload) {
    return (
      <div className="ai-fallback-content">
        <div className="ai-markdown-content">{renderMarkdown(result.explanation)}</div>

        {result.real_world_scenario && (
          <div className="ai-scenario-card glass-panel">
            <div className="ai-section-badge scenario">
              <Globe size={15} />
              <span>Real-World Scenario & Practical Analogy</span>
            </div>
            <p className="ai-scenario-text">{result.real_world_scenario}</p>
          </div>
        )}

        {result.code_sample && (
          <div className="ai-code-card glass-panel">
            <div className="ai-code-header">
              <div className="ai-section-badge code">
                <Terminal size={15} />
                <span>Production Implementation / Verification Blueprint</span>
              </div>
              <button
                type="button"
                className="copy-ai-code-btn"
                onClick={() => {
                  navigator.clipboard.writeText(result.code_sample!);
                  setCopiedCode(true);
                  setTimeout(() => setCopiedCode(false), 2000);
                }}
              >
                {copiedCode ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>
            <pre className="ai-code-pre">
              <code>{result.code_sample}</code>
            </pre>
          </div>
        )}

        {result.key_interview_takeaways && result.key_interview_takeaways.length > 0 && (
          <div className="ai-takeaways-card glass-panel">
            <div className="ai-section-badge takeaways">
              <Award size={15} />
              <span>Key Interviewer Talking Points & Evaluation Criteria</span>
            </div>
            <ul className="ai-takeaways-list">
              {result.key_interview_takeaways.map((item, idx) => (
                <li key={idx}>
                  <CheckCircle2 size={14} className="takeaway-icon" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  const payload: StructuredAIExplanationPayload = result.structured_payload;
  const variants: ScenarioVariant[] = payload.scenario?.variants || [];
  const currentVariant = variants[activeVariantIndex] || variants[0];
  const actors: Actor[] = payload.actors || [];
  const steps: ScenarioStep[] = currentVariant?.steps || [];
  const displayedSteps = showAllSteps ? steps : steps.slice(0, currentPlaybackStep + 1);

  // SVG dimensions & layout calculations
  const laneCount = Math.max(1, actors.length);
  const svgWidth = 840;
  const laneWidth = svgWidth / laneCount;
  const rowHeight = 90;
  const svgHeight = Math.max(240, displayedSteps.length * rowHeight + 60);

  const getActorIcon = (role: string) => {
    switch (role) {
      case 'attacker':
        return <ShieldAlert size={16} className="actor-icon attacker" />;
      case 'legitimate_user':
      case 'client':
        return <User size={16} className="actor-icon user" />;
      case 'database':
        return <Database size={16} className="actor-icon database" />;
      default:
        return <Server size={16} className="actor-icon system" />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'attack':
        return '#f43f5e'; // rose red
      case 'blocked':
        return '#ef4444'; // red
      case 'secure':
        return '#10b981'; // emerald
      default:
        return '#38bdf8'; // cyan
    }
  };

  return (
    <div className="visual-ai-explanation-root">
      {/* 1. CONCEPT SUMMARY & ANALOGY BANNER */}
      <div className="ai-concept-analogy-banner glass-panel">
        <div className="concept-block">
          <div className="section-label">
            <Sparkles size={15} className="text-primary" />
            <span>Foundational Engineering Mechanism</span>
          </div>
          <p className="concept-summary-text">{payload.concept_summary}</p>
        </div>

        {payload.analogy && (
          <div className="analogy-block">
            <div className="section-label analogy">
              <Globe size={15} />
              <span>Real-World Intuition & Analogy</span>
            </div>
            <p className="analogy-text">"{payload.analogy}"</p>
          </div>
        )}
      </div>

      {/* 2. SCENARIO SEQUENCE LANE DIAGRAM */}
      <section className="actor-diagram-card glass-panel">
        <div className="diagram-header-row">
          <div className="diagram-title-group">
            <Layers size={18} className="text-primary" />
            <div>
              <h3 className="scenario-title">{payload.scenario?.title || 'Production Execution Flow'}</h3>
              <p className="scenario-subtitle">
                Interactive sequence lane mapping operational requests, failure modes, and architectural protections.
              </p>
            </div>
          </div>

          {/* Variant Selector Tabs */}
          {variants.length > 1 && (
            <div className="variant-tabs-row" role="tablist" aria-label="Scenario Architecture Variants">
              {variants.map((v, vIdx) => {
                const isSelected = activeVariantIndex === vIdx;
                return (
                  <button
                    key={vIdx}
                    type="button"
                    className={`variant-tab-btn ${isSelected ? 'active' : ''} ${v.outcome}`}
                    onClick={() => {
                      setActiveVariantIndex(vIdx);
                      setCurrentPlaybackStep(0);
                    }}
                    role="tab"
                    aria-selected={isSelected}
                  >
                    <span className={`outcome-dot ${v.outcome}`} />
                    <span className="variant-tab-label">{v.label}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Step-Through Playback Controller */}
        <div className="playback-controls-bar">
          <div className="playback-btn-group">
            <button
              type="button"
              className="playback-btn"
              onClick={() => {
                setCurrentPlaybackStep(0);
                setShowAllSteps(false);
              }}
              disabled={currentPlaybackStep === 0 && !showAllSteps}
              title="First Step"
            >
              <SkipBack size={13} />
            </button>
            <button
              type="button"
              className="playback-btn"
              onClick={() => {
                setCurrentPlaybackStep((prev) => Math.max(0, prev - 1));
                setShowAllSteps(false);
              }}
              disabled={currentPlaybackStep === 0 && !showAllSteps}
              title="Previous Step"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="step-counter-text">
              {showAllSteps
                ? `Showing All ${steps.length} Steps`
                : `Step ${currentPlaybackStep + 1} of ${steps.length}`}
            </span>
            <button
              type="button"
              className="playback-btn"
              onClick={() => {
                setCurrentPlaybackStep((prev) => Math.min(steps.length - 1, prev + 1));
                setShowAllSteps(false);
              }}
              disabled={currentPlaybackStep >= steps.length - 1 && !showAllSteps}
              title="Next Step"
            >
              <ChevronRight size={14} />
            </button>
            <button
              type="button"
              className="playback-btn"
              onClick={() => {
                setCurrentPlaybackStep(steps.length - 1);
                setShowAllSteps(false);
              }}
              disabled={currentPlaybackStep >= steps.length - 1 && !showAllSteps}
              title="Last Step"
            >
              <SkipForward size={13} />
            </button>
          </div>

          <button
            type="button"
            className={`mode-toggle-btn ${showAllSteps ? 'active' : ''}`}
            onClick={() => setShowAllSteps((prev) => !prev)}
            title="Toggle between seeing all steps and stepping through one by one"
          >
            {showAllSteps ? <EyeOff size={13} /> : <Eye size={13} />}
            <span>{showAllSteps ? 'Step-by-Step Playback' : 'Show Complete Sequence'}</span>
          </button>
        </div>

        {/* Top Actor Lanes Header */}
        <div className="actor-lanes-header-row">
          {actors.map((actor) => (
            <div key={actor.id} className={`actor-lane-card ${actor.role}`}>
              <div className="actor-icon-box">{getActorIcon(actor.role)}</div>
              <div className="actor-meta">
                <span className="actor-label">{actor.label}</span>
                <span className="actor-role-chip">{actor.role.replace('_', ' ')}</span>
                <span className="actor-desc">{actor.description}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Pure SVG Sequence Lane Diagram */}
        <div className="diagram-svg-scroll-container">
          <svg
            className="sequence-lane-svg"
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            width="100%"
            height={svgHeight}
            aria-label="Sequence Lane Flowchart"
          >
            <defs>
              <marker
                id="arrow-normal"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
              </marker>
              <marker
                id="arrow-attack"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
              </marker>
              <marker
                id="arrow-secure"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
              </marker>
              <marker
                id="arrow-blocked"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
              </marker>
            </defs>

            {/* Vertical Lifelines */}
            {actors.map((actor, aIdx) => {
              const x = (aIdx + 0.5) * laneWidth;
              return (
                <line
                  key={actor.id}
                  x1={x}
                  y1={8}
                  x2={x}
                  y2={svgHeight - 12}
                  stroke="rgba(255, 255, 255, 0.12)"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                />
              );
            })}

            {/* Step Sequence Arrows */}
            {displayedSteps.map((step, sIdx) => {
              const fromId = step.from || (step as any).from_actor;
              const toId = step.to || (step as any).to_actor;

              let fi = actors.findIndex((a) => a.id === fromId);
              let ti = actors.findIndex((a) => a.id === toId);
              if (fi === -1) fi = 0;
              if (ti === -1) ti = Math.min(1, actors.length - 1);

              const x1 = (fi + 0.5) * laneWidth;
              const x2 = (ti + 0.5) * laneWidth;
              const y = 50 + sIdx * rowHeight;
              const midX = (x1 + x2) / 2;
              const statusColor = getStatusColor(step.status);
              const isSelf = fi === ti;

              return (
                <g key={sIdx} className={`step-arrow-group status-${step.status || 'normal'}`}>
                  {isSelf ? (
                    <path
                      d={`M ${x1} ${y - 12} C ${x1 + 65} ${y - 28}, ${x1 + 65} ${y + 20}, ${x1 + 8} ${y + 14}`}
                      fill="none"
                      stroke={statusColor}
                      strokeWidth={2.5}
                      strokeDasharray={step.status === 'attack' ? '5 3' : undefined}
                      markerEnd={`url(#arrow-${step.status || 'normal'})`}
                    />
                  ) : (
                    <line
                      x1={x1}
                      y1={y}
                      x2={x2 > x1 ? x2 - 12 : x2 + 12}
                      y2={y}
                      stroke={statusColor}
                      strokeWidth={2.5}
                      strokeDasharray={step.status === 'attack' ? '5 3' : undefined}
                      markerEnd={step.status !== 'blocked' ? `url(#arrow-${step.status || 'normal'})` : undefined}
                    />
                  )}

                  {/* Blocked marker ✕ */}
                  {step.status === 'blocked' && (
                    <g transform={`translate(${x2}, ${y})`}>
                      <circle r={9} fill="#ef4444" />
                      <text y={3.5} textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">
                        ✕
                      </text>
                    </g>
                  )}

                  {/* Secure checkmark ✓ */}
                  {step.status === 'secure' && (
                    <g transform={`translate(${x2}, ${y})`}>
                      <circle r={8} fill="#10b981" />
                      <text y={3} textAnchor="middle" fill="#ffffff" fontSize="9" fontWeight="bold">
                        ✓
                      </text>
                    </g>
                  )}

                  {/* Step order circle */}
                  <g transform={`translate(${isSelf ? x1 + 35 : midX}, ${y - 18})`}>
                    <circle r={9} fill="#0f172a" stroke={statusColor} strokeWidth={1.5} />
                    <text y={3.5} textAnchor="middle" fill={statusColor} fontSize="9" fontWeight="bold">
                      {step.order}
                    </text>
                  </g>

                  {/* Action label */}
                  <text
                    x={isSelf ? x1 + 75 : midX}
                    y={y - 7}
                    textAnchor={isSelf ? 'start' : 'middle'}
                    fill="#f8fafc"
                    fontSize="11"
                    fontWeight="600"
                  >
                    {step.action}
                  </text>

                  {/* Payload badge */}
                  {step.payload && (
                    <g transform={`translate(${isSelf ? x1 + 75 : midX}, ${y + 14})`}>
                      <rect
                        x={-55}
                        y={-8}
                        width={110}
                        height={16}
                        rx={4}
                        fill="#0b1120"
                        stroke={statusColor}
                        strokeWidth={0.8}
                      />
                      <text y={4} textAnchor="middle" fill={statusColor} fontSize="9" fontWeight="500">
                        {step.payload.length > 28 ? step.payload.slice(0, 26) + '…' : step.payload}
                      </text>
                    </g>
                  )}

                  {/* Annotation note */}
                  {step.annotation && (
                    <text
                      x={isSelf ? x1 + 75 : midX}
                      y={y + 30}
                      textAnchor={isSelf ? 'start' : 'middle'}
                      fill="#94a3b8"
                      fontSize="9.5"
                      fontStyle="italic"
                    >
                      {step.annotation}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Accessible Step Breakdown Cards */}
        <div className="step-breakdown-details-list">
          <span className="breakdown-list-title">Sequence Step Ledger:</span>
          <div className="breakdown-cards-grid">
            {displayedSteps.map((step, idx) => {
              const fromId = step.from || (step as any).from_actor;
              const toId = step.to || (step as any).to_actor;
              const fromLabel = actors.find((a) => a.id === fromId)?.label || fromId;
              const toLabel = actors.find((a) => a.id === toId)?.label || toId;

              return (
                <div key={idx} className={`step-ledger-card status-${step.status || 'normal'}`}>
                  <div className="step-ledger-head">
                    <span className="step-num-pill">#{step.order}</span>
                    <span className="step-route">
                      {fromLabel} → {toLabel}
                    </span>
                    <span className={`step-status-tag ${step.status || 'normal'}`}>{step.status || 'normal'}</span>
                  </div>
                  <p className="step-action-desc">{step.action}</p>
                  {step.payload && (
                    <div className="step-payload-row">
                      <span className="payload-label">Data Payload:</span>
                      <code>{step.payload}</code>
                    </div>
                  )}
                  {step.annotation && <p className="step-annotation-text">💡 {step.annotation}</p>}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 3. SYNTAX-ANNOTATED CODE PANEL (HIDDEN IF NULL) */}
      {payload.code_sample && (
        <section className="ai-code-card visual glass-panel">
          <div className="ai-code-header">
            <div className="ai-section-badge code">
              <Terminal size={15} />
              <span>Production Implementation & Verification Blueprint</span>
              <span className="lang-tag">{payload.code_sample.language.toUpperCase()}</span>
            </div>
            <button
              type="button"
              className="copy-ai-code-btn"
              onClick={() => {
                navigator.clipboard.writeText(payload.code_sample!.code);
                setCopiedCode(true);
                setTimeout(() => setCopiedCode(false), 2000);
              }}
            >
              {copiedCode ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
              <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
            </button>
          </div>

          <div className="annotated-code-container">
            {payload.code_sample.code.split('\n').map((lineText, idx) => {
              const lineNum = idx + 1;
              const noteObj = payload.code_sample!.explanation_lines?.find((el) => el.line === lineNum);
              return (
                <div key={idx} className={`annotated-code-row ${noteObj ? 'has-note' : ''}`}>
                  <div className="code-line-gutter">
                    <span className="gutter-num">{lineNum}</span>
                    {noteObj && <span className="gutter-dot" title={`Line ${lineNum} Note`} />}
                  </div>
                  <div className="code-line-content">
                    <span className="code-text">{lineText || ' '}</span>
                    {noteObj && (
                      <div className="inline-gutter-note">
                        <span className="note-badge">Line {lineNum} Insight:</span>
                        <span className="note-text">{noteObj.note}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 4. TECHNICAL COMPARISON TABLE */}
      {payload.comparison_table && payload.comparison_table.length > 0 && (
        <section className="ai-comparison-card glass-panel">
          <div className="ai-section-badge comparison">
            <Layers size={15} />
            <span>Architectural Trade-off & Engineering Comparison</span>
          </div>
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th className="th-criterion">Evaluation Criterion</th>
                  <th className="th-option-a">Option A (Naive / Vulnerable)</th>
                  <th className="th-option-b">Option B (Production / Hardened)</th>
                </tr>
              </thead>
              <tbody>
                {payload.comparison_table.map((row, rIdx) => (
                  <tr key={rIdx}>
                    <td className="td-criterion">{row.criterion}</td>
                    <td className="td-option-a">{row.option_a}</td>
                    <td className="td-option-b">{row.option_b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 5. INTERVIEW TAKEAWAYS & TRAPS GRID */}
      <div className="ai-insights-split-grid">
        {payload.takeaways && payload.takeaways.length > 0 && (
          <div className="ai-insights-box takeaways glass-panel">
            <div className="insights-head">
              <Award size={15} className="text-emerald" />
              <h5>Key Interviewer Talking Points</h5>
            </div>
            <ul className="insights-list">
              {payload.takeaways.map((item, idx) => (
                <li key={idx}>
                  <CheckCircle2 size={14} className="icon-point" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {payload.common_mistakes && payload.common_mistakes.length > 0 && (
          <div className="ai-insights-box mistakes glass-panel">
            <div className="insights-head">
              <AlertTriangle size={15} className="text-amber" />
              <h5>Common Candidate Traps & Anti-patterns</h5>
            </div>
            <ul className="insights-list">
              {payload.common_mistakes.map((item, idx) => (
                <li key={idx}>
                  <span className="trap-bullet">⚠</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
