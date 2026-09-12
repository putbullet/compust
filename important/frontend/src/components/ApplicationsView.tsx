import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Bookmark,
  Send,
  Calendar,
  Award,
  XCircle,
  Trash2,
  ExternalLink,
  Edit2,
  Check,
  MapPin,
  Clock,
} from 'lucide-react';
import { api } from '../api/client';
import type { ApplicationItem, Job } from '../api/client';

interface ApplicationsViewProps {
  onSelectJob: (job: Job) => void;
}

const STAGES: Array<{ id: ApplicationItem['status']; label: string; icon: any; color: string }> = [
  { id: 'saved', label: 'Saved', icon: Bookmark, color: '#3b82f6' },
  { id: 'applied', label: 'Applied', icon: Send, color: '#f59e0b' },
  { id: 'interviewing', label: 'Interviewing', icon: Calendar, color: '#a855f7' },
  { id: 'offer', label: 'Offer Received', icon: Award, color: '#10b981' },
  { id: 'rejected', label: 'Archived / Rejected', icon: XCircle, color: '#64748b' },
];

export const ApplicationsView: React.FC<ApplicationsViewProps> = ({ onSelectJob }) => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingNotesId, setEditingNotesId] = useState<number | null>(null);
  const [tempNotes, setTempNotes] = useState('');

  const loadApplications = async () => {
    try {
      setLoading(true);
      const data = await api.getApplications();
      setApplications(data);
    } catch (err: any) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  const handleStageChange = async (appId: number, nextStatus: ApplicationItem['status']) => {
    try {
      const updated = await api.updateApplication(appId, { status: nextStatus });
      setApplications((prev) => prev.map((a) => (a.id === appId ? updated : a)));
    } catch (err: any) {
      alert('Failed to update stage');
    }
  };

  const handleDelete = async (appId: number) => {
    if (!confirm('Remove this application from your pipeline?')) return;
    try {
      await api.deleteApplication(appId);
      setApplications((prev) => prev.filter((a) => a.id !== appId));
    } catch (err: any) {
      alert('Failed to delete application');
    }
  };

  const handleSaveNotes = async (appId: number) => {
    try {
      const updated = await api.updateApplication(appId, { notes: tempNotes });
      setApplications((prev) => prev.map((a) => (a.id === appId ? updated : a)));
      setEditingNotesId(null);
    } catch (err: any) {
      alert('Failed to save notes');
    }
  };

  if (loading) {
    return (
      <StyledContainer>
        <div className="loading-state glass-panel">
          <Clock className="spin" size={32} />
          <p>Loading your career applications pipeline...</p>
        </div>
      </StyledContainer>
    );
  }

  return (
    <StyledContainer>
      <div className="pipeline-header glass-panel">
        <div>
          <h2>Application Tracker</h2>
          <p className="subtitle">
            Manage your opportunities lifecycle from bookmarked postings to confirmed offers.
          </p>
        </div>
        <div className="header-stats">
          <div className="stat-pill">
            <span className="count">{applications.length}</span>
            <span className="label">Tracked</span>
          </div>
          <div className="stat-pill accent">
            <span className="count">
              {applications.filter((a) => a.status === 'interviewing' || a.status === 'offer').length}
            </span>
            <span className="label">Active Stages</span>
          </div>
        </div>
      </div>

      <div className="kanban-board">
        {STAGES.map((stage) => {
          const stageApps = applications.filter((a) => a.status === stage.id);
          const Icon = stage.icon;

          return (
            <div key={stage.id} className="kanban-column glass-panel">
              <div className="column-header" style={{ borderTopColor: stage.color }}>
                <div className="col-title">
                  <Icon size={16} style={{ color: stage.color }} />
                  <span>{stage.label}</span>
                </div>
                <span className="col-count">{stageApps.length}</span>
              </div>

              <div className="cards-wrapper">
                {stageApps.length === 0 ? (
                  <div className="empty-col">No {stage.label.toLowerCase()} jobs</div>
                ) : (
                  stageApps.map((app) => (
                    <div key={app.id} className="app-card">
                      <div className="card-top">
                        <h4
                          onClick={() => app.job && onSelectJob(app.job)}
                          className="job-title"
                          title="View vacancy details"
                        >
                          {app.job?.title || `Job #${app.job_id}`}
                        </h4>
                        <button
                          type="button"
                          onClick={() => handleDelete(app.id)}
                          className="action-icon-btn delete"
                          title="Remove application"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>

                      {app.job?.location && (
                        <div className="card-meta">
                          <MapPin size={12} />
                          <span>{app.job.location}</span>
                        </div>
                      )}

                      {/* Notes Section */}
                      <div className="notes-box">
                        {editingNotesId === app.id ? (
                          <div className="edit-notes-row">
                            <input
                              type="text"
                              value={tempNotes}
                              onChange={(e) => setTempNotes(e.target.value)}
                              placeholder="Add follow-up notes..."
                              className="notes-input"
                              autoFocus
                            />
                            <button
                              type="button"
                              onClick={() => handleSaveNotes(app.id)}
                              className="save-notes-btn"
                            >
                              <Check size={13} />
                            </button>
                          </div>
                        ) : (
                          <div
                            className="notes-display"
                            onClick={() => {
                              setEditingNotesId(app.id);
                              setTempNotes(app.notes || '');
                            }}
                          >
                            <span className={app.notes ? 'has-notes' : 'no-notes'}>
                              {app.notes || '+ Add notes...'}
                            </span>
                            <Edit2 size={11} className="edit-icon" />
                          </div>
                        )}
                      </div>

                      {/* Stage Transitions */}
                      <div className="stage-actions">
                        <select
                          value={app.status}
                          onChange={(e) =>
                            handleStageChange(app.id, e.target.value as ApplicationItem['status'])
                          }
                          className="stage-select"
                        >
                          {STAGES.map((s) => (
                            <option key={s.id} value={s.id}>
                              Move to {s.label}
                            </option>
                          ))}
                        </select>

                        {app.job && (
                          <button
                            type="button"
                            onClick={() => onSelectJob(app.job!)}
                            className="view-job-btn"
                            title="Open vacancy"
                          >
                            <ExternalLink size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </StyledContainer>
  );
};

const StyledContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: 1300px;
  margin: 0 auto;

  .pipeline-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 24px 32px;
    border-radius: 16px;

    h2 {
      font-size: 1.5rem;
      margin-bottom: 4px;
    }
    .subtitle {
      font-size: 0.88rem;
      color: #94a3b8;
    }
  }

  .header-stats {
    display: flex;
    gap: 12px;
  }

  .stat-pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;

    .count {
      font-size: 1.3rem;
      font-weight: 700;
      color: #f8fafc;
    }
    .label {
      font-size: 0.72rem;
      color: #94a3b8;
      text-transform: uppercase;
    }

    &.accent {
      background: rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.3);
      .count { color: #34d399; }
    }
  }

  .kanban-board {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
    gap: 16px;
    align-items: flex-start;
  }

  .kanban-column {
    padding: 16px;
    border-radius: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .col-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      color: #f8fafc;
    }

    .col-count {
      padding: 2px 8px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      font-size: 0.75rem;
      font-weight: 700;
      color: #94a3b8;
    }
  }

  .cards-wrapper {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 200px;
  }

  .empty-col {
    padding: 32px 12px;
    text-align: center;
    font-size: 0.82rem;
    color: #94a3b8;
    border: 1px dashed rgba(255, 255, 255, 0.12);
    border-radius: 10px;
  }

  .app-card {
    padding: 14px;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: all 0.2s;

    &:hover {
      border-color: rgba(59, 130, 246, 0.4);
      transform: translateY(-1px);
    }
  }

  .card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;

    .job-title {
      font-size: 0.88rem;
      font-weight: 600;
      color: #f8fafc;
      cursor: pointer;
      line-height: 1.35;
      word-break: break-word;
      overflow-wrap: break-word;

      &:hover {
        color: #60a5fa;
      }
    }
  }

  .action-icon-btn {
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    padding: 2px;
    border-radius: 4px;

    &:hover.delete {
      color: #f43f5e;
    }
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.76rem;
    color: #94a3b8;
    word-break: break-word;
  }

  .notes-box {
    margin-top: 4px;
  }

  .notes-display {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 6px 8px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.76rem;

    .no-notes { color: #94a3b8; font-style: italic; }
    .has-notes { color: #cbd5e1; word-break: break-word; }
    .edit-icon { color: #64748b; flex-shrink: 0; }

    &:hover {
      background: rgba(0, 0, 0, 0.35);
      .edit-icon { color: #94a3b8; }
    }
  }

  .edit-notes-row {
    display: flex;
    gap: 6px;

    .notes-input {
      flex: 1;
      padding: 4px 8px;
      font-size: 0.78rem;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid #3b82f6;
      border-radius: 6px;
      color: #f8fafc;
      outline: none;
    }

    .save-notes-btn {
      padding: 4px 8px;
      background: #2563eb;
      border: none;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
    }
  }

  .stage-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);

    .stage-select {
      flex: 1;
      padding: 5px 8px;
      font-size: 0.74rem;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      color: #94a3b8;
      outline: none;

      option { background: #0f172a; color: #f8fafc; }
    }

    .view-job-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 5px 8px;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 6px;
      color: #60a5fa;
      cursor: pointer;

      &:hover {
        background: #2563eb;
        color: #ffffff;
      }
    }
  }

  .loading-state {
    padding: 64px;
    text-align: center;
    color: #94a3b8;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;

    .spin {
      animation: spin 1.5s linear infinite;
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
