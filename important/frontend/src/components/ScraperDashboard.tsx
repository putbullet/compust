import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Activity,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Zap,
  Layers,
  Database,
  Timer,
} from 'lucide-react';
import { api } from '../api/client';
import type { Company, ScrapeTarget, ScraperTelemetry, SyncResponse } from '../api/client';

interface ScraperDashboardProps {
  companies: Company[];
}

export const ScraperDashboard: React.FC<ScraperDashboardProps> = ({ companies }) => {
  const [targets, setTargets] = useState<ScrapeTarget[]>([]);
  const [telemetry, setTelemetry] = useState<ScraperTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [lastSyncResult, setLastSyncResult] = useState<{ id: number; data: SyncResponse } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [targetsData, metricsData] = await Promise.all([
        api.getScrapeTargets(),
        api.getScraperMetrics().catch(() => null),
      ]);
      setTargets(targetsData);
      setTelemetry(metricsData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load scrape targets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSync = async (targetId: number) => {
    setSyncingId(targetId);
    setErrorMsg(null);
    try {
      const result = await api.syncScrapeTarget(targetId, 3);
      setLastSyncResult({ id: targetId, data: result });
      await loadData();
    } catch (err: any) {
      setErrorMsg(`Target ${targetId} sync failed: ${err.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  const getCompanyName = (companyId: number) => {
    const comp = companies.find((c) => c.id === companyId);
    return comp ? comp.name : `Company #${companyId}`;
  };

  return (
    <StyledDashboard>
      {/* Header */}
      <div className="dashboard-header glass-panel">
        <div className="header-info">
          <div className="title-row">
            <Activity size={24} className="icon-pulse" />
            <h2>Scraper Health & Compliance Dashboard</h2>
          </div>
          <p className="subtitle">
            Monitors robots.txt compliance, failure analytics, cooldown windows, and on-demand synchronization.
          </p>
        </div>

        <button className="refresh-all-btn" onClick={loadData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Telemetry Overview Cards */}
      {telemetry && (
        <div className="telemetry-grid">
          <div className="telemetry-card glass-panel">
            <div className="t-icon-box blue">
              <Zap size={20} />
            </div>
            <div className="t-data">
              <span className="t-value">{telemetry.success_rate_percent}%</span>
              <span className="t-label">Success Rate ({telemetry.total_runs} runs)</span>
            </div>
          </div>

          <div className="telemetry-card glass-panel">
            <div className="t-icon-box emerald">
              <Database size={20} />
            </div>
            <div className="t-data">
              <span className="t-value">
                {telemetry.total_jobs_added} <span className="sub-val">/ +{telemetry.total_jobs_updated}</span>
              </span>
              <span className="t-label">Jobs Added / Refreshed</span>
            </div>
          </div>

          <div className="telemetry-card glass-panel">
            <div className="t-icon-box purple">
              <Layers size={20} />
            </div>
            <div className="t-data">
              <span className="t-value">{telemetry.duplicate_rate_percent}%</span>
              <span className="t-label">Ingestion Stability Rate</span>
            </div>
          </div>

          <div className="telemetry-card glass-panel">
            <div className="t-icon-box amber">
              <Timer size={20} />
            </div>
            <div className="t-data">
              <span className="t-value">{telemetry.avg_duration_seconds}s</span>
              <span className="t-label">Avg Crawl Duration</span>
            </div>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="alert-banner error">
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {lastSyncResult && (
        <div className="alert-banner success">
          <CheckCircle2 size={18} />
          <div>
            <strong>Sync Completed for Target #{lastSyncResult.id}:</strong>{' '}
            Found {lastSyncResult.data.jobs_found} jobs ({lastSyncResult.data.jobs_added} new,{' '}
            {lastSyncResult.data.jobs_updated} updated)
            {lastSyncResult.data.parser_errors.length > 0 && (
              <span> | Errors: {lastSyncResult.data.parser_errors.length}</span>
            )}
          </div>
        </div>
      )}

      {/* Target Cards Grid */}
      <div className="targets-grid">
        {targets.map((target) => {
          const isSyncing = syncingId === target.id;
          const isInCooldown = target.cooldown_until && new Date(target.cooldown_until) > new Date();

          return (
            <div key={target.id} className="target-card glass-panel">
              <div className="target-header">
                <div className="company-info">
                  <h3>{getCompanyName(target.company_id)}</h3>
                  <a
                    href={target.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="target-link"
                  >
                    <span>{target.url.replace('https://', '').slice(0, 35)}...</span>
                    <ExternalLink size={12} />
                  </a>
                </div>

                <div className="status-indicator">
                  {target.robots_txt_allowed === false ? (
                    <span className="badge badge-rose">
                      <ShieldAlert size={12} /> Disallowed
                    </span>
                  ) : (
                    <span className="badge badge-emerald">
                      <ShieldCheck size={12} /> Robots Permitted
                    </span>
                  )}
                </div>
              </div>

              <div className="metrics-row">
                <div className="metric">
                  <span className="m-label">Last Scraped</span>
                  <span className="m-val">
                    {target.last_scraped_at ? new Date(target.last_scraped_at).toLocaleTimeString() : 'Never'}
                  </span>
                </div>

                <div className="metric">
                  <span className="m-label">Cooldown</span>
                  <span className="m-val">
                    {isInCooldown ? (
                      <span className="cooldown-active">Active</span>
                    ) : (
                      'Ready'
                    )}
                  </span>
                </div>

                <div className="metric">
                  <span className="m-label">Target Type</span>
                  <span className="m-val uppercase">{target.type || 'Standard'}</span>
                </div>
              </div>

              <div className="card-actions">
                <button
                  className="sync-action-btn"
                  onClick={() => handleSync(target.id)}
                  disabled={isSyncing || loading}
                >
                  <RefreshCw size={14} className={isSyncing ? 'spin' : ''} />
                  <span>{isSyncing ? 'Scraping Target...' : 'Synchronize Source'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </StyledDashboard>
  );
};

const StyledDashboard = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;

  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24px 28px;
    border-radius: 16px;
  }

  .header-info {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 { font-size: 1.45rem; }
    .icon-pulse { color: #10b981; }
  }

  .subtitle {
    font-size: 0.88rem;
    color: #94a3b8;
  }

  .refresh-all-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #f8fafc;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.12);
    }
  }

  .telemetry-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
    gap: 16px;
  }

  .telemetry-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 20px;
    border-radius: 14px;
  }

  .t-icon-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    flex-shrink: 0;

    &.blue {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    &.emerald {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    &.purple {
      background: rgba(168, 85, 247, 0.15);
      color: #c084fc;
      border: 1px solid rgba(168, 85, 247, 0.3);
    }
    &.amber {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
  }

  .t-data {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .t-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #f8fafc;

    .sub-val {
      font-size: 0.95rem;
      color: #94a3b8;
      font-weight: 500;
    }
  }

  .t-label {
    font-size: 0.74rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .alert-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 20px;
    border-radius: 14px;
    font-size: 0.88rem;

    &.error {
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.3);
      color: #f87171;
    }

    &.success {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }
  }

  .targets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
    gap: 20px;
  }

  .target-card {
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .target-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }

  .company-info {
    h3 { font-size: 1.15rem; margin-bottom: 4px; word-break: break-word; }
  }

  .target-link {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.76rem;
    color: #60a5fa;
    word-break: break-all;

    &:hover { text-decoration: underline; }
  }

  .metrics-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.04);
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .m-label {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
  }

  .m-val {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e2e8f0;

    &.uppercase {
      text-transform: uppercase;
      font-size: 0.78rem;
    }
  }

  .cooldown-active {
    color: #f59e0b;
  }

  .card-actions {
    margin-top: auto;
  }

  .sync-action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 10px;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 10px;
    color: #60a5fa;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #2563eb;
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
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
