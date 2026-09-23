import React, { useState, useEffect, useMemo } from 'react';
import {
  Building2,
  ExternalLink,
  MapPin,
  Calendar,
  Search,
  RefreshCw,
  LayoutGrid,
  List,
  CheckCircle2,
  XCircle,
  Flag,
  Shield,
  Tag,
  Clock,
  GitBranch,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  X,
} from 'lucide-react';
import type {
  GitHubInternshipsResponse,
  GitHubRepoMeta,
} from '../../api/client';
import { api } from '../../api/client';
import { CompanyLogo } from './CompanyLogo';
import { VisaBadge } from './VisaBadge';
import { useTranslation } from '../../i18n';

const PAGE_SIZE_OPTIONS = [24, 48, 96, 200];

export const normalizeCategory = (rawCat?: string): string => {
  if (!rawCat) return 'Software Engineering';
  const c = rawCat.toLowerCase();
  if (c.includes('cyber') || c.includes('security') || c.includes('soc') || c.includes('appsec') || c.includes('forensics') || c.includes('threat')) {
    return 'Cybersecurity';
  }
  if (c.includes('ai') || c.includes('machine learning') || c.includes('data') || c.includes('deep learning')) {
    return 'Data Science & AI';
  }
  if (c.includes('quant') || c.includes('finance') || c.includes('trading')) {
    return 'Quantitative Finance';
  }
  if (c.includes('hardware') || c.includes('silicon') || c.includes('firmware') || c.includes('analog') || c.includes('asic')) {
    return 'Hardware Engineering';
  }
  if (c.includes('product') || c.includes('pm')) {
    return 'Product Management';
  }
  if (c.includes('cloud') || c.includes('devops') || c.includes('infra') || c.includes('sre')) {
    return 'Cloud & DevOps';
  }
  return 'Software Engineering';
};

