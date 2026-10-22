import React, { useState, useEffect } from 'react';
import {
  BrainCircuit,
  Search,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Sparkles,
  ExternalLink,
  Copy,
  Check,
  Bookmark,
  BookmarkCheck,
  Layers,
  ArrowRight,
  Terminal,
  FileText,
  HelpCircle,
  Clock,
  Bot,
  Loader2,
  X,
  Briefcase,
  GraduationCap,
  Mic,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  BehavioralPrepResponse,
  InterviewDomainSummary,
  InterviewDomainTree,
  InterviewQuestionDetail,
  InterviewQuestionSummary,
  QuestionAIExplainResponse,
} from '../../api/client';
import {
  STARProportionBar,
  ExpandableSTARCards,
  StoryThemeCoverageMatrix,
  STAREvaluatorWidget,
} from './STARVisuals';
import { VisualAIExplanation } from './VisualAIExplanation';
import { MockInterviewView } from './MockInterviewView';
import { StageProgressList, useStageProgress } from '../common/StageProgressList';
import { useTranslation } from '../../i18n';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import './InterviewPrepView.css';

const AI_EXPLAIN_STAGES = [
  'Connecting to active AI gateway...',
  'Analyzing question domain & technical requirements...',
  'Synthesizing real-world scenario & practical analogy...',
  'Validating architecture & visual SVG diagram...',
  'Finalizing structured breakdown & interview takeaways...',
];

export const STAR_TARGET_SPLIT = {
  situation: 15,
  task: 10,
  action: 60,
  result: 15,
};

interface InterviewPrepViewProps {
  onNavigateToProfile?: () => void;
}

type PrepTab = 'behavioral' | 'technical' | 'mock_interview';
type SupportedPrepLang = 'en' | 'fr' | 'de';

