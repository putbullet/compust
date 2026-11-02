import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Database,
  Server,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  HardDrive,
  ShieldAlert,
  ShieldCheck,
  Eye,
  EyeOff,
  Zap,
  Download,
  PlusCircle,
} from 'lucide-react';
import {
  api,
  type DatabaseActiveInfoResponse,
  type DatabaseDetectResponse,
  type DatabaseTestResponse,
} from '../api/client';

interface DatabaseSectionProps {
  setupToken?: string;
  onDatabaseChanged?: () => void;
  onLaunchImport?: (sourceId: string) => void;
}

export const DatabaseSection: React.FC<DatabaseSectionProps> = ({
  setupToken,
  onDatabaseChanged,
  onLaunchImport,
}) => {
  const [activeInfo, setActiveInfo] = useState<DatabaseActiveInfoResponse | null>(null);
  const [loadingActive, setLoadingActive] = useState(false);

  // Detection state
  const [scanning, setScanning] = useState(false);
  const [detectedServers, setDetectedServers] = useState<DatabaseDetectResponse['detected_servers']>([]);

  // Form state
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState(3306);
  const [user, setUser] = useState('root');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [database, setDatabase] = useState('compust');

  // Test state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<DatabaseTestResponse | null>(null);
  const [creatingDb, setCreatingDb] = useState(false);

  // Switching state
  const [switching, setSwitching] = useState(false);
  const [switchSuccess, setSwitchSuccess] = useState<string | null>(null);
  const [switchError, setSwitchError] = useState<string | null>(null);

  const fetchActiveInfo = async () => {
    try {
      setLoadingActive(true);
      const res = await api.getActiveDatabaseInfo();
      setActiveInfo(res);
    } catch (err) {
      console.error('Failed to load active database info:', err);
    } finally {
      setLoadingActive(false);
    }
  };

  useEffect(() => {
    fetchActiveInfo();
  }, []);

  const handleScan = async () => {
    try {
      setScanning(true);
      const res = await api.detectDatabaseServers();
      setDetectedServers(res.detected_servers);
      if (res.detected_servers.length > 0) {
        const first = res.detected_servers[0];
        setHost(first.host);
        setPort(first.port);
      }
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setScanning(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      setSwitchError(null);
      setSwitchSuccess(null);
      const res = await api.testDatabaseConnection({
        host,
        port,
        user,
        password,
        database,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        error_code: 'CLIENT_ERROR',
        message: err.message || 'Connection test failed',
        database_exists: false,
        schema_state: 'unreachable',
        table_counts: {},
      });
    } finally {
      setTesting(false);
    }
  };

  const handleCreateDatabase = async () => {
    try {
      setCreatingDb(true);
      await api.createDatabase(
        { host, port, user, password, database },
        setupToken
      );
      // Re-test
      await handleTestConnection();
    } catch (err: any) {
      setSwitchError(err.message || 'Failed creating database');
    } finally {
      setCreatingDb(false);
    }
  };

  const handleSwitchToMySQL = async () => {
    if (!window.confirm(
      `Are you sure you want to link Compust live to MySQL (${host}:${port}/${database})?\n\nAn automated backup of the target database will be created before running migrations.`
    )) {
      return;
    }

    try {
      setSwitching(true);
      setSwitchError(null);
      setSwitchSuccess(null);
      const updated = await api.switchDatabase(
        {
          target_engine: 'mysql',
          host,
          port,
          user,
          password,
          database,
          run_migrations: true,
        },
        setupToken
      );
      setActiveInfo(updated);
      setSwitchSuccess(`Successfully linked live to MySQL (${host}:${port}/${database})!`);
      onDatabaseChanged?.();
    } catch (err: any) {
      setSwitchError(err.message || 'Failed to switch database engine');
    } finally {
      setSwitching(false);
    }
  };

  const handleSwitchToSqlite = async () => {
    if (!window.confirm('Revert to local standalone SQLite database? Compust will disconnect from MySQL.')) {
      return;
    }

    try {
      setSwitching(true);
      setSwitchError(null);
      setSwitchSuccess(null);
      const updated = await api.switchToSqlite(setupToken);
      setActiveInfo(updated);
      setSwitchSuccess('Successfully reverted to local standalone SQLite database.');
      onDatabaseChanged?.();
    } catch (err: any) {
      setSwitchError(err.message || 'Failed reverting to SQLite');
    } finally {
      setSwitching(false);
    }
  };

  return (
    <SectionWrapper>
      {/* 1. Active Database Card */}
      <ActiveCard>
        <div className="card-header">
          <div className="header-left">
            <Database size={22} className="icon-blue" />
            <div>
              <h3>Active Database</h3>
              <p className="subtext">The database engine currently serving Compust</p>
            </div>
          </div>
          <div className="header-right">
            <button className="refresh-btn" onClick={fetchActiveInfo} disabled={loadingActive}>
              <RefreshCw size={14} className={loadingActive ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {activeInfo && (
          <div className="active-details">
            <div className="badges-row">
              <span className={`badge engine-badge ${activeInfo.is_sqlite ? 'sqlite' : 'mysql'}`}>
                {activeInfo.is_sqlite ? 'SQLite Local' : 'MySQL / MariaDB'}
              </span>
              {activeInfo.schema_synced ? (
                <span className="badge synced-badge">
                  <ShieldCheck size={12} />
                  Schema Synced
                </span>
              ) : (
                <span className="badge outdated-badge">
                  <ShieldAlert size={12} />
                  Schema Update Required
                </span>
              )}
              {activeInfo.is_fallback_active && (
                <span className="badge fallback-badge">
                  <AlertTriangle size={12} />
                  Emergency Fallback to SQLite Active
                </span>
              )}
            </div>

            <div className="location-box">
              <span className="label">Location:</span>
              <code className="location-text">{activeInfo.location}</code>
              {activeInfo.size_mb !== null && activeInfo.size_mb !== undefined && (
                <span className="size-text">({activeInfo.size_mb} MB)</span>
              )}
            </div>

            <div className="counts-grid">
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.users ?? 0}</span>
                <span className="tag">Users</span>
              </div>
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.jobs ?? 0}</span>
                <span className="tag">Jobs</span>
              </div>
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.companies ?? 0}</span>
                <span className="tag">Companies</span>
              </div>
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.user_applications ?? 0}</span>
                <span className="tag">Applications</span>
              </div>
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.contacts ?? 0}</span>
                <span className="tag">Contacts</span>
              </div>
              <div className="count-pill">
                <span className="num">{activeInfo.table_counts.resumes ?? 0}</span>
                <span className="tag">Resumes</span>
              </div>
            </div>

            {!activeInfo.is_sqlite && (
              <div className="sqlite-revert-row">
                <button
                  className="revert-btn"
                  onClick={handleSwitchToSqlite}
                  disabled={switching}
                >
                  <HardDrive size={14} />
                  <span>Disconnect MySQL & Use Local SQLite</span>
                </button>
              </div>
            )}
          </div>
        )}
      </ActiveCard>

      {/* 2. Link MySQL Server Form */}
      <ConnectCard>
        <div className="card-header">
          <div className="header-left">
            <Server size={22} className="icon-green" />
            <div>
              <h3>Connect or Link MySQL / MariaDB Database</h3>
              <p className="subtext">
                Connect Compust directly to your local XAMPP or custom MySQL server, or import data from it.
              </p>
            </div>
          </div>
          <div className="header-right">
            <button className="scan-btn" onClick={handleScan} disabled={scanning}>
              <Zap size={14} className={scanning ? 'spin' : ''} />
              <span>{scanning ? 'Scanning...' : 'Detect Local MySQL'}</span>
            </button>
          </div>
        </div>

        {detectedServers.length > 0 && (
          <DetectedList>
            <span className="detected-label">Detected servers:</span>
            {detectedServers.map((srv) => (
              <div key={srv.port} className="server-chip">
                <CheckCircle2 size={13} className="text-green" />
                <span>
                  127.0.0.1:{srv.port} ({srv.server_version})
                </span>
                <button
                  type="button"
                  className="fill-btn"
                  onClick={() => {
                    setHost(srv.host);
                    setPort(srv.port);
                  }}
                >
                  Use Port {srv.port}
                </button>
              </div>
            ))}
          </DetectedList>
        )}

        <FormGrid>
          <div className="field-group">
            <label>Host</label>
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="127.0.0.1"
            />
          </div>
          <div className="field-group">
            <label>Port</label>
            <input
              type="number"
              value={port}
              onChange={(e) => setPort(parseInt(e.target.value, 10) || 3306)}
              placeholder="3306"
            />
          </div>
          <div className="field-group">
            <label>Username</label>
            <input
              type="text"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="root"
            />
          </div>
          <div className="field-group">
            <label>Password</label>
            <div className="pwd-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="(leave empty for default XAMPP)"
              />
              <button
                type="button"
                className="pwd-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <div className="field-group full-width">
            <label>Database Name</label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder="compust"
            />
            <span className="field-hint">
              Default XAMPP configuration: host <code>127.0.0.1</code>, user <code>root</code>, empty password.
            </span>
          </div>
        </FormGrid>

        <div className="actions-bar">
          <button
            type="button"
            className="test-btn"
            onClick={handleTestConnection}
            disabled={testing}
          >
            <RefreshCw size={14} className={testing ? 'spin' : ''} />
            <span>{testing ? 'Testing Connection...' : 'Test Connection'}</span>
          </button>
        </div>

        {/* Test Result Display */}
        {testResult && (
          <TestResultBox $success={testResult.success}>
            <div className="result-header">
              {testResult.success ? (
                <CheckCircle2 size={18} className="icon-green" />
              ) : (
                <AlertTriangle size={18} className="icon-red" />
              )}
              <strong>{testResult.message}</strong>
            </div>

            {testResult.success && (
              <div className="result-body">
                <div className="meta-line">
                  <span>Server: {testResult.server_version}</span>
                  <span>•</span>
                  <span>
                    Database: {testResult.database_exists ? `Found (${testResult.schema_state})` : 'Not Found'}
                  </span>
                </div>

                {!testResult.database_exists ? (
                  <div className="missing-db-box">
                    <p>Database &quot;{database}&quot; does not exist on this server.</p>
                    <button
                      className="create-db-btn"
                      onClick={handleCreateDatabase}
                      disabled={creatingDb}
                    >
                      <PlusCircle size={14} />
                      <span>{creatingDb ? 'Creating...' : `Create Database "${database}"`}</span>
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="test-counts">
                      <span>Users: {testResult.table_counts.users ?? 0}</span>
                      <span>Jobs: {testResult.table_counts.jobs ?? 0}</span>
                      <span>Companies: {testResult.table_counts.companies ?? 0}</span>
                      <span>Applications: {testResult.table_counts.user_applications ?? 0}</span>
                    </div>

                    <div className="link-options-grid">
                      <div className="option-choice">
                        <h4>Choice 1: Live Database Link</h4>
                        <p>
                          Point Compust directly to this MySQL database. All changes will be saved to MySQL.
                        </p>
                        <button
                          className="link-live-btn"
                          onClick={handleSwitchToMySQL}
                          disabled={switching}
                        >
                          <Zap size={14} />
                          <span>{switching ? 'Connecting...' : 'Use as Live Database'}</span>
                        </button>
                      </div>

                      <div className="option-choice">
                        <h4>Choice 2: Safe Copy Import</h4>
                        <p>
                          Keep your local SQLite database and import a copy of all jobs, companies, and applications.
                        </p>
                        <button
                          className="import-copy-btn"
                          onClick={() => {
                            const sId = `mysql-${host}-${port}-${database}`;
                            onLaunchImport?.(sId);
                          }}
                        >
                          <Download size={14} />
                          <span>Import Copy into Local SQLite</span>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </TestResultBox>
        )}

        {switchSuccess && (
          <AlertBox $type="success">
            <CheckCircle2 size={16} />
            <span>{switchSuccess}</span>
          </AlertBox>
        )}

        {switchError && (
          <AlertBox $type="error">
            <AlertTriangle size={16} />
            <span>{switchError}</span>
          </AlertBox>
        )}
      </ConnectCard>
    </SectionWrapper>
  );
};

const SectionWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
`;

const ActiveCard = styled.div`
  background: var(--card-bg, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 12px;
  padding: 1.5rem;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary, #f8fafc);
      }
      .subtext {
        margin: 0;
        font-size: 0.8125rem;
        color: var(--text-secondary, #94a3b8);
      }
    }

    .icon-blue {
      color: #38bdf8;
    }

    .refresh-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
      background: var(--bg-secondary, #334155);
      color: var(--text-primary, #f8fafc);
      border: 1px solid var(--border-color, #475569);
      cursor: pointer;
      &:hover {
        background: var(--bg-hover, #475569);
      }
    }
  }

  .active-details {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .badges-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;

    &.engine-badge.sqlite {
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
    &.engine-badge.mysql {
      background: rgba(34, 197, 94, 0.15);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }
    &.synced-badge {
      background: rgba(34, 197, 94, 0.15);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }
    &.outdated-badge {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    &.fallback-badge {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
  }

  .location-box {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--text-secondary, #94a3b8);

    .label {
      font-weight: 500;
    }
    .location-text {
      background: var(--bg-secondary, #0f172a);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      color: #38bdf8;
      font-size: 0.8125rem;
    }
    .size-text {
      font-size: 0.8125rem;
      color: var(--text-tertiary, #64748b);
    }
  }

  .counts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 0.75rem;
  }

  .count-pill {
    background: var(--bg-secondary, #0f172a);
    border: 1px solid var(--border-color, #334155);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    display: flex;
    flex-direction: column;
    align-items: center;

    .num {
      font-size: 1.125rem;
      font-weight: 700;
      color: var(--text-primary, #f8fafc);
    }
    .tag {
      font-size: 0.75rem;
      color: var(--text-secondary, #94a3b8);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  }

  .sqlite-revert-row {
    margin-top: 0.5rem;

    .revert-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      background: rgba(239, 68, 68, 0.1);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
      font-size: 0.8125rem;
      font-weight: 600;
      cursor: pointer;
      &:hover {
        background: rgba(239, 68, 68, 0.2);
      }
    }
  }
`;

const ConnectCard = styled.div`
  background: var(--card-bg, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.75rem;

      h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary, #f8fafc);
      }
      .subtext {
        margin: 0;
        font-size: 0.8125rem;
        color: var(--text-secondary, #94a3b8);
      }
    }

    .icon-green {
      color: #4ade80;
    }

    .scan-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.45rem 0.9rem;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 600;
      background: #0284c7;
      color: #fff;
      border: none;
      cursor: pointer;
      &:hover {
        background: #0369a1;
      }
    }
  }

  .actions-bar {
    display: flex;
    gap: 0.75rem;

    .test-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      background: var(--accent-color, #2563eb);
      color: #fff;
      font-size: 0.875rem;
      font-weight: 600;
      border: none;
      cursor: pointer;
      &:hover {
        background: #1d4ed8;
      }
    }
  }
`;

const DetectedList = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  background: var(--bg-secondary, #0f172a);
  padding: 0.75rem 1rem;
  border-radius: 8px;

  .detected-label {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-secondary, #94a3b8);
  }

  .server-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    padding: 0.3rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    color: var(--text-primary, #f8fafc);

    .text-green {
      color: #4ade80;
    }

    .fill-btn {
      background: #22c55e;
      color: #0f172a;
      border: none;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.15rem 0.4rem;
      cursor: pointer;
      &:hover {
        background: #16a34a;
      }
    }
  }
`;

const FormGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;

    &.full-width {
      grid-column: 1 / -1;
    }

    label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-secondary, #94a3b8);
    }

    input {
      background: var(--bg-secondary, #0f172a);
      border: 1px solid var(--border-color, #334155);
      border-radius: 6px;
      padding: 0.5rem 0.75rem;
      color: var(--text-primary, #f8fafc);
      font-size: 0.875rem;
      &:focus {
        outline: none;
        border-color: #38bdf8;
      }
    }

    .pwd-wrapper {
      position: relative;
      display: flex;
      align-items: center;

      input {
        width: 100%;
        padding-right: 2.2rem;
      }

      .pwd-toggle {
        position: absolute;
        right: 0.5rem;
        background: transparent;
        border: none;
        color: var(--text-secondary, #94a3b8);
        cursor: pointer;
      }
    }

    .field-hint {
      font-size: 0.75rem;
      color: var(--text-tertiary, #64748b);
      margin-top: 0.2rem;

      code {
        color: #38bdf8;
      }
    }
  }
`;

const TestResultBox = styled.div<{ $success: boolean }>`
  background: ${(p) => (p.$success ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)')};
  border: 1px solid ${(p) => (p.$success ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)')};
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;

  .result-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9375rem;
    color: var(--text-primary, #f8fafc);

    .icon-green {
      color: #4ade80;
    }
    .icon-red {
      color: #f87171;
    }
  }

  .result-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;

    .meta-line {
      display: flex;
      gap: 0.5rem;
      font-size: 0.8125rem;
      color: var(--text-secondary, #94a3b8);
    }

    .test-counts {
      display: flex;
      gap: 1.5rem;
      font-size: 0.8125rem;
      font-weight: 600;
      color: #38bdf8;
      background: var(--bg-secondary, #0f172a);
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
    }
  }

  .missing-db-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 0.6rem 0.8rem;
    border-radius: 6px;

    p {
      margin: 0;
      font-size: 0.8125rem;
      color: #fbbf24;
    }

    .create-db-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      background: #f59e0b;
      color: #0f172a;
      border: none;
      font-size: 0.8125rem;
      font-weight: 700;
      cursor: pointer;
      &:hover {
        background: #d97706;
      }
    }
  }

  .link-options-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 0.5rem;

    @media (max-width: 680px) {
      grid-template-columns: 1fr;
    }

    .option-choice {
      background: var(--bg-secondary, #0f172a);
      border: 1px solid var(--border-color, #334155);
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      h4 {
        margin: 0;
        font-size: 0.9375rem;
        color: var(--text-primary, #f8fafc);
      }
      p {
        margin: 0;
        font-size: 0.8125rem;
        color: var(--text-secondary, #94a3b8);
        flex-grow: 1;
      }

      .link-live-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.4rem;
        padding: 0.5rem;
        border-radius: 6px;
        background: #16a34a;
        color: #fff;
        border: none;
        font-size: 0.8125rem;
        font-weight: 600;
        cursor: pointer;
        &:hover {
          background: #15803d;
        }
      }

      .import-copy-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.4rem;
        padding: 0.5rem;
        border-radius: 6px;
        background: #0284c7;
        color: #fff;
        border: none;
        font-size: 0.8125rem;
        font-weight: 600;
        cursor: pointer;
        &:hover {
          background: #0369a1;
        }
      }
    }
  }
`;

const AlertBox = styled.div<{ $type: 'success' | 'error' }>`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  background: ${(p) => (p.$type === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)')};
  border: 1px solid ${(p) => (p.$type === 'success' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)')};
  color: ${(p) => (p.$type === 'success' ? '#4ade80' : '#f87171')};
`;
