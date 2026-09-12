import React, { useState } from 'react';
import styled from 'styled-components';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  Trash2,
  Briefcase,
  History,
  X,
} from 'lucide-react';
import type { ApplicationItem, ApplicationStatus, Job } from '../../api/client';

interface ApplicationSpreadsheetProps {
  applications: ApplicationItem[];
  onUpdateApplication: (appId: number, data: any) => Promise<void>;
  onDeleteApplication: (appId: number) => Promise<void>;
  onSelectJob?: (job: Job) => void;
  loading?: boolean;
}

type SortField =
  | 'title'
  | 'company'
  | 'source'
  | 'status'
  | 'applied_at'
  | 'priority'
  | 'updated_at'
  | 'next_follow_up';

const STATUS_CONFIG: Record<
  ApplicationStatus,
  { label: string; color: string; bg: string; border: string }
> = {
  saved: { label: 'Saved', color: '#60a5fa', bg: 'rgba(59, 130, 246, 0.12)', border: 'rgba(59, 130, 246, 0.3)' },
  applied: { label: 'Applied', color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)' },
  no_answer: { label: 'No Answer', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.12)', border: 'rgba(148, 163, 184, 0.3)' },
  interviewing: { label: 'Interviewing', color: '#c084fc', bg: 'rgba(168, 85, 247, 0.12)', border: 'rgba(168, 85, 247, 0.3)' },
  '1st_interview': { label: '1st Round', color: '#a78bfa', bg: 'rgba(139, 92, 246, 0.12)', border: 'rgba(139, 92, 246, 0.3)' },
  '2nd_interview': { label: '2nd Round', color: '#818cf8', bg: 'rgba(99, 102, 241, 0.12)', border: 'rgba(99, 102, 241, 0.3)' },
  '3rd_interview': { label: '3rd Round', color: '#f472b6', bg: 'rgba(236, 72, 153, 0.12)', border: 'rgba(236, 72, 153, 0.3)' },
  final_interview: { label: 'Final Round', color: '#e879f9', bg: 'rgba(217, 70, 239, 0.12)', border: 'rgba(217, 70, 239, 0.3)' },
  offer: { label: 'Offer Received', color: '#34d399', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.3)' },
  accepted: { label: 'Accepted 🎉', color: '#10b981', bg: 'rgba(5, 150, 105, 0.18)', border: 'rgba(16, 185, 129, 0.4)' },
  rejected: { label: 'Rejected', color: '#f87171', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.3)' },
  withdrawn: { label: 'Withdrawn', color: '#64748b', bg: 'rgba(100, 116, 139, 0.12)', border: 'rgba(100, 116, 139, 0.3)' },
};

const ALL_STATUSES: ApplicationStatus[] = [
  'saved',
  'applied',
  'no_answer',
  'interviewing',
  '1st_interview',
  '2nd_interview',
  '3rd_interview',
  'final_interview',
  'offer',
  'accepted',
  'rejected',
  'withdrawn',
];

const SOURCES = [
  'Compust',
  'LinkedIn',
  'Indeed',
  'Company Website',
  'Referral',
  'Recruiter',
  'Glassdoor',
  'JobTeaser',
  'Email',
  'Other',
];

