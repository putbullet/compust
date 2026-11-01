import React, { useState } from 'react';
import styled from 'styled-components';
import {
  Sparkles,
  Globe,
  Terminal,
  Check,
  Copy,
  Layers,
  ChevronRight,
  RefreshCw,
  Sliders,
  AlertCircle,
  HelpCircle,
  Maximize2,
  Minimize2,
  BookOpen,
} from 'lucide-react';
import type {
  QuestionExplanationResponse,
  QuestionDeepDivePayload,
  QuestionAIExplainResponse,
} from '../../api/client';

interface VisualAIExplanationProps {
  preExplanation?: QuestionExplanationResponse | null;
  deepDive?: QuestionDeepDivePayload | null;
  deepDiveLoading?: boolean;
  deepDiveError?: string | null;
  canRetry?: boolean;
  activeProvider?: string | null;
  activeModel?: string | null;
  language?: string;
  onRetryDeepDive?: () => void;
  onOpenAISettings?: () => void;
  renderMarkdown: (markdown: string) => React.ReactNode;
  // Backward compatibility
  result?: QuestionAIExplainResponse;
}

const UI_TEXT: Record<string, Record<string, string>> = {
  en: {
    coreBadge: 'VERIFIED PRE-EXPLANATION',
    tldrLabel: 'Core Takeaway (TL;DR)',
    conceptLabel: 'Foundational Mechanism',
    scenarioLabel: 'Real-World Scenario & Intuition',
    pitfallsLabel: 'Why It Matters & Pitfalls',
    keyTermsLabel: 'Key Terminology',
    codeLabel: 'Code Blueprint',
    diagramLabel: 'Architecture Diagram',
    deepDiveTitle: 'AI TECHNICAL DEEP DIVE',
    deepDiveGoing: 'Going deeper with',
    deepDiveUnavailable: 'Deep dive unavailable',
    retry: 'Retry',
    aiSettings: 'Configure AI',
    mechanicsLabel: 'Advanced Mechanics & Internals',
    extraScenarioLabel: 'Production Incident & Edge Case',
    pitfallsHeader: 'Critical Engineering Pitfalls',
    followupsHeader: 'Likely Interview Follow-Up Questions',
    noPreExp: 'No verified pre-explanation authored for this question yet.',
    noPreExpSub: 'Connect an AI provider in settings to generate an on-demand deep dive.',
    copyCode: 'Copy Code',
    copied: 'Copied!',
    expand: 'Expand Diagram',
    shrink: 'Close Zoom',
  },
  fr: {
    coreBadge: 'EXPLICATION FONDAMENTALE VALIDÉE',
    tldrLabel: "L'Essentiel (TL;DR)",
    conceptLabel: 'Mécanisme Fondamental',
    scenarioLabel: 'Scénario Concret & Analogie',
    pitfallsLabel: 'Enjeux & Pièges Courants',
    keyTermsLabel: 'Termes Clés',
    codeLabel: 'Exemple de Code',
    diagramLabel: 'Diagramme d\'Architecture',
    deepDiveTitle: 'ANALYSE TECHNIQUE APPROFONDIE (IA)',
    deepDiveGoing: 'Approfondissement avec',
    deepDiveUnavailable: 'Approfondissement IA indisponible',
    retry: 'Réessayer',
    aiSettings: "Configurer l'IA",
    mechanicsLabel: 'Mécanique Avancée & Fonctionnement Interne',
    extraScenarioLabel: 'Cas Pratique en Production & Cas Limite',
    pitfallsHeader: "Pièges d'Ingénierie à Éviter",
    followupsHeader: "Questions de Relance en Entretien",
    noPreExp: 'Aucune explication hors ligne disponible pour cette question pour le moment.',
    noPreExpSub: "Connectez un fournisseur d'IA dans les paramètres pour générer une analyse.",
    copyCode: 'Copier',
    copied: 'Copié !',
    expand: 'Agrandir',
    shrink: 'Fermer Zoom',
  },
  nl: {
    coreBadge: 'GEVERIFIEERDE KERNUITLEG',
    tldrLabel: 'Belangrijkste Inzicht (TL;DR)',
    conceptLabel: 'Kernmechanisme',
    scenarioLabel: 'Praktijkvoorbeeld & Scenario',
    pitfallsLabel: 'Waarom Dit Telt & Veelgemaakte Fouten',
    keyTermsLabel: 'Kernbegrippen',
    codeLabel: 'Code Voorbeeld',
    diagramLabel: 'Architectuurdiagram',
    deepDiveTitle: 'AI TECHNISCHE VERDIEPING',
    deepDiveGoing: 'Dieper ingaan met',
    deepDiveUnavailable: 'AI-verdieping niet beschikbaar',
    retry: 'Opnieuw proberen',
    aiSettings: 'AI configureren',
    mechanicsLabel: 'Geavanceerde Werking & Internals',
    extraScenarioLabel: 'Productiescenario & Randgeval',
    pitfallsHeader: 'Valkuilen om te Vermijden',
    followupsHeader: 'Mogelijke Vervolgvragen in Interview',
    noPreExp: 'Voor deze vraag is offline nog geen uitleg beschikbaar.',
    noPreExpSub: 'Koppel een AI-provider in instellingen voor een analyse op maat.',
    copyCode: 'Kopiëren',
    copied: 'Gekopieerd!',
    expand: 'Vergroten',
    shrink: 'Sluiten',
  },
  de: {
    coreBadge: 'VERIFIZIERTE GRUNDERKLÄRUNG',
    tldrLabel: 'Kernbotschaft (TL;DR)',
    conceptLabel: 'Grundlegender Mechanismus',
    scenarioLabel: 'Praxisbeispiel & Alltagsanalogie',
    pitfallsLabel: 'Warum es zählt & Fallstricke',
    keyTermsLabel: 'Schlüsselbegriffe',
    codeLabel: 'Code-Blaupause',
    diagramLabel: 'Architekturdiagramm',
    deepDiveTitle: 'TECHNISCHER AI-DEEP-DIVE',
    deepDiveGoing: 'Vertiefung mit',
    deepDiveUnavailable: 'AI-Vertiefung nicht verfügbar',
    retry: 'Wiederholen',
    aiSettings: 'AI konfigurieren',
    mechanicsLabel: 'Fortgeschrittene Mechanismen & Interna',
    extraScenarioLabel: 'Produktionsszenario & Grenzfall',
    pitfallsHeader: 'Kritische Fallstricke in der Praxis',
    followupsHeader: 'Häufige Nachfragen im Interview',
    noPreExp: 'Für diese Frage liegt offline noch keine vorgefertigte Erklärung vor.',
    noPreExpSub: 'Verbinden Sie einen AI-Anbieter in den Einstellungen für einen Deep-Dive.',
    copyCode: 'Kopieren',
    copied: 'Kopiert!',
    expand: 'Vergrößern',
    shrink: 'Schließen',
  },
};

