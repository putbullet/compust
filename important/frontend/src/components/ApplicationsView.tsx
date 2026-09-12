import React, { useState, useEffect, useMemo } from 'react';
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
  Table as TableIcon,
  Columns as KanbanIcon,
  GitFork,
  Download,
  Plus,
  RefreshCw,
  Search,
  TrendingUp,
  Percent,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  ApplicationItem,
  ApplicationStats,
  ApplicationStatus,
  Job,
  SankeyData,
} from '../api/client';
import { AddApplicationModal } from './Applications/AddApplicationModal';
import { ApplicationSpreadsheet } from './Applications/ApplicationSpreadsheet';
import { SankeyPipelineChart } from './Applications/SankeyPipelineChart';

interface ApplicationsViewProps {
  onSelectJob: (job: Job) => void;
}

type ViewMode = 'spreadsheet' | 'kanban' | 'pipeline';

const KANBAN_STAGES: Array<{ id: ApplicationStatus; label: string; icon: any; color: string }> = [
  { id: 'saved', label: 'Saved / Bookmarked', icon: Bookmark, color: '#3b82f6' },
  { id: 'applied', label: 'Applied', icon: Send, color: '#f59e0b' },
  { id: 'interviewing', label: 'Interviewing', icon: Calendar, color: '#a855f7' },
  { id: 'offer', label: 'Offers', icon: Award, color: '#10b981' },
  { id: 'rejected', label: 'Archived / Rejected', icon: XCircle, color: '#64748b' },
];