export const InterviewPrepView: React.FC<InterviewPrepViewProps> = ({ onNavigateToProfile }) => {
  const { language } = useTranslation();
  // Navigation & Language state synchronized with global switcher
  const [activeTab, setActiveTab] = useState<PrepTab>('behavioral');
  const prepLanguage: SupportedPrepLang = language === 'fr' ? 'fr' : 'en';

  // Behavioral Prep data
  const [behavioralData, setBehavioralData] = useState<BehavioralPrepResponse | null>(null);
  const [loadingBehavioral, setLoadingBehavioral] = useState(false);
  const [expandedQuestionId, setExpandedQuestionId] = useState<string | null>('q1');
  const [expandedStarStep, setExpandedStarStep] = useState<string | null>('Action');
  const [expandedAnchorIndex, setExpandedAnchorIndex] = useState<number | null>(0);

  // Technical Prep data
  const [domains, setDomains] = useState<InterviewDomainSummary[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState<string>('security_engineering');
  const [domainTree, setDomainTree] = useState<InterviewDomainTree | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [heroImageError, setHeroImageError] = useState(false);

  // Active question viewer
  const [activeQuestionSlug, setActiveQuestionSlug] = useState<string>('oauth2-pkce-architecture');
  const [activeQuestion, setActiveQuestion] = useState<InterviewQuestionDetail | null>(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);

  // Search & Filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<InterviewQuestionSummary[]>([]);
  const [searching, setSearching] = useState(false);

  // User Local Progress: Bookmarks & Reviewed Questions
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('compust_prep_bookmarks');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  const [reviewedIds, setReviewedIds] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('compust_prep_reviewed');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  // AI Explanation State
  const [aiExplainLoading, setAiExplainLoading] = useState(false);
  const [aiExplainResult, setAiExplainResult] = useState<QuestionAIExplainResponse | null>(null);
  const [userDraftAnswer, setUserDraftAnswer] = useState('');
  const [showAiModal, setShowAiModal] = useState(false);
  const [aiMode, setAiMode] = useState<'simplify' | 'mock_feedback'>('simplify');
  const explainProgressStage = useStageProgress(AI_EXPLAIN_STAGES, aiExplainLoading, 480);

  // Copy code feedback
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);


  // Sidebar Smart Navigation, Filtering & Level Scoping
  const [sidebarFilterText, setSidebarFilterText] = useState('');
  const [experienceFilter, setExperienceFilter] = useState<string>('All');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('All');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  const toggleCategoryCollapse = (catId: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  };

  // Load Domains list on mount
  useEffect(() => {
    api.getInterviewDomains()
      .then((data) => {
        setDomains(data);
        if (data.length > 0 && !selectedDomainId) {
          setSelectedDomainId(data[0].id);
        }
      })
      .catch((err) => console.error('Failed to load domains:', err));
  }, []);

  // Fetch Behavioral Prep when language changes
  useEffect(() => {
    setLoadingBehavioral(true);
    api.getBehavioralPrep(prepLanguage)
      .then((res) => {
        setBehavioralData(res);
      })
      .catch((err) => console.error('Failed to load behavioral prep:', err))
      .finally(() => setLoadingBehavioral(false));
  }, [prepLanguage]);

  // Fetch Domain Tree when selected domain changes
  useEffect(() => {
    setHeroImageError(false);
    if (!selectedDomainId) return;
    setLoadingTree(true);
    api.getInterviewDomainTree(selectedDomainId)
      .then((tree) => {
        setDomainTree(tree);
        // If current active question is not in this domain, pick first question of domain
        if (tree.categories.length > 0 && tree.categories[0].topics.length > 0) {
          const firstQ = tree.categories[0].topics[0].questions[0];
          if (firstQ) {
            setActiveQuestionSlug(firstQ.slug);
          }
        }
      })
      .catch((err) => console.error('Failed to load domain tree:', err))
      .finally(() => setLoadingTree(false));
  }, [selectedDomainId]);

  // Fetch Active Question Detail
  useEffect(() => {
    if (!selectedDomainId || !activeQuestionSlug) return;
    setLoadingQuestion(true);
    setAiExplainResult(null);
    setUserDraftAnswer('');
    api.getInterviewQuestionDetail(selectedDomainId, activeQuestionSlug)
      .then((detail) => {
        setActiveQuestion(detail);
      })
      .catch((err) => console.error('Failed to load question detail:', err))
      .finally(() => setLoadingQuestion(false));
  }, [selectedDomainId, activeQuestionSlug]);

  // Search handler
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await api.searchInterviewQuestions(searchQuery.trim());
        setSearchResults(results);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setSearching(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Toggle bookmark
  const toggleBookmark = (id: string) => {
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      localStorage.setItem('compust_prep_bookmarks', JSON.stringify([...next]));
      return next;
    });
  };

  // Toggle reviewed
  const toggleReviewed = (id: string) => {
    setReviewedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      localStorage.setItem('compust_prep_reviewed', JSON.stringify([...next]));
      return next;
    });
  };

  // Trigger AI explanation
  const handleRequestAIExplanation = async (
    mode: 'simplify' | 'mock_feedback',
    forceRegenerate: boolean = false
  ) => {
    if (!activeQuestion) return;
    setAiExplainLoading(true);
    setAiMode(mode);
    setShowAiModal(true);
    try {
      const res = await api.explainInterviewQuestionAI(
        activeQuestion.domain_id,
        activeQuestion.slug,
        mode,
        mode === 'mock_feedback' ? userDraftAnswer : undefined,
        prepLanguage,
        forceRegenerate
      );
      setAiExplainResult(res);
    } catch (err: any) {
      setAiExplainResult({
        question_id: activeQuestion.id,
        mode,
        explanation: `AI service encountered an issue: ${err.message}. Question content, educational diagrams, and repository material remain fully functional.`,
        ai_model_used: 'unavailable',
        is_ai_generated: true,
        disclaimer: 'Active AI gateway generation unavailable. Deterministic educational resources remain available.',
      });
    } finally {
      setAiExplainLoading(false);
    }
  };

  // Copy code handler
  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeIndex(index);
    setTimeout(() => setCopiedCodeIndex(null), 2000);
  };

  // Helper for inline bold, code, links, and LaTeX math formulas
  const formatInlineMarkdown = (text: string): string => {
    if (!text) return '';

    // 1. Process block math if embedded in paragraph: $$...$$
    let out = text.replace(/\$\$([\s\S]+?)\$\$/g, (_match, math) => {
      try {
        return `<div class="katex-display-wrapper">${katex.renderToString(math.trim(), {
          displayMode: true,
          throwOnError: false,
        })}</div>`;
      } catch {
        return `<div class="katex-display-wrapper error"><code>${math}</code></div>`;
      }
    });

    // 2. Process inline math: $...$ (ensure not escaped with backslash)
    out = out.replace(/(^|[^\\])\$([^\$\n]+?)\$/g, (_match, prefix, math) => {
      try {
        const rendered = katex.renderToString(math.trim(), {
          displayMode: false,
          throwOnError: false,
        });
        return `${prefix}<span class="katex-inline-wrapper">${rendered}</span>`;
      } catch {
        return `${prefix}<span class="katex-inline-wrapper error"><code>${math}</code></span>`;
      }
    });

    // 3. Process markdown formatting: bold, inline code, links
    out = out
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="md-link">$1</a>')
      .replace(/\\(\$)/g, '$1');

    return out;
  };

  // Render Markdown safely into styled semantic HTML elements with KaTeX math
  const renderMarkdown = (markdown: string) => {
    if (!markdown) return null;

    const sections = markdown.split('\n\n');
    let codeBlockCount = 0;

    return sections.map((sec, idx) => {
      const trimmed = sec.trim();

      // Heading 3: ### Title (with inline math support)
      if (trimmed.startsWith('### ')) {
        return (
          <h3
            key={idx}
            className="md-h3"
            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed.replace('### ', '')) }}
          />
        );
      }

      // Heading 4: #### Title
      if (trimmed.startsWith('#### ')) {
        return (
          <h4
            key={idx}
            className="md-h4"
            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed.replace('#### ', '')) }}
          />
        );
      }

      // Heading 5: ##### Title
      if (trimmed.startsWith('##### ')) {
        return (
          <h5
            key={idx}
            className="md-h5"
            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed.replace('##### ', '')) }}
          />
        );
      }

      // Dedicated Standalone Math Block: $$...$$
      if (trimmed.startsWith('$$') && trimmed.endsWith('$$') && trimmed.length >= 4) {
        const mathContent = trimmed.slice(2, -2).trim();
        try {
          const renderedMath = katex.renderToString(mathContent, {
            displayMode: true,
            throwOnError: false,
          });
          return (
            <div
              key={idx}
              className="md-math-block"
              dangerouslySetInnerHTML={{ __html: renderedMath }}
            />
          );
        } catch {
          return (
            <div key={idx} className="md-math-block error">
              <code>{mathContent}</code>
            </div>
          );
        }
      }

      // Code block
      if (trimmed.startsWith('```')) {
        const lines = trimmed.split('\n');
        const lang = lines[0].replace('```', '').trim() || 'text';
        const codeContent = lines.slice(1, -1).join('\n');
        const currCount = codeBlockCount++;

        return (
          <div key={idx} className="md-code-block">
            <div className="md-code-header">
              <span className="md-code-lang">{lang.toUpperCase()}</span>
              <button
                type="button"
                className="md-copy-btn"
                onClick={() => handleCopyCode(codeContent, currCount)}
                title="Copy code to clipboard"
              >
                {copiedCodeIndex === currCount ? <Check size={13} /> : <Copy size={13} />}
                <span>{copiedCodeIndex === currCount ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className="md-pre">
              <code>{codeContent}</code>
            </pre>
          </div>
        );
      }

      // Markdown Table
      if (trimmed.includes('|') && trimmed.includes('\n|')) {
        const rows = trimmed.split('\n').filter((r) => r.trim().startsWith('|'));
        if (rows.length >= 2) {
          const headers = rows[0].split('|').map((c) => c.trim()).filter(Boolean);
          // Skip row[1] if it's separator e.g. | :--- | :--- |
          const dataRows = rows.slice(2);
          return (
            <div key={idx} className="md-table-wrapper">
              <table className="md-table">
                <thead>
                  <tr>
                    {headers.map((h, hi) => (
                      <th
                        key={hi}
                        dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(h.replace(/\*\*/g, '')) }}
                      />
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataRows.map((dr, dri) => {
                    const cells = dr.split('|').map((c) => c.trim()).filter(Boolean);
                    return (
                      <tr key={dri}>
                        {cells.map((cell, ci) => (
                          <td
                            key={ci}
                            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(cell.replace(/\*\*/g, '')) }}
                          />
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        }
      }

      // Bullet List
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
        const items = trimmed.split('\n').map((i) => i.replace(/^[\*\-]\s+/, '').trim());
        return (
          <ul key={idx} className="md-ul">
            {items.map((item, ii) => (
              <li key={ii} dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(item) }} />
            ))}
          </ul>
        );
      }

      // Numbered List
      if (/^\d+\.\s+/.test(trimmed)) {
        const items = trimmed.split('\n').map((i) => i.replace(/^\d+\.\s+/, '').trim());
        return (
          <ol key={idx} className="md-ol">
            {items.map((item, ii) => (
              <li key={ii} dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(item) }} />
            ))}
          </ol>
        );
      }

      // Blockquote
      if (trimmed.startsWith('> ')) {
        return (
          <blockquote
            key={idx}
            className="md-blockquote"
            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed.replace(/^>\s+/, '')) }}
          />
        );
      }

      // Image
      const imgMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)$/);
      if (imgMatch) {
        if (activeQuestion?.educational_diagram && imgMatch[2] === activeQuestion.educational_diagram) {
          return null;
        }
        return (
          <div key={idx} className="md-image-box">
            <img src={imgMatch[2]} alt={imgMatch[1]} className="md-img" />
            <span className="md-img-caption">{imgMatch[1]}</span>
          </div>
        );
      }

      // Regular Paragraph with inline bold, code formatting, and math formulas
      return (
        <p
          key={idx}
          className="md-p"
          dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed) }}
        />
      );
    });
  };

  return (
    <div className="interview-prep-container">
      {/* Top Header & Context Ribbon */}
      <header className="prep-hero-bar glass-panel">
        <div className="hero-meta-left">
          {onNavigateToProfile && (
            <button
              type="button"
              className="back-to-profile-btn"
              onClick={onNavigateToProfile}
              title="Return to Profile & Resume Studio"
            >
              <ChevronLeft size={14} />
              <span>Back to Profile & Resume Studio</span>
            </button>
          )}
          <div className="hero-badge">
            <BrainCircuit size={15} className="text-primary" />
            <span>Structured Interview Intelligence</span>
          </div>
          <h1 className="hero-title">Interview Prep Knowledge Center</h1>
          <p className="hero-subtitle">
            Master behavioral frameworks with the STAR methodology and study repository-backed technical interview tracks.
          </p>
        </div>

        <div className="hero-actions-right">
          {/* User Progress Stats */}
          <div className="progress-pills">
            <span className="pill" title="Bookmarked Questions">
              <Bookmark size={13} />
              <span>{bookmarkedIds.size} Saved</span>
            </span>
            <span className="pill success" title="Marked as Reviewed">
              <CheckCircle2 size={13} />
              <span>{reviewedIds.size} Reviewed</span>
            </span>
          </div>
        </div>
      </header>

      {/* Main Track Selection Bar */}
      <nav className="prep-mode-nav glass-panel" aria-label="Interview Tracks">
        <button
          type="button"
          className={`mode-nav-btn ${activeTab === 'behavioral' ? 'active' : ''}`}
          onClick={() => setActiveTab('behavioral')}
        >
          <BookOpen size={17} />
          <span>Behavioral & HR Prep</span>
          <span className="mode-badge">STAR Method</span>
        </button>

        <button
          type="button"
          className={`mode-nav-btn ${activeTab === 'technical' ? 'active' : ''}`}
          onClick={() => setActiveTab('technical')}
        >
          <Terminal size={17} />
          <span>Technical Tracks</span>
          <span className="mode-badge count">3 Domains</span>
        </button>

        <button
          type="button"
          className={`mode-nav-btn ${activeTab === 'mock_interview' ? 'active' : ''}`}
          onClick={() => setActiveTab('mock_interview')}
        >
          <Mic size={17} />
          <span>AI Mock Interview</span>
          <span className="mode-badge live">Voice Live</span>
        </button>

        {/* Instant Search Bar */}
        <div className="prep-search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search questions, OAuth, Kafka, RAG, STAR..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="prep-search-input"
            aria-label="Search questions"
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setSearchQuery('')}
            >
              ✕
            </button>
          )}
        </div>
      </nav>

      {/* Search Overlay Results when query is active */}
      {searchQuery.trim() && (
        <section className="search-results-overlay glass-panel">
          <div className="search-results-header">
            <h4>
              Search Results for "{searchQuery}" ({searchResults.length} found)
            </h4>
            {searching && <Loader2 size={14} className="animate-spin" />}
          </div>
          <div className="search-results-grid">
            {searchResults.length === 0 && !searching ? (
              <p className="empty-search">No matching interview topics found. Try another keyword.</p>
            ) : (
              searchResults.map((res) => (
                <div
                  key={res.id}
                  className="search-result-card"
                  onClick={() => {
                    setActiveTab('technical');
                    setSelectedDomainId(res.id.split('-')[0] === 'sec' ? 'security_engineering' : res.id.split('-')[0] === 'de' ? 'data_engineering' : 'ai_tech_interview');
                    setActiveQuestionSlug(res.slug);
                    setSearchQuery('');
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="res-meta">
                    <span className="res-cat">{res.category}</span>
                    <span className="res-diff">{res.difficulty}</span>
                  </div>
                  <h5 className="res-title">{res.title}</h5>
                  <span className="res-link">Open Question →</span>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {/* VIEW 1: BEHAVIORAL & HR PREP */}
      {activeTab === 'behavioral' && (
        <main className="behavioral-prep-layout">
          {loadingBehavioral || !behavioralData ? (
            <div className="prep-loading-box">
              <Loader2 size={32} className="animate-spin text-primary" />
              <p>Loading {prepLanguage.toUpperCase()} behavioral methodologies...</p>
            </div>
          ) : (
            <>
              {/* STAR Method Interactive Guide Card */}
              <section className="star-guide-card glass-panel">
                <div className="star-card-header">
                  <div className="star-header-left">
                    <Sparkles size={22} className="icon-star" />
                    <div>
                      <h2>{behavioralData.star_guide.title}</h2>
                      <p className="star-tagline">{behavioralData.star_guide.what_is_star}</p>
                    </div>
                  </div>
                  <div className="star-ratio-tag">
                    <span>Target: 15% S · 10% T · 60% A · 15% R</span>
                  </div>
                </div>

                {/* Calibrated STAR Horizontal Proportion Bar */}
                <STARProportionBar
                  activeStep={expandedStarStep}
                  onSelectStep={(step) => setExpandedStarStep(step)}
                />

                {/* Expandable STAR Quadrant Cards */}
                <ExpandableSTARCards
                  starGuide={behavioralData.star_guide}
                  expandedStep={expandedStarStep}
                  onToggleStep={(step) => setExpandedStarStep(expandedStarStep === step ? null : step)}
                />

                {/* What Makes an Answer Strong & Common Mistakes */}
                <div className="star-advice-split">
                  <div className="advice-col strong">
                    <h4>✓ What Makes Your Answer Stand Out</h4>
                    <ul>
                      {behavioralData.star_guide.what_makes_answer_strong.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="advice-col mistakes">
                    <h4>⚠ Common Pitfalls to Avoid</h4>
                    <ul>
                      {behavioralData.star_guide.common_mistakes.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>

              {/* Story Matrix: 5 Engineering Anchors */}
              {behavioralData.story_matrix && (
                <section className="story-matrix-card glass-panel">
                  <div className="story-matrix-header">
                    <div className="matrix-title-row">
                      <Layers size={20} className="text-primary" />
                      <div>
                        <h3>{behavioralData.story_matrix.title}</h3>
                        <p className="matrix-desc">{behavioralData.story_matrix.description}</p>
                      </div>
                    </div>
                    <span className="matrix-badge">5 Engineering Anchors</span>
                  </div>
                  <div className="story-pillars-grid">
                    {behavioralData.story_matrix.pillars.map((pillar, idx) => {
                      const isExpanded = expandedAnchorIndex === idx;
                      return (
                        <div
                          key={idx}
                          className={`story-pillar-item ${isExpanded ? 'expanded' : ''}`}
                          onClick={() => setExpandedAnchorIndex(isExpanded ? null : idx)}
                          role="button"
                          tabIndex={0}
                          aria-expanded={isExpanded}
                        >
                          <div className="pillar-top">
                            <span className="pillar-num">{idx + 1}</span>
                            <h4 className="pillar-name">{pillar.name.replace(/^Pillar \d+:\s*/, '')}</h4>
                            <span className="pillar-toggle-hint">{isExpanded ? '▲' : '▼'}</span>
                          </div>
                          <p className="pillar-focus">{pillar.focus}</p>
                          <div className="pillar-triggers">
                            <span className="triggers-label">High-Yield Interview Prompts:</span>
                            <ul>
                              {pillar.applies_to.map((prompt, pi) => (
                                <li key={pi}>"{prompt}"</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Story ↔ Behavioral Theme Coverage Matrix */}
              <StoryThemeCoverageMatrix />

              {/* Interactive AI STAR Draft Story Evaluator */}
              <STAREvaluatorWidget
                prepLanguage={prepLanguage}
                questionTitle={
                  expandedQuestionId && behavioralData
                    ? behavioralData.questions.find((q) => q.id === expandedQuestionId)?.question
                    : undefined
                }
              />


              {/* Interview Preparation Lifecycle Modules */}
              {behavioralData.interview_modules && behavioralData.interview_modules.length > 0 && (
                <section className="interview-modules-card glass-panel">
                  <div className="modules-header">
                    <Clock size={20} className="text-primary" />
                    <div>
                      <h3>Interview Lifecycle Modules</h3>
                      <p className="modules-desc">Structured execution from architectural preparation to reverse-interviewing and post-offer negotiation.</p>
                    </div>
                  </div>
                  <div className="interview-modules-grid">
                    {behavioralData.interview_modules.map((mod, idx) => (
                      <div key={mod.id || idx} className="module-item-card">
                        <div className="module-step-badge">Stage {idx + 1}</div>
                        <h4 className="module-title">{mod.title}</h4>
                        <p className="module-summary">{mod.summary}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Questions Accordion List */}
              <section className="behavioral-questions-section">
                <div className="section-title-row">
                  <h3>Frequently Asked Behavioral & Leadership Questions</h3>
                  <span className="q-count">{behavioralData.questions.length} Questions</span>
                </div>

                <div className="questions-accordion-list">
                  {behavioralData.questions.map((q) => {
                    const isExpanded = expandedQuestionId === q.id;
                    return (
                      <article key={q.id} className={`behavioral-q-card glass-panel ${isExpanded ? 'expanded' : ''}`}>
                        <div
                          className="q-card-header"
                          onClick={() => setExpandedQuestionId(isExpanded ? null : q.id)}
                          role="button"
                          tabIndex={0}
                          aria-expanded={isExpanded}
                        >
                          <div className="q-title-group">
                            <span className="q-category-chip">{q.category}</span>
                            <h4 className="q-title">{q.question}</h4>
                          </div>
                          <span className="q-expand-indicator">
                            {isExpanded ? 'Collapse ▲' : 'Read Guide ▼'}
                          </span>
                        </div>

                        {isExpanded && (
                          <div className="q-card-body">
                            {/* Intent */}
                            <div className="q-intent-box">
                              <HelpCircle size={15} className="intent-icon" />
                              <div>
                                <strong>What the Recruiter is Really Testing:</strong>
                                <p>{q.intent}</p>
                              </div>
                            </div>

                            {/* Recommended Structure */}
                            <div className="q-structure-box">
                              <h5>Recommended Answer Flow:</h5>
                              <ol>
                                {q.recommended_structure.map((st, i) => (
                                  <li key={i}>{st}</li>
                                ))}
                              </ol>
                            </div>

                            {/* Strong Example Answer */}
                            <div className="q-example-answer-box">
                              <div className="ex-head">
                                <FileText size={15} />
                                <span>Strong Sample Response ({prepLanguage.toUpperCase()}):</span>
                              </div>
                              <blockquote className="example-quote">
                                "{q.strong_example_answer}"
                              </blockquote>
                            </div>

                            {/* Pitfalls & Self Reflection */}
                            <div className="q-footer-split">
                              <div className="pitfalls-list">
                                <span className="warning-label">Avoid:</span>
                                <ul>
                                  {q.common_pitfalls.map((p, i) => (
                                    <li key={i}>{p}</li>
                                  ))}
                                </ul>
                              </div>
                              <div className="self-reflection-box">
                                <span className="reflect-label">Personal Reflection:</span>
                                <p>{q.self_reflection_prompt}</p>
                              </div>
                            </div>
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              </section>
            </>
          )}
        </main>
      )}

      {/* VIEW 2: TECHNICAL TRACKS */}
      {activeTab === 'technical' && (
        <main className="technical-tracks-layout">
          {/* Domain Selector Ribbon */}
          <section className="domain-cards-row">
            {domains.map((dom) => {
              const isSelected = selectedDomainId === dom.id;
              return (
                <div
                  key={dom.id}
                  className={`domain-card glass-panel ${isSelected ? 'active' : ''}`}
                  onClick={() => setSelectedDomainId(dom.id)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="domain-card-content">
                    <div className="domain-top-line">
                      <span className="domain-short">{dom.short_title}</span>
                      <span className="domain-badge">{dom.total_questions} Questions</span>
                    </div>
                    <h3 className="domain-name">{dom.title}</h3>
                    <p className="domain-tagline">{dom.tagline}</p>
                  </div>
                  <div className="domain-card-footer">
                    <span className="explore-link">
                      {isSelected ? 'Currently Viewing' : 'Explore Track'} <ArrowRight size={14} />
                    </span>
                  </div>
                </div>
              );
            })}
          </section>

          {/* Domain Two-Column Knowledge Surface */}
          <div className="domain-two-column-grid">
            {/* Left Sidebar: Categories, Topics & Questions Tree */}
            <aside className="domain-tree-sidebar glass-panel">
              <div className="sidebar-header">
                <div className="sidebar-header-title">
                  <Layers size={16} className="text-primary" />
                  <h4>Topics & Questions</h4>
                </div>
                {domainTree && (
                  <span className="sidebar-total-badge">
                    {domainTree.categories.reduce((acc, c) => acc + c.topics.reduce((tacc, t) => tacc + t.questions.length, 0), 0)} Questions
                  </span>
                )}
              </div>

              {/* In-Sidebar Live Search */}
              <div className="sidebar-search-box">
                <Search size={14} className="sidebar-search-icon" />
                <input
                  type="text"
                  placeholder="Filter questions or tags..."
                  value={sidebarFilterText}
                  onChange={(e) => setSidebarFilterText(e.target.value)}
                  className="sidebar-search-input"
                />
                {sidebarFilterText && (
                  <button
                    type="button"
                    onClick={() => setSidebarFilterText('')}
                    className="sidebar-search-clear"
                    title="Clear filter"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              {/* Experience Level Quick Scoping Pills */}
              <div className="experience-filter-ribbon">
                <span className="filter-ribbon-label">Experience Tier:</span>
                <div className="experience-filter-pills">
                  {['All', 'Entry-Level', 'Mid-Level', 'Senior'].map((lvl) => {
                    const isActive = experienceFilter === lvl;
                    return (
                      <button
                        key={lvl}
                        type="button"
                        className={`exp-filter-pill ${isActive ? 'active' : ''}`}
                        onClick={() => setExperienceFilter(lvl)}
                      >
                        {lvl === 'Entry-Level' ? 'Entry' : lvl === 'Mid-Level' ? 'Mid' : lvl}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Category Quick Jump Chips */}
              {domainTree && domainTree.categories.length > 1 && (
                <div className="category-jump-row">
                  <button
                    type="button"
                    className={`cat-jump-chip ${selectedCategoryFilter === 'All' ? 'active' : ''}`}
                    onClick={() => setSelectedCategoryFilter('All')}
                  >
                    All Categories
                  </button>
                  {domainTree.categories.map((cat) => (
                    <button
                      key={cat.id}
                      type="button"
                      className={`cat-jump-chip ${selectedCategoryFilter === cat.id ? 'active' : ''}`}
                      onClick={() => setSelectedCategoryFilter(selectedCategoryFilter === cat.id ? 'All' : cat.id)}
                    >
                      {cat.title}
                    </button>
                  ))}
                </div>
              )}

              {loadingTree || !domainTree ? (
                <div className="sidebar-loading">
                  <Loader2 size={20} className="animate-spin" />
                </div>
              ) : (
                <div className="sidebar-categories-tree">
                  {domainTree.categories
                    .filter((cat) => selectedCategoryFilter === 'All' || selectedCategoryFilter === cat.id)
                    .map((cat) => {
                      const isCollapsed = collapsedCategories.has(cat.id);

                      // Filter questions within this category
                      const matchingTopics = cat.topics.map((top) => {
                        const matchingQuestions = top.questions.filter((q) => {
                          const matchesText = !sidebarFilterText.trim() ||
                            q.title.toLowerCase().includes(sidebarFilterText.toLowerCase()) ||
                            q.slug.toLowerCase().includes(sidebarFilterText.toLowerCase()) ||
                            (q.target_roles && q.target_roles.some((r) => r.toLowerCase().includes(sidebarFilterText.toLowerCase())));

                          const matchesExp = experienceFilter === 'All' ||
                            (q.experience_level && q.experience_level.toLowerCase().includes(experienceFilter.toLowerCase()));

                          return matchesText && matchesExp;
                        });

                        return { ...top, questions: matchingQuestions };
                      }).filter((top) => top.questions.length > 0);

                      const totalMatching = matchingTopics.reduce((acc, t) => acc + t.questions.length, 0);

                      if (totalMatching === 0 && (sidebarFilterText || experienceFilter !== 'All')) {
                        return null;
                      }

                      return (
                        <div key={cat.id} className="category-group glass-card">
                          <button
                            type="button"
                            className="category-accordion-header"
                            onClick={() => toggleCategoryCollapse(cat.id)}
                            aria-expanded={!isCollapsed}
                          >
                            <div className="category-header-text">
                              <h5 className="category-title">{cat.title}</h5>
                              <span className="cat-count-badge">{totalMatching} questions</span>
                            </div>
                            <span className="cat-toggle-icon">
                              {isCollapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                            </span>
                          </button>

                          {!isCollapsed && (
                            <div className="category-bounded-scroll">
                              <div className="topics-list">
                                {matchingTopics.map((top) => (
                                  <div key={top.id} className="topic-block">
                                    <span className="topic-name">{top.title}</span>
                                    <div className="questions-pills">
                                      {top.questions.map((q) => {
                                        const isCurrent = activeQuestionSlug === q.slug;
                                        const isBookmarked = bookmarkedIds.has(q.id);
                                        const isReviewed = reviewedIds.has(q.id);

                                        // Short role badge preview
                                        const primaryRole = q.target_roles && q.target_roles[0] ? q.target_roles[0] : null;

                                        return (
                                          <button
                                            key={q.id}
                                            type="button"
                                            className={`q-nav-pill ${isCurrent ? 'active' : ''} ${isReviewed ? 'reviewed' : ''}`}
                                            onClick={() => setActiveQuestionSlug(q.slug)}
                                          >
                                            <div className="q-pill-left">
                                              {q.experience_level && (
                                                <span
                                                  className={`q-level-dot ${
                                                    q.experience_level.toLowerCase().includes('senior')
                                                      ? 'senior'
                                                      : q.experience_level.toLowerCase().includes('mid')
                                                      ? 'mid'
                                                      : 'entry'
                                                  }`}
                                                  title={`Experience: ${q.experience_level}`}
                                                />
                                              )}
                                              <span className="q-pill-title">{q.title}</span>
                                            </div>

                                            <div className="q-pill-tags">
                                              {primaryRole && (
                                                <span className="micro-tag role" title={`Role: ${primaryRole}`}>
                                                  {primaryRole.split(' ')[0]}
                                                </span>
                                              )}
                                              {q.has_code && <span className="micro-tag code">Code</span>}
                                              {isBookmarked && <Bookmark size={11} fill="#fbbf24" color="#fbbf24" />}
                                              {isReviewed && <CheckCircle2 size={11} color="#34d399" />}
                                            </div>
                                          </button>
                                        );
                                      })}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </aside>

            {/* Right Main Article / Question Reading Surface */}
            <article className="question-reading-surface glass-panel">
              {loadingQuestion || !activeQuestion ? (
                <div className="reading-loading-box">
                  <Loader2 size={32} className="animate-spin text-primary" />
                  <p>Loading technical question content...</p>
                </div>
              ) : (
                <>
                  {/* Domain Hero Banner */}
                  <div className="domain-hero-banner">
                    {domainTree?.domain.hero_illustration && !heroImageError ? (
                      <div className="hero-ill-wrapper">
                        <img
                          src={domainTree.domain.hero_illustration}
                          alt={domainTree.domain.title}
                          className="hero-ill-img"
                          onError={() => setHeroImageError(true)}
                        />
                      </div>
                    ) : (
                      <div className="hero-ill-placeholder">
                        <div className="hero-ill-placeholder-glow" />
                        <div className="hero-ill-placeholder-content">
                          <div className="placeholder-icon-wrap">
                            <BrainCircuit size={38} className="placeholder-track-icon" />
                          </div>
                          <div className="placeholder-text-wrap">
                            <span className="placeholder-domain-pill">
                              {domainTree?.domain.short_title || 'Engineering Track'}
                            </span>
                            <h3 className="placeholder-domain-title">
                              {domainTree?.domain.title || 'Technical Knowledge Track'}
                            </h3>
                            <p className="placeholder-domain-tagline">
                              {domainTree?.domain.tagline || 'Curated repository-backed interview technical questions and system architectures.'}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Breadcrumbs & Metadata Bar */}
                  <header className="question-header-bar">
                    <nav className="q-breadcrumbs" aria-label="Breadcrumb">
                      <span>{activeQuestion.domain_title}</span>
                      <ChevronRight size={13} />
                      <span>{activeQuestion.category}</span>
                      <ChevronRight size={13} />
                      <span className="active">{activeQuestion.topic}</span>
                    </nav>

                    <div className="q-action-toolbar">
                      <button
                        type="button"
                        className={`tool-btn ${bookmarkedIds.has(activeQuestion.id) ? 'active' : ''}`}
                        onClick={() => toggleBookmark(activeQuestion.id)}
                        title={bookmarkedIds.has(activeQuestion.id) ? 'Remove Bookmark' : 'Bookmark Question'}
                      >
                        {bookmarkedIds.has(activeQuestion.id) ? (
                          <BookmarkCheck size={16} fill="#fbbf24" color="#fbbf24" />
                        ) : (
                          <Bookmark size={16} />
                        )}
                        <span>{bookmarkedIds.has(activeQuestion.id) ? 'Saved' : 'Save'}</span>
                      </button>

                      <button
                        type="button"
                        className={`tool-btn ${reviewedIds.has(activeQuestion.id) ? 'active success' : ''}`}
                        onClick={() => toggleReviewed(activeQuestion.id)}
                        title="Mark as Reviewed"
                      >
                        <CheckCircle2 size={16} color={reviewedIds.has(activeQuestion.id) ? '#34d399' : 'currentColor'} />
                        <span>{reviewedIds.has(activeQuestion.id) ? 'Reviewed' : 'Mark Reviewed'}</span>
                      </button>

                      <button
                        type="button"
                        className="tool-btn ai-btn"
                        onClick={() => handleRequestAIExplanation('simplify')}
                        title="Explain this question simply with local AI"
                      >
                        <Bot size={16} />
                        <span>Explain with AI</span>
                      </button>
                    </div>
                  </header>

                  {/* Question Title & Smart Badges */}
                  <div className="question-title-section">
                    <h2 className="q-main-title">{activeQuestion.title}</h2>
                    <div className="q-meta-badges">
                      <span className={`difficulty-badge ${activeQuestion.difficulty.toLowerCase()}`}>
                        {activeQuestion.difficulty}
                      </span>
                      {activeQuestion.experience_level && (
                        <span className="experience-level-badge">
                          <GraduationCap size={13} /> {activeQuestion.experience_level}
                        </span>
                      )}
                      <span className="read-time-badge">
                        <Clock size={13} /> {activeQuestion.estimated_read_time_min} min read
                      </span>
                      {activeQuestion.target_roles && activeQuestion.target_roles.map((role) => (
                        <span key={role} className="target-role-badge">
                          <Briefcase size={11} /> {role}
                        </span>
                      ))}
                      {activeQuestion.tags.map((tag) => (
                        <span key={tag} className="tag-badge">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Dedicated Educational Diagram Spotlight */}
                  {activeQuestion.educational_diagram && (
                    <div className="educational-diagram-banner glass-panel">
                      <div className="diagram-banner-header">
                        <div className="banner-title-row">
                          <Sparkles size={16} className="text-primary" />
                          <span className="banner-title">Educational Architecture Diagram</span>
                        </div>
                        <a
                          href={activeQuestion.educational_diagram}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="diagram-external-btn"
                          title="Open full resolution diagram in new tab"
                        >
                          <span>Full Resolution</span>
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="diagram-display-wrapper">
                        <img
                          src={activeQuestion.educational_diagram}
                          alt={activeQuestion.educational_diagram_alt || activeQuestion.title}
                          className="diagram-img"
                        />
                      </div>
                      {activeQuestion.educational_diagram_alt && (
                        <p className="diagram-caption">{activeQuestion.educational_diagram_alt}</p>
                      )}
                    </div>
                  )}

                  {/* Rendered Markdown Body */}
                  <div className="question-markdown-body">
                    {renderMarkdown(activeQuestion.markdown_content)}
                  </div>

                  {/* AI Explanation Drawer / Output Modal */}
                  {showAiModal && (
                    <div className="ai-explanation-drawer glass-panel">
                      <div className="drawer-header">
                        <div className="drawer-title-row">
                          <Bot size={18} className="text-primary" />
                          <h4>AI Technical Explanation · {aiMode === 'simplify' ? 'Concept Simplification & Real-World Example' : 'Answer Evaluation'}</h4>
                          <span className="ai-notice-pill">Active AI Gateway</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            type="button"
                            className="regenerate-ai-btn"
                            onClick={() => handleRequestAIExplanation(aiMode, true)}
                            disabled={aiExplainLoading}
                            title="Regenerate explanation bypassing cache"
                          >
                            <RefreshCw size={12} className={aiExplainLoading ? 'animate-spin' : ''} />
                            <span>Regenerate</span>
                          </button>
                          <button
                            type="button"
                            className="close-drawer-btn"
                            onClick={() => setShowAiModal(false)}
                            title="Close Explanation"
                          >
                            ✕
                          </button>
                        </div>
                      </div>

                      {aiExplainLoading ? (
                        <div className="ai-loading-box-stages" style={{ padding: '24px 16px' }}>
                          <StageProgressList
                            stages={AI_EXPLAIN_STAGES}
                            currentStage={explainProgressStage}
                            title="Synthesizing AI Technical Explanation..."
                          />
                        </div>
                      ) : aiExplainResult ? (
                        <div className="ai-result-box">
                          <VisualAIExplanation
                            result={aiExplainResult}
                            renderMarkdown={renderMarkdown}
                          />

                          <div className="ai-drawer-footer">
                            <span className="disclaimer-text">{aiExplainResult.disclaimer}</span>
                            <span className="model-tag">Engine: {aiExplainResult.ai_model_used}</span>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )}

                  {/* Source Attribution Box */}
                  <footer className="source-attribution-card">
                    <div className="source-meta">
                      <span className="source-lbl">Source Material Attribution:</span>
                      <span className="source-repo">{activeQuestion.source.repository_name}</span>
                      <span className="source-path">{activeQuestion.source.source_path}</span>
                      <span className="source-lic badge">{activeQuestion.source.license_name}</span>
                    </div>
                    {activeQuestion.source.repository_url && (
                      <a
                        href={activeQuestion.source.repository_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="source-external-link"
                      >
                        <span>View Original Repository</span>
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </footer>

                  {/* Previous / Next Question Navigation */}
                  <nav className="previous-next-nav-bar" aria-label="Question Pagination">
                    {activeQuestion.previous_question ? (
                      <button
                        type="button"
                        className="p-btn prev"
                        onClick={() => setActiveQuestionSlug(activeQuestion.previous_question!.slug)}
                        title={`Previous: ${activeQuestion.previous_question.title}`}
                      >
                        <ChevronLeft size={16} />
                        <div className="p-text-col">
                          <span className="p-dir">Previous Question</span>
                          <span className="p-title">{activeQuestion.previous_question.title}</span>
                        </div>
                      </button>
                    ) : <div />}

                    {activeQuestion.next_question && (
                      <button
                        type="button"
                        className="p-btn next"
                        onClick={() => setActiveQuestionSlug(activeQuestion.next_question!.slug)}
                        title={`Next: ${activeQuestion.next_question.title}`}
                      >
                        <div className="p-text-col">
                          <span className="p-dir">Next Question</span>
                          <span className="p-title">{activeQuestion.next_question.title}</span>
                        </div>
                        <ChevronRight size={16} />
                      </button>
                    )}
                  </nav>
                </>
              )}
            </article>
          </div>
        </main>
      )}

      {activeTab === 'mock_interview' && (
        <MockInterviewView
          initialDomainId={selectedDomainId}
          onNavigateBack={() => setActiveTab('technical')}
          onNavigateToPrepSection={(_section) => setActiveTab('behavioral')}
        />
      )}
    </div>
  );
};
