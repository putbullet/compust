import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Database,
  Download,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileArchive,
  ArrowRight,
  ShieldCheck,
  HardDrive,
  Briefcase,
  FolderKanban,
  Contact,
  FileText,
  Server,
  Sparkles,
} from 'lucide-react';
import {
  api,
  type ImportSourcesResponse,
  type ImportPreviewResponse,
  type ImportExecuteResponse,
  type BackupExportResponse,
  type BackupRestoreResponse,
} from '../api/client';

interface DataManagementProps {
  onImportComplete?: () => void;
}

export const DataManagementView: React.FC<DataManagementProps> = ({ onImportComplete }) => {
  const [loading, setLoading] = useState(false);
  const [sourcesData, setSourcesData] = useState<ImportSourcesResponse | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [selectedUserId, setSelectedUserId] = useState<number | undefined>(undefined);
  const [conflictStrategy, setConflictStrategy] = useState<'merge' | 'skip' | 'overwrite'>('merge');

  // Preview & Execute state
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportExecuteResponse | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Backup & Restore state
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<BackupExportResponse | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreResult, setRestoreResult] = useState<BackupRestoreResponse | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const res = await api.getImportSources();
      setSourcesData(res);
      if (res.sources && res.sources.length > 0 && !selectedSourceId) {
        const first = res.sources[0];
        setSelectedSourceId(first.id);
        if (first.users && first.users.length > 0) {
          // Default to user with most applications (owner)
          const topUser = [...first.users].sort((a, b) => b.applications_count - a.applications_count)[0];
          setSelectedUserId(topUser.id);
        }
      }
    } catch (err: any) {
      console.error('Failed to load data sources:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleSelectSource = (sId: string) => {
    setSelectedSourceId(sId);
    setPreviewData(null);
    setImportResult(null);
    setImportError(null);
    const src = sourcesData?.sources.find((s) => s.id === sId);
    if (src && src.users && src.users.length > 0) {
      const topUser = [...src.users].sort((a, b) => b.applications_count - a.applications_count)[0];
      setSelectedUserId(topUser.id);
    } else {
      setSelectedUserId(undefined);
    }
  };

  const handlePreview = async () => {
    if (!selectedSourceId) return;
    try {
      setPreviewLoading(true);
      setImportError(null);
      const res = await api.previewDataImport(selectedSourceId, selectedUserId);
      setPreviewData(res);
    } catch (err: any) {
      setImportError(err.message || 'Failed to preview import.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!selectedSourceId) return;
    try {
      setImporting(true);
      setImportError(null);
      const res = await api.executeDataImport(selectedSourceId, selectedUserId, undefined, conflictStrategy);
      setImportResult(res);
      await fetchSources();
      onImportComplete?.();
    } catch (err: any) {
      setImportError(err.message || 'Data import failed.');
    } finally {
      setImporting(false);
    }
  };

  const handleExportBackup = async () => {
    try {
      setExporting(true);
      setExportResult(null);
      const res = await api.exportDataBackup();
      setExportResult(res);
      // Trigger download
      window.location.href = res.download_url;
    } catch (err: any) {
      alert(`Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      setExporting(false);
    }
  };

  const handleRestoreFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setRestoreError('Uploaded backup file must be a .zip archive.');
      return;
    }
    const confirmed = window.confirm(
      'Are you sure you want to restore from this backup archive? ' +
        'A timestamped safety backup of your current database will be created before restoration.'
    );
    if (!confirmed) {
      e.target.value = '';
      return;
    }
    try {
      setRestoring(true);
      setRestoreError(null);
      setRestoreResult(null);
      const res = await api.restoreDataBackup(file);
      setRestoreResult(res);
      await fetchSources();
      onImportComplete?.();
    } catch (err: any) {
      setRestoreError(err.message || 'Restore failed.');
    } finally {
      setRestoring(false);
      e.target.value = '';
    }
  };

  const selectedSource = sourcesData?.sources.find((s) => s.id === selectedSourceId);
  const targetStats = sourcesData?.target_stats || {};

  return (
    <Container>
      <HeaderSection>
        <div className="title-row">
          <Database size={24} className="header-icon" />
          <div>
            <h2>Data Management & Portability</h2>
            <p className="subtitle">
              Safely import jobs, applications, and contacts from existing databases or create portable zip backups.
            </p>
          </div>
        </div>
        <button className="refresh-btn" onClick={fetchSources} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          <span>Refresh Status</span>
        </button>
      </HeaderSection>

      {/* Target Database Status Card */}
      <StatusCard>
        <div className="card-top">
          <div className="db-info">
            <HardDrive size={18} className="icon-blue" />
            <div>
              <div className="db-title">Active Local Database (SQLite Standalone)</div>
              <code className="db-path">{sourcesData?.target_database_path || 'Loading...'}</code>
            </div>
          </div>
          <span className={`status-pill ${sourcesData?.target_has_data ? 'active' : 'empty'}`}>
            <span className="dot" />
            <span>{sourcesData?.target_has_data ? 'Data Populated' : 'Empty Database'}</span>
          </span>
        </div>

        <div className="stats-grid">
          <div className="stat-item">
            <Briefcase size={16} />
            <div className="stat-val">{targetStats['jobs'] || 0}</div>
            <div className="stat-label">Jobs</div>
          </div>
          <div className="stat-item">
            <FolderKanban size={16} />
            <div className="stat-val">{targetStats['user_applications'] || 0}</div>
            <div className="stat-label">Applications</div>
          </div>
          <div className="stat-item">
            <Contact size={16} />
            <div className="stat-val">{targetStats['contacts'] || 0}</div>
            <div className="stat-label">Contacts</div>
          </div>
          <div className="stat-item">
            <FileText size={16} />
            <div className="stat-val">{targetStats['resumes'] || 0}</div>
            <div className="stat-label">Resumes</div>
          </div>
        </div>
      </StatusCard>

      {/* Guided Import Wizard */}
      <WizardSection>
        <div className="section-header">
          <Sparkles size={20} className="icon-sparkle" />
          <div>
            <h3>Guided Data Import Wizard</h3>
            <p>Import your existing applications and jobs from a detected MySQL or SQLite database.</p>
          </div>
        </div>

        {sourcesData?.sources && sourcesData.sources.length > 0 ? (
          <div className="wizard-body">
            {/* Step 1: Select Source */}
            <div className="wizard-step">
              <div className="step-num">1</div>
              <div className="step-content">
                <div className="step-title">Select Data Source</div>
                <div className="sources-list">
                  {sourcesData.sources.map((src) => (
                    <SourceCard
                      key={src.id}
                      $selected={selectedSourceId === src.id}
                      onClick={() => handleSelectSource(src.id)}
                    >
                      <div className="source-header">
                        <Server size={18} className="src-icon" />
                        <div>
                          <strong>{src.name}</strong>
                          <div className="source-loc">{src.location}</div>
                        </div>
                      </div>
                      <div className="source-meta">
                        <span>{src.total_jobs} jobs</span> · <span>{src.total_companies} companies</span> ·{' '}
                        <span>{src.users.length} users</span>
                      </div>
                    </SourceCard>
                  ))}
                </div>
              </div>
            </div>

            {/* Step 2: Select Profile & Review */}
            {selectedSource && selectedSource.users.length > 0 && (
              <div className="wizard-step">
                <div className="step-num">2</div>
                <div className="step-content">
                  <div className="step-title">Select User Profile to Import</div>
                  <div className="user-select-row">
                    <select
                      value={selectedUserId}
                      onChange={(e) => {
                        setSelectedUserId(Number(e.target.value));
                        setPreviewData(null);
                        setImportResult(null);
                      }}
                    >
                      {selectedSource.users.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.email} ({u.first_name || ''} {u.last_name || ''}) — {u.applications_count} apps,{' '}
                          {u.contacts_count} contacts
                        </option>
                      ))}
                    </select>

                    <button className="preview-btn" onClick={handlePreview} disabled={previewLoading}>
                      <RefreshCw size={13} className={previewLoading ? 'spin' : ''} />
                      <span>{previewLoading ? 'Inspecting...' : 'Preview Import'}</span>
                    </button>
                  </div>

                  {/* Preview breakdown */}
                  {previewData && (
                    <PreviewCard>
                      <div className="preview-head">
                        <ShieldCheck size={16} className="icon-green" />
                        <span>Read-Only Import Preview</span>
                      </div>
                      <div className="preview-grid">
                        <div className="p-item">
                          <span className="p-val">{previewData.jobs_count}</span>
                          <span className="p-lbl">Jobs</span>
                        </div>
                        <div className="p-item">
                          <span className="p-val">{previewData.companies_count}</span>
                          <span className="p-lbl">Companies</span>
                        </div>
                        <div className="p-item">
                          <span className="p-val">{previewData.applications_count}</span>
                          <span className="p-lbl">Applications</span>
                        </div>
                        <div className="p-item">
                          <span className="p-val">{previewData.contacts_count}</span>
                          <span className="p-lbl">Contacts</span>
                        </div>
                        <div className="p-item">
                          <span className="p-val">{previewData.resumes_count}</span>
                          <span className="p-lbl">Resumes</span>
                        </div>
                      </div>

                      {previewData.warning && (
                        <div className="preview-warn">
                          <AlertTriangle size={15} />
                          <span>{previewData.warning}</span>
                        </div>
                      )}
                    </PreviewCard>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Conflict Strategy & Execution */}
            <div className="wizard-step">
              <div className="step-num">3</div>
              <div className="step-content">
                <div className="step-title">Conflict Strategy & Execution</div>
                <div className="strategy-options">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="strategy"
                      value="merge"
                      checked={conflictStrategy === 'merge'}
                      onChange={() => setConflictStrategy('merge')}
                    />
                    <div>
                      <strong>Merge (Recommended)</strong>
                      <span>Update existing records with new data and insert newly found jobs and applications.</span>
                    </div>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="strategy"
                      value="skip"
                      checked={conflictStrategy === 'skip'}
                      onChange={() => setConflictStrategy('skip')}
                    />
                    <div>
                      <strong>Skip Existing</strong>
                      <span>Only insert records that do not currently exist in your local database.</span>
                    </div>
                  </label>
                </div>

                <div className="execute-row">
                  <button
                    className="execute-btn"
                    onClick={handleExecuteImport}
                    disabled={importing || !selectedSourceId}
                  >
                    {importing ? (
                      <>
                        <RefreshCw size={15} className="spin" />
                        <span>Safely Importing Data & Files...</span>
                      </>
                    ) : (
                      <>
                        <ArrowRight size={15} />
                        <span>Execute Guided Import</span>
                      </>
                    )}
                  </button>
                  <span className="backup-note">
                    An automatic safety backup of your database will be created before import.
                  </span>
                </div>

                {importError && (
                  <AlertBox $type="error">
                    <AlertTriangle size={16} />
                    <span>{importError}</span>
                  </AlertBox>
                )}

                {importResult && (
                  <AlertBox $type="success">
                    <CheckCircle2 size={16} />
                    <div>
                      <strong>{importResult.message}</strong>
                      {importResult.backup_file && (
                        <div className="backup-loc">Safety backup saved to: {importResult.backup_file}</div>
                      )}
                    </div>
                  </AlertBox>
                )}
              </div>
            </div>
          </div>
        ) : (
          <EmptySourcesNotice>
            <Server size={24} className="notice-icon" />
            <div>
              <strong>No external data sources detected.</strong>
              <p>
                Compust is running standalone with its local database. If you have a legacy MySQL server, start it
                on port 3306 and click &quot;Refresh Status&quot;.
              </p>
            </div>
          </EmptySourcesNotice>
        )}
      </WizardSection>

      {/* Backup & Restore Section */}
      <BackupSection>
        <div className="section-header">
          <FileArchive size={20} className="icon-blue" />
          <div>
            <h3>Portable Backup & Disaster Recovery</h3>
            <p>Export a full zip snapshot of your local database and storage files or restore an existing backup.</p>
          </div>
        </div>

        <div className="backup-grid">
          {/* Export Card */}
          <ActionCard>
            <div className="action-top">
              <Download size={22} className="icon-blue" />
              <div>
                <h4>Export Complete Backup (.zip)</h4>
                <p>Creates a self-contained zip archive containing your database, resumes, and manifest.</p>
              </div>
            </div>
            <button className="action-btn" onClick={handleExportBackup} disabled={exporting}>
              <Download size={14} className={exporting ? 'spin' : ''} />
              <span>{exporting ? 'Creating Backup Zip...' : 'Export Backup Archive'}</span>
            </button>
            {exportResult && (
              <div className="result-note success">
                <CheckCircle2 size={14} />
                <span>Downloaded {exportResult.filename} ({(exportResult.size_bytes / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            )}
          </ActionCard>

          {/* Restore Card */}
          <ActionCard>
            <div className="action-top">
              <Upload size={22} className="icon-green" />
              <div>
                <h4>Restore from Backup Archive</h4>
                <p>Restore your database and uploaded documents from an exported Compust backup zip.</p>
              </div>
            </div>
            <label className="upload-label">
              <input type="file" accept=".zip" onChange={handleRestoreFile} disabled={restoring} />
              <Upload size={14} className={restoring ? 'spin' : ''} />
              <span>{restoring ? 'Validating & Restoring...' : 'Select Backup (.zip) File'}</span>
            </label>
            {restoreError && (
              <div className="result-note error">
                <AlertTriangle size={14} />
                <span>{restoreError}</span>
              </div>
            )}
            {restoreResult && (
              <div className="result-note success">
                <CheckCircle2 size={14} />
                <span>{restoreResult.message}</span>
              </div>
            )}
          </ActionCard>
        </div>
      </BackupSection>
    </Container>
  );
};

const Container = styled.div`
  max-width: 1040px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const HeaderSection = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;

  .title-row {
    display: flex;
    align-items: center;
    gap: 14px;

    .header-icon {
      color: #3b82f6;
    }

    h2 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #f8fafc;
      margin: 0;
    }

    .subtitle {
      font-size: 0.88rem;
      color: #94a3b8;
      margin: 4px 0 0 0;
    }
  }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
    }
  }

  .spin {
    animation: spin 1s linear infinite;
  }
`;

const StatusCard = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .db-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .icon-blue {
        color: #3b82f6;
      }

      .db-title {
        font-weight: 600;
        color: #f8fafc;
        font-size: 0.95rem;
      }

      .db-path {
        font-size: 0.78rem;
        color: #94a3b8;
        background: rgba(0, 0, 0, 0.3);
        padding: 2px 6px;
        border-radius: 4px;
        word-break: break-all;
      }
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 600;

      .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
      }

      &.active {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        .dot {
          background: #10b981;
        }
      }

      &.empty {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        .dot {
          background: #f59e0b;
        }
      }
    }
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;

    .stat-item {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      color: #94a3b8;

      .stat-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f8fafc;
      }

      .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
    }
  }
`;

const WizardSection = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;

  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;

    .icon-sparkle {
      color: #8b5cf6;
    }

    h3 {
      font-size: 1.15rem;
      font-weight: 600;
      color: #f8fafc;
      margin: 0;
    }

    p {
      font-size: 0.85rem;
      color: #94a3b8;
      margin: 2px 0 0 0;
    }
  }

  .wizard-body {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .wizard-step {
    display: flex;
    gap: 16px;

    .step-num {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #1e293b;
      border: 1px solid #3b82f6;
      color: #3b82f6;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.85rem;
      flex-shrink: 0;
    }

    .step-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 12px;

      .step-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f8fafc;
      }
    }
  }

  .sources-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .user-select-row {
    display: flex;
    gap: 12px;
    align-items: center;

    select {
      flex: 1;
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f8fafc;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.88rem;
    }

    .preview-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 10px 16px;
      background: #1e293b;
      border: 1px solid #3b82f6;
      color: #60a5fa;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 600;
      white-space: nowrap;

      &:hover {
        background: rgba(59, 130, 246, 0.15);
      }
    }
  }

  .strategy-options {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .radio-label {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 10px 14px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      cursor: pointer;

      input {
        margin-top: 3px;
      }

      strong {
        display: block;
        font-size: 0.88rem;
        color: #f8fafc;
      }

      span {
        font-size: 0.8rem;
        color: #94a3b8;
      }
    }
  }

  .execute-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 6px;

    .execute-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 22px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.92rem;
      font-weight: 600;
      transition: all 0.2s ease;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }

    .backup-note {
      font-size: 0.78rem;
      color: #94a3b8;
    }
  }