export const ApplicationsView: React.FC<ApplicationsViewProps> = ({ onSelectJob }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('spreadsheet');
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [pipelineData, setPipelineData] = useState<SankeyData | null>(null);

  const [loading, setLoading] = useState(true);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingNotesId, setEditingNotesId] = useState<number | null>(null);
  const [tempNotes, setTempNotes] = useState('');

  const loadAllData = async () => {
    try {
      setLoading(true);
      const apps = await api.getApplications();
      setApplications(apps);
    } catch (err: any) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
    }

    loadStats();
    loadPipeline();
  };

  const loadStats = async () => {
    try {
      const s = await api.getApplicationStats();
      setStats(s);
    } catch (err: any) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadPipeline = async () => {
    try {
      setPipelineLoading(true);
      const p = await api.getPipelineData();
      setPipelineData(p);
    } catch (err: any) {
      console.error('Failed to load pipeline:', err);
    } finally {
      setPipelineLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleUpdateApplication = async (appId: number, data: any) => {
    try {
      const updated = await api.updateApplication(appId, data);
      setApplications((prev) => prev.map((a) => (a.id === appId ? updated : a)));
      loadStats();
      loadPipeline();
    } catch (err: any) {
      alert(err.message || 'Failed to update application');
    }
  };

  const handleDelete = async (appId: number) => {
    if (!confirm('Remove this application from your tracker?')) return;
    try {
      await api.deleteApplication(appId);
      setApplications((prev) => prev.filter((a) => a.id !== appId));
      loadStats();
      loadPipeline();
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

  const handleApplicationCreated = (newApp: ApplicationItem) => {
    setApplications((prev) => [newApp, ...prev]);
    loadStats();
    loadPipeline();
  };

  const handleExportXlsx = async () => {
    try {
      setExporting(true);
      await api.exportApplicationsXlsx();
    } catch (err: any) {
      console.error('Export failed:', err);
      alert('Failed to export Excel workbook. Please check authentication.');
    } finally {
      setExporting(false);
    }
  };

  // Distinct sources for dropdown filter
  const distinctSources = useMemo(() => {
    const s = new Set<string>();
    applications.forEach((a) => {
      if (a.source) s.add(a.source);
    });
    return Array.from(s).sort();
  }, [applications]);

  // Filtered applications
  const filteredApplications = useMemo(() => {
    return applications.filter((app) => {
      if (selectedSource !== 'all' && app.source !== selectedSource) {
        return false;
      }
      if (selectedStatus !== 'all' && app.status !== selectedStatus) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const titleMatch = app.effective_title.toLowerCase().includes(q);
        const companyMatch = app.effective_company.toLowerCase().includes(q);
        const notesMatch = (app.notes || '').toLowerCase().includes(q);
        const recruiterMatch = (app.recruiter || '').toLowerCase().includes(q);
        const contactMatch = (app.contact_name || '').toLowerCase().includes(q);
        const locationMatch = (app.effective_location || '').toLowerCase().includes(q);
        if (
          !titleMatch &&
          !companyMatch &&
          !notesMatch &&
          !recruiterMatch &&
          !contactMatch &&
          !locationMatch
        ) {
          return false;
        }
      }
      return true;
    });
  }, [applications, selectedSource, selectedStatus, searchQuery]);

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
      {/* Top Header Card */}
      <HeaderCard className="glass-panel">
        <div className="header-left">
          <h2>Application Tracker & Management</h2>
          <p className="subtitle">
            Comprehensive spreadsheet grid, recruitment funnel Sankey, and candidate pipeline tracking.
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="action-btn export-btn"
            onClick={handleExportXlsx}
            disabled={exporting}
            title="Download full applications database as styled Excel workbook"
          >
            <Download size={15} />
            <span>{exporting ? 'Exporting...' : 'Export Excel (.xlsx)'}</span>
          </button>

          <button
            type="button"
            className="action-btn add-btn"
            onClick={() => setIsAddModalOpen(true)}
          >
            <Plus size={16} />
            <span>Add Application</span>
          </button>

          <button
            type="button"
            className="refresh-btn"
            onClick={loadAllData}
            title="Refresh data"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </HeaderCard>

      {/* KPI Metrics Summary Row */}
      {stats && (
        <MetricsRow>
          <MetricCard>
            <div className="metric-header">
              <span className="metric-label">Total Applications</span>
              <Bookmark size={15} className="metric-icon blue" />
            </div>
            <div className="metric-val">{stats.total_applications}</div>
            <div className="metric-sub">{stats.active_applications} active in pipeline</div>
          </MetricCard>

          <MetricCard>
            <div className="metric-header">
              <span className="metric-label">Interview Rate</span>
              <TrendingUp size={15} className="metric-icon purple" />
            </div>
            <div className="metric-val">{stats.interview_rate_percent}%</div>
            <div className="metric-sub">
              {stats.avg_days_to_interview ? `Avg ${stats.avg_days_to_interview}d to 1st interview` : 'First round rate'}
            </div>
          </MetricCard>

          <MetricCard>
            <div className="metric-header">
              <span className="metric-label">Response Rate</span>
              <Percent size={15} className="metric-icon amber" />
            </div>
            <div className="metric-val">{stats.response_rate_percent}%</div>
            <div className="metric-sub">Replies & screening reached</div>
          </MetricCard>

          <MetricCard>
            <div className="metric-header">
              <span className="metric-label">Offers Received</span>
              <Award size={15} className="metric-icon emerald" />
            </div>
            <div className="metric-val">{stats.status_breakdown?.offer || 0}</div>
            <div className="metric-sub">{stats.offer_rate_percent}% conversion from applied</div>
          </MetricCard>

          <MetricCard>
            <div className="metric-header">
              <span className="metric-label">Offer Accepted</span>
              <CheckCircle2 size={15} className="metric-icon green" />
            </div>
            <div className="metric-val">{stats.status_breakdown?.accepted || 0}</div>
            <div className="metric-sub">{stats.acceptance_rate_percent}% offer closure rate</div>
          </MetricCard>
        </MetricsRow>
      )}

      {/* Control Bar: Search, Filters, View Modes */}
      <ControlBar className="glass-panel">
        <div className="search-group">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search by title, company, notes, contact..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Sources</option>
            {distinctSources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Stages</option>
            <option value="applied">Applied</option>
            <option value="saved">Saved</option>
            <option value="interviewing">Interviewing</option>
            <option value="1st_interview">1st Interview</option>
            <option value="2nd_interview">2nd Interview</option>
            <option value="final_interview">Final Interview</option>
            <option value="offer">Offer Received</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="no_answer">No Answer / Ghosted</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
        </div>

        <div className="view-switcher">
          <button
            type="button"
            className={`view-btn ${viewMode === 'spreadsheet' ? 'active' : ''}`}
            onClick={() => setViewMode('spreadsheet')}
            title="Excel Spreadsheet Table"
          >
            <TableIcon size={15} />
            <span>Table</span>
          </button>

          <button
            type="button"
            className={`view-btn ${viewMode === 'kanban' ? 'active' : ''}`}
            onClick={() => setViewMode('kanban')}
            title="Kanban Pipeline Board"
          >
            <KanbanIcon size={15} />
            <span>Board</span>
          </button>

          <button
            type="button"
            className={`view-btn ${viewMode === 'pipeline' ? 'active' : ''}`}
            onClick={() => setViewMode('pipeline')}
            title="Sankey Recruitment Funnel"
          >
            <GitFork size={15} />
            <span>Funnel</span>
          </button>
        </div>
      </ControlBar>

      {/* Main View Render */}
      {viewMode === 'spreadsheet' && (
        <ApplicationSpreadsheet
          applications={filteredApplications}
          onUpdateApplication={handleUpdateApplication}
          onDeleteApplication={handleDelete}
          onSelectJob={onSelectJob}
          loading={loading}
        />
      )}

      {viewMode === 'pipeline' && (
        <SankeyPipelineChart
          data={pipelineData}
          loading={pipelineLoading}
        />
      )}

      {viewMode === 'kanban' && (
        <KanbanBoard>
          {KANBAN_STAGES.map((stage) => {
            const stageApps = filteredApplications.filter((a) => {
              if (stage.id === 'interviewing') {
                return (
                  a.status === 'interviewing' ||
                  a.status === '1st_interview' ||
                  a.status === '2nd_interview' ||
                  a.status === '3rd_interview' ||
                  a.status === 'final_interview'
                );
              }
              if (stage.id === 'offer') {
                return a.status === 'offer' || a.status === 'accepted';
              }
              if (stage.id === 'rejected') {
                return a.status === 'rejected' || a.status === 'withdrawn' || a.status === 'no_answer';
              }
              return a.status === stage.id;
            });
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
                            {app.effective_title}
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

                        <div className="card-meta">
                          <span className="company-badge">{app.effective_company}</span>
                          <span className="source-badge">{app.source}</span>
                          {app.effective_location && (
                            <span className="location-info">
                              <MapPin size={11} />
                              {app.effective_location}
                            </span>
                          )}
                        </div>

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
                              handleUpdateApplication(app.id, {
                                status: e.target.value as ApplicationStatus,
                              })
                            }
                            className="stage-select"
                          >
                            {KANBAN_STAGES.map((s) => (
                              <option key={s.id} value={s.id}>
                                Move to {s.label}
                              </option>
                            ))}
                          </select>

                          {app.effective_job_url && (
                            <a
                              href={app.effective_job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="view-job-btn"
                              title="Open posting"
                            >
                              <ExternalLink size={13} />
                            </a>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </KanbanBoard>
      )}

      {/* Add Manual Application Modal */}
      <AddApplicationModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onApplicationCreated={handleApplicationCreated}
      />
    </StyledContainer>
  );
};

const StyledContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 16px;
    color: #94a3b8;

    .spin {
      animation: spin 1s linear infinite;
      color: #6366f1;
    }
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

const HeaderCard = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-radius: 16px;
  flex-wrap: wrap;
  gap: 16px;

  .header-left {
    h2 {
      font-size: 1.45rem;
      font-weight: 700;
      color: #f8fafc;
      margin: 0 0 4px;
    }
    .subtitle {
      font-size: 0.85rem;
      color: #94a3b8;
      margin: 0;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;

    .action-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0.6rem 1rem;
      border-radius: 8px;
      font-size: 0.825rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      outline: none;

      &.export-btn {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;

        &:hover:not(:disabled) {
          background: rgba(16, 185, 129, 0.2);
          color: #6ee7b7;
        }

        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      }

      &.add-btn {
        background: linear-gradient(135deg, #6366f1, #3b82f6);
        border: none;
        color: white;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);

        &:hover {
          opacity: 0.95;
          box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
        }
      }
    }

    .refresh-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;
      padding: 0.6rem;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #f8fafc;
      }
    }
  }
`;

const MetricsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
`;

const MetricCard = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .metric-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .metric-label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #94a3b8;
    }

    .metric-icon {
      &.blue { color: #60a5fa; }
      &.purple { color: #c084fc; }
      &.amber { color: #fbbf24; }
      &.emerald { color: #34d399; }
      &.green { color: #10b981; }
    }
  }

  .metric-val {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .metric-sub {
    font-size: 0.725rem;
    color: #64748b;
  }
`;

const ControlBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-radius: 12px;
  gap: 14px;
  flex-wrap: wrap;

  .search-group {
    flex: 1;
    min-width: 240px;
    position: relative;
    display: flex;
    align-items: center;

    .search-icon {
      position: absolute;
      left: 0.75rem;
      color: #64748b;
    }

    input {
      width: 100%;
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 0.5rem 0.75rem 0.5rem 2.2rem;
      color: #f8fafc;
      font-size: 0.825rem;
      outline: none;

      &:focus {
        border-color: #6366f1;
      }
    }
  }

  .filter-group {
    display: flex;
    gap: 8px;

    .filter-select {
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 0.5rem 0.75rem;
      color: #cbd5e1;
      font-size: 0.8rem;
      outline: none;
      cursor: pointer;

      option {
        background: #0f172a;
        color: #f8fafc;
      }

      &:focus {
        border-color: #6366f1;
      }
    }
  }

  .view-switcher {
    display: flex;
    background: rgba(0, 0, 0, 0.3);
    padding: 3px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    .view-btn {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 0.775rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.12s ease;

      &.active {
        background: rgba(99, 102, 241, 0.25);
        color: #f8fafc;
      }

      &:hover:not(.active) {
        color: #cbd5e1;
      }
    }
  }
`;

const KanbanBoard = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
  gap: 16px;
  align-items: flex-start;

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
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;

    .company-badge {
      font-weight: 600;
      color: #cbd5e1;
    }

    .source-badge {
      background: rgba(99, 102, 241, 0.15);
      color: #818cf8;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      font-size: 0.7rem;
    }

    .location-info {
      display: flex;
      align-items: center;
      gap: 3px;
      color: #94a3b8;
    }
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
      background: #3b82f6;
      border: none;
      border-radius: 6px;
      color: white;
      cursor: pointer;
    }
  }

  .stage-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;

    .stage-select {
      flex: 1;
      padding: 5px 8px;
      font-size: 0.76rem;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      color: #cbd5e1;
      outline: none;
      cursor: pointer;

      option {
        background: #0f172a;
        color: #f8fafc;
      }
    }

    .view-job-btn {
      padding: 5px 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      color: #94a3b8;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #f8fafc;
      }
    }
  }
`;
