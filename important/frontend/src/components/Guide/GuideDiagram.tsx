import React, { useEffect, useRef, useState } from 'react';

interface GuideDiagramProps {
  /** Mermaid diagram definition string */
  definition: string;
  /** Accessible label for screen readers */
  ariaLabel?: string;
  className?: string;
}

let mermaidReady = false;
let mermaidLoading: Promise<void> | null = null;
let mermaidTheme = '';

function getMermaidTheme(): 'dark' | 'light' {
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

/**
 * Lazily initialises Mermaid once and renders diagrams into Shadow-DOM-safe
 * container divs. Uses the app's dark-mode colour tokens.
 */
async function initMermaid(): Promise<void> {
  const theme = getMermaidTheme();
  if (mermaidReady && mermaidTheme === theme) return;
  if (mermaidLoading) return mermaidLoading;

  mermaidLoading = (async () => {
    const mermaid = (await import('mermaid')).default;
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        // Sync with index.css design tokens
        background: theme === 'light' ? '#ffffff' : '#0f1623',
        mainBkg: theme === 'light' ? '#f8fafc' : '#162032',
        nodeBorder: theme === 'light' ? '#cbd5e1' : 'rgba(255,255,255,0.12)',
        clusterBkg: theme === 'light' ? '#f1f5f9' : '#162032',
        titleColor: theme === 'light' ? '#0f172a' : '#f8fafc',
        edgeLabelBackground: theme === 'light' ? '#ffffff' : '#0f1623',
        lineColor: '#3b82f6',
        primaryColor: theme === 'light' ? '#ffffff' : '#162032',
        primaryTextColor: theme === 'light' ? '#0f172a' : '#f8fafc',
        primaryBorderColor: 'rgba(59,130,246,0.5)',
        secondaryColor: theme === 'light' ? '#e2e8f0' : '#1e2a3e',
        secondaryTextColor: theme === 'light' ? '#334155' : '#94a3b8',
        secondaryBorderColor: theme === 'light' ? '#cbd5e1' : 'rgba(255,255,255,0.08)',
        tertiaryColor: theme === 'light' ? '#f8fafc' : '#0a1220',
        tertiaryTextColor: theme === 'light' ? '#475569' : '#94a3b8',
        tertiaryBorderColor: theme === 'light' ? '#cbd5e1' : 'rgba(255,255,255,0.08)',
        noteBkgColor: theme === 'light' ? '#e2e8f0' : '#1e2a3e',
        noteTextColor: theme === 'light' ? '#334155' : '#cbd5e1',
        noteBorderColor: theme === 'light' ? '#cbd5e1' : 'rgba(255,255,255,0.08)',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        fontSize: '13px',
      },
      flowchart: {
        curve: 'basis',
        padding: 20,
        useMaxWidth: true,
        htmlLabels: true,
      },
      securityLevel: 'loose',
    });
    mermaidReady = true;
    mermaidTheme = theme;
    mermaidLoading = null;
  })();

  return mermaidLoading;
}

let diagramCounter = 0;

export const GuideDiagram: React.FC<GuideDiagramProps> = ({
  definition,
  ariaLabel = 'Diagram',
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`guide-diagram-${++diagramCounter}`);

  useEffect(() => {
    let cancelled = false;

    const render = async () => {
      try {
        await initMermaid();
        const mermaid = (await import('mermaid')).default;
        const { svg } = await mermaid.render(idRef.current, definition);
        if (!cancelled) {
          setSvgContent(svg);
          setError(null);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error('[GuideDiagram] render error:', err);
          setError('Diagram could not be rendered.');
        }
      }
    };

    render();
    return () => { cancelled = true; };
  }, [definition]);

  if (error) {
    return (
      <div className={`guide-diagram-error ${className}`} role="img" aria-label={ariaLabel}>
        <span>⚠ {error}</span>
      </div>
    );
  }

  if (svgContent) {
    return (
      <div
        ref={containerRef}
        className={`guide-diagram-container ${className}`}
        role="img"
        aria-label={ariaLabel}
        // biome-ignore lint/security/noDangerouslySetInnerHtml: trusted Mermaid SVG output
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className={`guide-diagram-container ${className}`}
      role="img"
      aria-label={ariaLabel}
    >
      <div className="guide-diagram-loading">
        <div className="guide-diagram-spinner" aria-hidden="true" />
        <span>Rendering diagram…</span>
      </div>
    </div>
  );
};
