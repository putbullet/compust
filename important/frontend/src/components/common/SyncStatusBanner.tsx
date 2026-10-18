import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  RotateCw,
  Clock,
  Calendar,
  Settings2,
  CheckCircle2,
  AlertCircle,
  X,
  Play,
  ShieldCheck,
  Check,
} from 'lucide-react';
import { api } from '../../api/client';
import { useTranslation } from '../../i18n';

interface SyncStatusBannerProps {
  onSyncCompleted?: () => void;
  compact?: boolean;
}

const DAYS_OF_WEEK = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
];

export const SyncStatusBanner: React.FC<SyncStatusBannerProps> = ({
  onSyncCompleted,
  compact = false,
}) => {
  const { language } = useTranslation();
  const [status, setStatus] = useState<any>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncStage, setSyncStage] = useState('');
  const [toastMsg, setToastMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  // Form states
  const [cfgEnabled, setCfgEnabled] = useState(true);
  const [cfgDays, setCfgDays] = useState<number[]>([0, 4]);
  const [cfgHour, setCfgHour] = useState(9);
  const [cfgMinute, setCfgMinute] = useState(0);
  const [cfgSafetyNet, setCfgSafetyNet] = useState(5);
  const [cfgMissedRuns, setCfgMissedRuns] = useState(2);
  const [cfgMaxAgeDays, setCfgMaxAgeDays] = useState(60);

  const fetchStatus = async () => {
    try {
      const data = await api.getSchedulerStatus();
      setStatus(data);
      setCfgEnabled(data.enabled);
      setCfgDays(data.days_of_week || [0, 4]);
      setCfgHour(data.preferred_hour ?? 9);
      setCfgMinute(data.preferred_minute ?? 0);
      setCfgSafetyNet(data.max_days_safety_net ?? 5);
      setCfgMissedRuns(data.stale_job_missed_runs ?? 2);
      setCfgMaxAgeDays(data.stale_job_max_age_days ?? 60);
    } catch (err) {
      console.error('Failed to load scheduler status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, []);

  const handleSyncNow = async () => {
    if (syncing) return;
    setSyncing(true);
    setSyncStage('Connecting to career sources...');

    const stages = [
      'Scraping verified company career portals...',
      'Synchronizing GitHub internships list...',
      'Evaluating freshness & archiving stale vacancies...',
    ];

    let stageIdx = 0;
    const stageTimer = setInterval(() => {
      if (stageIdx < stages.length) {
        setSyncStage(stages[stageIdx]);
        stageIdx++;
      }
    }, 1200);

    try {
      const result = await api.triggerSchedulerSync();
      clearInterval(stageTimer);
      if (result.success) {
        setToastMsg({
          type: 'success',
          text: `Sync complete: ${result.jobs_new} new, ${result.jobs_updated} updated, ${result.jobs_retired} closed (${result.internships_synced} internships verified)`,
        });
      } else {
        setToastMsg({
          type: 'error',
          text: `Sync partial: ${result.errors.join('; ')}`,
        });
      }
      await fetchStatus();
      if (onSyncCompleted) onSyncCompleted();
    } catch (err: any) {
      clearInterval(stageTimer);
      setToastMsg({
        type: 'error',
        text: `Sync failed: ${err.message || 'Server error'}`,
      });
    } finally {
      setSyncing(false);
      setSyncStage('');
      setTimeout(() => setToastMsg(null), 8000);
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      await api.updateSchedulerSettings({
        enabled: cfgEnabled,
        days_of_week: cfgDays,
        preferred_hour: cfgHour,
        preferred_minute: cfgMinute,
        max_days_safety_net: cfgSafetyNet,
        stale_job_missed_runs: cfgMissedRuns,
        stale_job_max_age_days: cfgMaxAgeDays,
      });
      await fetchStatus();
      setIsModalOpen(false);
      setToastMsg({ type: 'success', text: 'Automatic sync settings saved successfully.' });
      setTimeout(() => setToastMsg(null), 4000);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    } finally {
      setSavingSettings(false);
    }
  };

  const toggleDay = (day: number) => {
    if (cfgDays.includes(day)) {
      if (cfgDays.length > 1) {
        setCfgDays(cfgDays.filter((d) => d !== day));
      }
    } else {
      setCfgDays([...cfgDays, day].sort());
    }
  };

  const formatTimestamp = (isoStr?: string | null) => {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(language === 'fr' ? 'fr-FR' : (language === 'nl' ? 'nl-NL' : 'en-US'), {
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const formatNextDue = (isoStr?: string | null) => {
    if (!status?.enabled) return 'Disabled';
    if (!isoStr) return 'Pending evaluation';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(language === 'fr' ? 'fr-FR' : (language === 'nl' ? 'nl-NL' : 'en-US'), {
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const lastSuccess = status?.companies_scrape?.last_success_at || status?.internships_sync?.last_success_at;

  return (
    <BannerContainer className={compact ? 'compact' : ''}>
      <div className="status-info">
        <Clock size={15} className="clock-icon" />
        <span className="sync-text">
          Last synced: <strong>{formatTimestamp(lastSuccess)}</strong>
        </span>
        <span className="dot-sep">·</span>
        <span className="next-text">
          Next: <strong>{formatNextDue(status?.next_due_at)}</strong>
        </span>
      </div>

      <div className="actions">
        {syncing && <span className="sync-stage-pill">{syncStage}</span>}

        <button
          className={`sync-btn ${syncing ? 'loading' : ''}`}
          onClick={handleSyncNow}
          disabled={syncing}
          title="Scrape company career portals and sync GitHub internships now"
        >
          <RotateCw size={14} className={syncing ? 'spin' : ''} />
          <span>{syncing ? 'Syncing...' : 'Sync now'}</span>
        </button>

        <button
          className="settings-btn"
          onClick={() => setIsModalOpen(true)}
          title="Automatic update schedule settings"
        >
          <Settings2 size={15} />
        </button>
      </div>

      {toastMsg && (
        <ToastNotification className={toastMsg.type}>
          {toastMsg.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{toastMsg.text}</span>
          <button className="close-toast" onClick={() => setToastMsg(null)}>
            <X size={14} />
          </button>
        </ToastNotification>
      )}

      {/* Settings Modal */}
      {isModalOpen && (
        <ModalBackdrop onClick={() => setIsModalOpen(false)}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="title-area">
                <Calendar size={20} className="header-icon" />
                <h3>Automatic Opportunity Updates</h3>
              </div>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p className="desc-text">
                Compust periodically checks verified employer career portals and the curated GitHub internship directories,
                imports new vacancies, and archives stale ones while ensuring your saved jobs and applications remain strictly preserved.
              </p>

              {/* Enable Toggle */}
              <div className="setting-row">
                <div>
                  <div className="row-label">Enable Scheduled Sync</div>
                  <div className="row-sub">Runs automatically when the app is open or starts up.</div>
                </div>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={cfgEnabled}
                    onChange={(e) => setCfgEnabled(e.target.checked)}
                  />
                  <span className="slider round" />
                </label>
              </div>

              {/* Days of Week */}
              <div className="setting-block">
                <div className="row-label">Scheduled Days</div>
                <div className="row-sub">Select which days of the week automatic runs take place:</div>
                <div className="days-picker">
                  {DAYS_OF_WEEK.map((d) => (
                    <button
                      key={d.value}
                      type="button"
                      className={`day-btn ${cfgDays.includes(d.value) ? 'selected' : ''}`}
                      onClick={() => toggleDay(d.value)}
                    >
                      {cfgDays.includes(d.value) && <Check size={12} className="check-icon" />}
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preferred Time Window */}
              <div className="setting-row">
                <div>
                  <div className="row-label">Preferred Time (Local)</div>
                  <div className="row-sub">Sync triggers on the first app launch on or after this time.</div>
                </div>
                <div className="time-inputs">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={cfgHour}
                    onChange={(e) => setCfgHour(Math.max(0, Math.min(23, parseInt(e.target.value) || 0)))}
                    className="time-num-input"
                  />
                  <span>:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={cfgMinute}
                    onChange={(e) => setCfgMinute(Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
                    className="time-num-input"
                  />
                </div>
              </div>

              {/* Safety Net */}
              <div className="setting-row">
                <div>
                  <div className="row-label">Safety Net Interval</div>
                  <div className="row-sub">Trigger a catch-up run if more than N days pass without a successful sync:</div>
                </div>
                <div className="num-with-unit">
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={cfgSafetyNet}
                    onChange={(e) => setCfgSafetyNet(Math.max(1, parseInt(e.target.value) || 5))}
                    className="number-input"
                  />
                  <span>days</span>
                </div>
              </div>

              {/* Stale Retirement Rules */}
              <div className="setting-block safety-notice">
                <div className="notice-header">
                  <ShieldCheck size={16} />
                  <span>Vacancy Retention & Safety Guarantee</span>
                </div>
                <p>
                  Any opportunity you bookmark, note, track, or apply to is <strong>strictly protected</strong> and will NEVER be removed.
                  Untracked vacancies are marked archived only after missing <strong>{cfgMissedRuns} consecutive verified scrapes</strong> or exceeding <strong>{cfgMaxAgeDays} days</strong> of age.
                </p>
              </div>

              {/* Recent Run History */}
              {status?.recent_history && status.recent_history.length > 0 && (
                <div className="setting-block">
                  <div className="row-label">Recent Run History</div>
                  <div className="history-table-wrapper">
                    <table className="history-table">
                      <thead>
                        <tr>
                          <th>Finished</th>
                          <th>Trigger</th>
                          <th>Outcome</th>
                          <th>New / Retired</th>
                        </tr>
                      </thead>
                      <tbody>
                        {status.recent_history.slice(0, 5).map((h: any) => (
                          <tr key={h.id}>
                            <td>{formatTimestamp(h.finished_at)}</td>
                            <td><span className="trigger-badge">{h.trigger}</span></td>
                            <td>
                              <span className={`status-badge ${h.status}`}>
                                {h.status}
                              </span>
                            </td>
                            <td>+{h.jobs_new} / -{h.jobs_retired}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  setIsModalOpen(false);
                  handleSyncNow();
                }}
              >
                <Play size={14} />
                <span>Run Now</span>
              </button>
              <div className="footer-right">
                <button className="btn-cancel" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button
                  className="btn-primary"
                  onClick={handleSaveSettings}
                  disabled={savingSettings}
                >
                  {savingSettings ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>
          </ModalContent>
        </ModalBackdrop>
      )}
    </BannerContainer>
  );
};

const BannerContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(8px);
  font-size: 0.85rem;
  color: #94a3b8;
  position: relative;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

  &.compact {
    padding: 6px 12px;
    font-size: 0.8rem;
  }

  .status-info {
    display: flex;
    align-items: center;
    gap: 8px;

    .clock-icon {
      color: #3b82f6;
    }

    strong {
      color: #e2e8f0;
      font-weight: 600;
    }

    .dot-sep {
      opacity: 0.4;
    }
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 10px;

    .sync-stage-pill {
      font-size: 0.75rem;
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.12);
      padding: 3px 10px;
      border-radius: 12px;
      border: 1px solid rgba(59, 130, 246, 0.25);
      animation: pulse 1.5s infinite;
    }

    .sync-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.85), rgba(37, 99, 235, 0.85));
      border: 1px solid rgba(96, 165, 250, 0.4);
      border-radius: 8px;
      color: #ffffff;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover:not(:disabled) {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
        transform: translateY(-1px);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .spin {
        animation: spin 1s linear infinite;
      }
    }

    .settings-btn {
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 8px;
      color: #94a3b8;
      padding: 5px 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      transition: all 0.2s ease;

      &:hover {
        color: #f1f5f9;
        border-color: rgba(148, 163, 184, 0.4);
        background: rgba(51, 65, 85, 0.8);
      }
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
  }
`;

const ToastNotification = styled.div`
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.82rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  animation: slideDown 0.25s ease-out;

  &.success {
    background: #064e3b;
    border: 1px solid #059669;
    color: #a7f3d0;
  }

  &.error {
    background: #7f1d1d;
    border: 1px solid #dc2626;
    color: #fecaca;
  }

  .close-toast {
    background: transparent;
    border: none;
    color: inherit;
    opacity: 0.7;
    cursor: pointer;
    margin-left: 6px;

    &:hover {
      opacity: 1;
    }
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
`;

const ModalContent = styled.div`
  background: #0f172a;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #f8fafc;

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);

    .title-area {
      display: flex;
      align-items: center;
      gap: 10px;

      .header-icon {
        color: #3b82f6;
      }

      h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
      }
    }

    .close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      &:hover { color: #f1f5f9; }
    }
  }

  .modal-body {
    padding: 20px 24px;
    overflow-y: auto;
    max-height: 70vh;
    display: flex;
    flex-direction: column;
    gap: 18px;

    .desc-text {
      font-size: 0.85rem;
      color: #94a3b8;
      line-height: 1.5;
      margin: 0;
    }

    .row-label {
      font-size: 0.9rem;
      font-weight: 600;
      color: #e2e8f0;
    }

    .row-sub {
      font-size: 0.8rem;
      color: #64748b;
      margin-top: 2px;
    }

    .setting-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 14px;
      background: rgba(30, 41, 59, 0.4);
      border-radius: 10px;
      border: 1px solid rgba(148, 163, 184, 0.08);
    }

    .setting-block {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .days-picker {
      display: flex;
      gap: 8px;
      margin-top: 4px;

      .day-btn {
        flex: 1;
        padding: 8px 4px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 8px;
        color: #94a3b8;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 3px;
        transition: all 0.2s ease;

        &.selected {
          background: rgba(59, 130, 246, 0.2);
          border-color: #3b82f6;
          color: #60a5fa;
          font-weight: 600;
        }

        &:hover:not(.selected) {
          background: rgba(51, 65, 85, 0.6);
          color: #e2e8f0;
        }
      }
    }

    .time-inputs {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #94a3b8;
      font-weight: 600;

      .time-num-input {
        width: 48px;
        padding: 6px 8px;
        background: #090d16;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 6px;
        color: #f8fafc;
        font-size: 0.9rem;
        text-align: center;
      }
    }

    .num-with-unit {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #94a3b8;
      font-size: 0.85rem;

      .number-input {
        width: 56px;
        padding: 6px 8px;
        background: #090d16;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 6px;
        color: #f8fafc;
        font-size: 0.9rem;
        text-align: center;
      }
    }

    .safety-notice {
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 0.82rem;
      color: #a7f3d0;
      line-height: 1.45;

      .notice-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 600;
        margin-bottom: 6px;
        color: #34d399;
      }

      p {
        margin: 0;
      }
    }

    .history-table-wrapper {
      max-height: 140px;
      overflow-y: auto;
      border: 1px solid rgba(148, 163, 184, 0.12);
      border-radius: 8px;

      .history-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.78rem;

        th {
          background: #1e293b;
          padding: 6px 10px;
          text-align: left;
          color: #94a3b8;
          font-weight: 500;
        }

        td {
          padding: 6px 10px;
          border-top: 1px solid rgba(148, 163, 184, 0.08);
          color: #cbd5e1;
        }

        .trigger-badge {
          background: rgba(148, 163, 184, 0.15);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.72rem;
        }

        .status-badge {
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.72rem;
          font-weight: 500;

          &.success {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
          }
          &.partial {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
          }
          &.failed {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
          }
        }
      }
    }

    /* Switch CSS */
    .switch {
      position: relative;
      display: inline-block;
      width: 44px;
      height: 24px;

      input {
        opacity: 0;
        width: 0;
        height: 0;
      }

      .slider {
        position: absolute;
        cursor: pointer;
        inset: 0;
        background-color: #334155;
        transition: 0.3s;
        border-radius: 24px;

        &:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: 0.3s;
          border-radius: 50%;
        }
      }

      input:checked + .slider {
        background-color: #3b82f6;
      }

      input:checked + .slider:before {
        transform: translateX(20px);
      }
    }
  }

  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    background: #090d16;
    border-top: 1px solid rgba(148, 163, 184, 0.12);

    .footer-right {
      display: flex;
      gap: 10px;
    }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
      border-radius: 8px;
      font-size: 0.85rem;
      cursor: pointer;
      &:hover { background: rgba(59, 130, 246, 0.2); }
    }

    .btn-cancel {
      padding: 7px 14px;
      background: transparent;
      border: 1px solid rgba(148, 163, 184, 0.2);
      color: #94a3b8;
      border-radius: 8px;
      font-size: 0.85rem;
      cursor: pointer;
      &:hover { color: #f1f5f9; }
    }

    .btn-primary {
      padding: 7px 16px;
      background: #2563eb;
      border: 1px solid #3b82f6;
      color: white;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      &:hover:not(:disabled) { background: #1d4ed8; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }
  }
`;
