import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Layers,
} from 'lucide-react';
import { Modal } from '../common/Modal';
import './DiagramViewer.css';

export interface DiagramViewerProps {
  /** Mermaid diagram definition string */
  definition: string;
  /** Visible title displayed in toolbar header */
  title?: string;
  /** Accessible label for screen readers */
  ariaLabel?: string;
  /** Additional CSS class names */
  className?: string;
  /** Minimum zoom factor (defaults to 0.5) */
  minZoom?: number;
  /** Maximum zoom factor (defaults to 4.0) */
  maxZoom?: number;
  /** Initial zoom level (defaults to 1.0) */
  initialZoom?: number;
}

let mermaidReady = false;
let mermaidLoading: Promise<void> | null = null;
let mermaidTheme = '';

function getMermaidTheme(): 'dark' | 'light' {
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

/**
 * Lazily initialises Mermaid once with Bootstrap-style monochrome documentation palette.
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
        background: theme === 'light' ? '#ffffff' : '#0f172a',
        mainBkg: theme === 'light' ? '#f8fafc' : '#1e293b',
        nodeBorder: theme === 'light' ? '#cbd5e1' : '#475569',
        clusterBkg: theme === 'light' ? '#f1f5f9' : '#0f172a',
        clusterBorder: theme === 'light' ? '#cbd5e1' : '#334155',
        titleColor: theme === 'light' ? '#0f172a' : '#f8fafc',
        edgeLabelBackground: theme === 'light' ? '#ffffff' : '#0f172a',
        lineColor: theme === 'light' ? '#64748b' : '#94a3b8',
        primaryColor: theme === 'light' ? '#f8fafc' : '#1e293b',
        primaryTextColor: theme === 'light' ? '#0f172a' : '#f8fafc',
        primaryBorderColor: theme === 'light' ? '#94a3b8' : '#64748b',
        secondaryColor: theme === 'light' ? '#f1f5f9' : '#0f172a',
        secondaryTextColor: theme === 'light' ? '#334155' : '#cbd5e1',
        secondaryBorderColor: theme === 'light' ? '#cbd5e1' : '#475569',
        tertiaryColor: theme === 'light' ? '#ffffff' : '#1e293b',
        tertiaryTextColor: theme === 'light' ? '#475569' : '#94a3b8',
        tertiaryBorderColor: theme === 'light' ? '#e2e8f0' : '#334155',
        noteBkgColor: theme === 'light' ? '#f1f5f9' : '#1e293b',
        noteTextColor: theme === 'light' ? '#0f172a' : '#f8fafc',
        noteBorderColor: theme === 'light' ? '#cbd5e1' : '#475569',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
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

export const DiagramViewer: React.FC<DiagramViewerProps> = ({
  definition,
  title,
  ariaLabel = 'Interactive Diagram',
  className = '',
  minZoom = 0.5,
  maxZoom = 4.0,
  initialZoom = 1.0,
}) => {
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`diagram-viewer-${++diagramCounter}`);

  // Inline viewport zoom and pan state
  const [zoom, setZoom] = useState<number>(initialZoom);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const inlineViewportRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ startX: number; startY: number; initialPanX: number; initialPanY: number } | null>(null);

  // Modal expand state
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [modalZoom, setModalZoom] = useState<number>(1.1);
  const [modalPan, setModalPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isModalDragging, setIsModalDragging] = useState<boolean>(false);
  const modalViewportRef = useRef<HTMLDivElement>(null);
  const modalDragStartRef = useRef<{ startX: number; startY: number; initialPanX: number; initialPanY: number } | null>(null);

  // ── Render Mermaid SVG ──────────────────────────────────────────────────────
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
          console.error('[DiagramViewer] render error:', err);
          setError('Diagram could not be rendered.');
        }
      }
    };

    render();
    return () => {
      cancelled = true;
    };
  }, [definition]);

  // ── Zoom Actions ────────────────────────────────────────────────────────────
  const zoomIn = useCallback(() => {
    setZoom((prev) => Math.min(maxZoom, +(prev + 0.25).toFixed(2)));
  }, [maxZoom]);

  const zoomOut = useCallback(() => {
    setZoom((prev) => Math.max(minZoom, +(prev - 0.25).toFixed(2)));
  }, [minZoom]);

  const resetView = useCallback(() => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  }, []);

  const modalZoomIn = useCallback(() => {
    setModalZoom((prev) => Math.min(maxZoom, +(prev + 0.25).toFixed(2)));
  }, [maxZoom]);

  const modalZoomOut = useCallback(() => {
    setModalZoom((prev) => Math.max(minZoom, +(prev - 0.25).toFixed(2)));
  }, [minZoom]);

  const modalResetView = useCallback(() => {
    setModalZoom(1.0);
    setModalPan({ x: 0, y: 0 });
  }, []);

  // ── Inline Wheel Interaction (Ctrl/Meta Zoom, Natural Scroll otherwise) ─────
  useEffect(() => {
    const el = inlineViewportRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 0.15 : -0.15;
        setZoom((prev) => Math.min(maxZoom, Math.max(minZoom, +(prev + delta).toFixed(2))));
      }
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleWheel);
    };
  }, [minZoom, maxZoom]);

  // ── Modal Wheel Interaction ─────────────────────────────────────────────────
  useEffect(() => {
    const el = modalViewportRef.current;
    if (!el || !isExpanded) return;

    const handleModalWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      setModalZoom((prev) => Math.min(maxZoom, Math.max(minZoom, +(prev + delta).toFixed(2))));
    };

    el.addEventListener('wheel', handleModalWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleModalWheel);
    };
  }, [isExpanded, minZoom, maxZoom]);

  // ── Inline Drag Panning ─────────────────────────────────────────────────────
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return; // Only primary button
    e.currentTarget.setPointerCapture(e.pointerId);
    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialPanX: pan.x,
      initialPanY: pan.y,
    };
    setIsDragging(true);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging || !dragStartRef.current) return;
    const dx = e.clientX - dragStartRef.current.startX;
    const dy = e.clientY - dragStartRef.current.startY;
    setPan({
      x: dragStartRef.current.initialPanX + dx,
      y: dragStartRef.current.initialPanY + dy,
    });
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDragging) {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
      setIsDragging(false);
      dragStartRef.current = null;
    }
  };

  // ── Modal Drag Panning ──────────────────────────────────────────────────────
  const handleModalPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    modalDragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialPanX: modalPan.x,
      initialPanY: modalPan.y,
    };
    setIsModalDragging(true);
  };

  const handleModalPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isModalDragging || !modalDragStartRef.current) return;
    const dx = e.clientX - modalDragStartRef.current.startX;
    const dy = e.clientY - modalDragStartRef.current.startY;
    setModalPan({
      x: modalDragStartRef.current.initialPanX + dx,
      y: modalDragStartRef.current.initialPanY + dy,
    });
  };

  const handleModalPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isModalDragging) {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
      setIsModalDragging(false);
      modalDragStartRef.current = null;
    }
  };

  // ── Double-click Toggle Zoom ────────────────────────────────────────────────
  const handleDoubleClick = () => {
    if (zoom !== 1.0 || pan.x !== 0 || pan.y !== 0) {
      resetView();
    } else {
      setZoom(1.5);
    }
  };

  const handleModalDoubleClick = () => {
    if (modalZoom !== 1.0 || modalPan.x !== 0 || modalPan.y !== 0) {
      modalResetView();
    } else {
      setModalZoom(1.6);
    }
  };

  // ── Keyboard Navigation ─────────────────────────────────────────────────────
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      zoomIn();
    } else if (e.key === '-' || e.key === '_') {
      e.preventDefault();
      zoomOut();
    } else if (e.key === '0') {
      e.preventDefault();
      resetView();
    }
  };

  if (error) {
    return (
      <div className={`diagram-viewer-error ${className}`} role="img" aria-label={ariaLabel}>
        <span>⚠ {error}</span>
      </div>
    );
  }

  if (!svgContent) {
    return (
      <div className={`diagram-viewer-card ${className}`}>
        <div className="diagram-viewer-loading">
          <div className="diagram-viewer-spinner" aria-hidden="true" />
          <span>Rendering diagram…</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <div
        className={`diagram-viewer-card ${className}`}
        tabIndex={0}
        onKeyDown={handleKeyDown}
        role="region"
        aria-label={ariaLabel}
      >
        {/* Toolbar Header */}
        <div className="diagram-viewer-toolbar">
          <div className="diagram-viewer-title-group">
            <span className="diagram-viewer-title-icon" aria-hidden="true">
              <Layers size={16} />
            </span>
            <span>{title || 'Architecture & Process Diagram'}</span>
          </div>

          <div className="diagram-viewer-actions">
            <div className="diagram-viewer-btn-group" role="toolbar" aria-label="Diagram zoom controls">
              <button
                type="button"
                className="diagram-viewer-btn"
                onClick={zoomOut}
                disabled={zoom <= minZoom}
                aria-label="Zoom out (-)"
                title="Zoom out (-)"
              >
                <ZoomOut size={14} />
              </button>

              <button
                type="button"
                className="diagram-viewer-btn diagram-viewer-zoom-indicator"
                onClick={resetView}
                title="Reset zoom to 100% (0)"
                aria-label={`Current zoom: ${Math.round(zoom * 100)}%. Click to reset.`}
              >
                {Math.round(zoom * 100)}%
              </button>

              <button
                type="button"
                className="diagram-viewer-btn"
                onClick={zoomIn}
                disabled={zoom >= maxZoom}
                aria-label="Zoom in (+)"
                title="Zoom in (+)"
              >
                <ZoomIn size={14} />
              </button>

              <button
                type="button"
                className="diagram-viewer-btn"
                onClick={resetView}
                aria-label="Reset zoom and position (0)"
                title="Reset view (0)"
              >
                <RotateCcw size={13} />
              </button>
            </div>

            <button
              type="button"
              className="diagram-viewer-btn diagram-viewer-expand-btn"
              onClick={() => {
                setModalZoom(Math.max(1.1, zoom));
                setModalPan({ x: 0, y: 0 });
                setIsExpanded(true);
              }}
              aria-label="Expand diagram to full screen modal"
              title="Expand to full screen modal"
            >
              <Maximize2 size={13} />
              <span>Expand</span>
            </button>
          </div>
        </div>

        {/* Viewport */}
        <div
          ref={inlineViewportRef}
          className={`diagram-viewer-viewport ${isDragging ? 'dragging' : ''}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onDoubleClick={handleDoubleClick}
        >
          <div
            className={`diagram-viewer-canvas ${isDragging ? 'no-transition' : ''}`}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            }}
            // biome-ignore lint/security/noDangerouslySetInnerHtml: sanitized Mermaid SVG output
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        </div>

        {/* Footer Hint */}
        <div className="diagram-viewer-footer">
          <div className="diagram-viewer-hint-text">
            <span>Scroll with <kbd className="diagram-viewer-kbd">Ctrl</kbd> to zoom</span>
            <span>•</span>
            <span>Drag to pan</span>
            <span>•</span>
            <span>Double-click to toggle</span>
          </div>
          <div>
            <span>Press <kbd className="diagram-viewer-kbd">+</kbd> / <kbd className="diagram-viewer-kbd">-</kbd> / <kbd className="diagram-viewer-kbd">0</kbd></span>
          </div>
        </div>
      </div>

      {/* Expanded Modal */}
      {isExpanded && (
        <Modal
          isOpen={isExpanded}
          onClose={() => setIsExpanded(false)}
          maxWidth="95vw"
          title={title || ariaLabel || 'Diagram Viewer'}
          icon={<Layers size={18} />}
          ariaLabel={title || ariaLabel || 'Diagram Viewer'}
        >
          <div className="diagram-viewer-modal-container">
            <div className="diagram-viewer-modal-toolbar">
              <div className="diagram-viewer-hint-text">
                <span>Drag to pan across the diagram</span>
                <span>•</span>
                <span>Mouse wheel or buttons to zoom</span>
              </div>

              <div className="diagram-viewer-btn-group" role="toolbar" aria-label="Expanded diagram zoom controls">
                <button
                  type="button"
                  className="diagram-viewer-btn"
                  onClick={modalZoomOut}
                  disabled={modalZoom <= minZoom}
                  aria-label="Zoom out (-)"
                  title="Zoom out"
                >
                  <ZoomOut size={15} />
                </button>

                <button
                  type="button"
                  className="diagram-viewer-btn diagram-viewer-zoom-indicator"
                  onClick={modalResetView}
                  title="Reset zoom to 100%"
                >
                  {Math.round(modalZoom * 100)}%
                </button>

                <button
                  type="button"
                  className="diagram-viewer-btn"
                  onClick={modalZoomIn}
                  disabled={modalZoom >= maxZoom}
                  aria-label="Zoom in (+)"
                  title="Zoom in"
                >
                  <ZoomIn size={15} />
                </button>

                <button
                  type="button"
                  className="diagram-viewer-btn"
                  onClick={modalResetView}
                  aria-label="Reset zoom and position"
                  title="Reset view"
                >
                  <RotateCcw size={14} />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            <div
              ref={modalViewportRef}
              className={`diagram-viewer-modal-viewport ${isModalDragging ? 'dragging' : ''}`}
              onPointerDown={handleModalPointerDown}
              onPointerMove={handleModalPointerMove}
              onPointerUp={handleModalPointerUp}
              onPointerCancel={handleModalPointerUp}
              onDoubleClick={handleModalDoubleClick}
            >
              <div
                className={`diagram-viewer-canvas ${isModalDragging ? 'no-transition' : ''}`}
                style={{
                  transform: `translate(${modalPan.x}px, ${modalPan.y}px) scale(${modalZoom})`,
                }}
                // biome-ignore lint/security/noDangerouslySetInnerHtml: sanitized Mermaid SVG output
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};

export default DiagramViewer;