export const GitHubInternshipsView: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<GitHubInternshipsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [selectedRepoId, setSelectedRepoId] = useState<string>('all');
  const [selectedVisaStatus, setSelectedVisaStatus] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [openOnly, setOpenOnly] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);

  const fetchInternships = async (isSync = false) => {
    try {
      if (isSync) setSyncing(true);
      else setLoading(true);
      setErrorMsg(null);

      const response = isSync
        ? await api.syncCuratedGitHubInternships()
        : await api.getCuratedGitHubInternships();
      setData(response);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load curated internships.');
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchInternships();
  }, []);

  // Filter items in memory with instantaneous responsiveness
  const filteredItems = useMemo(() => {
    if (!data) return [];
    let items = data.items;

    if (selectedRepoId !== 'all') {
      items = items.filter((it) => it.source_repo_id === selectedRepoId);
    }

    if (selectedVisaStatus !== 'all') {
      if (selectedVisaStatus === 'sponsors_visa') {
        items = items.filter((it) => it.visa_status === 'sponsors_visa');
      } else if (selectedVisaStatus === 'no_sponsorship') {
        items = items.filter((it) => it.visa_status === 'no_sponsorship');
      } else if (selectedVisaStatus === 'us_citizen_only') {
        items = items.filter((it) => it.visa_status === 'us_citizen_only');
      } else if (selectedVisaStatus === 'canada_authorized') {
        items = items.filter((it) => it.visa_status === 'canada_authorized');
      } else if (selectedVisaStatus === 'not_specified') {
        items = items.filter((it) => it.visa_status === 'not_specified' || !it.visa_status);
      }
    }

    if (selectedCategory !== 'all') {
      items = items.filter((it) => normalizeCategory(it.category) === selectedCategory);
    }

    if (openOnly) {
      items = items.filter((it) => !it.is_closed);
    }

    if (searchQuery.trim()) {
      const terms = searchQuery.toLowerCase().split(/\s+/).filter(Boolean);
      items = items.filter((it) => {
        const normCat = normalizeCategory(it.category);
        const searchCorpus = `${it.company || ''} ${it.role || ''} ${it.location || ''} ${it.category || ''} ${normCat} ${it.source_repo_name || ''} ${it.visa_text || ''} ${it.notes || ''}`.toLowerCase();
        return terms.every((term) => searchCorpus.includes(term));
      });
    }

    return items;
  }, [data, selectedRepoId, selectedVisaStatus, selectedCategory, openOnly, searchQuery]);

  // Reset pagination on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedRepoId, selectedVisaStatus, selectedCategory, openOnly, searchQuery, pageSize]);

  const totalPages = Math.ceil(filteredItems.length / pageSize) || 1;
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredItems.slice(start, start + pageSize);
  }, [filteredItems, currentPage, pageSize]);

  // Distinct canonical category choices
  const categoryOptions = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    data.items.forEach((it) => {
      set.add(normalizeCategory(it.category));
    });
    return Array.from(set).sort();
  }, [data]);

  const hasActiveFilters =
    selectedRepoId !== 'all' ||
    selectedVisaStatus !== 'all' ||
    selectedCategory !== 'all' ||
    Boolean(searchQuery.trim()) ||
    openOnly;

  const handleResetFilters = () => {
    setSelectedRepoId('all');
    setSelectedVisaStatus('all');
    setSelectedCategory('all');
    setSearchQuery('');
    setOpenOnly(false);
  };

  const visaPillOptions = [
    { id: 'all', label: t.internships.allVisas },
    { id: 'sponsors_visa', label: `🟢 ${t.internships.sponsorsVisa}` },
    { id: 'no_sponsorship', label: `🔴 ${t.internships.noSponsorship}` },
    { id: 'us_citizen_only', label: `🇺🇸 ${t.internships.usCitizenOnly}` },
    { id: 'canada_authorized', label: `🇨🇦 ${t.internships.canadaEligible}` },
    { id: 'not_specified', label: `⚪ ${t.internships.notSpecified}` },
  ];

  return (
    <div className="curated-internships-view">
      {/* Top Banner & Telemetry Stats */}
      <div className="curated-header-banner">
        <div className="banner-text-side">
          <div className="banner-title-line">
            <span className="source-counter-badge">
              <Sparkles size={12} className="inline-icon" /> 7 Active Repositories
            </span>
            <span className="season-badge">Summer 2026 & 2027</span>
          </div>
          <h2 className="banner-title">
            {t.internships.title}
          </h2>
          <p className="banner-desc">
            {t.internships.subtitle}
          </p>
        </div>

        <div className="banner-action-side">
          <button
            type="button"
            className={`sync-github-btn ${syncing ? 'syncing' : ''}`}
            onClick={() => fetchInternships(true)}
            disabled={syncing || loading}
            title="Fetch latest README commits and updates directly from GitHub"
          >
            <RefreshCw size={15} className={syncing ? 'spin-icon' : ''} />
            <span>{syncing ? t.internships.syncing : t.internships.syncGithub}</span>
          </button>
          {data?.stats?.last_synced_at && (
            <span className="last-sync-text">
              <Clock size={12} />
              <span>
                Updated {new Date(data.stats.last_synced_at).toLocaleDateString()} {new Date(data.stats.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      {data && (
        <div className="stats-cards-grid">
          <div className="stat-card">
            <div className="stat-card-label">{t.internships.totalListings}</div>
            <div className="stat-card-value">{data.stats.total_listings.toLocaleString()}</div>
            <div className="stat-card-sub">{data.stats.active_listings.toLocaleString()} {t.internships.activeOpenings}</div>
          </div>

          <div className="stat-card stat-card-green">
            <div className="stat-card-label">
              <CheckCircle2 size={13} className="inline-icon text-emerald-400" />
              <span>{t.internships.sponsorsVisa}</span>
            </div>
            <div className="stat-card-value text-emerald-400">
              {data.stats.visa_sponsored_count.toLocaleString()}
            </div>
            <div className="stat-card-sub">
              {Math.round((data.stats.visa_sponsored_count / (data.stats.total_listings || 1)) * 100)}% of tracked listings
            </div>
          </div>

          <div className="stat-card stat-card-amber">
            <div className="stat-card-label">
              <XCircle size={13} className="inline-icon text-amber-400" />
              <span>{t.internships.noSponsorship} (🛂)</span>
            </div>
            <div className="stat-card-value text-amber-400">
              {data.stats.no_sponsorship_count.toLocaleString()}
            </div>
            <div className="stat-card-sub">Requires pre-existing work auth</div>
          </div>

          <div className="stat-card stat-card-blue">
            <div className="stat-card-label">
              <Flag size={13} className="inline-icon text-sky-400" />
              <span>{t.internships.usCitizenOnly} (🇺🇸)</span>
            </div>
            <div className="stat-card-value text-sky-400">
              {data.stats.us_citizens_count.toLocaleString()}
            </div>
            <div className="stat-card-sub">Clearance / US Citizens</div>
          </div>

          <div className="stat-card stat-card-red">
            <div className="stat-card-label">
              <Shield size={13} className="inline-icon text-rose-400" />
              <span>{t.internships.canadaEligible} (🇨🇦)</span>
            </div>
            <div className="stat-card-value text-rose-400">
              {data.stats.canada_authorized_count.toLocaleString()}
            </div>
            <div className="stat-card-sub">Canadian universities / students</div>
          </div>
        </div>
      )}

      {/* Repository Filter Tabs */}
      <div className="repo-tabs-scroll" role="tablist" aria-label="Repository filter tabs">
        <button
          type="button"
          className={`repo-tab-btn ${selectedRepoId === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedRepoId('all')}
        >
          <span>{t.internships.allRepos}</span>
          <span className="tab-count">{data?.stats.total_listings || 0}</span>
        </button>

        {data?.repositories.map((repo: GitHubRepoMeta) => (
          <button
            key={repo.id}
            type="button"
            className={`repo-tab-btn ${selectedRepoId === repo.id ? 'active' : ''}`}
            onClick={() => setSelectedRepoId(repo.id)}
            title={`${repo.name} (${repo.region})`}
          >
            <GitBranch size={13} />
            <span>{repo.name.split(':')[0]}</span>
            <span className="tab-count">{repo.item_count}</span>
          </button>
        ))}
      </div>

      {/* Main Search & Control Filters Wrapper */}
      <div className="curated-controls-card">
        {/* Main Search Row with Glowing Input Container */}
        <div className="controls-row-main">
          <div className="curated-search-box">
            <Search size={18} className="search-icon-inside" />
            <input
              type="text"
              className="curated-search-input"
              placeholder={t.internships.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label={t.internships.searchPlaceholder}
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSearchQuery('')}
                title="Clear search term"
                aria-label="Clear search"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* View Mode Toggle */}
          <div className="view-mode-toggle" role="group" aria-label="View mode">
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title={t.internships.viewGrid}
              aria-pressed={viewMode === 'grid'}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              title={t.internships.viewTable}
              aria-pressed={viewMode === 'table'}
            >
              <List size={16} />
            </button>
          </div>
        </div>

        {/* Filter Pills Bar */}
        <div className="filter-pills-row">
          <div className="pill-group">
            <span className="pill-group-label">
              <SlidersHorizontal size={13} />
              <span>Visa:</span>
            </span>

            {visaPillOptions.map((v) => (
              <button
                key={v.id}
                type="button"
                className={`filter-pill ${selectedVisaStatus === v.id ? 'active' : ''}`}
                onClick={() => setSelectedVisaStatus(v.id)}
              >
                {v.label}
              </button>
            ))}
          </div>

          {/* Canonical Category Selector Dropdown */}
          <div className="category-select-wrapper">
            <Tag size={14} className="select-icon" />
            <select
              className="curated-select"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              aria-label="Filter by category"
            >
              <option value="all">{t.internships.allCategories} ({categoryOptions.length})</option>
              {categoryOptions.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Open Only Toggle */}
          <label className="open-only-toggle" title="Show only currently active/open opportunities">
            <input
              type="checkbox"
              checked={openOnly}
              onChange={(e) => setOpenOnly(e.target.checked)}
            />
            <span>{t.internships.openOnly}</span>
          </label>

          {/* Reset All Filters Button */}
          {hasActiveFilters && (
            <button
              type="button"
              className="reset-pill-btn"
              onClick={handleResetFilters}
              title="Reset all active filters"
            >
              <X size={12} />
              <span>{t.internships.clearFilters}</span>
            </button>
          )}
        </div>
      </div>

      {/* Results Header & Counter */}
      <div className="results-status-bar">
        <div className="status-counter">
          <span>
            {t.directory.of ? 'Showing' : 'Showing'} <strong>{filteredItems.length}</strong> {t.internships.matchingCount}
          </span>
          {selectedRepoId !== 'all' && (
            <span className="active-filter-tag">
              Repo: {data?.repositories.find((r) => r.id === selectedRepoId)?.name.split(':')[0]}
              <button type="button" onClick={() => setSelectedRepoId('all')}>×</button>
            </span>
          )}
          {selectedVisaStatus !== 'all' && (
            <span className="active-filter-tag">
              Visa: {selectedVisaStatus.replace('_', ' ')}
              <button type="button" onClick={() => setSelectedVisaStatus('all')}>×</button>
            </span>
          )}
          {selectedCategory !== 'all' && (
            <span className="active-filter-tag">
              Category: {selectedCategory}
              <button type="button" onClick={() => setSelectedCategory('all')}>×</button>
            </span>
          )}
          {openOnly && (
            <span className="active-filter-tag">
              {t.internships.openOnly}
              <button type="button" onClick={() => setOpenOnly(false)}>×</button>
            </span>
          )}
        </div>

        {/* Page size dropdown */}
        <div className="pagination-size-select">
          <span>Show:</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="page-size-select"
            aria-label="Items per page"
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt} per page
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="curated-loading-box">
          <div className="progress-spinner" />
          <p>{t.common.loading}</p>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && !loading && (
        <div className="curated-error-banner">
          <p>{errorMsg}</p>
          <button type="button" onClick={() => fetchInternships()} className="retry-btn">
            {t.common.retry}
          </button>
        </div>
      )}

      {/* Content: Grid Mode */}
      {!loading && !errorMsg && viewMode === 'grid' && (
        <div className="curated-grid">
          {paginatedItems.map((item) => (
            <div key={item.id} className={`curated-card ${item.is_closed ? 'card-closed' : ''}`}>
              <div className="curated-card-header">
                <CompanyLogo
                  company={item.company}
                  domain={item.company_domain}
                  logoUrl={item.logo_url}
                  size={46}
                />
                <div className="curated-card-company-info">
                  <div className="curated-company-name-row">
                    <span className="curated-company-name">{item.company}</span>
                  </div>
                  <div className="curated-location-row">
                    <MapPin size={13} />
                    <span title={item.location}>{item.location || 'Remote / Unspecified'}</span>
                  </div>
                </div>
              </div>

              <h4 className="curated-role-title" title={item.role}>
                {item.role}
              </h4>

              <div className="curated-meta-pills">
                <VisaBadge
                  status={item.visa_status}
                  customText={item.visa_text}
                  isClosed={item.is_closed}
                />
                <span className="curated-category-pill" title={normalizeCategory(item.category)}>
                  {normalizeCategory(item.category)}
                </span>
              </div>

              <div className="curated-card-footer">
                <div className="curated-source-info">
                  <span className="source-repo-tag" title={item.source_repo_name}>
                    {item.source_repo_name.split(':')[0]}
                  </span>
                  {item.date_posted && (
                    <span className="posted-time">
                      <Calendar size={11} />
                      <span>{item.date_posted}</span>
                    </span>
                  )}
                </div>

                {item.apply_url && !item.is_closed ? (
                  <a
                    href={item.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="curated-apply-btn"
                  >
                    <span>{t.internships.applyNow}</span>
                    <ExternalLink size={13} />
                  </a>
                ) : (
                  <span className="curated-closed-tag">{t.internships.closed}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Content: Table Mode */}
      {!loading && !errorMsg && viewMode === 'table' && (
        <div className="curated-table-container">
          <table className="curated-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Location</th>
                <th>Category</th>
                <th>Visa Sponsorship</th>
                <th>Posted / Age</th>
                <th>Source</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {paginatedItems.map((item) => (
                <tr key={item.id} className={item.is_closed ? 'row-closed' : ''}>
                  <td className="table-col-company">
                    <div className="table-company-cell">
                      <CompanyLogo
                        company={item.company}
                        domain={item.company_domain}
                        logoUrl={item.logo_url}
                        size={32}
                      />
                      <span className="table-company-name">{item.company}</span>
                    </div>
                  </td>
                  <td className="table-col-role">
                    <span className="table-role-text">{item.role}</span>
                  </td>
                  <td className="table-col-location">
                    <span className="table-location-text">{item.location}</span>
                  </td>
                  <td>
                    <span className="table-cat-badge">{normalizeCategory(item.category)}</span>
                  </td>
                  <td>
                    <VisaBadge
                      status={item.visa_status}
                      customText={item.visa_text}
                      isClosed={item.is_closed}
                      size="sm"
                    />
                  </td>
                  <td>
                    <span className="table-posted-text">{item.date_posted || '—'}</span>
                  </td>
                  <td>
                    <span className="table-source-tag">
                      {item.source_repo_name.split(':')[0]}
                    </span>
                  </td>
                  <td>
                    {item.apply_url && !item.is_closed ? (
                      <a
                        href={item.apply_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="table-apply-btn"
                      >
                        <span>{t.internships.applyNow}</span>
                        <ExternalLink size={12} />
                      </a>
                    ) : (
                      <span className="table-closed-text">{t.internships.closed}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && !errorMsg && filteredItems.length === 0 && (
        <div className="curated-empty-box">
          <Building2 size={42} className="empty-icon" />
          <h3>{t.directory.noJobsFound}</h3>
          <p>{t.directory.noJobsSub}</p>
          <button
            type="button"
            className="reset-filters-btn"
            onClick={handleResetFilters}
          >
            {t.internships.clearFilters}
          </button>
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && !errorMsg && totalPages > 1 && (
        <div className="curated-pagination-row">
          <button
            type="button"
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} />
            <span>{t.directory.prev}</span>
          </button>

          <span className="pagination-info">
            {t.directory.page} <strong>{currentPage}</strong> {t.directory.of} <strong>{totalPages}</strong> ({filteredItems.length} total)
          </span>

          <button
            type="button"
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          >
            <span>{t.directory.next}</span>
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