`;

const SourceCard = styled.div<{ $selected: boolean }>`
  padding: 14px 16px;
  background: ${(props) => (props.$selected ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.02)')};
  border: 1px solid ${(props) => (props.$selected ? '#3b82f6' : 'rgba(255, 255, 255, 0.08)')};
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;

  .source-header {
    display: flex;
    align-items: center;
    gap: 12px;

    .src-icon {
      color: ${(props) => (props.$selected ? '#3b82f6' : '#94a3b8')};
    }

    strong {
      color: #f8fafc;
      font-size: 0.92rem;
    }

    .source-loc {
      font-size: 0.78rem;
      color: #94a3b8;
    }
  }

  .source-meta {
    font-size: 0.8rem;
    color: #94a3b8;
  }
`;

const PreviewCard = styled.div`
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;

  .preview-head {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #34d399;

    .icon-green {
      color: #10b981;
    }
  }

  .preview-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;

    .p-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      background: rgba(0, 0, 0, 0.2);
      padding: 8px;
      border-radius: 6px;

      .p-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
      }

      .p-lbl {
        font-size: 0.72rem;
        color: #94a3b8;
        text-transform: uppercase;
      }
    }
  }

  .preview-warn {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: #fbbf24;
  }
`;

const BackupSection = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;

  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;

    .icon-blue {
      color: #3b82f6;
    }

    h3 {
      font-size: 1.15rem;
      font-weight: 600;
      color: #f8fafc;
      margin: 0;
    }

    p {
      font-size: 0.85rem;
      color: #94a3b8;
      margin: 2px 0 0 0;
    }
  }

  .backup-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
`;

