import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Building2,
  Plus,
  Edit2,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Globe,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  Power,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import type { Company, Country, ScrapeTarget, CompanyCreate } from '../api/client';
import { Loader } from './Loader';

interface CompanyManagementViewProps {
  countries: Country[];
  onRefreshCountries?: () => void;
}

export const CompanyManagementView: React.FC<CompanyManagementViewProps> = ({ countries }) => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all');
  const [expandedCompanyId, setExpandedCompanyId] = useState<number | null>(null);

  // Targets state per company
  const [targetsMap, setTargetsMap] = useState<Record<number, ScrapeTarget[]>>({});
  const [loadingTargets, setLoadingTargets] = useState<Record<number, boolean>>({});
  const [runningTargetId, setRunningTargetId] = useState<number | null>(null);
  const [syncOutcome, setSyncOutcome] = useState<{ targetId: number; success: boolean; message: string } | null>(null);

  // Company Modal State
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [companyForm, setCompanyForm] = useState<CompanyCreate>({
    name: '',
    website_url: '',
    careers_url: '',
    active: true,
    country_ids: [],
  });
  const [companySubmitting, setCompanySubmitting] = useState(false);

  // Target Modal State
  const [isTargetModalOpen, setIsTargetModalOpen] = useState(false);
  const [targetCompanyId, setTargetCompanyId] = useState<number | null>(null);
  const [editingTarget, setEditingTarget] = useState<ScrapeTarget | null>(null);
  const [targetForm, setTargetForm] = useState<{ url: string; type: string; active: boolean }>({
    url: '',
    type: 'generic_html',
    active: true,
  });
  const [targetSubmitting, setTargetSubmitting] = useState(false);

  // Hard Delete Confirmation Modal
  const [hardDeleteTarget, setHardDeleteTarget] = useState<{ id: number; name: string } | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Fetch Companies
  const loadCompanies = async () => {
    try {
      setLoading(true);
      const list = await api.getCompanies();
      setCompanies(list);
    } catch (err) {
      console.error('Failed to load companies:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  // Fetch targets for a company
  const loadTargetsForCompany = async (companyId: number) => {
    try {
      setLoadingTargets((prev) => ({ ...prev, [companyId]: true }));
      const targets = await api.getScrapeTargets(companyId);
      setTargetsMap((prev) => ({ ...prev, [companyId]: targets }));
    } catch (err) {
      console.error(`Failed to load targets for company ${companyId}:`, err);
    } finally {
      setLoadingTargets((prev) => ({ ...prev, [companyId]: false }));
    }
  };

  const handleToggleExpand = (companyId: number) => {
    if (expandedCompanyId === companyId) {
      setExpandedCompanyId(null);
    } else {
      setExpandedCompanyId(companyId);
      if (!targetsMap[companyId]) {
        loadTargetsForCompany(companyId);
      }
    }
  };

  // Run Scraper Now
  const handleRunScraperNow = async (target: ScrapeTarget) => {
    try {
      setRunningTargetId(target.id);
      setSyncOutcome(null);
      const result = await api.syncScrapeTarget(target.id);
      setSyncOutcome({
        targetId: target.id,
        success: true,
        message: `Synced ${result.jobs_found} jobs found (+${result.jobs_added} added, ~${result.jobs_updated} updated).`,
      });
      // Refresh targets
      loadTargetsForCompany(target.company_id);
    } catch (err: any) {
      setSyncOutcome({
        targetId: target.id,
        success: false,
        message: err.message || 'Scrape sync failed.',
      });
    } finally {
      setRunningTargetId(null);
    }
  };

  // Company Actions
  const handleOpenAddCompany = () => {
    setEditingCompany(null);
    setCompanyForm({
      name: '',
      website_url: '',
      careers_url: '',
      active: true,
      country_ids: countries.length > 0 ? [countries[0].id] : [],
    });
    setIsCompanyModalOpen(true);
  };

  const handleOpenEditCompany = (comp: Company) => {
    setEditingCompany(comp);
    setCompanyForm({
      name: comp.name,
      website_url: comp.website_url,
      careers_url: comp.careers_url || '',
      active: comp.active,
      country_ids: comp.countries.map((c) => c.id),
    });
    setIsCompanyModalOpen(true);
  };

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyForm.name.trim()) return;
    try {
      setCompanySubmitting(true);
      if (editingCompany) {
        await api.updateCompany(editingCompany.id, companyForm);
      } else {
        await api.createCompany(companyForm);
      }
      setIsCompanyModalOpen(false);
      loadCompanies();
    } catch (err) {
      console.error('Failed to save company:', err);
    } finally {
      setCompanySubmitting(false);
    }
  };

  const handleToggleCompanyActive = async (companyId: number) => {
    try {
      await api.toggleCompany(companyId);
      loadCompanies();
    } catch (err) {
      console.error('Failed to toggle company active status:', err);
    }
  };

  const handleConfirmHardDelete = async () => {
    if (!hardDeleteTarget) return;
    try {
      setDeleteSubmitting(true);
      await api.deleteCompany(hardDeleteTarget.id, true);
      setHardDeleteTarget(null);
      loadCompanies();
    } catch (err) {
      console.error('Failed to delete company:', err);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // Scrape Target Actions
  const handleOpenAddTarget = (companyId: number) => {
    setTargetCompanyId(companyId);
    setEditingTarget(null);
    setTargetForm({ url: '', type: 'generic_html', active: true });
    setIsTargetModalOpen(true);
  };

  const handleOpenEditTarget = (target: ScrapeTarget) => {
    setTargetCompanyId(target.company_id);
    setEditingTarget(target);
    setTargetForm({ url: target.url, type: target.type || 'generic_html', active: target.active });
    setIsTargetModalOpen(true);
  };

  const handleSaveTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetCompanyId || !targetForm.url.trim()) return;
    try {
      setTargetSubmitting(true);
      if (editingTarget) {
        await api.updateScrapeTarget(editingTarget.id, targetForm);
      } else {
        await api.createScrapeTarget({
          company_id: targetCompanyId,
          url: targetForm.url,
          type: targetForm.type,
          active: targetForm.active,
        });
      }
      setIsTargetModalOpen(false);
      loadTargetsForCompany(targetCompanyId);
      loadCompanies();
    } catch (err) {
      console.error('Failed to save target:', err);
    } finally {
      setTargetSubmitting(false);
    }
  };

  const handleToggleTargetActive = async (target: ScrapeTarget) => {
    try {
      await api.toggleScrapeTarget(target.id);
      loadTargetsForCompany(target.company_id);
    } catch (err) {
      console.error('Failed to toggle target:', err);
    }
  };

  const handleDeleteTarget = async (target: ScrapeTarget) => {
    if (!window.confirm('Delete this scrape target?')) return;
    try {
      await api.deleteScrapeTarget(target.id);
      loadTargetsForCompany(target.company_id);
    } catch (err) {
      console.error('Failed to delete target:', err);
    }
  };

  // Filtered companies
  const filteredCompanies = companies.filter((c) => {
    const matchSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.website_url.toLowerCase().includes(search.toLowerCase());
    const matchActive =
      filterActive === 'all' ? true : filterActive === 'active' ? c.active : !c.active;
    return matchSearch && matchActive;
  });

  return (
    <Container>
      {/* Header & Controls */}
      <HeaderSection>
        <div>
          <h2>Manage Companies & Sources</h2>
          <p className="subtitle">
            Configure local employers, associate operating countries, and monitor scrape targets.
          </p>
        </div>
        <div className="header-actions">
          <button className="primary-btn" onClick={handleOpenAddCompany}>
            <Plus size={16} />
            <span>Add Company</span>
          </button>
        </div>
      </HeaderSection>

      {/* Search and Filters Bar */}
      <FilterBar>
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search companies by name or website..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <button
            className={`pill-btn ${filterActive === 'all' ? 'active' : ''}`}
            onClick={() => setFilterActive('all')}
          >
            All ({companies.length})
          </button>
          <button
            className={`pill-btn ${filterActive === 'active' ? 'active' : ''}`}
            onClick={() => setFilterActive('active')}
          >
            Active ({companies.filter((c) => c.active).length})
          </button>
          <button
            className={`pill-btn ${filterActive === 'inactive' ? 'active' : ''}`}
            onClick={() => setFilterActive('inactive')}
          >
            Inactive ({companies.filter((c) => !c.active).length})
          </button>
          <button className="refresh-btn" onClick={loadCompanies} title="Refresh companies list">
            <RefreshCw size={15} />
          </button>
        </div>
      </FilterBar>

      {/* Companies List */}
      {loading ? (
        <Loader />
      ) : filteredCompanies.length === 0 ? (
        <EmptyState>
          <Building2 size={40} className="empty-icon" />
          <h3>No companies found</h3>
          <p>Try adjusting your search query or add a new company.</p>
        </EmptyState>
      ) : (
        <CompaniesList>
          {filteredCompanies.map((company) => {
            const isExpanded = expandedCompanyId === company.id;
            const targets = targetsMap[company.id] || [];
            const isLoadingTargets = loadingTargets[company.id];

            return (
              <CompanyCard key={company.id} $active={company.active}>
                <div className="company-summary">
                  <div className="company-info" onClick={() => handleToggleExpand(company.id)}>
                    <div className="title-row">
                      <span className="company-name">{company.name}</span>
                      <span className={`status-badge ${company.active ? 'active' : 'inactive'}`}>
                        {company.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    <div className="meta-row">
                      <a
                        href={company.website_url}
                        target="_blank"
                        rel="noreferrer"
                        className="meta-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Globe size={13} />
                        <span>Website</span>
                        <ExternalLink size={11} />
                      </a>
                      {company.careers_url && (
                        <a
                          href={company.careers_url}
                          target="_blank"
                          rel="noreferrer"
                          className="meta-link"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span>Careers Portal</span>
                          <ExternalLink size={11} />
                        </a>
                      )}
                      <div className="country-badges">
                        {company.countries.length > 0 ? (
                          company.countries.map((c) => (
                            <span key={c.id} className="country-pill">
                              {c.code} · {c.name}
                            </span>
                          ))
                        ) : (
                          <span className="no-country">No countries linked</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="actions-cluster">
                    {/* Reversible Deactivation */}
                    <button
                      className={`action-icon-btn toggle-btn ${company.active ? 'active' : 'inactive'}`}
                      onClick={() => handleToggleCompanyActive(company.id)}
                      title={company.active ? 'Deactivate company (Reversible)' : 'Reactivate company'}
                    >
                      <Power size={16} />
                    </button>

                    {/* Edit Company */}
                    <button
                      className="action-icon-btn edit-btn"
                      onClick={() => handleOpenEditCompany(company)}
                      title="Edit company"
                    >
                      <Edit2 size={16} />
                    </button>

                    {/* Hard Delete */}
                    <button
                      className="action-icon-btn delete-btn"
                      onClick={() => setHardDeleteTarget({ id: company.id, name: company.name })}
                      title="Permanently delete company"
                    >
                      <Trash2 size={16} />
                    </button>

                    {/* Expand Targets */}
                    <button
                      className="action-icon-btn expand-btn"
                      onClick={() => handleToggleExpand(company.id)}
                      title={isExpanded ? 'Hide scrape targets' : 'View scrape targets'}
                    >
                      {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                  </div>
                </div>

                {/* Scrape Targets Section (Accordion) */}
                {isExpanded && (
                  <TargetsSection>
                    <div className="targets-header">
                      <h4>Scrape Targets ({targets.length})</h4>
                      <button
                        className="small-add-btn"
                        onClick={() => handleOpenAddTarget(company.id)}
                      >
                        <Plus size={13} />
                        <span>Add Target</span>
                      </button>
                    </div>

                    {isLoadingTargets ? (
                      <div className="targets-loading">
                        <RefreshCw size={18} className="spin" />
                        <span>Loading targets...</span>
                      </div>
                    ) : targets.length === 0 ? (
                      <div className="targets-empty">
                        <AlertTriangle size={18} />
                        <span>No scraping targets configured for {company.name}.</span>
                        <button
                          className="link-btn"
                          onClick={() => handleOpenAddTarget(company.id)}
                        >
                          Add first scrape target
                        </button>
                      </div>
                    ) : (
                      <div className="targets-table-wrapper">
                        <table className="targets-table">
                          <thead>
                            <tr>
                              <th>Status</th>
                              <th>Target URL</th>
                              <th>Type</th>
                              <th>Last Scrape</th>
                              <th>Outcome</th>
                              <th style={{ textAlign: 'right' }}>Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {targets.map((target) => {
                              const isRunning = runningTargetId === target.id;
                              const outcome =
                                syncOutcome && syncOutcome.targetId === target.id
                                  ? syncOutcome
                                  : null;

                              return (
                                <tr key={target.id}>
                                  <td>
                                    <span
                                      className={`target-status-dot ${target.active ? 'active' : 'inactive'}`}
                                      title={target.active ? 'Active' : 'Inactive'}
                                    />
                                  </td>
                                  <td className="url-cell" title={target.url}>
                                    <span className="truncate-url">{target.url}</span>
                                  </td>
                                  <td>
                                    <span className="type-badge">{target.type || 'standard'}</span>
                                  </td>
                                  <td className="date-cell">
                                    {target.last_scraped_at
                                      ? new Date(target.last_scraped_at).toLocaleDateString() +
                                        ' ' +
                                        new Date(target.last_scraped_at).toLocaleTimeString([], {
                                          hour: '2-digit',
                                          minute: '2-digit',
                                        })
                                      : 'Never'}
                                  </td>
                                  <td>
                                    <span
                                      className={`outcome-pill ${
                                        target.status === 'success'
                                          ? 'success'
                                          : target.status === 'failed'
                                          ? 'failed'
                                          : target.status === 'restricted'
                                          ? 'warning'
                                          : 'neutral'
                                      }`}
                                    >
                                      {target.status || 'pending'}
                                    </span>
                                  </td>
                                  <td style={{ textAlign: 'right' }}>
                                    <div className="target-actions">
                                      {/* Run Scraper Now */}
                                      <button
                                        className="run-btn"
                                        onClick={() => handleRunScraperNow(target)}
                                        disabled={isRunning}
                                        title="Run scraper now"
                                      >
                                        <Play size={12} className={isRunning ? 'spin' : ''} />
                                        <span>{isRunning ? 'Running...' : 'Run now'}</span>
                                      </button>

                                      {/* Toggle Target */}
                                      <button
                                        className="small-icon-btn"
                                        onClick={() => handleToggleTargetActive(target)}
                                        title={target.active ? 'Deactivate target' : 'Activate target'}
                                      >
                                        <Power size={13} />
                                      </button>

                                      {/* Edit Target */}
                                      <button
                                        className="small-icon-btn"
                                        onClick={() => handleOpenEditTarget(target)}
                                        title="Edit target"
                                      >
                                        <Edit2 size={13} />
                                      </button>

                                      {/* Delete Target */}
                                      <button
                                        className="small-icon-btn delete"
                                        onClick={() => handleDeleteTarget(target)}
                                        title="Delete target"
                                      >
                                        <Trash2 size={13} />
                                      </button>
                                    </div>
                                    {outcome && (
                                      <div
                                        className={`sync-feedback ${
                                          outcome.success ? 'success' : 'error'
                                        }`}
                                      >
                                        {outcome.success ? (
                                          <CheckCircle2 size={12} />
                                        ) : (
                                          <XCircle size={12} />
                                        )}
                                        <span>{outcome.message}</span>
                                      </div>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </TargetsSection>
                )}
              </CompanyCard>
            );
          })}
        </CompaniesList>
      )}

      {/* Add / Edit Company Modal */}
      {isCompanyModalOpen && (
        <ModalOverlay onClick={() => setIsCompanyModalOpen(false)}>
          <ModalCard onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingCompany ? 'Edit Company' : 'Add New Company'}</h3>
              <button className="close-btn" onClick={() => setIsCompanyModalOpen(false)}>
                &times;
              </button>
            </div>
            <form onSubmit={handleSaveCompany}>
              <div className="form-group">
                <label>Company Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Corp"
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Official Website *</label>
                <input
                  type="url"
                  required
                  placeholder="https://example.com"
                  value={companyForm.website_url}
                  onChange={(e) => setCompanyForm({ ...companyForm, website_url: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Careers URL</label>
                <input
                  type="url"
                  placeholder="https://example.com/careers"
                  value={companyForm.careers_url || ''}
                  onChange={(e) => setCompanyForm({ ...companyForm, careers_url: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Operating Countries</label>
                <div className="country-selector">
                  {countries.map((c) => {
                    const selected = companyForm.country_ids?.includes(c.id);
                    return (
                      <label key={c.id} className={`country-check-pill ${selected ? 'checked' : ''}`}>
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={(e) => {
                            const current = companyForm.country_ids || [];
                            const updated = e.target.checked
                              ? [...current, c.id]
                              : current.filter((id) => id !== c.id);
                            setCompanyForm({ ...companyForm, country_ids: updated });
                          }}
                        />
                        <span>{c.name} ({c.code})</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={companyForm.active}
                    onChange={(e) => setCompanyForm({ ...companyForm, active: e.target.checked })}
                  />
                  <span>Company is active and enabled for research</span>
                </label>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={() => setIsCompanyModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="save-btn" disabled={companySubmitting}>
                  {companySubmitting ? 'Saving...' : editingCompany ? 'Update Company' : 'Create Company'}
                </button>
              </div>
            </form>
          </ModalCard>
        </ModalOverlay>
      )}

      {/* Add / Edit Scrape Target Modal */}
      {isTargetModalOpen && (
        <ModalOverlay onClick={() => setIsTargetModalOpen(false)}>
          <ModalCard onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingTarget ? 'Edit Scrape Target' : 'Add Scrape Target'}</h3>
              <button className="close-btn" onClick={() => setIsTargetModalOpen(false)}>
                &times;
              </button>
            </div>
            <form onSubmit={handleSaveTarget}>
              <div className="form-group">
                <label>Target URL *</label>
                <input
                  type="url"
                  required
                  placeholder="https://company.com/api/jobs or careers page URL"
                  value={targetForm.url}
                  onChange={(e) => setTargetForm({ ...targetForm, url: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Parser / Source Type</label>
                <select
                  value={targetForm.type}
                  onChange={(e) => setTargetForm({ ...targetForm, type: e.target.value })}
                >
                  <option value="generic_html">Standard HTML Career Portal</option>
                  <option value="capgemini_json">Capgemini JSON API</option>
                  <option value="orange_next">Orange Maroc Pagination</option>
                  <option value="inwi_stream">Inwi TurboStream</option>
                  <option value="workday">Workday ATS</option>
                  <option value="greenhouse">Greenhouse ATS</option>
                </select>
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={targetForm.active}
                    onChange={(e) => setTargetForm({ ...targetForm, active: e.target.checked })}
                  />
                  <span>Target is active and eligible for scraping</span>
                </label>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={() => setIsTargetModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="save-btn" disabled={targetSubmitting}>
                  {targetSubmitting ? 'Saving...' : editingTarget ? 'Update Target' : 'Add Target'}
                </button>
              </div>
            </form>
          </ModalCard>
        </ModalOverlay>
      )}

      {/* Hard Delete Confirmation Modal */}
      {hardDeleteTarget && (
        <ModalOverlay onClick={() => setHardDeleteTarget(null)}>
          <ModalCard onClick={(e) => e.stopPropagation()} className="danger-modal">
            <div className="modal-header danger">
              <ShieldAlert size={24} className="danger-icon" />
              <h3>Confirm Permanent Deletion</h3>
            </div>
            <div className="modal-body">
              <p>
                Are you sure you want to permanently delete <strong>{hardDeleteTarget.name}</strong>?
              </p>
              <div className="warning-box">
                <AlertTriangle size={16} />
                <span>
                  This will permanently delete the company record, all associated scrape targets,
                  scraping run history, and ingested jobs. This action CANNOT be undone.
                </span>
              </div>
              <p className="hint">
                Tip: If you simply want to pause scraping or hide this company, use the reversible
                <strong> Deactivate</strong> toggle instead.
              </p>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="cancel-btn"
                onClick={() => setHardDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-btn"
                onClick={handleConfirmHardDelete}
                disabled={deleteSubmitting}
              >
                {deleteSubmitting ? 'Deleting...' : 'Permanently Delete'}
              </button>
            </div>
          </ModalCard>
        </ModalOverlay>
      )}
    </Container>
  );
};

// Styled Components
const Container = styled.div`
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 20px 80px;
`;

const HeaderSection = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;

  h2 {
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0 0 6px;
    background: linear-gradient(135deg, #ffffff 40%, #94a3b8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .subtitle {
    font-size: 0.9rem;
    color: #94a3b8;
    margin: 0;
  }

  .primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.85rem;
    font-weight: 600;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);

    &:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
    }
  }
`;

const FilterBar = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;

  .search-box {
    position: relative;
    flex: 1;
    min-width: 240px;

    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: #64748b;
    }

    input {
      width: 100%;
      padding: 10px 14px 10px 38px;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      color: #f8fafc;
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s;

      &:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
      }
    }
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .pill-btn {
    padding: 8px 14px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #ffffff;
    }

    &.active {
      background: rgba(59, 130, 246, 0.15);
      border-color: rgba(59, 130, 246, 0.35);
      color: #3b82f6;
    }
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #ffffff;
    }
  }
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  text-align: center;

  .empty-icon {
    color: #64748b;
    margin-bottom: 12px;
  }

  h3 {
    font-size: 1.1rem;
    color: #f1f5f9;
    margin: 0 0 6px;
  }

  p {
    font-size: 0.85rem;
    color: #94a3b8;
    margin: 0;
  }
`;

const CompaniesList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const CompanyCard = styled.div<{ $active: boolean }>`
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid ${(props) => (props.$active ? 'rgba(255, 255, 255, 0.08)' : 'rgba(244, 63, 94, 0.2)')};
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.2s;
  opacity: ${(props) => (props.$active ? 1 : 0.75)};

  .company-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    gap: 16px;
  }

  .company-info {
    flex: 1;
    cursor: pointer;
    user-select: none;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }

  .company-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .status-badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    letter-spacing: 0.04em;

    &.active {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }

    &.inactive {
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.3);
      color: #f43f5e;
    }
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .meta-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #60a5fa;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .country-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .country-pill {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 500;
  }

  .no-country {
    color: #64748b;
    font-style: italic;
    font-size: 0.75rem;
  }

  .actions-cluster {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .action-icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #ffffff;
    }

    &.toggle-btn.active:hover {
      color: #f43f5e;
      border-color: rgba(244, 63, 94, 0.3);
    }

    &.toggle-btn.inactive:hover {
      color: #10b981;
      border-color: rgba(16, 185, 129, 0.3);
    }

    &.delete-btn:hover {
      color: #f43f5e;
      border-color: rgba(244, 63, 94, 0.3);
      background: rgba(244, 63, 94, 0.1);
    }
  }
`;

const TargetsSection = styled.div`
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(10, 15, 26, 0.6);
  padding: 16px 20px;

  .targets-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    h4 {
      font-size: 0.85rem;
      font-weight: 600;
      color: #cbd5e1;
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  }

  .small-add-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #60a5fa;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(59, 130, 246, 0.25);
    }
  }

  .targets-loading,
  .targets-empty {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px;
    color: #94a3b8;
    font-size: 0.85rem;
    justify-content: center;

    .spin {
      animation: spin 1.5s linear infinite;
    }

    .link-btn {
      background: none;
      border: none;
      color: #3b82f6;
      cursor: pointer;
      text-decoration: underline;
      font-size: 0.85rem;
      margin-left: 4px;
    }
  }

  .targets-table-wrapper {
    overflow-x: auto;
  }

  .targets-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;

    th {
      text-align: left;
      padding: 8px 10px;
      color: #64748b;
      font-weight: 600;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    td {
      padding: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      vertical-align: middle;
      color: #cbd5e1;
    }

    .target-status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;

      &.active {
        background: #10b981;
        box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
      }

      &.inactive {
        background: #64748b;
      }
    }

    .url-cell {
      max-width: 280px;

      .truncate-url {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-family: monospace;
        font-size: 0.78rem;
        color: #93c5fd;
      }
    }

    .type-badge {
      background: rgba(255, 255, 255, 0.06);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.72rem;
      color: #94a3b8;
    }

    .outcome-pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: capitalize;

      &.success {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
      }

      &.failed {
        background: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
      }

      &.warning {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
      }

      &.neutral {
        background: rgba(100, 116, 139, 0.15);
        color: #94a3b8;
      }
    }

    .target-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
    }

    .run-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .spin {
        animation: spin 1s linear infinite;
      }
    }

    .small-icon-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      color: #94a3b8;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
      }

      &.delete:hover {
        color: #f43f5e;
        border-color: rgba(244, 63, 94, 0.3);
      }
    }

    .sync-feedback {
      display: flex;
      align-items: center;
      gap: 4px;
      justify-content: flex-end;
      margin-top: 4px;
      font-size: 0.72rem;

      &.success {
        color: #34d399;
      }

      &.error {
        color: #f43f5e;
      }
    }
  }
`;

// Modals
const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
`;

const ModalCard = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  width: 100%;
  max-width: 520px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h3 {
      font-size: 1.2rem;
      font-weight: 700;
      color: #f8fafc;
      margin: 0;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 1.5rem;
      color: #64748b;
      cursor: pointer;

      &:hover {
        color: #ffffff;
      }
    }

    &.danger {
      justify-content: flex-start;
      gap: 12px;

      .danger-icon {
        color: #f43f5e;
      }
    }
  }

  .form-group {
    margin-bottom: 16px;

    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 6px;
    }

    input[type='text'],
    input[type='url'],
    select {
      width: 100%;
      padding: 10px 12px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      color: #f8fafc;
      font-size: 0.85rem;
      outline: none;

      &:focus,
      &:focus-visible {
        border-color: #3b82f6;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
      }

      &::placeholder {
        color: #94a3b8;
      }
    }
  }

  .country-selector {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    max-height: 120px;
    overflow-y: auto;
    padding: 8px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .country-check-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    font-size: 0.78rem;
    cursor: pointer;
    transition: all 0.2s;

    input {
      position: absolute;
      opacity: 0;
      width: 1px;
      height: 1px;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
    }

    &:focus-within {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }

    &.checked {
      background: rgba(59, 130, 246, 0.2);
      border-color: rgba(59, 130, 246, 0.4);
      color: #60a5fa;
      font-weight: 600;
    }
  }

  .checkbox-group {
    margin-top: 16px;
  }

  .checkbox-label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #cbd5e1;
    font-size: 0.85rem;
    cursor: pointer;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;

    button {
      padding: 10px 18px;
      border-radius: 10px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .cancel-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
      }
    }

    .save-btn {
      background: #2563eb;
      border: none;
      color: #ffffff;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .danger-btn {
      background: #e11d48;
      border: none;
      color: #ffffff;

      &:hover:not(:disabled) {
        background: #be123c;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
  }

  .warning-box {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
    background: rgba(244, 63, 94, 0.1);
    border: 1px solid rgba(244, 63, 94, 0.3);
    border-radius: 10px;
    color: #fda4af;
    font-size: 0.8rem;
    line-height: 1.4;
    margin: 12px 0;
  }

  .hint {
    font-size: 0.78rem;
    color: #94a3b8;
    line-height: 1.4;
  }
`;
