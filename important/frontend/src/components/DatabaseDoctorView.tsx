import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Download,
  HardDrive,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Wrench,
  ArrowLeft,
  Server,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  api,
  type DoctorStatusResponse,
  type DoctorRepairResponse,
} from '../api/client';
import { DatabaseSection } from './DatabaseSection';

interface DatabaseDoctorViewProps {
  setupToken?: string;
  onNavigateHome?: () => void;
}

export const DatabaseDoctorView: React.FC<DatabaseDoctorViewProps> = ({
  setupToken: propSetupToken,
  onNavigateHome,
}) => {
  // Extract setup token from prop or URL
  const [token] = useState<string>(() => {
    if (propSetupToken) return propSetupToken;
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get('setup_token') || localStorage.getItem('compust_setup_token') || '';
    } catch {
      return '';
    }
  });

  const [status, setStatus] = useState<DoctorStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Repair state
  const [repairing, setRepairing] = useState(false);
  const [repairResult, setRepairResult] = useState<DoctorRepairResponse | null>(null);
  const [repairError, setRepairError] = useState<string | null>(null);

  // Restore state
  const [restoringFile, setRestoringFile] = useState<string | null>(null);
  const [restoreSuccess, setRestoreSuccess] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  // Switching state
  const [switchingToSQLite, setSwitchingToSQLite] = useState(false);

  // Accordion state for MySQL Linking
  const [showMysqlSection, setShowMysqlSection] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getDoctorStatus();
      setStatus(res);
    } catch (err: any) {
      console.error('Failed to load doctor status:', err);
      setError(err.message || 'Unable to connect to database doctor service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleRepair = async () => {
    try {
      setRepairing(true);
      setRepairResult(null);
      setRepairError(null);
      const res = await api.repairDatabase(token || undefined);
      setRepairResult(res);
      await fetchStatus();
    } catch (err: any) {
      setRepairError(err.message || 'Schema repair failed.');
    } finally {
      setRepairing(false);
    }
  };

  const handleSwitchToSQLite = async () => {
    const confirmed = window.confirm(
      'Switch active storage back to local SQLite standalone database? A safety backup will be created.'
    );
    if (!confirmed) return;

    try {
      setSwitchingToSQLite(true);
      await api.switchToSQLite(token || undefined);
      await fetchStatus();
    } catch (err: any) {
      alert(`Failed to switch to SQLite: ${err.message || 'Unknown error'}`);
    } finally {
      setSwitchingToSQLite(false);
    }
  };

  const handleRestoreBackup = async (filename: string) => {
    const confirmed = window.confirm(
      `Are you sure you want to restore the database from backup: "${filename}"?\n\nA safety snapshot of your current database will be saved before restoration.`
    );
    if (!confirmed) return;

    try {
      setRestoringFile(filename);
      setRestoreSuccess(null);
      setRestoreError(null);
      const res = await api.restoreDoctorBackup(filename, token || undefined);
      setRestoreSuccess(res.message);
      await fetchStatus();
    } catch (err: any) {
      setRestoreError(err.message || 'Restore failed.');
    } finally {
      setRestoringFile(null);
    }
  };

  const isHealthy = status?.is_healthy && status.schema_synced && !status.is_fallback_active;

  return (
    <DoctorContainer>
      {/* Top Navigation / Action Bar */}
      <TopBar>
        {onNavigateHome && (
          <button className="back-btn" onClick={onNavigateHome}>
            <ArrowLeft size={16} />
            <span>Return to App</span>
          </button>
        )}
        <div className="bar-actions">
          <button className="refresh-btn" onClick={fetchStatus} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      </TopBar>

      {error && (
        <AlertBanner $variant="danger">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-text">
            <strong>Diagnostic Error</strong>
            <p>{error}</p>
          </div>
        </AlertBanner>
      )}

      {/* Main Title Header */}
      <HeaderCard>
        <div className="header-left">
          <div className="pulse-icon">
            <Activity size={28} />
          </div>
          <div>
            <div className="badge-row">
              <h2>Compust Database Doctor</h2>
              <span className={`status-tag ${isHealthy ? 'healthy' : 'warning'}`}>
                {isHealthy ? (
                  <>
                    <ShieldCheck size={14} /> Healthy &amp; Synced
                  </>
                ) : (
                  <>
                    <ShieldAlert size={14} /> Attention Required
                  </>
                )}
              </span>
            </div>
            <p className="subtitle">
              Self-healing database diagnostics, automated schema reconciliation, and disaster recovery.
            </p>
          </div>
        </div>

        {/* Quick Action Button in Header */}
        <div className="header-actions">
          <button
            className="repair-primary-btn"
            onClick={handleRepair}
            disabled={repairing}
          >
            <Wrench size={16} className={repairing ? 'spin' : ''} />
            <span>{repairing ? 'Reconciling Schema...' : 'Run Self-Healing Schema Repair'}</span>
          </button>
        </div>
      </HeaderCard>

      {/* Fallback Notice Banner */}
      {status?.is_fallback_active && (
        <AlertBanner $variant="warning">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-text">
            <strong>Active Database Fallback Engaged</strong>
            <p>
              Your configured MySQL database was unreachable at startup. Compust safely engaged its local SQLite
              storage engine so no work is interrupted. Reconnect your MySQL server or click &quot;Switch to SQLite&quot;
              below to dismiss.
            </p>
          </div>
          <button
            className="banner-action-btn"
            onClick={handleSwitchToSQLite}
            disabled={switchingToSQLite}
          >
            {switchingToSQLite ? 'Switching...' : 'Switch Permanently to SQLite'}
          </button>
        </AlertBanner>
      )}

      {/* Schema Mismatch Alert */}
      {status && !status.schema_synced && (
        <AlertBanner $variant="danger">
          <ShieldAlert size={20} className="alert-icon" />
          <div className="alert-text">
            <strong>Schema Mismatch Detected</strong>
            <p>
              One or more tables or columns in the active database do not match the expected application schema.
              Click &quot;Run Self-Healing Schema Repair&quot; to automatically add missing columns without losing any existing data.
            </p>
            {status.missing_tables && status.missing_tables.length > 0 && (
              <div className="missing-list">
                <strong>Missing Tables:</strong> {status.missing_tables.join(', ')}
              </div>
            )}
            {status.missing_columns && Object.keys(status.missing_columns).length > 0 && (
              <div className="missing-list">
                <strong>Missing Columns:</strong>{' '}
                {Object.entries(status.missing_columns).map(([tbl, cols]) => (
                  <span key={tbl} className="missing-chip">
                    {tbl}: {cols.join(', ')}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            className="banner-action-btn"
            onClick={handleRepair}
            disabled={repairing}
          >
            Repair Now
          </button>
        </AlertBanner>
      )}

      {/* Repair Feedback Box */}
      {repairResult && (
        <AlertBanner $variant="success">
          <CheckCircle2 size={20} className="alert-icon" />
          <div className="alert-text">
            <strong>{repairResult.message}</strong>
            {repairResult.created_tables.length > 0 && (
              <div>Created Tables: {repairResult.created_tables.join(', ')}</div>
            )}
            {Object.keys(repairResult.added_columns).length > 0 && (
              <div>
                Added Columns:{' '}
                {Object.entries(repairResult.added_columns).map(([tbl, cols]) => (
                  <span key={tbl}>
                    {tbl} ({cols.join(', ')})
                  </span>
                ))}
              </div>
            )}
            {repairResult.backup_file && (
              <div className="sub-text">Safety backup saved to: {repairResult.backup_file}</div>
            )}
          </div>
        </AlertBanner>
      )}

      {repairError && (
        <AlertBanner $variant="danger">
          <AlertTriangle size={20} className="alert-icon" />
          <div className="alert-text">
            <strong>Repair Encountered an Error</strong>
            <p>{repairError}</p>
          </div>
        </AlertBanner>
      )}

      {/* Main Grid: Engine Overview & Table Counts */}
      <DiagnosticGrid>
        {/* Card 1: Engine Details */}
        <DiagCard>
          <div className="card-head">
            <HardDrive size={18} className="card-icon" />
            <h3>Active Engine &amp; Storage</h3>
          </div>
          <div className="card-content">
            <div className="info-row">
              <span className="lbl">Engine:</span>
              <span className="val bold">
                {status?.active_engine ? status.active_engine.toUpperCase() : 'Loading...'}
              </span>
            </div>
            <div className="info-row">
              <span className="lbl">Location / Host:</span>
              <code className="val path">{status?.active_location || 'Loading...'}</code>
            </div>
            <div className="info-row">
              <span className="lbl">Database Size:</span>
              <span className="val">{status?.size_mb ? `${status.size_mb} MB` : 'N/A'}</span>
            </div>
            <div className="info-row">
              <span className="lbl">Schema Health:</span>
              <span className={`val badge ${status?.schema_synced ? 'green' : 'amber'}`}>
                {status?.schema_synced ? '100% Synced' : 'Columns Missing'}
              </span>
            </div>
            <div className="info-row">
              <span className="lbl">Mode:</span>
              <span className="val">
                {status?.is_sqlite ? 'SQLite (Standalone Local)' : 'MySQL / MariaDB (Live Server)'}
              </span>
            </div>

            <div className="engine-actions">
              <button
                className="sub-btn"
                onClick={handleRepair}
                disabled={repairing}
              >
                <Wrench size={14} />
                <span>Verify &amp; Reconcile Schema</span>
              </button>

              {!status?.is_sqlite && (
                <button
                  className="sub-btn warning"
                  onClick={handleSwitchToSQLite}
                  disabled={switchingToSQLite}
                >
                  <RotateCcw size={14} />
                  <span>Switch to Local SQLite</span>
                </button>
              )}
            </div>
          </div>
        </DiagCard>

        {/* Card 2: Live Table Row Counts */}
        <DiagCard>
          <div className="card-head">
            <Layers size={18} className="card-icon" />
            <h3>Database Table Counts</h3>
          </div>
          <div className="card-content">
            {status?.table_counts && Object.keys(status.table_counts).length > 0 ? (
              <div className="table-counts-grid">
                {Object.entries(status.table_counts).map(([tbl, cnt]) => (
                  <div key={tbl} className="count-pill">
                    <span className="table-name">{tbl}</span>
                    <span className={`count-number ${cnt > 0 ? 'has-data' : ''}`}>{cnt}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-counts">No table count data available.</div>
            )}
          </div>
        </DiagCard>
      </DiagnosticGrid>

      {/* Available Backups & One-Click Restore */}
      <BackupsSection>
        <div className="section-head">
          <Download size={20} className="sec-icon" />
          <div>
            <h3>Available Timestamped SQLite Backups</h3>
            <p>Automatic safety snapshots created prior to any migration, repair, or restore.</p>
          </div>
        </div>

        {restoreSuccess && (
          <AlertBanner $variant="success">
            <CheckCircle2 size={18} />
            <span>{restoreSuccess}</span>
          </AlertBanner>
        )}

        {restoreError && (
          <AlertBanner $variant="danger">
            <AlertTriangle size={18} />
            <span>{restoreError}</span>
          </AlertBanner>
        )}

        {status?.available_backups && status.available_backups.length > 0 ? (
          <div className="backups-table-wrap">
            <table className="backups-table">
              <thead>
                <tr>
                  <th>Backup File</th>
                  <th>Date &amp; Time (UTC)</th>
                  <th>Size</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {status.available_backups.map((b) => (
                  <tr key={b.filename}>
                    <td>
                      <code className="backup-filename">{b.filename}</code>
                    </td>
                    <td>{new Date(b.created_at).toLocaleString()}</td>
                    <td>{b.size_mb} MB</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="restore-btn"
                        onClick={() => handleRestoreBackup(b.filename)}
                        disabled={restoringFile === b.filename}
                      >
                        <RotateCcw
                          size={14}
                          className={restoringFile === b.filename ? 'spin' : ''}
                        />
                        <span>
                          {restoringFile === b.filename ? 'Restoring...' : 'Restore'}
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-backups-note">
            No local SQLite backups found yet. Backups are automatically generated when executing repairs or schema updates.
          </div>
        )}
      </BackupsSection>

      {/* Expandable MySQL Database Configuration & Linking Section */}
      <AccordionSection>
        <button
          className="accordion-header"
          onClick={() => setShowMysqlSection(!showMysqlSection)}
        >
          <div className="acc-title">
            <Server size={18} />
            <span>MySQL / MariaDB Connection &amp; Linking</span>
          </div>
          {showMysqlSection ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>

        {showMysqlSection && (
          <div className="accordion-body">
            <DatabaseSection
              setupToken={token}
              onDatabaseChanged={fetchStatus}
            />
          </div>
        )}
      </AccordionSection>
    </DoctorContainer>
  );
};

// Styled Components
const DoctorContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 80px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  font-family: inherit;
  color: var(--text-primary, #f8fafc);
`;

const TopBar = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: var(--bg-surface, #0f1623);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 8px;
    color: var(--text-primary, #f8fafc);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-card-hover, rgba(26, 38, 60, 0.85));
      border-color: var(--primary, #3b82f6);
    }
  }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 8px;
    color: var(--text-secondary, #cbd5e1);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      color: var(--primary, #3b82f6);
      border-color: var(--primary, #3b82f6);
      background: rgba(255, 255, 255, 0.04);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const HeaderCard = styled.div`
  background: var(--bg-card, rgba(18, 26, 42, 0.75));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 14px);
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  box-shadow: var(--shadow-card, 0 10px 30px -10px rgba(0, 0, 0, 0.6));

  @media (max-width: 800px) {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 18px;

    .pulse-icon {
      width: 52px;
      height: 52px;
      border-radius: 12px;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .badge-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;

      h2 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: var(--text-primary, #f8fafc);
        font-family: var(--font-heading);
      }
    }

    .subtitle {
      margin: 4px 0 0;
      font-size: 13px;
      color: var(--text-muted, #94a3b8);
    }
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;

    &.healthy {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }

    &.warning {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
    }
  }

  .repair-primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: #1d4ed8;
    color: #ffffff;
    border: 1px solid #2563eb;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(29, 78, 216, 0.4);
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #1e40af;
      transform: translateY(-1px);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
`;

const AlertBanner = styled.div<{ $variant: 'warning' | 'danger' | 'success' }>`
  border-radius: var(--radius-sm, 10px);
  padding: 16px 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  font-size: 13px;
  line-height: 1.5;

  ${({ $variant }) =>
    $variant === 'warning' &&
    `
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    .alert-icon { color: #f59e0b; }
  `}

  ${({ $variant }) =>
    $variant === 'danger' &&
    `
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #fca5a5;
    .alert-icon { color: #f87171; }
  `}

  ${({ $variant }) =>
    $variant === 'success' &&
    `
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #6ee7b7;
    .alert-icon { color: #34d399; }
  `}

  .alert-icon {
    flex-shrink: 0;
    margin-top: 2px;
  }

  .alert-text {
    flex: 1;

    strong {
      display: block;
      margin-bottom: 4px;
      font-size: 14px;
      color: var(--text-primary, #f8fafc);
    }

    p {
      margin: 0;
      color: var(--text-secondary, #cbd5e1);
    }

    .missing-list {
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-secondary, #cbd5e1);
      strong {
        display: inline;
        color: #fca5a5;
      }
    }

    .missing-chip {
      display: inline-block;
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid rgba(239, 68, 68, 0.35);
      color: #fecaca;
      padding: 2px 8px;
      border-radius: 4px;
      margin: 2px 4px 2px 0;
      font-family: monospace;
      font-size: 11px;
    }

    .sub-text {
      margin-top: 4px;
      font-size: 11px;
      color: var(--text-muted, #94a3b8);
      font-family: monospace;
    }
  }

  .banner-action-btn {
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid currentColor;
    border-radius: 6px;
    color: inherit;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    align-self: center;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.16);
      transform: translateY(-1px);
    }
  }
`;

const DiagnosticGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
`;

const DiagCard = styled.div`
  background: var(--bg-card, rgba(18, 26, 42, 0.75));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 12px);
  overflow: hidden;
  box-shadow: var(--shadow-card, 0 10px 30px -10px rgba(0, 0, 0, 0.6));

  .card-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    background: var(--bg-surface-elevated, #162032);

    .card-icon {
      color: #60a5fa;
    }

    h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary, #f8fafc);
      font-family: var(--font-heading);
    }
  }

  .card-content {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    padding-bottom: 8px;
    border-bottom: 1px dashed var(--border-subtle, rgba(255, 255, 255, 0.08));

    &:last-of-type {
      border-bottom: none;
    }

    .lbl {
      color: var(--text-muted, #94a3b8);
      font-weight: 500;
    }

    .val {
      color: var(--text-primary, #f8fafc);

      &.bold {
        font-weight: 600;
      }

      &.path {
        font-size: 11px;
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-secondary, #cbd5e1);
        border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
        padding: 3px 8px;
        border-radius: 4px;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      &.badge {
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;

        &.green {
          background: rgba(16, 185, 129, 0.15);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.3);
        }

        &.amber {
          background: rgba(245, 158, 11, 0.15);
          color: #fbbf24;
          border: 1px solid rgba(245, 158, 11, 0.3);
        }
      }
    }
  }

  .engine-actions {
    display: flex;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;

    .sub-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.12));
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      color: var(--text-primary, #f8fafc);
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.1);
        border-color: var(--primary, #3b82f6);
        color: #60a5fa;
      }

      &.warning {
        color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.35);
        &:hover:not(:disabled) {
          background: rgba(245, 158, 11, 0.15);
          border-color: #f59e0b;
        }
      }
    }
  }

  .table-counts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 8px;
    max-height: 250px;
    overflow-y: auto;
    padding-right: 4px;
  }

  .count-pill {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    border-radius: 6px;
    padding: 6px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;

    .table-name {
      color: var(--text-secondary, #cbd5e1);
      font-family: monospace;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .count-number {
      font-weight: 600;
      color: var(--text-muted, #94a3b8);

      &.has-data {
        color: #60a5fa;
      }
    }
  }

  .empty-counts {
    font-size: 13px;
    color: var(--text-muted, #94a3b8);
    text-align: center;
    padding: 20px;
  }
`;

const BackupsSection = styled.div`
  background: var(--bg-card, rgba(18, 26, 42, 0.75));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 12px);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-card, 0 10px 30px -10px rgba(0, 0, 0, 0.6));

  .section-head {
    display: flex;
    align-items: center;
    gap: 12px;

    .sec-icon {
      color: #60a5fa;
    }

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #f8fafc);
      font-family: var(--font-heading);
    }

    p {
      margin: 2px 0 0;
      font-size: 12px;
      color: var(--text-muted, #94a3b8);
    }
  }

  .backups-table-wrap {
    overflow-x: auto;
  }

  .backups-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;

    th, td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
      text-align: left;
    }

    th {
      font-weight: 600;
      color: var(--text-secondary, #cbd5e1);
      font-size: 12px;
      background: var(--bg-surface-elevated, #162032);
    }

    td {
      color: var(--text-secondary, #cbd5e1);
    }

    .backup-filename {
      font-family: monospace;
      font-size: 12px;
      color: var(--text-primary, #f8fafc);
    }

    .restore-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.15));
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary, #f8fafc);
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        border-color: #f59e0b;
        color: #fbbf24;
        background: rgba(245, 158, 11, 0.15);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }

  .no-backups-note {
    font-size: 13px;
    color: var(--text-muted, #94a3b8);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    padding: 16px;
    border-radius: 8px;
    text-align: center;
  }
`;

const AccordionSection = styled.div`
  background: var(--bg-card, rgba(18, 26, 42, 0.75));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 12px);
  overflow: hidden;
  box-shadow: var(--shadow-card, 0 10px 30px -10px rgba(0, 0, 0, 0.6));

  .accordion-header {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: var(--bg-surface-elevated, #162032);
    border: none;
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary, #f8fafc);
    font-family: var(--font-heading);
    transition: background 0.2s;

    &:hover {
      background: var(--bg-card-hover, rgba(26, 38, 60, 0.85));
    }

    .acc-title {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--text-primary, #f8fafc);
    }
  }

  .accordion-body {
    padding: 20px;
    border-top: none;
    background: transparent;
  }
`;