export const VisualAIExplanation: React.FC<VisualAIExplanationProps> = ({
  preExplanation,
  deepDive,
  deepDiveLoading = false,
  deepDiveError = null,
  canRetry = false,
  activeProvider = 'ollama',
  activeModel = 'qwen3.5:0.8b',
  language = 'en',
  onRetryDeepDive,
  onOpenAISettings,
  renderMarkdown,
  result,
}) => {
  const [copiedPreCode, setCopiedPreCode] = useState(false);
  const [copiedDeepCode, setCopiedDeepCode] = useState(false);
  const [diagramExpanded, setDiagramExpanded] = useState(false);

  const lang = (language || 'en').toLowerCase().slice(0, 2);
  const t = UI_TEXT[lang] || UI_TEXT.en;

  const providerLabel = activeProvider === 'gemini'
    ? 'Google Gemini'
    : activeProvider === 'openai'
    ? 'OpenAI'
    : 'Ollama';

  // 1. Backward compatibility adapter if legacy QuestionAIExplainResponse was passed
  const hasLegacyPayload = Boolean(result?.structured_payload);
  const legacyPayload = result?.structured_payload;

  return (
    <RootContainer className="visual-ai-explanation-root">
      {/* ─── SECTION 1: INSTANT PRE-EXPLANATION ──────────────────────────── */}
      {preExplanation && preExplanation.has_pre_explanation ? (
        <PreExplanationSection className="pre-explanation-card">
          <SectionHeaderBadge>
            <BookOpen size={14} className="badge-icon" />
            <span>{t.coreBadge} {preExplanation.tier ? `· TIER ${preExplanation.tier}` : ''}</span>
          </SectionHeaderBadge>

          {/* TL;DR Box */}
          {preExplanation.tldr && (
            <TldrBox className="tldr-box glass-panel">
              <div className="box-title">
                <Sparkles size={14} className="text-accent" />
                <span>{t.tldrLabel}</span>
              </div>
              <p className="tldr-text">{preExplanation.tldr}</p>
            </TldrBox>
          )}

          {/* Core Concept */}
          {preExplanation.simple_explanation && (
            <ContentCard className="concept-card glass-panel">
              <div className="card-header">
                <span className="card-title">{t.conceptLabel}</span>
              </div>
              <div className="card-body">
                {renderMarkdown(preExplanation.simple_explanation)}
              </div>
            </ContentCard>
          )}

          {/* Real-World Scenario */}
          {preExplanation.real_world_example && (
            <ContentCard className="scenario-card glass-panel">
              <div className="card-header">
                <Globe size={15} className="text-secondary" />
                <span className="card-title">{t.scenarioLabel}</span>
              </div>
              <div className="card-body scenario-body">
                {renderMarkdown(preExplanation.real_world_example)}
              </div>
            </ContentCard>
          )}

          {/* Why It Matters & Pitfalls */}
          {preExplanation.why_it_matters_and_pitfalls && (
            <ContentCard className="pitfalls-card glass-panel">
              <div className="card-header">
                <AlertCircle size={15} className="text-warning" />
                <span className="card-title">{t.pitfallsLabel}</span>
              </div>
              <div className="card-body">
                {renderMarkdown(preExplanation.why_it_matters_and_pitfalls)}
              </div>
            </ContentCard>
          )}

          {/* Key Terminology Pills */}
          {preExplanation.key_terms && preExplanation.key_terms.length > 0 && (
            <KeyTermsRow className="key-terms-row">
              <span className="terms-label">{t.keyTermsLabel}:</span>
              <div className="terms-chips">
                {preExplanation.key_terms.map((term, i) => (
                  <span key={i} className="term-chip">{term}</span>
                ))}
              </div>
            </KeyTermsRow>
          )}

          {/* Code Blueprint - ONLY WHEN FLAGGED */}
          {preExplanation.needs_code && preExplanation.code_snippet && (
            <CodeBox className="code-box glass-panel">
              <div className="code-header">
                <div className="code-lang-tag">
                  <Terminal size={14} />
                  <span>{preExplanation.code_language ? preExplanation.code_language.toUpperCase() : 'SNIPPET'}</span>
                </div>
                <button
                  type="button"
                  className="copy-btn"
                  onClick={() => {
                    navigator.clipboard.writeText(preExplanation.code_snippet!);
                    setCopiedPreCode(true);
                    setTimeout(() => setCopiedPreCode(false), 2000);
                  }}
                  aria-label="Copy code snippet"
                >
                  {copiedPreCode ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                  <span>{copiedPreCode ? t.copied : t.copyCode}</span>
                </button>
              </div>
              <pre className="code-pre">
                <code>{preExplanation.code_snippet}</code>
              </pre>
            </CodeBox>
          )}

          {/* Architectural SVG Diagram - ONLY WHEN FLAGGED */}
          {preExplanation.needs_diagram && preExplanation.diagram_svg && (
            <DiagramContainer className={`diagram-container glass-panel ${diagramExpanded ? 'expanded' : ''}`}>
              <div className="diagram-header">
                <div className="diagram-title-row">
                  <Layers size={15} className="text-accent" />
                  <span>{preExplanation.diagram_caption || t.diagramLabel}</span>
                </div>
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => setDiagramExpanded((prev) => !prev)}
                  title={diagramExpanded ? t.shrink : t.expand}
                >
                  {diagramExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                  <span>{diagramExpanded ? t.shrink : t.expand}</span>
                </button>
              </div>
              <div
                className="svg-rendered-wrapper"
                dangerouslySetInnerHTML={{ __html: preExplanation.diagram_svg }}
              />
            </DiagramContainer>
          )}
        </PreExplanationSection>
      ) : hasLegacyPayload && legacyPayload ? (
        /* Legacy fallback representation */
        <PreExplanationSection className="pre-explanation-card">
          <TldrBox className="tldr-box glass-panel">
            <div className="box-title">
              <Sparkles size={14} className="text-accent" />
              <span>{t.tldrLabel}</span>
            </div>
            <p className="tldr-text">{legacyPayload.concept_summary}</p>
          </TldrBox>
          {legacyPayload.analogy && (
            <ContentCard className="scenario-card glass-panel">
              <div className="card-header">
                <Globe size={15} className="text-secondary" />
                <span className="card-title">{t.scenarioLabel}</span>
              </div>
              <div className="card-body scenario-body">
                <p>"{legacyPayload.analogy}"</p>
              </div>
            </ContentCard>
          )}
        </PreExplanationSection>
      ) : !deepDive && !deepDiveLoading ? (
        <EmptyStateCard className="empty-state-card glass-panel">
          <BookOpen size={28} className="empty-icon" />
          <h4 className="empty-title">{t.noPreExp}</h4>
          <p className="empty-sub">{t.noPreExpSub}</p>
          {onOpenAISettings && (
            <button type="button" className="action-link-btn" onClick={onOpenAISettings}>
              <Sliders size={14} />
              <span>{t.aiSettings}</span>
            </button>
          )}
        </EmptyStateCard>
      ) : null}

      {/* ─── SECTION 2: AI DEEP DIVE ─────────────────────────────────────── */}
      {deepDiveLoading && (
        <DeepDiveLoadingBox className="deep-dive-loading glass-panel">
          <div className="spinner" />
          <div className="loading-text">
            <span>{t.deepDiveGoing} <strong>{providerLabel} · {activeModel}</strong>…</span>
          </div>
        </DeepDiveLoadingBox>
      )}

      {deepDive && (
        <DeepDiveSection className="deep-dive-section">
          <DeepDiveDivider>
            <span className="divider-line" />
            <div className="divider-badge">
              <Sparkles size={14} />
              <span>{t.deepDiveTitle} · {providerLabel} ({activeModel})</span>
            </div>
            <span className="divider-line" />
          </DeepDiveDivider>

          {/* Advanced Mechanics */}
          <ContentCard className="mechanics-card glass-panel">
            <div className="card-header">
              <span className="card-title">{t.mechanicsLabel}</span>
            </div>
            <div className="card-body">
              {renderMarkdown(deepDive.deeper_explanation)}
            </div>
          </ContentCard>

          {/* Production Incident & Edge Case */}
          {deepDive.extra_example && (
            <ContentCard className="scenario-card glass-panel">
              <div className="card-header">
                <Globe size={15} className="text-secondary" />
                <span className="card-title">{t.extraScenarioLabel}</span>
              </div>
              <div className="card-body">
                {renderMarkdown(deepDive.extra_example)}
              </div>
            </ContentCard>
          )}

          {/* Critical Pitfalls */}
          {deepDive.pitfalls && deepDive.pitfalls.length > 0 && (
            <ContentCard className="pitfalls-card glass-panel">
              <div className="card-header">
                <AlertCircle size={15} className="text-warning" />
                <span className="card-title">{t.pitfallsHeader}</span>
              </div>
              <ul className="bullet-list">
                {deepDive.pitfalls.map((p, idx) => (
                  <li key={idx}>{renderMarkdown(p)}</li>
                ))}
              </ul>
            </ContentCard>
          )}

          {/* Interviewer Follow-Up Questions */}
          {deepDive.interview_followups && deepDive.interview_followups.length > 0 && (
            <ContentCard className="followups-card glass-panel">
              <div className="card-header">
                <HelpCircle size={15} className="text-accent" />
                <span className="card-title">{t.followupsHeader}</span>
              </div>
              <ul className="bullet-list followups-list">
                {deepDive.interview_followups.map((q, idx) => (
                  <li key={idx}>
                    <ChevronRight size={14} className="followup-arrow" />
                    <span>{renderMarkdown(q)}</span>
                  </li>
                ))}
              </ul>
            </ContentCard>
          )}

          {/* Optional Code from Deep Dive - ONLY WHEN FLAGGED/NEEDED */}
          {deepDive.has_code && deepDive.code_snippet && (
            <CodeBox className="code-box glass-panel">
              <div className="code-header">
                <div className="code-lang-tag">
                  <Terminal size={14} />
                  <span>{deepDive.code_language ? deepDive.code_language.toUpperCase() : 'CODE'}</span>
                </div>
                <button
                  type="button"
                  className="copy-btn"
                  onClick={() => {
                    navigator.clipboard.writeText(deepDive.code_snippet!);
                    setCopiedDeepCode(true);
                    setTimeout(() => setCopiedDeepCode(false), 2000);
                  }}
                  aria-label="Copy deep dive code"
                >
                  {copiedDeepCode ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                  <span>{copiedDeepCode ? t.copied : t.copyCode}</span>
                </button>
              </div>
              <pre className="code-pre">
                <code>{deepDive.code_snippet}</code>
              </pre>
            </CodeBox>
          )}

          {/* Optional Diagram from Deep Dive - ONLY WHEN FLAGGED/NEEDED */}
          {deepDive.has_diagram && deepDive.diagram_svg && (
            <DiagramContainer className="diagram-container glass-panel">
              <div className="diagram-header">
                <div className="diagram-title-row">
                  <Layers size={15} className="text-accent" />
                  <span>{t.diagramLabel}</span>
                </div>
              </div>
              <div
                className="svg-rendered-wrapper"
                dangerouslySetInnerHTML={{ __html: deepDive.diagram_svg }}
              />
            </DiagramContainer>
          )}
        </DeepDiveSection>
      )}

      {/* Neutral Status Note when Deep Dive is Unavailable */}
      {deepDiveError && (
        <NeutralNoteBox className="deep-dive-neutral-note">
          <div className="note-left">
            <AlertCircle size={14} className="note-icon" />
            <span className="note-text">
              {t.deepDiveUnavailable}: {deepDiveError}
            </span>
          </div>
          <div className="note-actions">
            {canRetry && onRetryDeepDive && (
              <button type="button" className="retry-btn" onClick={onRetryDeepDive}>
                <RefreshCw size={12} />
                <span>{t.retry}</span>
              </button>
            )}
            {onOpenAISettings && (
              <button type="button" className="settings-link-btn" onClick={onOpenAISettings}>
                <span>{t.aiSettings}</span>
              </button>
            )}
          </div>
        </NeutralNoteBox>
      )}
    </RootContainer>
  );
};

// ─── STYLES (Theme-safe with CSS variables, accessible in dark and light modes) ─

const RootContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  color: var(--text-primary, #f1f5f9);
`;

const PreExplanationSection = styled.section`
  display: flex;
  flex-direction: column;
  gap: 14px;
`;

const SectionHeaderBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  background: rgba(56, 189, 248, 0.12);
  color: var(--accent-color, #38bdf8);
  border: 1px solid rgba(56, 189, 248, 0.25);
`;

const TldrBox = styled.div`
  padding: 14px 18px;
  border-radius: 10px;
  background: var(--card-bg, rgba(30, 41, 59, 0.6));
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.15));
  border-left: 4px solid var(--accent-color, #38bdf8);

  .box-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--accent-color, #38bdf8);
    margin-bottom: 6px;
  }

  .tldr-text {
    font-size: 0.95rem;
    line-height: 1.5;
    font-weight: 500;
    color: var(--text-primary, #f8fafc);
    margin: 0;
  }
`;

const ContentCard = styled.div`
  padding: 16px 18px;
  border-radius: 10px;
  background: var(--card-bg, rgba(30, 41, 59, 0.5));
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.12));

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-secondary, #94a3b8);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .card-body {
    font-size: 0.92rem;
    line-height: 1.6;
    color: var(--text-primary, #e2e8f0);

    p {
      margin: 0 0 8px 0;
      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  .bullet-list {
    margin: 0;
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text-primary, #e2e8f0);
  }

  .followups-list {
    list-style: none;
    padding-left: 0;

    li {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      margin-bottom: 8px;

      .followup-arrow {
        color: var(--accent-color, #38bdf8);
        flex-shrink: 0;
        margin-top: 3px;
      }
    }
  }
`;

const KeyTermsRow = styled.div`
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  font-size: 0.82rem;

  .terms-label {
    font-weight: 700;
    color: var(--text-secondary, #94a3b8);
  }

  .terms-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .term-chip {
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(148, 163, 184, 0.12);
    color: var(--text-primary, #cbd5e1);
    border: 1px solid rgba(148, 163, 184, 0.2);
  }
`;

const CodeBox = styled.div`
  border-radius: 8px;
  overflow: hidden;
  background: var(--code-bg, #0b1120);
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.18));

  .code-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: rgba(0, 0, 0, 0.2);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .code-lang-tag {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--accent-color, #38bdf8);
      letter-spacing: 0.05em;
    }

    .copy-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: var(--text-secondary, #94a3b8);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
      }
    }
  }

  .code-pre {
    margin: 0;
    padding: 14px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.85rem;
    line-height: 1.5;
    color: #e2e8f0;
  }
`;

const DiagramContainer = styled.div`
  border-radius: 10px;
  padding: 14px;
  background: var(--card-bg, rgba(30, 41, 59, 0.6));
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.15));
  transition: all 0.3s ease;

  &.expanded {
    position: fixed;
    top: 5vh;
    left: 5vw;
    right: 5vw;
    bottom: 5vh;
    z-index: 1000;
    background: var(--modal-bg, #0f172a);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
    overflow: auto;
    display: flex;
    flex-direction: column;
  }

  .diagram-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .diagram-title-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-primary, #f1f5f9);
    }

    .zoom-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      background: transparent;
      border: 1px solid var(--border-color, rgba(255, 255, 255, 0.15));
      color: var(--text-secondary, #94a3b8);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
      }
    }
  }

  .svg-rendered-wrapper {
    display: flex;
    justify-content: center;
    overflow-x: auto;
    padding: 8px;

    svg {
      max-width: 100%;
      height: auto;
    }
  }
`;

const DeepDiveLoadingBox = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);

  .spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(56, 189, 248, 0.3);
    border-top-color: #38bdf8;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .loading-text {
    font-size: 0.88rem;
    color: var(--text-primary, #f1f5f9);
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

const DeepDiveSection = styled.section`
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: fadeIn 0.3s ease;

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const DeepDiveDivider = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0 6px 0;

  .divider-line {
    flex: 1;
    height: 1px;
    background: var(--border-color, rgba(148, 163, 184, 0.2));
  }

  .divider-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent-color, #38bdf8);
    letter-spacing: 0.05em;
  }
`;

const NeutralNoteBox = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.15);
  font-size: 0.82rem;
  color: var(--text-secondary, #94a3b8);

  .note-left {
    display: flex;
    align-items: center;
    gap: 6px;

    .note-icon {
      flex-shrink: 0;
    }
  }

  .note-actions {
    display: flex;
    align-items: center;
    gap: 8px;

    .retry-btn, .settings-link-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: transparent;
      border: 1px solid rgba(148, 163, 184, 0.3);
      color: var(--text-primary, #f1f5f9);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.08);
      }
    }
  }
`;

const EmptyStateCard = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  text-align: center;
  border-radius: 10px;

  .empty-icon {
    color: var(--text-secondary, #94a3b8);
    margin-bottom: 12px;
  }

  .empty-title {
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 6px 0;
    color: var(--text-primary, #f1f5f9);
  }

  .empty-sub {
    font-size: 0.85rem;
    color: var(--text-secondary, #94a3b8);
    margin: 0 0 16px 0;
    max-width: 440px;
  }

  .action-link-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(56, 189, 248, 0.15);
    color: var(--accent-color, #38bdf8);
    border: 1px solid rgba(56, 189, 248, 0.3);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;

    &:hover {
      background: rgba(56, 189, 248, 0.25);
    }
  }
`;
