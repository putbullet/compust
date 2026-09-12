import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Database,
  Search,
  Edit2,
  Trash2,
  Eye,
  EyeOff,
  Play,
  XCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Check,
  X,
} from 'lucide-react';
import {
  api,
  type Job,
  type ScrapingRunItem,
  type ScraperDiagnosticResponse,
  type JobSupervisionUpdate,
} from '../api/client';

export const MyDataSupervisionView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'jobs' | 'runs' | 'test'>('jobs');

  // Jobs state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Editing job state
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [editFormData, setEditFormData] = useState<JobSupervisionUpdate>({});
  const [savingEdit, setSavingEdit] = useState(false);

  // Deleting job state
  const [deletingJobId, setDeletingJobId] = useState<number | null>(null);
  const [forceDelete, setForceDelete] = useState(false);

  // Scraping runs state
  const [runs, setRuns] = useState<ScrapingRunItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  // Scraper Test Diagnostic state
  const [testUrl, setTestUrl] = useState('https://www.deloitte.com/fr/fr/careers/content/job/results.html');
  const [testStrategy, setTestStrategy] = useState<'auto' | 'universal' | 'deloitte' | 'greenhouse' | 'lever'>('auto');
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<ScraperDiagnosticResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Load jobs
  const fetchJobs = async () => {
    try {
      setLoadingJobs(true);
      const res = await api.getJobs({
        page,
        page_size: 15,
        search: searchQuery || undefined,
        active_only: false, // show all so user can supervise inactive too
      });
      setJobs(res.items);
      setTotalJobs(res.total);
    } catch (err) {
      console.error('Failed to load jobs for supervision:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  // Load runs
  const fetchRuns = async () => {
    try {
      setLoadingRuns(true);
      const res = await api.getAllScrapingRuns(40);
      setRuns(res);
    } catch (err) {
      console.error('Failed to load scraping runs:', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  useEffect(() => {
    if (activeSubTab === 'jobs') {
      fetchJobs();
    } else if (activeSubTab === 'runs') {
      fetchRuns();
    }
  }, [activeSubTab, page]);

  const handleToggleJobActive = async (job: Job) => {
    try {
      const updated = await api.superviseUpdateJob(job.id, { active: !job.active });
      setJobs((prev) => prev.map((j) => (j.id === job.id ? updated : j)));
    } catch (err) {
      console.error('Failed to toggle job active:', err);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingJob) return;
    try {
      setSavingEdit(true);
      const updated = await api.superviseUpdateJob(editingJob.id, editFormData);
      setJobs((prev) => prev.map((j) => (j.id === editingJob.id ? updated : j)));
      setEditingJob(null);
    } catch (err) {
      console.error('Failed to update job:', err);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!deletingJobId) return;
    try {
      await api.superviseDeleteJob(deletingJobId, forceDelete);
      setJobs((prev) => prev.filter((j) => j.id !== deletingJobId));
      setDeletingJobId(null);
      setForceDelete(false);
    } catch (err) {
      console.error('Failed to delete job:', err);
    }
  };

  const handleRunDiagnostic = async () => {
    if (!testUrl.trim()) return;
    try {
      setRunningTest(true);
      setTestError(null);
      setTestResult(null);
      const strat = testStrategy === 'auto' ? undefined : testStrategy;
      const res = await api.testScraperDiagnostic({
        url: testUrl.trim(),
        strategy: strat,
        max_pages: 1,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestError(err.message || 'Diagnostic execution failed');
    } finally {
      setRunningTest(false);
    }
  };

  return (
    <Container>
      {/* Header */}
      <Header>
        <div className="title-row">
          <Database className="header-icon" size={28} />
          <div>
            <h1>Data Supervision & Local Control</h1>
            <p>Supervise extracted opportunities, correct scraper mistakes, and test scrapers safely</p>
          </div>
        </div>

        {/* Sub Navigation */}
        <SubNav>
          <button
            className={`subnav-btn ${activeSubTab === 'jobs' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('jobs')}
          >
            Collected Jobs ({totalJobs})
          </button>
          <button
            className={`subnav-btn ${activeSubTab === 'runs' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('runs')}
          >
            Scraping Runs History
          </button>
          <button
            className={`subnav-btn ${activeSubTab === 'test' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('test')}
          >
            Parser Testing & Diagnostics
          </button>
        </SubNav>
      </Header>

      {/* Tab 1: Collected Jobs Supervision */}
      {activeSubTab === 'jobs' && (
        <SectionContent>
          <FilterBar>
            <div className="search-input-wrap">
              <Search size={16} />
              <input
                type="text"
                placeholder="Filter by title, location, or department..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchJobs()}
              />
            </div>
            <button className="refresh-btn" onClick={fetchJobs} title="Refresh">
              <RefreshCw size={16} className={loadingJobs ? 'spin' : ''} />
            </button>
          </FilterBar>

          {loadingJobs ? (
            <LoadingBox>
              <Loader2 size={28} className="spin" />
              <span>Loading opportunities...</span>
            </LoadingBox>
          ) : (
            <TableWrap>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Title & Location</th>
                    <th>Source</th>
                    <th>Type / Mode</th>
                    <th>Status</th>
                    <th>Discovered</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.id} className={!job.active ? 'inactive-row' : ''}>
                      <td>
                        <div className="job-title-col">
                          <span className="title-text">{job.title}</span>
                          <span className="loc-text">{job.location || 'Location Unspecified'}</span>
                        </div>
                      </td>
                      <td>
                        <span className="source-badge">{job.source || 'Direct'}</span>
                      </td>
                      <td>
                        <div className="types-col">
                          <span>{job.employment_type || '—'}</span>
                          <span className="remote-text">{job.remote_type || '—'}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`status-pill ${job.active ? 'active' : 'inactive'}`}>
                          {job.active ? 'Active' : 'Hidden'}
                        </span>
                      </td>
                      <td>
                        <span className="date-text">{new Date(job.discovered_at).toLocaleDateString()}</span>
                      </td>
                      <td>
                        <div className="actions-cell">
                          <button
                            className="icon-btn edit"
                            onClick={() => {
                              setEditingJob(job);
                              setEditFormData({
                                title: job.title,
                                description: job.description || '',
                                location: job.location || '',
                                department: job.department || '',
                                employment_type: job.employment_type || '',
                                remote_type: job.remote_type || '',
                                job_url: job.job_url,
                                active: job.active,
                              });
                            }}
                            title="Edit Job Details"
                          >
                            <Edit2 size={14} />
                          </button>

                          <button
                            className={`icon-btn toggle ${job.active ? 'hide' : 'show'}`}
                            onClick={() => handleToggleJobActive(job)}
                            title={job.active ? 'Hide Job' : 'Unhide Job'}
                          >
                            {job.active ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>

                          <button
                            className="icon-btn delete"
                            onClick={() => setDeletingJobId(job.id)}
                            title="Delete Job"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <PaginationBar>
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="page-btn"
                >
                  Previous
                </button>
                <span className="page-indicator">Page {page}</span>
                <button
                  disabled={jobs.length < 15}
                  onClick={() => setPage((p) => p + 1)}
                  className="page-btn"
                >
                  Next
                </button>
              </PaginationBar>
            </TableWrap>
          )}
        </SectionContent>
      )}

      {/* Tab 2: Scraping Runs History */}
      {activeSubTab === 'runs' && (
        <SectionContent>
          <div className="section-intro">
            <h3>Recent Crawler & Scraper Execution Logs</h3>
            <p>Inspect crawl durations, discovered vacancies, parser errors, and diagnostic outcomes</p>
          </div>

          {loadingRuns ? (
            <LoadingBox>
              <Loader2 size={28} className="spin" />
              <span>Fetching scraping runs...</span>
            </LoadingBox>
          ) : (
            <TableWrap>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Started</th>
                    <th>Status</th>
                    <th>Jobs Found</th>
                    <th>Added / Updated</th>
                    <th>Outcome & Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td>#{r.id}</td>
                      <td>
                        <span className="date-text">{new Date(r.started_at).toLocaleString()}</span>
                      </td>
                      <td>
                        <span className={`status-pill run-${r.status}`}>
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td>{r.jobs_found}</td>
                      <td>
                        <span className="add-badge">+{r.jobs_added}</span> / 
                        <span className="up-badge">~{r.jobs_updated}</span>
                      </td>
                      <td>
                        {r.error_message ? (
                          <div className="error-log-preview" title={r.error_message}>
                            <AlertTriangle size={13} className="err-icon" />
                            <span>{r.error_message.slice(0, 90)}...</span>
                          </div>
                        ) : (
                          <span className="clean-log">Clean execution</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </SectionContent>
      )}

      {/* Tab 3: Parser Testing & Diagnostics */}
      {activeSubTab === 'test' && (
        <SectionContent>
          <TestPanel>
            <div className="test-header">
              <h3>Live Scraper Diagnostic Engine (Dry-Run)</h3>
              <p>Test any career or ATS portal with universal or platform strategies without writing records to MySQL.</p>
            </div>

            <div className="test-controls">
              <div className="control-group input-group">
                <label>Target Career URL</label>
                <input
                  type="text"
                  placeholder="https://..."
                  value={testUrl}
                  onChange={(e) => setTestUrl(e.target.value)}
                />
              </div>

              <div className="control-group select-group">
                <label>Strategy Mode</label>
                <select
                  value={testStrategy}
                  onChange={(e) => setTestStrategy(e.target.value as any)}
                >
                  <option value="auto">Automatic (Tiered Platform/Universal)</option>
                  <option value="universal">Universal Parser (JSON-LD + Semantic Cards)</option>
                  <option value="deloitte">Deloitte Custom Parser</option>
                  <option value="greenhouse">Greenhouse Adapter</option>
                  <option value="lever">Lever Adapter</option>
                </select>
              </div>

              <button
                className="run-test-btn"
                onClick={handleRunDiagnostic}
                disabled={runningTest || !testUrl.trim()}
              >
                {runningTest ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
                <span>{runningTest ? 'Diagnosing...' : 'Test Scraper'}</span>
              </button>
            </div>

            {testError && (
              <div className="diagnostic-error">
                <XCircle size={16} />
                <span>{testError}</span>
              </div>
            )}

            {testResult && (
              <DiagnosticReportCard>
                <div className="report-top">
                  <div className="report-status-badge">
                    <span className={`status-tag status-${testResult.status.toLowerCase()}`}>
                      {testResult.status}
                    </span>
                    <span className="time-tag">{testResult.execution_time_seconds}s execution</span>
                  </div>

                  <div className="metrics-cluster">
                    <div className="metric">
                      <span className="metric-label">Platform Detected</span>
                      <span className="metric-val">{testResult.platform_detected || 'Unknown'}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Strategy Used</span>
                      <span className="metric-val highlight">{testResult.strategy_used}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Discovered</span>
                      <span className="metric-val">{testResult.jobs_discovered}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Accepted</span>
                      <span className="metric-val success">{testResult.jobs_accepted}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Confidence</span>
                      <span className="metric-val">{Math.round(testResult.confidence_score * 100)}%</span>
                    </div>
                  </div>
                </div>

                {testResult.errors.length > 0 && (
                  <div className="report-errors">
                    <h4>Reported Diagnostics:</h4>
                    <ul>
                      {testResult.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {testResult.sample_jobs.length > 0 && (
                  <div className="sample-jobs-list">
                    <h4>Sample Candidates Extracted:</h4>
                    <div className="sample-grid">
                      {testResult.sample_jobs.map((s, idx) => (
                        <div key={idx} className="sample-card">
                          <span className="sample-title">{s.title}</span>
                          <span className="sample-loc">{s.location || 'Location Not Stated'}</span>
                          <a href={s.job_url} target="_blank" rel="noreferrer" className="sample-link">
                            <span>Link</span>
                            <ExternalLink size={12} />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </DiagnosticReportCard>
            )}
          </TestPanel>
        </SectionContent>
      )}

      {/* Edit Job Modal */}
      {editingJob && (
        <ModalOverlay onClick={() => setEditingJob(null)}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit Job Posting #{editingJob.id}</h3>
              <button onClick={() => setEditingJob(null)} className="close-btn"><X size={18} /></button>
            </div>

            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={editFormData.title || ''}
                onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  value={editFormData.location || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, location: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Department</label>
                <input
                  type="text"
                  value={editFormData.department || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, department: e.target.value })}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Employment Type</label>
                <input
                  type="text"
                  value={editFormData.employment_type || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, employment_type: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Remote / Work Mode</label>
                <input
                  type="text"
                  value={editFormData.remote_type || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, remote_type: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Description (Sanitized HTML)</label>
              <textarea
                rows={5}
                value={editFormData.description || ''}
                onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
              />
            </div>

            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setEditingJob(null)}>Cancel</button>
              <button className="save-btn" onClick={handleSaveEdit} disabled={savingEdit}>
                {savingEdit ? <Loader2 size={15} className="spin" /> : <Check size={15} />}
                <span>Save Corrections</span>
              </button>
            </div>
          </ModalContent>
        </ModalOverlay>
      )}

      {/* Delete Job Confirmation Modal */}
      {deletingJobId && (
        <ModalOverlay onClick={() => setDeletingJobId(null)}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <ShieldAlert className="warning-icon" size={24} />
              <h3>Confirm Opportunity Removal</h3>
            </div>

            <p className="confirm-p">
              Are you sure you want to remove Job #{deletingJobId}? By default, if user applications exist, it will be soft-deactivated to preserve your history.
            </p>

            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={forceDelete}
                onChange={(e) => setForceDelete(e.target.checked)}
              />
              <span>Force hard deletion (also removes related applications)</span>
            </label>

            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setDeletingJobId(null)}>Cancel</button>
              <button className="danger-btn" onClick={handleDeleteJob}>
                <span>Confirm Delete</span>
              </button>
            </div>
          </ModalContent>
        </ModalOverlay>
      )}
    </Container>
  );
};

const Container = styled.div`
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px;
`;

const Header = styled.div`
  margin-bottom: 28px;

  .title-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;

    .header-icon {
      color: #3b82f6;
    }

    h1 {
      font-size: 1.6rem;
      font-weight: 800;
      color: #f8fafc;
      margin: 0 0 4px;
    }

    p {
      color: #94a3b8;
      font-size: 0.9rem;
      margin: 0;
    }
  }
`;

const SubNav = styled.div`
  display: flex;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 8px;

  .subnav-btn {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #94a3b8;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.05);
    }

    &.active {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.12);
    }
  }
`;

const SectionContent = styled.div`
  margin-top: 20px;

  .section-intro {
    margin-bottom: 16px;
    h3 { font-size: 1.1rem; color: #f8fafc; margin: 0 0 4px; }
    p { color: #94a3b8; font-size: 0.85rem; margin: 0; }
  }
`;

const FilterBar = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  .search-input-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 8px 14px;
    flex: 1;

    svg { color: #64748b; }

    input {
      background: transparent;
      border: none;
      color: #ffffff;
      font-size: 0.85rem;
      width: 100%;
      outline: none;
    }
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 14px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    cursor: pointer;
    &:hover { color: #ffffff; background: rgba(255, 255, 255, 0.1); }
  }
`;

const TableWrap = styled.div`
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  overflow: hidden;

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;

    th {
      text-align: left;
      padding: 12px 16px;
      color: #94a3b8;
      font-weight: 600;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(10, 15, 26, 0.5);
    }

    td {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: #cbd5e1;
      vertical-align: middle;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    tr.inactive-row td {
      opacity: 0.55;
    }
  }

  .job-title-col {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .title-text {
      font-weight: 600;
      color: #f8fafc;
    }
    .loc-text {
      font-size: 0.75rem;
      color: #64748b;
    }
  }

  .source-badge {
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(59, 130, 246, 0.12);
    color: #93c5fd;
    font-size: 0.75rem;
  }

  .types-col {
    display: flex;
    flex-direction: column;
    font-size: 0.75rem;
    .remote-text { color: #94a3b8; }
  }

  .status-pill {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;

    &.active { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    &.inactive { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    &.run-success { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    &.run-failed { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    &.run-partial { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
  }

  .date-text {
    font-size: 0.75rem;
    color: #64748b;
  }

  .add-badge { color: #34d399; font-weight: 600; }
  .up-badge { color: #38bdf8; }

  .actions-cell {
    display: flex;
    gap: 6px;

    .icon-btn {
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      color: #94a3b8;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.1);
      }

      &.delete:hover {
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.3);
      }
    }
  }

  .error-log-preview {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #fbbf24;
    font-size: 0.75rem;
  }

  .clean-log {
    color: #64748b;
    font-size: 0.75rem;
  }
`;

const PaginationBar = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);

  .page-btn {
    padding: 6px 14px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
    font-size: 0.8rem;
    cursor: pointer;
    &:disabled { opacity: 0.4; cursor: default; }
  }

  .page-indicator {
    font-size: 0.8rem;
    color: #94a3b8;
  }
`;

const LoadingBox = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: #94a3b8;
`;

const TestPanel = styled.div`
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 24px;

  .test-header {
    margin-bottom: 20px;
    h3 { font-size: 1.15rem; color: #f8fafc; margin: 0 0 4px; }
    p { color: #94a3b8; font-size: 0.85rem; margin: 0; }
  }

  .test-controls {
    display: flex;
    gap: 14px;
    align-items: flex-end;
    margin-bottom: 20px;

    .control-group {
      display: flex;
      flex-direction: column;
      gap: 6px;

      label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #cbd5e1;
      }

      input, select {
        padding: 9px 12px;
        background: rgba(10, 15, 26, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #ffffff;
        font-size: 0.85rem;
      }
    }

    .input-group { flex: 1; }
    .select-group { min-width: 240px; }

    .run-test-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 18px;
      border-radius: 8px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      &:hover:not(:disabled) { background: #1d4ed8; }
      &:disabled { opacity: 0.6; }
    }
  }

  .diagnostic-error {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 8px;
    color: #fca5a5;
    font-size: 0.85rem;
  }
`;

const DiagnosticReportCard = styled.div`
  margin-top: 20px;
  padding: 18px;
  background: rgba(10, 15, 26, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;

  .report-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 14px;
    margin-bottom: 14px;
  }

  .report-status-badge {
    display: flex;
    align-items: center;
    gap: 10px;

    .status-tag {
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 700;
      &.status-success { background: rgba(16, 185, 129, 0.18); color: #34d399; }
      &.status-partial_success { background: rgba(245, 158, 11, 0.18); color: #fbbf24; }
      &.status-no_jobs_found { background: rgba(239, 68, 68, 0.18); color: #f87171; }
      &.status-scrape_failed { background: rgba(239, 68, 68, 0.18); color: #f87171; }
    }

    .time-tag { font-size: 0.78rem; color: #64748b; }
  }

  .metrics-cluster {
    display: flex;
    gap: 18px;

    .metric {
      display: flex;
      flex-direction: column;
      align-items: flex-end;

      .metric-label { font-size: 0.7rem; color: #64748b; }
      .metric-val {
        font-size: 0.85rem;
        font-weight: 600;
        color: #f8fafc;
        &.highlight { color: #60a5fa; }
        &.success { color: #34d399; }
      }
    }
  }

  .report-errors {
    margin-top: 12px;
    h4 { font-size: 0.82rem; color: #fbbf24; margin: 0 0 6px; }
    ul { margin: 0; padding-left: 18px; font-size: 0.78rem; color: #cbd5e1; }
  }

  .sample-jobs-list {
    margin-top: 14px;
    h4 { font-size: 0.82rem; color: #94a3b8; margin: 0 0 10px; }

    .sample-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 10px;
    }

    .sample-card {
      padding: 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;

      .sample-title { font-weight: 600; color: #ffffff; font-size: 0.82rem; }
      .sample-loc { font-size: 0.72rem; color: #94a3b8; }
      .sample-link {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        font-size: 0.72rem;
        color: #60a5fa;
        text-decoration: none;
        margin-top: 4px;
      }
    }
  }
`;

const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
`;

const ModalContent = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  width: 100%;
  max-width: 560px;
  padding: 24px;
  color: #f8fafc;

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h3 { font-size: 1.15rem; margin: 0; }
    .close-btn { background: none; border: none; color: #94a3b8; cursor: pointer; }
    .warning-icon { color: #f59e0b; margin-right: 8px; }
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;

    label { font-size: 0.8rem; font-weight: 600; color: #cbd5e1; }
    input, textarea {
      padding: 9px 12px;
      background: rgba(10, 15, 26, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      color: #ffffff;
      font-size: 0.85rem;
    }
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .confirm-p {
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.5;
    margin-bottom: 16px;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: #f87171;
    margin-bottom: 20px;
    cursor: pointer;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;

    .cancel-btn {
      padding: 8px 16px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      cursor: pointer;
    }

    .save-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      font-weight: 600;
      cursor: pointer;
    }

    .danger-btn {
      padding: 8px 16px;
      border-radius: 8px;
      background: #ef4444;
      color: #ffffff;
      border: none;
      font-weight: 600;
      cursor: pointer;
    }
  }
`;
