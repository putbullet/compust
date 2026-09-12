import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Download, Loader2 } from 'lucide-react';
import type { StructuredResumeData, ResumeSettings } from '../../api/client';
import { api } from '../../api/client';
import { ResumeRenderer } from './ResumeRenderer';
import './ResumePreview.css';

interface ResumePreviewProps {
  resumeId: number;
  resumeTitle: string;
  data: StructuredResumeData;
  settings: ResumeSettings;
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({
  resumeId,
  resumeTitle,
  data,
  settings,
}) => {
  const [scale, setScale] = useState(0.85);
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'docx' | null>(null);

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

  const isA4 = settings.document_size === 'A4';
  const paperWidthPx = isA4 ? 794 : 816; // 96 DPI approximations
  const paperMinHeightPx = isA4 ? 1123 : 1056;

  return (
    <div className="resume-preview-container">
      {/* Top Preview Control Bar */}
      <div className="preview-toolbar">
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

        <div className="download-actions">
          <button
            type="button"
            className={`download-btn pdf-btn ${downloadingFormat === 'pdf' ? 'loading' : ''}`}
            disabled={downloadingFormat !== null}
            onClick={() => handleDownload('pdf')}
          >
            {downloadingFormat === 'pdf' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            <span>{downloadingFormat === 'pdf' ? 'Exporting...' : 'Download PDF'}</span>
          </button>

          <button
            type="button"
            className={`download-btn docx-btn ${downloadingFormat === 'docx' ? 'loading' : ''}`}
            disabled={downloadingFormat !== null}
            onClick={() => handleDownload('docx')}
          >
            {downloadingFormat === 'docx' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            <span>{downloadingFormat === 'docx' ? 'Exporting...' : 'Download Word (DOCX)'}</span>
          </button>
        </div>
      </div>

      {/* Scalable Viewport */}
      <div className="preview-canvas-viewport">
        <div
          className="canvas-scale-wrapper"
          style={{
            width: `${paperWidthPx * scale}px`,
            minHeight: `${paperMinHeightPx * scale}px`,
          }}
        >
          <div
            className="canvas-transformed"
            style={{
              width: `${paperWidthPx}px`,
              minHeight: `${paperMinHeightPx}px`,
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
            }}
          >
            <ResumeRenderer data={data} settings={settings} />
          </div>
        </div>
      </div>
    </div>
  );
};
