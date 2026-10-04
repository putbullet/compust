import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import {
  X,
  Upload,
  FileSpreadsheet,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../../api/client';
import type { ContactImportPreviewResult, ContactImportPreviewRow } from '../../api/client';
import { useTranslation } from '../../i18n';

interface ImportContactsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: (importedCount: number) => void;
}

export const ImportContactsModal: React.FC<ImportContactsModalProps> = ({
  isOpen,
  onClose,
  onImportSuccess,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  const [file, setFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ContactImportPreviewResult | null>(null);
  const [strategy, setStrategy] = useState<'skip_duplicates' | 'update_existing' | 'import_all'>('skip_duplicates');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (!selected.name.endsWith('.xlsx') && !selected.name.endsWith('.xls')) {
      setError('Please select a valid Excel workbook file (.xlsx or .xls).');
      return;
    }

    setFile(selected);
    setError(null);

    // Automatically trigger preview analysis
    try {
      setAnalyzing(true);
      const res = await api.previewContactsImport(selected);
      setPreview(res);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze spreadsheet.');
      setPreview(null);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!preview || !preview.preview_rows) return;

    try {
      setImporting(true);
      setError(null);
      const result = await api.confirmContactsImport({
        mode: strategy,
        rows: preview.preview_rows,
      });
      onImportSuccess(result.created_count + result.updated_count);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to complete import.');
    } finally {
      setImporting(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <ModalBackdrop onClick={onClose}>
      <ModalContainer onClick={(e) => e.stopPropagation()}>
        <ModalHeader>
          <div className="header-title">
            <div className="icon-wrapper">
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3>{tApp.btnImportContacts} (.xlsx)</h3>
              <p>Smart importer with column synonym mapping and duplicate detection.</p>
            </div>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </ModalHeader>

        <ModalBody>
          {error && <div className="error-alert">{error}</div>}

          {!preview ? (
            /* Upload step */
            <UploadZone
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const dropped = e.dataTransfer.files[0];
                if (dropped) {
                  const fakeEvent = { target: { files: [dropped] } } as any;
                  handleFileChange(fakeEvent);
                }
              }}
            >
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept=".xlsx,.xls"
                onChange={handleFileChange}
              />
              <Upload size={36} className="upload-icon" />
              <h4>{analyzing ? 'Analyzing Excel workbook...' : 'Choose or drop your .xlsx file'}</h4>
              <p>Supports columns: First Name, Last Name, Email, Phone, Company, Role, LinkedIn, Location, Notes, Tags.</p>
              {analyzing && <RefreshCw size={20} className="spin text-blue" style={{ marginTop: '12px' }} />}
            </UploadZone>
          ) : (
            /* Preview Step */
            <PreviewSection>
              <div className="file-chip">
                <FileSpreadsheet size={16} />
                <span className="file-name">{file?.name}</span>
                <button type="button" className="reset-btn" onClick={handleReset}>
                  Change File
                </button>
              </div>

              {/* Counts Breakdown Grid */}
              <BreakdownGrid>
                <div className="breakdown-card total">
                  <span className="num">{preview.total_detected}</span>
                  <span className="label">Total Detected</span>
                </div>
                <div className="breakdown-card new">
                  <span className="num text-emerald">{preview.new_count}</span>
                  <span className="label">New Contacts</span>
                </div>
                <div className="breakdown-card existing">
                  <span className="num text-amber">{preview.existing_count}</span>
                  <span className="label">Existing</span>
                </div>
                <div className="breakdown-card dups">
                  <span className="num text-purple">{preview.duplicate_count}</span>
                  <span className="label">Duplicates</span>
                </div>
              </BreakdownGrid>

              {/* Column Mapping Preview */}
              {preview.column_mapping && Object.keys(preview.column_mapping).length > 0 && (
                <MappingBox>
                  <h5>Mapped Columns</h5>
                  <div className="mapping-tags">
                    {Object.entries(preview.column_mapping).map(([field, colName]) => (
                      <span key={field} className="mapping-tag">
                        <strong>{colName}</strong> ➔ {field}
                      </span>
                    ))}
                  </div>
                </MappingBox>
              )}

              {/* Duplicate Details if any */}
              {preview.preview_rows && preview.preview_rows.filter((r) => r.status === 'duplicate' || r.status === 'existing').length > 0 && (
                <DuplicateDetailsBox>
                  <div className="dup-header">
                    <AlertTriangle size={15} />
                    <span>
                      {preview.preview_rows.filter((r) => r.status === 'duplicate' || r.status === 'existing').length} Existing / Possible Duplicates Detected:
                    </span>
                  </div>
                  <div className="dup-list">
                    {preview.preview_rows
                      .filter((r) => r.status === 'duplicate' || r.status === 'existing')
                      .slice(0, 5)
                      .map((d: ContactImportPreviewRow, i: number) => (
                        <div key={i} className="dup-row">
                          <span className="dup-name">
                            {d.name || `${d.first_name || ''} ${d.last_name || ''}`.trim()} ({d.email || d.company || 'No Email'})
                          </span>
                          <span className="dup-reason">
                            {d.match_name ? `Matches: ${d.match_name}` : `Status: ${d.status}`}
                          </span>
                        </div>
                      ))}
                    {preview.preview_rows.filter((r) => r.status === 'duplicate' || r.status === 'existing').length > 5 && (
                      <span className="dup-more">
                        +{preview.preview_rows.filter((r) => r.status === 'duplicate' || r.status === 'existing').length - 5} more duplicates
                      </span>
                    )}
                  </div>
                </DuplicateDetailsBox>
              )}

              {/* Strategy Selector */}
              <StrategyBox>
                <label className="strategy-title">Duplicate Handling Strategy:</label>
                <div className="strategy-options">
                  <label className={`strategy-radio ${strategy === 'skip_duplicates' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="strategy"
                      value="skip_duplicates"
                      checked={strategy === 'skip_duplicates'}
                      onChange={() => setStrategy('skip_duplicates')}
                    />
                    <div>
                      <strong>Skip Duplicates (Recommended)</strong>
                      <p>Only import brand-new contacts, keeping existing records unchanged.</p>
                    </div>
                  </label>

                  <label className={`strategy-radio ${strategy === 'update_existing' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="strategy"
                      value="update_existing"
                      checked={strategy === 'update_existing'}
                      onChange={() => setStrategy('update_existing')}
                    />
                    <div>
                      <strong>Update Existing</strong>
                      <p>Overwrite existing contacts with new information from the file.</p>
                    </div>
                  </label>

                  <label className={`strategy-radio ${strategy === 'import_all' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="strategy"
                      value="import_all"
                      checked={strategy === 'import_all'}
                      onChange={() => setStrategy('import_all')}
                    />
                    <div>
                      <strong>Import All Records</strong>
                      <p>Create duplicate contact entries without merging.</p>
                    </div>
                  </label>
                </div>
              </StrategyBox>
            </PreviewSection>
          )}
        </ModalBody>

        <ModalFooter>
          <button type="button" className="cancel-btn" onClick={onClose} disabled={importing}>
            {tApp.btnCancel}
          </button>
          {preview && (
            <button
              type="button"
              className="confirm-btn"
              onClick={handleConfirmImport}
              disabled={importing || preview.total_detected === 0}
            >
              {importing ? (
                <>
                  <RefreshCw size={14} className="spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={15} />
                  <span>Confirm & Import ({preview.total_detected})</span>
                </>
              )}
            </button>
          )}
        </ModalFooter>
      </ModalContainer>
    </ModalBackdrop>
  );
};

const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.2s ease-out;

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

const ModalContainer = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
`;

const ModalHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(30, 41, 59, 0.5);

  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;

    .icon-wrapper {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    h3 {
      margin: 0;
      font-size: 17px;
      font-weight: 600;
      color: #f8fafc;
    }

    p {
      margin: 2px 0 0;
      font-size: 12px;
      color: #94a3b8;
    }
  }

  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 6px;
    border-radius: 6px;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }
  }
`;

const ModalBody = styled.div`
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .error-alert {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
  }
`;

const UploadZone = styled.div`
  border: 2px dashed rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.04);
  }

  .upload-icon {
    color: #3b82f6;
    margin-bottom: 12px;
  }

  h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #f1f5f9;
  }

  p {
    margin: 8px 0 0;
    font-size: 12px;
    color: #94a3b8;
    max-width: 440px;
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

const PreviewSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;

  .file-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.05);
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    color: #cbd5e1;

    .file-name {
      flex: 1;
      font-weight: 500;
    }

    .reset-btn {
      background: transparent;
      border: none;
      color: #38bdf8;
      font-size: 12px;
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }
  }
`;

const BreakdownGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;

  .breakdown-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;

    .num {
      font-size: 20px;
      font-weight: 700;
      color: #f8fafc;
    }

    .label {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
    }

    .text-emerald {
      color: #34d399;
    }
    .text-amber {
      color: #fbbf24;
    }
    .text-purple {
      color: #c084fc;
    }
  }

  @media (max-width: 600px) {
    grid-template-columns: 1fr 1fr;
  }
`;

const MappingBox = styled.div`
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px;

  h5 {
    margin: 0 0 8px 0;
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
  }

  .mapping-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    .mapping-tag {
      font-size: 11px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 3px 8px;
      border-radius: 4px;
      color: #cbd5e1;

      strong {
        color: #38bdf8;
      }
    }
  }
`;

const DuplicateDetailsBox = styled.div`
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 8px;
  padding: 12px;

  .dup-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #fbbf24;
    margin-bottom: 8px;
  }

  .dup-list {
    display: flex;
    flex-direction: column;
    gap: 6px;

    .dup-row {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #cbd5e1;

      .dup-name {
        font-weight: 500;
      }

      .dup-reason {
        font-size: 11px;
        color: #d97706;
      }
    }

    .dup-more {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
    }
  }
`;

const StrategyBox = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;

  .strategy-title {
    font-size: 12px;
    font-weight: 600;
    color: #cbd5e1;
  }

  .strategy-options {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .strategy-radio {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.08);
      cursor: pointer;
      transition: all 0.15s;

      &.active {
        background: rgba(59, 130, 246, 0.08);
        border-color: rgba(59, 130, 246, 0.3);
      }

      input {
        margin-top: 3px;
      }

      strong {
        display: block;
        font-size: 13px;
        color: #f1f5f9;
      }

      p {
        margin: 2px 0 0 0;
        font-size: 11px;
        color: #94a3b8;
      }
    }
  }
`;

const ModalFooter = styled.div`
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: rgba(15, 23, 42, 0.5);

  button {
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .cancel-btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #94a3b8;

    &:hover {
      background: rgba(255, 255, 255, 0.05);
      color: #f1f5f9;
    }
  }

  .confirm-btn {
    background: #10b981;
    border: none;
    color: #ffffff;
    font-weight: 600;

    &:hover:not(:disabled) {
      background: #059669;
    }
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
`;
