import React, { useState, useEffect, useRef } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Loader2,
  FileText,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import type { StructuredResumeData, ResumeSettings } from '../../api/client';
import { api } from '../../api/client';
import { ResumeRenderer } from './ResumeRenderer';
import './ResumePreview.css';

interface ResumePreviewProps {
  resumeId: number;
  resumeTitle: string;
  data: StructuredResumeData;
  settings: ResumeSettings;
  onChangeSettings?: (settings: ResumeSettings) => void;
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({
  resumeId,
  resumeTitle,
  data,
  settings,
  onChangeSettings,
}) => {
  const [scale, setScale] = useState(0.85);
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'docx' | null>(null);

  // RenderCV Typeset Live Preview state
  const [renderedPages, setRenderedPages] = useState<string[]>([]);
  const [isTypesetting, setIsTypesetting] = useState(false);

  const isA4 = settings.document_size === 'A4';
  const paperWidthPx = isA4 ? 794 : 816; // 96 DPI approximations
  const pageHeightPx = isA4 ? 1123 : 1056; // Exact printed page height at 96 DPI

  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(pageHeightPx);

  // Measure rendered content height for fallback shell
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    const measure = () => {
      const h = el.scrollHeight;
      if (h > 0) {
        setContentHeight(h);
      }
    };

    measure();

    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => {
        measure();
      });
      ro.observe(el);
    }

    return () => {
      if (ro) ro.disconnect();
    };
  }, [data, settings]);

  // Debounced RenderCV Typst Live Preview compilation
  useEffect(() => {
    let active = true;
    setIsTypesetting(true);

    const timer = setTimeout(async () => {
      try {
        const res = await api.renderStructuredResumePreview(resumeId, {
          structured_data: data,
          settings: settings,
        });
        if (active && res && res.pages && res.pages.length > 0) {
          setRenderedPages(res.pages);
        }
      } catch (err) {
        console.warn('RenderCV preview generation warning:', err);
      } finally {
        if (active) {
          setIsTypesetting(false);
        }
      }
    }, 400);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [resumeId, data, settings]);

  const handleZoomIn = () => setScale((s) => Math.min(1.4, Number((s + 0.1).toFixed(2))));
  const handleZoomOut = () => setScale((s) => Math.max(0.4, Number((s - 0.1).toFixed(2))));
  const handleResetZoom = () => setScale(0.85);

  const handleDownload = async (format: 'pdf' | 'docx') => {
    if (downloadingFormat) return;
    setDownloadingFormat(format);
    try {
      const cleanName = `${(resumeTitle || 'resume').toLowerCase().replace(/[^a-z0-9]/g, '_')}.${format}`;
      await api.downloadStructuredResume(resumeId, format, cleanName);
    } catch (err: any) {
      alert(err.message || `Failed to download ${format.toUpperCase()}`);
    } finally {
      setTimeout(() => setDownloadingFormat(null), 1200);
    }
  };

  // Page calculations (from real RenderCV pages when available)
  const hasRealPages = renderedPages.length > 0;
  const pageCount = hasRealPages
    ? renderedPages.length
    : Math.max(1, Math.ceil(contentHeight / pageHeightPx));
  const isMultiPage = pageCount > 1;
  const page1Percent = Math.min(100, Math.round((contentHeight / pageHeightPx) * 100));
  const remainderHeight = contentHeight % pageHeightPx;
  const lastPagePercent = remainderHeight === 0 ? 100 : Math.round((remainderHeight / pageHeightPx) * 100);
  const renderedCanvasHeight = Math.max(pageCount * pageHeightPx, contentHeight);

  return (
    <div className="resume-preview-container">
      {/* Top Preview Control Bar */}
      <div className="preview-toolbar">
        <div className="toolbar-left-group">
          <div className="zoom-controls">
            <button
              type="button"
              className="tool-btn"
              onClick={handleZoomOut}
              title="Zoom Out"
            >
              <ZoomOut size={15} />
            </button>
            <span className="scale-display">{Math.round(scale * 100)}%</span>
            <button
              type="button"
              className="tool-btn"
              onClick={handleZoomIn}
              title="Zoom In"
            >
              <ZoomIn size={15} />
            </button>
            <button
              type="button"
              className="tool-btn reset-btn"
              onClick={handleResetZoom}
              title="Fit to Normal View"
            >
              <RotateCcw size={14} />
            </button>
          </div>

          {onChangeSettings && (
            <div className="preview-lang-switcher" title="Resume Language">
              {(['en', 'fr', 'de'] as const).map((langCode) => (
                <button
                  key={langCode}
                  type="button"
                  className={`lang-toggle-btn ${(settings.language || 'en') === langCode ? 'active' : ''}`}
                  onClick={() => onChangeSettings({ ...settings, language: langCode })}
                >
                  {langCode.toUpperCase()}
                </button>
              ))}
            </div>
          )}

          {isTypesetting ? (
            <span className="typeset-badge rendering" title="Compiling Typst Typesetting Engine">
              <Loader2 size={11} className="animate-spin" />
              <span>Typesetting...</span>
            </span>
          ) : hasRealPages ? (
            <span className="typeset-badge" title="RenderCV Typst 100% PDF-Accurate View">
              <CheckCircle2 size={11} />
              <span>RenderCV Typst</span>
            </span>
          ) : null}
        </div>

        {/* Download Actions: Always visible, never clipped */}
        <div className="download-actions">
          <button
            type="button"
            className={`download-btn pdf-btn ${downloadingFormat === 'pdf' ? 'loading' : ''}`}
            disabled={downloadingFormat !== null}
            onClick={() => handleDownload('pdf')}
            title="Download formatted PDF resume"
          >
            {downloadingFormat === 'pdf' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            <span>{downloadingFormat === 'pdf' ? 'Exporting...' : 'PDF'}</span>
          </button>

          <button
            type="button"
            className={`download-btn docx-btn ${downloadingFormat === 'docx' ? 'loading' : ''}`}
            disabled={downloadingFormat !== null}
            onClick={() => handleDownload('docx')}
            title="Download editable Word DOCX resume"
          >
            {downloadingFormat === 'docx' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            <span>{downloadingFormat === 'docx' ? 'Exporting...' : 'Word (DOCX)'}</span>
          </button>
        </div>
      </div>

      {/* Dedicated Page Count & Status Strip */}
      <div className={`preview-status-strip ${isMultiPage ? 'multi-page' : 'single-page'}`}>
        <div className="status-strip-left">
          {isMultiPage ? (
            <AlertTriangle size={13} className="status-strip-icon warning" />
          ) : (
            <CheckCircle2 size={13} className="status-strip-icon success" />
          )}
          <span className="status-strip-main">
            <strong>{isMultiPage ? `${pageCount} Pages` : '1 Page'}</strong> ({settings.document_size || 'A4'})
          </span>
          <span className="status-strip-divider">·</span>
          <span className="status-strip-detail">
            {hasRealPages
              ? 'RenderCV typesetting pipeline (matches PDF export 100%)'
              : isMultiPage
              ? `Page ${pageCount} is ~${lastPagePercent}% filled`
              : `${page1Percent}% of page filled`}
          </span>
        </div>

        <div className="status-strip-right">
          {hasRealPages ? (
            <span className="status-strip-tag success">✓ Verified Typst Layout</span>
          ) : isMultiPage ? (
            <span className="status-strip-tag warning">✂ Overflows into Page {pageCount}</span>
          ) : (
            <span className="status-strip-tag success">✓ Optimal 1-Page ATS Format</span>
          )}
        </div>
      </div>

      {/* Scalable Viewport */}
      <div className="preview-canvas-viewport">
        {hasRealPages ? (
          /* Exact RenderCV Typst Rendered Pages Stack */
          <div
            className="rendered-pages-stack"
            style={{
              transform: `scale(${scale})`,
              transformOrigin: 'top center',
              marginTop: '16px',
              marginBottom: '32px',
            }}
          >
            {renderedPages.map((pageSrc, idx) => (
              <div
                key={`typeset-page-${idx + 1}`}
                className="rendered-page-sheet"
                style={{
                  width: `${paperWidthPx}px`,
                }}
              >
                {/* Page Number Indicator */}
                <div className="sheet-page-tag sheet-page-1-tag">
                  <FileText size={11} />
                  <span>PAGE {idx + 1} OF {pageCount}</span>
                </div>
                <img
                  src={pageSrc}
                  alt={`Page ${idx + 1}`}
                  className="rendered-page-img"
                  style={{ width: `${paperWidthPx}px` }}
                />
              </div>
            ))}
          </div>
        ) : (
          /* Responsive Layout Measurement Container */
          <div
            className="canvas-scale-wrapper"
            style={{
              width: `${paperWidthPx * scale}px`,
              minHeight: `${renderedCanvasHeight * scale}px`,
            }}
          >
            <div
              className="canvas-transformed"
              style={{
                width: `${paperWidthPx}px`,
                minHeight: `${renderedCanvasHeight}px`,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
            >
              <div className="sheet-page-tag sheet-page-1-tag">
                <FileText size={11} />
                <span>PAGE 1</span>
              </div>

              <div ref={contentRef} className="resume-content-layer">
                <ResumeRenderer data={data} settings={settings} />
              </div>

              {Array.from({ length: pageCount - 1 }).map((_, idx) => {
                const breakTop = (idx + 1) * pageHeightPx;
                return (
                  <div
                    key={`page-break-${idx + 1}`}
                    className="page-break-overlay"
                    style={{ top: `${breakTop}px`, width: `${paperWidthPx}px` }}
                  >
                    <div className="page-break-divider-line" />
                    <div className="page-break-badge-pill">
                      <span className="break-badge-side">Page {idx + 1} Ends</span>
                      <span className="break-badge-center">✂ Page Break Guide</span>
                      <span className="break-badge-side highlight">Page {idx + 2} Starts</span>
                    </div>
                    <div className="sheet-page-tag next-sheet-tag">
                      <FileText size={11} />
                      <span>PAGE {idx + 2}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