const ActionCard = styled.div`
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;

  .action-top {
    display: flex;
    gap: 12px;

    .icon-blue {
      color: #3b82f6;
    }

    .icon-green {
      color: #10b981;
    }

    h4 {
      font-size: 0.95rem;
      font-weight: 600;
      color: #f8fafc;
      margin: 0;
    }

    p {
      font-size: 0.8rem;
      color: #94a3b8;
      margin: 4px 0 0 0;
      line-height: 1.4;
    }
  }

  .action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 18px;
    background: #1e293b;
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #60a5fa;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 600;
    transition: all 0.2s ease;

    &:hover:not(:disabled) {
      background: rgba(59, 130, 246, 0.15);
      border-color: #3b82f6;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  .upload-label {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 18px;
    background: #1e293b;
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 600;
    transition: all 0.2s ease;

    input[type='file'] {
      display: none;
    }

    &:hover {
      background: rgba(16, 185, 129, 0.15);
      border-color: #10b981;
    }
  }

  .result-note {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;

    &.success {
      color: #34d399;
    }

    &.error {
      color: #f87171;
    }
  }
`;

const AlertBox = styled.div<{ $type: 'success' | 'error' }>`
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 0.85rem;
  background: ${(props) => (props.$type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)')};
  border: 1px solid ${(props) => (props.$type === 'success' ? '#10b981' : '#ef4444')};
  color: ${(props) => (props.$type === 'success' ? '#34d399' : '#f87171')};

  .backup-loc {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 4px;
    word-break: break-all;
  }
`;

const EmptySourcesNotice = styled.div`
  display: flex;
  gap: 14px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 0.85rem;

  .notice-icon {
    color: #64748b;
    flex-shrink: 0;
  }

  strong {
    color: #f8fafc;
    display: block;
    margin-bottom: 4px;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }
`;
