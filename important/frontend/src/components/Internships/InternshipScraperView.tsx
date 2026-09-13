import React, { useState } from 'react';
import {
  GraduationCap,
  Search,
  MapPin,
  Calendar,
  Building2,
  ExternalLink,
  Sparkles,
  ShieldAlert,
  Clock,
  Compass,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import type { InternshipSearchResponse, Country } from '../../api/client';
import { api } from '../../api/client';
import './InternshipScraperView.css';

interface InternshipScraperViewProps {
  availableCountries?: Country[];
}

const POPULAR_FIELDS = [
  'Cybersecurity',
  'Software Engineering',
  'Data Science',
  'Cloud Architecture',
  'Machine Learning',
  'DevOps',
  'Web Development',
];

const SEARCH_STAGES = [
  'Preparing search & multilingual terminology expansion...',
  'Discovering opportunities across career portals...',
  'Analyzing pages & evaluating positive internship signals...',
  'Filtering out irrelevant blogs and landing portals...',
  'Removing duplicates and computing confidence...',
  'Finalizing internship opportunities...',
];

export const InternshipScraperView: React.FC<InternshipScraperViewProps> = ({ availableCountries = [] }) => {
  const [fieldInput, setFieldInput] = useState('Cybersecurity');
  const [countryInput, setCountryInput] = useState('');
  const [yearInput, setYearInput] = useState('2026');

  const [loading, setLoading] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [results, setResults] = useState<InternshipSearchResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSearch = async (customField?: string) => {
    const searchField = (customField || fieldInput).trim();
    if (!searchField) {
      setErrorMsg('Please specify an internship field or role keywords.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setCurrentStageIndex(0);

    // Simulate progressive stage updates while waiting for response
    const stageInterval = setInterval(() => {
      setCurrentStageIndex((prev) => (prev < SEARCH_STAGES.length - 1 ? prev + 1 : prev));
    }, 900);

    try {
      const response = await api.searchInternships({
        field: searchField,
        country: countryInput.trim() || undefined,
        year: yearInput.trim() || undefined,
        max_results: 24,
      });
      setResults(response);
    } catch (err: any) {
      setErrorMsg(err.message || 'Internship search failed. Please try again.');
    } finally {
      clearInterval(stageInterval);
      setLoading(false);
    }
  };

  return (
    <div className="internships-container">
      {/* Header & Description */}
      <div className="internships-header">
        <div className="internships-title-row">
          <h1 className="internships-heading">
            <GraduationCap size={32} className="text-blue-500" />
            <span>Internship Intelligence</span>
            <span className="heading-badge">Autonomous Discovery</span>
          </h1>
        </div>
        <p className="internships-subtitle">
          Dedicated career engine for students and emerging professionals. Ingests, classifies, and extracts verified
          internship and PFE opportunities worldwide using multilingual query expansion and structured job intelligence.
        </p>
      </div>

      {/* Search Filter Card */}
      <div className="internship-search-card">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
        >
          <div className="search-form-grid">
            {/* Field Input */}
            <div className="form-field">
              <label className="form-label">
                <Search size={13} />
                <span>Internship Field / Keyword</span>
              </label>
              <div className="input-with-icon">
                <Search size={16} className="input-icon" />
                <input
                  type="text"
                  className="search-input"
                  placeholder="e.g. Cybersecurity, Software Engineering..."
                  value={fieldInput}
                  onChange={(e) => setFieldInput(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Country Input */}
            <div className="form-field">
              <label className="form-label">
                <MapPin size={13} />
                <span>Target Country (Optional)</span>
              </label>
              <div className="input-with-icon">
                <Compass size={16} className="input-icon" />
                <input
                  type="text"
                  className="search-input"
                  placeholder="Worldwide (leave empty) or e.g. Germany"
                  value={countryInput}
                  onChange={(e) => setCountryInput(e.target.value)}
                  disabled={loading}
                  list="countries-datalist"
                />
                <datalist id="countries-datalist">
                  {availableCountries.map((c) => (
                    <option key={c.id} value={c.name} />
                  ))}
                  <option value="Germany" />
                  <option value="France" />
                  <option value="Morocco" />
                  <option value="United States" />
                  <option value="United Kingdom" />
                  <option value="Spain" />
                  <option value="Canada" />
                </datalist>
              </div>
            </div>

            {/* Year Input */}
            <div className="form-field">
              <label className="form-label">
                <Calendar size={13} />
                <span>Target Year</span>
              </label>
              <div className="input-with-icon">
                <Calendar size={16} className="input-icon" />
                <input
                  type="text"
                  className="search-input"
                  placeholder="e.g. 2026, 2027"
                  value={yearInput}
                  onChange={(e) => setYearInput(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Search Button */}
            <button type="submit" className="search-btn" disabled={loading}>
              <Sparkles size={16} />
              <span>{loading ? 'Searching...' : 'Discover Internships'}</span>
            </button>
          </div>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="related-titles-row">
          <span className="related-label">
            <Sparkles size={12} />
            <span>Trending Fields:</span>
          </span>
          {POPULAR_FIELDS.map((f) => (
            <button
              key={f}
              type="button"
              className="title-chip"
              onClick={() => {
                setFieldInput(f);
                handleSearch(f);
              }}
              disabled={loading}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Progressive Loading State */}
      {loading && (
        <div className="scraper-progress-card">
          <div className="progress-spinner" />
          <h3 className="progress-stage-text">{SEARCH_STAGES[currentStageIndex]}</h3>
          <p className="progress-subtext">
            Ingesting candidate pages, parsing career portal schemas, and rejecting generic landing pages.
          </p>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && !loading && (
        <div className="diagnostics-banner" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(239, 68, 68, 0.1)' }}>
          <div className="diag-stat" style={{ color: '#f87171' }}>
            <AlertTriangle size={16} />
            <span>{errorMsg}</span>
          </div>
        </div>
      )}

      {/* Results Section */}
      {results && !loading && (
        <>
          {/* Diagnostics Banner */}
          <div className="diagnostics-banner">
            <div className="diag-stat-group">
              <span className="diag-stat">
                <CheckCircle2 size={15} className="text-emerald-400" />
                <span>Found: <strong>{results.opportunities.length}</strong> opportunities</span>
              </span>
              <span className="diag-stat">
                <span>Checked: <strong>{results.diagnostics.sources_checked}</strong> sources</span>
              </span>
              {results.diagnostics.sources_unavailable > 0 && (
                <span className="diag-stat text-amber-400">
                  <ShieldAlert size={14} />
                  <span>{results.diagnostics.sources_unavailable} unavailable/blocked (skipped safely)</span>
                </span>
              )}
              {results.diagnostics.sources_rejected_non_job > 0 && (
                <span className="diag-stat">
                  <span>Filtered: <strong>{results.diagnostics.sources_rejected_non_job}</strong> non-job pages</span>
                </span>
              )}
            </div>
            <div className="diag-stat">
              <Clock size={14} />
              <span>Speed: <strong>{results.diagnostics.execution_time_ms} ms</strong></span>
            </div>
          </div>

          {/* Related Titles from Dataset */}
          {results.related_titles && results.related_titles.length > 0 && (
            <div className="related-titles-row" style={{ padding: '10px 0' }}>
              <span className="related-label">
                <GraduationCap size={13} />
                <span>Dataset Titles ({results.related_titles.length}):</span>
              </span>
              {results.related_titles.map((rt) => (
                <button
                  key={rt}
                  type="button"
                  className="title-chip"
                  onClick={() => {
                    setFieldInput(rt);
                    handleSearch(rt);
                  }}
                >
                  {rt}
                </button>
              ))}
            </div>
          )}

          {/* Opportunities Grid */}
          {results.opportunities.length > 0 ? (
            <div className="opportunities-grid">
              {results.opportunities.map((opp) => (
                <div key={opp.id} className="internship-card">
                  <div className="card-top-row">
                    <div className="card-badge-row">
                      <span className="badge-confidence">
                        {opp.confidence_score}% Confidence
                      </span>
                      {opp.is_year_match && (
                        <span className="badge-year">
                          ★ {yearInput || 'Target Year'}
                        </span>
                      )}
                      <span className="badge-type">{opp.internship_type}</span>
                    </div>
                  </div>

                  <h3 className="opp-title">{opp.title}</h3>

                  <div className="opp-company-row">
                    <span className="opp-company">
                      <Building2 size={14} />
                      <span>{opp.company}</span>
                    </span>
                    <span className="opp-location">
                      <MapPin size={13} />
                      <span>{opp.location} {opp.country && opp.country !== opp.location ? `(${opp.country})` : ''}</span>
                    </span>
                  </div>

                  {opp.description && (
                    <p className="opp-desc">{opp.description}</p>
                  )}

                  {opp.requirements && opp.requirements.length > 0 && (
                    <div className="opp-reqs-cloud">
                      {opp.requirements.slice(0, 4).map((req, rIdx) => (
                        <span key={rIdx} className="req-pill">
                          {req}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="card-footer-row">
                    <span className="opp-source-tag">
                      <Compass size={13} />
                      <span>{opp.source_domain || 'Career Portal'}</span>
                    </span>

                    <a
                      href={opp.application_url || opp.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="view-internship-btn"
                    >
                      <span>View Internship</span>
                      <ExternalLink size={13} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="internships-empty-card">
              <GraduationCap size={44} className="empty-icon-lg" />
              <h3 className="empty-title">No matching internship opportunities found</h3>
              <p className="empty-subtext">
                Try broadening your keyword, removing country filters to search Worldwide, or selecting one of the suggested titles above.
              </p>
            </div>
          )}
        </>
      )}

      {/* Initial Empty State */}
      {!results && !loading && (
        <div className="internships-empty-card">
          <Compass size={44} className="empty-icon-lg" />
          <h3 className="empty-title">Ready to discover internships</h3>
          <p className="empty-subtext">
            Enter your field of study, preferred country, or target year above to scan verified career pages and structured postings.
          </p>
        </div>
      )}
    </div>
  );
};