export const ApplicationSpreadsheet: React.FC<ApplicationSpreadsheetProps> = ({
  applications,
  onUpdateApplication,
  onDeleteApplication,
  onSelectJob,
}) => {
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Inline editing states
  const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  // History timeline modal state
  const [selectedAppForHistory, setSelectedAppForHistory] = useState<ApplicationItem | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sortedApplications = [...applications].sort((a, b) => {
    let valA: any = '';
    let valB: any = '';

    switch (sortField) {
      case 'title':
        valA = a.effective_title.toLowerCase();
        valB = b.effective_title.toLowerCase();
        break;
      case 'company':
        valA = a.effective_company.toLowerCase();
        valB = b.effective_company.toLowerCase();
        break;
      case 'source':
        valA = (a.source || '').toLowerCase();
        valB = (b.source || '').toLowerCase();
        break;
      case 'status':
        valA = a.status;
        valB = b.status;
        break;
      case 'applied_at':
        valA = a.applied_at || '';
        valB = b.applied_at || '';
        break;
      case 'priority':
        valA = a.priority || 'medium';
        valB = b.priority || 'medium';
        break;
      case 'next_follow_up':
        valA = a.next_follow_up || '';
        valB = b.next_follow_up || '';
        break;
      case 'updated_at':
      default:
        valA = a.updated_at || '';
        valB = b.updated_at || '';
        break;
    }

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const handleStartEdit = (app: ApplicationItem, field: string, currentValue: string) => {
    setEditingCell({ id: app.id, field });
    setEditValue(currentValue || '');
  };

  const handleCommitEdit = async (appId: number, field: string) => {
    try {
      await onUpdateApplication(appId, { [field]: editValue.trim() });
    } finally {
      setEditingCell(null);
    }
  };

  const handleStatusChange = async (appId: number, nextStatus: ApplicationStatus) => {
    await onUpdateApplication(appId, { status: nextStatus });
  };

  const handleSourceChange = async (appId: number, nextSource: string) => {
    await onUpdateApplication(appId, { source: nextSource });
  };

  const handlePriorityChange = async (appId: number, nextPriority: string) => {
    await onUpdateApplication(appId, { priority: nextPriority });
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown size={12} className="sort-idle" />;
    return sortAsc ? <ArrowUp size={12} className="sort-active" /> : <ArrowDown size={12} className="sort-active" />;
  };

  if (applications.length === 0) {
    return (
      <EmptyState>
        <Briefcase size={36} />
        <h4>No applications found</h4>
        <p>Start tracking your job search by adding manual entries or saving postings from Opportunities.</p>
      </EmptyState>
    );
  }

  return (
    <GridWrapper>
      <TableScrollContainer>
        <StyledTable>
          <thead>
            <tr>
              <th className="col-title" onClick={() => handleSort('title')}>
                <div className="th-content">
                  <span>Job Title</span>
                  {renderSortIcon('title')}
                </div>
              </th>
              <th className="col-company" onClick={() => handleSort('company')}>
                <div className="th-content">
                  <span>Company</span>
                  {renderSortIcon('company')}
                </div>
              </th>
              <th className="col-source" onClick={() => handleSort('source')}>
                <div className="th-content">
                  <span>Source</span>
                  {renderSortIcon('source')}
                </div>
              </th>
              <th className="col-status" onClick={() => handleSort('status')}>
                <div className="th-content">
                  <span>Status / Stage</span>
                  {renderSortIcon('status')}
                </div>
              </th>
              <th className="col-date" onClick={() => handleSort('applied_at')}>
                <div className="th-content">
                  <span>Applied</span>
                  {renderSortIcon('applied_at')}
                </div>
              </th>
              <th className="col-priority" onClick={() => handleSort('priority')}>
                <div className="th-content">
                  <span>Priority</span>
                  {renderSortIcon('priority')}
                </div>
              </th>
              <th className="col-salary">
                <div className="th-content">
                  <span>Salary / Pay</span>
                </div>
              </th>
              <th className="col-recruiter">
                <div className="th-content">
                  <span>Contact / Recruiter</span>
                </div>
              </th>
              <th className="col-followup" onClick={() => handleSort('next_follow_up')}>
                <div className="th-content">
                  <span>Follow-Up</span>
                  {renderSortIcon('next_follow_up')}
                </div>
              </th>
              <th className="col-notes">
                <div className="th-content">
                  <span>Notes</span>
                </div>
              </th>
              <th className="col-actions">
                <div className="th-content">
                  <span>Actions</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedApplications.map((app) => {
              const statusCfg = STATUS_CONFIG[app.status] || STATUS_CONFIG.saved;
              const appliedDisplay = app.applied_at
                ? new Date(app.applied_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })
                : '—';

              return (
                <tr key={app.id}>
                  {/* Job Title */}
                  <td className="cell-title">
                    <div className="title-row">
                      {app.job ? (
                        <span
                          className="title-link compust-job"
                          onClick={() => onSelectJob && onSelectJob(app.job!)}
                          title="View Compust job details"
                        >
                          {app.effective_title}
                        </span>
                      ) : (
                        <span className="title-text">{app.effective_title}</span>
                      )}
                      {app.effective_job_url && (
                        <a
                          href={app.effective_job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ext-url-icon"
                          title="Open original job link"
                        >
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                    {(app.effective_location || app.effective_country) && (
                      <span className="location-caption">
                        {[app.effective_location, app.effective_country].filter(Boolean).join(' • ')}
                      </span>
                    )}
                  </td>

                  {/* Company */}
                  <td className="cell-company">
                    <span className="company-text">{app.effective_company}</span>
                  </td>

                  {/* Source Dropdown */}
                  <td className="cell-source">
                    <SourceSelect
                      value={app.source || 'Compust'}
                      onChange={(e) => handleSourceChange(app.id, e.target.value)}
                    >
                      {SOURCES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </SourceSelect>
                  </td>

                  {/* Status Dropdown Pill */}
                  <td className="cell-status">
                    <StatusSelect
                      value={app.status}
                      onChange={(e) => handleStatusChange(app.id, e.target.value as ApplicationStatus)}
                      style={{
                        color: statusCfg.color,
                        background: statusCfg.bg,
                        borderColor: statusCfg.border,
                      }}
                    >
                      {ALL_STATUSES.map((st) => (
                        <option key={st} value={st}>
                          {STATUS_CONFIG[st]?.label || st}
                        </option>
                      ))}
                    </StatusSelect>
                  </td>

                  {/* Applied Date */}
                  <td className="cell-date">
                    <span className="date-text">{appliedDisplay}</span>
                  </td>

                  {/* Priority Pill */}
                  <td className="cell-priority">
                    <PrioritySelect
                      value={app.priority || 'medium'}
                      onChange={(e) => handlePriorityChange(app.id, e.target.value)}
                      className={app.priority || 'medium'}
                    >
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </PrioritySelect>
                  </td>

                  {/* Salary Inline Edit */}
                  <td
                    className="cell-editable"
                    onClick={() => {
                      if (editingCell?.id !== app.id || editingCell?.field !== 'salary') {
                        handleStartEdit(app, 'salary', app.salary || '');
                      }
                    }}
                  >
                    {editingCell?.id === app.id && editingCell?.field === 'salary' ? (
                      <InlineInput
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleCommitEdit(app.id, 'salary')}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleCommitEdit(app.id, 'salary');
                          if (e.key === 'Escape') setEditingCell(null);
                        }}
                      />
                    ) : (
                      <span className={app.salary ? 'cell-val' : 'cell-placeholder'}>
                        {app.salary || '+ Add salary'}
                      </span>
                    )}
                  </td>

                  {/* Recruiter / Contact */}
                  <td
                    className="cell-editable"
                    onClick={() => {
                      if (editingCell?.id !== app.id || editingCell?.field !== 'contact_name') {
                        handleStartEdit(app, 'contact_name', app.contact_name || app.recruiter || '');
                      }
                    }}
                  >
                    {editingCell?.id === app.id && editingCell?.field === 'contact_name' ? (
                      <InlineInput
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleCommitEdit(app.id, 'contact_name')}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleCommitEdit(app.id, 'contact_name');
                          if (e.key === 'Escape') setEditingCell(null);
                        }}
                      />
                    ) : (
                      <div className="contact-summary">
                        <span className={app.contact_name || app.recruiter ? 'cell-val' : 'cell-placeholder'}>
                          {app.contact_name || app.recruiter || '+ Add contact'}
                        </span>
                        {app.contact_email && <span className="contact-sub">{app.contact_email}</span>}
                      </div>
                    )}
                  </td>

                  {/* Next Follow-up Date */}
                  <td className="cell-followup">
                    <input
                      type="date"
                      className="inline-date-picker"
                      value={app.next_follow_up || ''}
                      onChange={(e) => onUpdateApplication(app.id, { next_follow_up: e.target.value || null })}
                    />
                  </td>

                  {/* Notes Inline Textarea/Cell */}
                  <td
                    className="cell-notes"
                    onClick={() => {
                      if (editingCell?.id !== app.id || editingCell?.field !== 'notes') {
                        handleStartEdit(app, 'notes', app.notes || '');
                      }
                    }}
                  >
                    {editingCell?.id === app.id && editingCell?.field === 'notes' ? (
                      <InlineInput
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleCommitEdit(app.id, 'notes')}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleCommitEdit(app.id, 'notes');
                          if (e.key === 'Escape') setEditingCell(null);
                        }}
                      />
                    ) : (
                      <div className="notes-preview" title={app.notes || 'Click to edit notes'}>
                        <span className={app.notes ? 'has-notes' : 'no-notes'}>
                          {app.notes || '+ Add notes...'}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* Actions (History, Delete) */}
                  <td className="cell-actions">
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="action-btn history-btn"
                        onClick={() => setSelectedAppForHistory(app)}
                        title="View status transition timeline"
                      >
                        <History size={14} />
                      </button>
                      <button
                        type="button"
                        className="action-btn delete-btn"
                        onClick={() => onDeleteApplication(app.id)}
                        title="Remove application"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </StyledTable>
      </TableScrollContainer>

      {/* Transition History Modal */}
      {selectedAppForHistory && (
        <HistoryModalBackdrop onClick={() => setSelectedAppForHistory(null)}>
          <HistoryModalContainer onClick={(e) => e.stopPropagation()}>
            <div className="hist-header">
              <div className="hist-title">
                <History size={18} />
                <h4>Application Stage History</h4>
              </div>
              <button
                type="button"
                className="close-hist-btn"
                onClick={() => setSelectedAppForHistory(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="hist-body">
              <div className="app-summary-card">
                <h5>{selectedAppForHistory.effective_title}</h5>
                <p>
                  {selectedAppForHistory.effective_company} • {selectedAppForHistory.source}
                </p>
              </div>

              <div className="timeline-wrapper">
                {(!selectedAppForHistory.history || selectedAppForHistory.history.length === 0) ? (
                  <p className="no-history-text">
                    No transition history recorded yet. Current status:{' '}
                    <strong>{selectedAppForHistory.status}</strong>.
                  </p>
                ) : (
                  selectedAppForHistory.history.map((item, idx) => (
                    <div key={item.id || idx} className="timeline-item">
                      <div className="timeline-dot" />
                      <div className="timeline-content">
                        <div className="timeline-meta">
                          <span className="status-transition">
                            {item.from_status ? (
                              <>
                                <span className="from-st">{item.from_status}</span>
                                <span className="arrow">→</span>
                              </>
                            ) : null}
                            <span className="to-st">{item.to_status}</span>
                          </span>
                          <span className="timestamp">
                            {new Date(item.changed_at).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        {item.notes && <p className="history-notes">{item.notes}</p>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </HistoryModalContainer>
        </HistoryModalBackdrop>
      )}
    </GridWrapper>
  );
};

const GridWrapper = styled.div`
  width: 100%;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
`;

const TableScrollContainer = styled.div`
  width: 100%;
  overflow-x: auto;
  max-height: 680px;

  &::-webkit-scrollbar {
    height: 8px;
    width: 8px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
  }
`;

const StyledTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.825rem;
  color: #e2e8f0;

  thead {
    position: sticky;
    top: 0;
    z-index: 10;
    background: #0f172a;
    border-bottom: 2px solid rgba(255, 255, 255, 0.1);

    th {
      padding: 0.75rem 0.85rem;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
      border-right: 1px solid rgba(255, 255, 255, 0.04);

      &:hover {
        background: rgba(255, 255, 255, 0.04);
        color: #f8fafc;
      }

      .th-content {
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }

      .sort-idle {
        opacity: 0.3;
      }
      .sort-active {
        color: #6366f1;
      }
    }
  }

  tbody {
    tr {
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      transition: background 0.12s ease;

      &:hover {
        background: rgba(255, 255, 255, 0.025);
      }

      &:nth-child(even) {
        background: rgba(255, 255, 255, 0.01);
      }
    }

    td {
      padding: 0.65rem 0.85rem;
      vertical-align: middle;
      border-right: 1px solid rgba(255, 255, 255, 0.03);
      white-space: nowrap;
    }
  }

  .col-title {
    min-width: 220px;
  }
  .col-company {
    min-width: 140px;
  }
  .col-source {
    min-width: 130px;
  }
  .col-status {
    min-width: 150px;
  }
  .col-date {
    min-width: 90px;
  }
  .col-priority {
    min-width: 100px;
  }
  .col-salary {
    min-width: 130px;
  }
  .col-recruiter {
    min-width: 160px;
  }
  .col-followup {
    min-width: 130px;
  }
  .col-notes {
    min-width: 200px;
  }
  .col-actions {
    min-width: 80px;
  }

  .cell-title {
    .title-row {
      display: flex;
      align-items: center;
      gap: 0.4rem;

      .title-link {
        font-weight: 600;
        color: #f8fafc;
        cursor: pointer;

        &.compust-job:hover {
          color: #60a5fa;
          text-decoration: underline;
        }
      }

      .title-text {
        font-weight: 600;
        color: #f8fafc;
      }

      .ext-url-icon {
        color: #94a3b8;
        display: flex;
        align-items: center;
        transition: color 0.15s ease;

        &:hover {
          color: #6366f1;
        }
      }
    }

    .location-caption {
      display: block;
      font-size: 0.725rem;
      color: #64748b;
      margin-top: 0.15rem;
    }
  }

  .cell-company {
    .company-text {
      font-weight: 500;
      color: #cbd5e1;
    }
  }

  .cell-date {
    .date-text {
      font-size: 0.775rem;
      color: #94a3b8;
    }
  }

  .cell-editable {
    cursor: text;

    .cell-val {
      color: #e2e8f0;
      font-size: 0.8rem;
    }

    .cell-placeholder {
      color: #475569;
      font-size: 0.75rem;
      font-style: italic;

      &:hover {
        color: #94a3b8;
      }
    }

    .contact-summary {
      display: flex;
      flex-direction: column;

      .contact-sub {
        font-size: 0.7rem;
        color: #64748b;
      }
    }
  }

  .inline-date-picker {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 0.25rem 0.4rem;
    color: #cbd5e1;
    font-size: 0.75rem;
    outline: none;

    &:focus {
      border-color: #6366f1;
      background: rgba(30, 41, 59, 0.8);
    }
  }

  .cell-notes {
    max-width: 250px;
    cursor: text;

    .notes-preview {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      .has-notes {
        color: #cbd5e1;
        font-size: 0.8rem;
      }

      .no-notes {
        color: #475569;
        font-size: 0.75rem;
        font-style: italic;

        &:hover {
          color: #94a3b8;
        }
      }
    }
  }

  .cell-actions {
    .action-buttons {
      display: flex;
      align-items: center;
      gap: 0.4rem;

      .action-btn {
        background: transparent;
        border: none;
        padding: 0.35rem;
        border-radius: 6px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.15s ease;

        &.history-btn {
          color: #94a3b8;
          &:hover {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
          }
        }

        &.delete-btn {
          color: #94a3b8;
          &:hover {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
          }
        }
      }
    }
  }
`;

const StatusSelect = styled.select`
  appearance: none;
  padding: 0.3rem 0.65rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid transparent;
  outline: none;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;

  option {
    background: #0f172a;
    color: #f8fafc;
  }

  &:hover {
    filter: brightness(1.15);
  }
`;

const SourceSelect = styled.select`
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  color: #94a3b8;
  font-size: 0.75rem;
  outline: none;
  cursor: pointer;

  option {
    background: #0f172a;
    color: #f8fafc;
  }

  &:hover {
    border-color: rgba(255, 255, 255, 0.2);
    color: #f8fafc;
  }
`;

const PrioritySelect = styled.select`
  appearance: none;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.725rem;
  font-weight: 600;
  border: 1px solid transparent;
  outline: none;
  cursor: pointer;
  text-transform: uppercase;

  option {
    background: #0f172a;
    color: #f8fafc;
  }

  &.high {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border-color: rgba(239, 68, 68, 0.3);
  }
  &.medium {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border-color: rgba(245, 158, 11, 0.3);
  }
  &.low {
    background: rgba(148, 163, 184, 0.15);
    color: #94a3b8;
    border-color: rgba(148, 163, 184, 0.3);
  }
`;

const InlineInput = styled.input`
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid #6366f1;
  border-radius: 6px;
  padding: 0.25rem 0.4rem;
  color: #f8fafc;
  font-size: 0.8rem;
  width: 100%;
  outline: none;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: #64748b;
  gap: 0.75rem;

  h4 {
    margin: 0;
    font-size: 1.1rem;
    color: #94a3b8;
  }

  p {
    margin: 0;
    font-size: 0.85rem;
    max-width: 420px;
  }
`;

const HistoryModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 29, 0.75);
  backdrop-filter: blur(6px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
`;

const HistoryModalContainer = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);

  .hist-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.15rem 1.25rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);

    .hist-title {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      color: #818cf8;

      h4 {
        margin: 0;
        font-size: 1.05rem;
        color: #f8fafc;
      }
    }

    .close-hist-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 0.3rem;
      border-radius: 6px;
      &:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #f8fafc;
      }
    }
  }

  .hist-body {
    padding: 1.25rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;

    .app-summary-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 0.75rem 1rem;

      h5 {
        margin: 0;
        font-size: 0.95rem;
        color: #f8fafc;
      }

      p {
        margin: 0.2rem 0 0;
        font-size: 0.8rem;
        color: #94a3b8;
      }
    }

    .timeline-wrapper {
      position: relative;
      padding-left: 1.25rem;
      border-left: 2px solid rgba(99, 102, 241, 0.25);
      margin-left: 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;

      .no-history-text {
        color: #64748b;
        font-size: 0.85rem;
      }

      .timeline-item {
        position: relative;

        .timeline-dot {
          position: absolute;
          left: -1.65rem;
          top: 0.25rem;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #6366f1;
          box-shadow: 0 0 8px rgba(99, 102, 241, 0.6);
        }

        .timeline-content {
          .timeline-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;

            .status-transition {
              font-size: 0.85rem;
              font-weight: 600;

              .from-st {
                color: #94a3b8;
              }
              .arrow {
                margin: 0 0.35rem;
                color: #64748b;
              }
              .to-st {
                color: #38bdf8;
              }
            }

            .timestamp {
              font-size: 0.725rem;
              color: #64748b;
            }
          }

          .history-notes {
            margin: 0.3rem 0 0;
            font-size: 0.8rem;
            color: #94a3b8;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
          }
        }
      }
    }
  }
`;
