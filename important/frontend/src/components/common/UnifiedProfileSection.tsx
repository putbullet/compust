import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  ShieldCheck,
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  ExternalLink,
  Eye,
  EyeOff,
  Pin,
  RefreshCw,
  Layers,
  Award,
  Briefcase,
  GraduationCap,
  Globe,
  Sparkles,
} from 'lucide-react';
import { api } from '../../api/client';
import type { LinkedInProfileStatus, UnifiedProfileData } from '../../api/client';

const LinkedInIcon: React.FC<{ size?: number; className?: string }> = ({ size = 20, className }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);


export const UnifiedProfileSection: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [liStatus, setLiStatus] = useState<LinkedInProfileStatus | null>(null);
  const [unified, setUnified] = useState<UnifiedProfileData | null>(null);
  const [urlInput, setUrlInput] = useState('');
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlSuccess, setUrlSuccess] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [importMode, setImportMode] = useState<'export' | 'pdf'>('export');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, unifiedRes] = await Promise.all([
        api.getLinkedInStatus(),
        api.getUnifiedProfile(),
      ]);
      setLiStatus(statusRes);
      setUnified(unifiedRes);
      if (statusRes.linkedin_url) {
        setUrlInput(statusRes.linkedin_url);
      }
    } catch (err: any) {
      console.error('Failed to load LinkedIn / Unified profile data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    setUrlError(null);
    setUrlSuccess(null);
    if (!urlInput.trim()) {
      setUrlError('Please enter a valid LinkedIn profile URL.');
      return;
    }
    try {
      const res = await api.updateLinkedInUrl(urlInput.trim());
      setLiStatus(res);
      setUrlInput(res.linkedin_url || urlInput);
      setUrlSuccess('LinkedIn profile URL saved and validated.');
      setTimeout(() => setUrlSuccess(null), 3500);
      const updatedUnified = await api.getUnifiedProfile();
      setUnified(updatedUnified);
    } catch (err: any) {
      setUrlError(err.message || 'Invalid LinkedIn URL. Expected https://www.linkedin.com/in/your-handle');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);
    setUploadSuccess(null);
    setUploading(true);

    try {
      if (importMode === 'export') {
        const lower = file.name.toLowerCase();
        if (!lower.endsWith('.zip') && !lower.endsWith('.csv')) {
          setUploadError('Please upload an official LinkedIn export (.zip or .csv file).');
          return;
        }
        await api.uploadLinkedInExport(file);
        setUploadSuccess(`LinkedIn export "${file.name}" imported and merged successfully!`);
      } else {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          setUploadError('Please upload a valid LinkedIn "Save to PDF" document.');
          return;
        }
        await api.uploadLinkedInPdf(file);
        setUploadSuccess(`LinkedIn PDF "${file.name}" parsed and merged successfully!`);
      }
      setTimeout(() => setUploadSuccess(null), 4000);
      await fetchData();
    } catch (err: any) {
      setUploadError(err.message || 'Import failed. Please verify the file format.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDeleteLinkedIn = async () => {
    if (!window.confirm('Are you sure you want to remove your LinkedIn data? Matching will revert to resume-only.')) {
      return;
    }
    try {
      await api.deleteLinkedInData();
      await fetchData();
      setUploadSuccess('LinkedIn data removed. Profile reverted to resume-only mode.');
      setTimeout(() => setUploadSuccess(null), 3500);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to remove LinkedIn data.');
    }
  };

  const handleToggleMatching = async (enabled: boolean) => {
    try {
      const res = await api.toggleUnifiedMatching(enabled);
      setUnified(res);
    } catch (err: any) {
      alert(err.message || 'Failed to toggle matching mode.');
    }
  };

  const handleToggleHideSkill = async (canonicalName: string) => {
    if (!unified) return;
    const currentHidden = unified.user_overrides?.hidden_skills || [];
    const isHidden = currentHidden.includes(canonicalName);
    const newHidden = isHidden
      ? currentHidden.filter((s) => s !== canonicalName)
      : [...currentHidden, canonicalName];
    const currentPinned = unified.user_overrides?.pinned_skills || [];
    try {
      const res = await api.updateUnifiedOverrides({
        pinned_skills: currentPinned,
        hidden_skills: newHidden,
      });
      setUnified(res);
    } catch (err: any) {
      console.error('Failed to update skill visibility:', err);
    }
  };

  const handleTogglePinSkill = async (canonicalName: string) => {
    if (!unified) return;
    const currentPinned = unified.user_overrides?.pinned_skills || [];
    const isPinned = currentPinned.includes(canonicalName);
    const newPinned = isPinned
      ? currentPinned.filter((s) => s !== canonicalName)
      : [...currentPinned, canonicalName];
    const currentHidden = unified.user_overrides?.hidden_skills || [];
    try {
      const res = await api.updateUnifiedOverrides({
        pinned_skills: newPinned,
        hidden_skills: currentHidden,
      });
      setUnified(res);
    } catch (err: any) {
      console.error('Failed to update skill pin status:', err);
    }
  };

  if (loading && !unified) {
    return (
      <Container className="glass-panel">
        <LoadingBox>
          <RefreshCw size={24} className="spin" />
          <span>Loading Unified Profile & LinkedIn Data...</span>
        </LoadingBox>
      </Container>
    );
  }

  const isImported = liStatus?.status === 'imported' || liStatus?.status === 'needs_refresh';
  const needsRefresh = liStatus?.status === 'needs_refresh';

  return (
    <Container className="glass-panel">
      {/* Header */}
      <HeaderRow>
        <div className="title-area">
          <div className="icon-badge">
            <LinkedInIcon size={22} />
          </div>

          <div>
            <h3>LinkedIn Profile Integration & Unified Career Intelligence</h3>
            <p className="subtitle">
              Combine your resume and LinkedIn into a single canonical Unified Profile.
              All matching features and browser extension analyze vacancies against this unified baseline.
            </p>
          </div>
        </div>
        {isImported && (
          <button type="button" onClick={handleDeleteLinkedIn} className="delete-btn" title="Remove LinkedIn data">
            <Trash2 size={15} />
            <span>Remove LinkedIn Data</span>
          </button>
        )}
      </HeaderRow>

      {/* URL Input Bar */}
      <UrlSection onSubmit={handleSaveUrl}>
        <div className="url-label">LinkedIn Profile URL</div>
        <div className="url-bar">
          <input
            type="text"
            placeholder="https://www.linkedin.com/in/your-handle"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            className="url-input"
          />
          <button type="submit" className="save-url-btn">
            Save URL
          </button>
        </div>
        {urlError && <div className="msg error"><AlertTriangle size={14} /><span>{urlError}</span></div>}
        {urlSuccess && <div className="msg success"><CheckCircle2 size={14} /><span>{urlSuccess}</span></div>}

        {liStatus?.linkedin_url && (
          <StatusRow>
            <a href={liStatus.linkedin_url} target="_blank" rel="noreferrer" className="profile-link">
              <span>{liStatus.linkedin_url}</span>
              <ExternalLink size={13} />
            </a>
            <span className={`status-pill ${liStatus.status}`}>
              {liStatus.status === 'not_imported' && 'Not Imported'}
              {liStatus.status === 'imported' && `Imported · ${liStatus.days_since_import ?? 0}d ago`}
              {liStatus.status === 'needs_refresh' && `Needs Refresh (Imported ${liStatus.days_since_import}d ago)`}
            </span>
          </StatusRow>
        )}
      </UrlSection>

      {/* Zero-Ban-Risk Import Methods */}
      <ImportBox>
        <div className="import-tabs">
          <button
            type="button"
            className={`tab-btn ${importMode === 'export' ? 'active' : ''}`}
            onClick={() => setImportMode('export')}
          >
            <ShieldCheck size={16} />
            <span>Path A: Official Data Export (Zero Ban Risk)</span>
          </button>
          <button
            type="button"
            className={`tab-btn ${importMode === 'pdf' ? 'active' : ''}`}
            onClick={() => setImportMode('pdf')}
          >
            <FileText size={16} />
            <span>Path B: Save to PDF Upload</span>
          </button>
        </div>

        {importMode === 'export' ? (
          <InstructionsBox>
            <div className="steps-title">Step-by-Step Instructions:</div>
            <ol className="steps-list">
              <li>Open LinkedIn &rarr; <strong>Settings & Privacy</strong> &rarr; <strong>Data Privacy</strong>.</li>
              <li>Click <strong>&quot;Get a copy of your data&quot;</strong>.</li>
              <li>Select <em>&quot;Want something in particular?&quot;</em> and check <strong>Profile, Positions, Education, Skills, Certifications</strong>.</li>
              <li>Click <strong>&quot;Request archive&quot;</strong>. Once ready, download the ZIP archive.</li>
              <li>Drop the downloaded <code>.zip</code> file (or individual CSV files) in the upload zone below.</li>
            </ol>
          </InstructionsBox>
        ) : (
          <InstructionsBox>
            <div className="steps-title">Step-by-Step Instructions:</div>
            <ol className="steps-list">
              <li>Open your personal profile on LinkedIn in your browser.</li>
              <li>Click the <strong>&quot;More&quot;</strong> button below your intro card &rarr; click <strong>&quot;Save to PDF&quot;</strong>.</li>
              <li>Upload the downloaded PDF below. Multilingual headings in EN, FR, NL, DE are supported.</li>
            </ol>
          </InstructionsBox>
        )}

        {/* Upload Drop Zone */}
        <DropZone>
          <UploadCloud size={32} className="upload-icon" />
          <div className="drop-title">
            {uploading ? 'Processing and merging profile entities...' : 'Select or drop your file here'}
          </div>
          <p className="drop-sub">
            {importMode === 'export'
              ? 'Accepts official LinkedIn export ZIP archive or individual CSVs.'
              : 'Accepts official LinkedIn "Save to PDF" document.'}
          </p>
          <label className="file-btn">
            <span>{uploading ? 'Parsing...' : 'Choose File'}</span>
            <input
              type="file"
              accept={importMode === 'export' ? '.zip,.csv' : '.pdf'}
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
          </label>
        </DropZone>

        {uploadError && <div className="msg error"><AlertTriangle size={14} /><span>{uploadError}</span></div>}
        {uploadSuccess && <div className="msg success"><CheckCircle2 size={14} /><span>{uploadSuccess}</span></div>}

        {/* Anti-Scraping / Account Safety Notice */}
        <SafetyNotice>
          <ShieldCheck size={16} className="safety-icon" />
          <div>
            <strong>100% Ban-Free & Private Architecture:</strong> Compust deliberately avoids headless bot scraping, proxy rotation, and auth-wall workarounds to guarantee your LinkedIn account is never flagged, restricted, or rate-limited. All processing occurs locally on your machine.
          </div>
        </SafetyNotice>
      </ImportBox>

      {/* Unified Profile Middleware Section: "What Compust Knows About You" */}
      {unified && (
        <UnifiedBox>
          <div className="unified-top-row">
            <div className="unified-title">
              <Layers size={18} className="highlight-icon" />
              <h4>What Compust Knows About You (Canonical Unified Profile)</h4>
            </div>
            <div className="toggle-matching-box">
              <span className="toggle-label">Use LinkedIn data in job matching:</span>
              <button
                type="button"
                className={`switch-btn ${unified.use_linkedin_in_matching ? 'on' : 'off'}`}
                onClick={() => handleToggleMatching(!unified.use_linkedin_in_matching)}
              >
                {unified.use_linkedin_in_matching ? 'Enabled' : 'Disabled (Resume-Only)'}
              </button>
            </div>
          </div>

          {needsRefresh && (
            <div className="refresh-banner">
              <AlertTriangle size={16} />
              <span>Your LinkedIn data was imported over 30 days ago. Upload a fresh export to keep job matching fully synchronized.</span>
            </div>
          )}

          {/* Conflicts Resolution Alert */}
          {unified.conflicts && unified.conflicts.length > 0 && (
            <ConflictsBox>
              <div className="conflicts-title">
                <AlertTriangle size={16} />
                <span>Detected Profile Differences for Review ({unified.conflicts.length})</span>
              </div>
              <div className="conflicts-list">
                {unified.conflicts.map((c, idx) => (
                  <div key={idx} className="conflict-item">
                    <span className="conflict-desc">{c.description}</span>
                  </div>
                ))}
              </div>
            </ConflictsBox>
          )}

          {/* Unified Skills Grid */}
          <SectionSubGroup>
            <div className="subgroup-title">
              <Sparkles size={16} />
              <span>Unified Skills ({unified.skills.length})</span>
            </div>
            <div className="skills-wrap">
              {unified.skills.map((s) => {
                const isBoth = s.provenances.some((p) => p.source === 'resume') && s.provenances.some((p) => p.source === 'linkedin');
                const isLinkedIn = s.provenances.some((p) => p.source === 'linkedin') && !s.provenances.some((p) => p.source === 'resume');
                const badgeText = isBoth ? 'Both' : isLinkedIn ? 'LinkedIn' : 'Resume';
                const badgeClass = isBoth ? 'badge-purple' : isLinkedIn ? 'badge-cyan' : 'badge-blue';

                return (
                  <div key={s.canonical_name} className={`skill-tag ${s.hidden ? 'hidden-skill' : ''} ${s.pinned ? 'pinned-skill' : ''}`}>
                    <span className="skill-name">{s.name}</span>
                    <span className={`source-badge ${badgeClass}`}>{badgeText}</span>
                    <div className="skill-actions">
                      <button
                        type="button"
                        onClick={() => handleTogglePinSkill(s.canonical_name)}
                        className={`action-btn ${s.pinned ? 'active' : ''}`}
                        title={s.pinned ? 'Unpin skill' : 'Pin skill (prioritize in matching)'}
                      >
                        <Pin size={12} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleHideSkill(s.canonical_name)}
                        className={`action-btn ${s.hidden ? 'active' : ''}`}
                        title={s.hidden ? 'Unhide skill' : 'Hide skill (exclude from matching)'}
                      >
                        {s.hidden ? <EyeOff size={12} /> : <Eye size={12} />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </SectionSubGroup>

          {/* Unified Experience */}
          <SectionSubGroup>
            <div className="subgroup-title">
              <Briefcase size={16} />
              <span>Unified Professional Experience ({unified.experience.length})</span>
            </div>
            <div className="items-list">
              {unified.experience.map((exp) => {
                const isBoth = exp.provenances.some((p) => p.source === 'resume') && exp.provenances.some((p) => p.source === 'linkedin');
                const isLinkedIn = exp.provenances.some((p) => p.source === 'linkedin') && !exp.provenances.some((p) => p.source === 'resume');
                const badgeText = isBoth ? 'Both' : isLinkedIn ? 'LinkedIn' : 'Resume';
                const badgeClass = isBoth ? 'badge-purple' : isLinkedIn ? 'badge-cyan' : 'badge-blue';

                return (
                  <div key={exp.id} className="item-card">
                    <div className="item-header">
                      <div>
                        <strong>{exp.title}</strong> &mdash; <span>{exp.company}</span>
                      </div>
                      <span className={`source-badge ${badgeClass}`}>{badgeText}</span>
                    </div>
                    {(exp.start_date || exp.end_date) && (
                      <div className="item-dates">
                        {exp.start_date || 'Start'} &ndash; {exp.end_date || 'Present'}
                        {exp.location ? ` · ${exp.location}` : ''}
                      </div>
                    )}
                    {exp.description && <div className="item-desc">{exp.description}</div>}
                  </div>
                );
              })}
            </div>
          </SectionSubGroup>

          {/* Unified Education & Certifications */}
          <TwoColGrid>
            <SectionSubGroup>
              <div className="subgroup-title">
                <GraduationCap size={16} />
                <span>Education ({unified.education.length})</span>
              </div>
              <div className="items-list">
                {unified.education.map((edu) => (
                  <div key={edu.id} className="item-card">
                    <strong>{edu.institution}</strong>
                    <div className="item-sub">{edu.degree} {edu.field ? `in ${edu.field}` : ''}</div>
                  </div>
                ))}
              </div>
            </SectionSubGroup>

            <SectionSubGroup>
              <div className="subgroup-title">
                <Award size={16} />
                <span>Certifications ({unified.certifications.length})</span>
              </div>
              <div className="items-list">
                {unified.certifications.map((c) => (
                  <div key={c.id} className="item-card">
                    <strong>{c.name}</strong>
                    {c.issuer && <div className="item-sub">{c.issuer}</div>}
                  </div>
                ))}
              </div>
            </SectionSubGroup>
          </TwoColGrid>

          {/* Unified Languages */}
          {unified.languages && unified.languages.length > 0 && (
            <SectionSubGroup>
              <div className="subgroup-title">
                <Globe size={16} />
                <span>Languages ({unified.languages.length})</span>
              </div>
              <div className="languages-chips">
                {unified.languages.map((l, idx) => (
                  <span key={idx} className="lang-chip">
                    {l.language} {l.proficiency ? `(${l.proficiency})` : ''}
                  </span>
                ))}
              </div>
            </SectionSubGroup>
          )}
        </UnifiedBox>
      )}
    </Container>
  );
};

// -----------------------------------------------------------------------------
// Styled Components
// -----------------------------------------------------------------------------

const Container = styled.div`
  margin-top: 24px;
  padding: 24px;
  border-radius: 14px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  background: var(--bg-card, rgba(255, 255, 255, 0.03));
`;

const LoadingBox = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: var(--text-muted, #94a3b8);
  font-size: 14px;

  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const HeaderRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 16px;

  .title-area {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  .icon-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: rgba(10, 102, 194, 0.15);
    color: #0a66c2;
    flex-shrink: 0;
  }

  h3 {
    margin: 0 0 4px 0;
    font-size: 17px;
    font-weight: 600;
    color: var(--text-color, #f8fafc);
  }

  .subtitle {
    margin: 0;
    font-size: 13px;
    color: var(--text-muted, #94a3b8);
    line-height: 1.4;
  }

  .delete-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 12px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.25);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    &:hover {
      background: rgba(239, 68, 68, 0.2);
    }
  }
`;

const UrlSection = styled.form`
  margin-bottom: 24px;
  padding: 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));

  .url-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted, #94a3b8);
    margin-bottom: 8px;
  }

  .url-bar {
    display: flex;
    gap: 8px;
  }

  .url-input {
    flex: 1;
    padding: 9px 14px;
    border-radius: 8px;
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.12));
    background: var(--bg-input, rgba(0, 0, 0, 0.2));
    color: var(--text-color, #f8fafc);
    font-size: 14px;
    outline: none;
    &:focus {
      border-color: #0a66c2;
    }
  }

  .save-url-btn {
    padding: 9px 18px;
    border-radius: 8px;
    background: #0a66c2;
    color: #fff;
    border: none;
    font-weight: 500;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.2s;
    &:hover {
      background: #004182;
    }
  }

  .msg {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    font-size: 12px;
    &.error { color: #f87171; }
    &.success { color: #4ade80; }
  }
`;

const StatusRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.05));

  .profile-link {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #38bdf8;
    font-size: 13px;
    text-decoration: none;
    &:hover {
      text-decoration: underline;
    }
  }

  .status-pill {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    &.imported {
      background: rgba(34, 197, 94, 0.15);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }
    &.needs_refresh {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    &.not_imported {
      background: rgba(148, 163, 184, 0.1);
      color: #94a3b8;
    }
  }
`;

const ImportBox = styled.div`
  margin-bottom: 24px;
  padding: 18px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));

  .import-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 8px;
    background: transparent;
    color: var(--text-muted, #94a3b8);
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    &.active {
      background: rgba(10, 102, 194, 0.15);
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.4);
    }
  }

  .msg {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    font-size: 12px;
    &.error { color: #f87171; }
    &.success { color: #4ade80; }
  }
`;

const InstructionsBox = styled.div`
  padding: 12px 16px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.15);
  margin-bottom: 16px;
  font-size: 13px;

  .steps-title {
    font-weight: 600;
    color: var(--text-color, #f8fafc);
    margin-bottom: 6px;
  }

  .steps-list {
    margin: 0;
    padding-left: 20px;
    color: var(--text-muted, #94a3b8);
    line-height: 1.6;
    strong {
      color: var(--text-color, #f8fafc);
    }
  }
`;

const DropZone = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  border: 2px dashed var(--border-color, rgba(255, 255, 255, 0.15));
  border-radius: 10px;
  text-align: center;
  background: rgba(255, 255, 255, 0.01);

  .upload-icon {
    color: #38bdf8;
    margin-bottom: 10px;
  }

  .drop-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-color, #f8fafc);
    margin-bottom: 4px;
  }

  .drop-sub {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    margin: 0 0 14px 0;
  }

  .file-btn {
    padding: 8px 18px;
    border-radius: 8px;
    background: #0a66c2;
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    &:hover {
      background: #004182;
    }
  }
`;

const SafetyNotice = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  color: var(--text-muted, #94a3b8);
  font-size: 12px;
  line-height: 1.5;

  .safety-icon {
    color: #4ade80;
    flex-shrink: 0;
    margin-top: 2px;
  }

  strong {
    color: #4ade80;
  }
`;

const UnifiedBox = styled.div`
  margin-top: 24px;
  padding: 20px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));

  .unified-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .unified-title {
    display: flex;
    align-items: center;
    gap: 10px;
    h4 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--text-color, #f8fafc);
    }
    .highlight-icon {
      color: #a855f7;
    }
  }

  .toggle-matching-box {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .toggle-label {
    font-size: 13px;
    color: var(--text-muted, #94a3b8);
  }

  .switch-btn {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
    &.on {
      background: #22c55e;
      color: #fff;
    }
    &.off {
      background: rgba(148, 163, 184, 0.2);
      color: #94a3b8;
    }
  }

  .refresh-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 8px;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.25);
    color: #fbbf24;
    font-size: 12px;
    margin-bottom: 16px;
  }
`;

const ConflictsBox = styled.div`
  margin-bottom: 20px;
  padding: 14px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);

  .conflicts-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #f87171;
    margin-bottom: 8px;
  }

  .conflicts-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .conflict-item {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    padding: 6px 10px;
    border-radius: 6px;
    background: rgba(0, 0, 0, 0.15);
  }
`;

const SectionSubGroup = styled.div`
  margin-top: 20px;

  .subgroup-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-color, #f8fafc);
    margin-bottom: 12px;
  }

  .skills-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .skill-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
    font-size: 13px;
    color: var(--text-color, #f8fafc);

    &.pinned-skill {
      border-color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
    }

    &.hidden-skill {
      opacity: 0.5;
      text-decoration: line-through;
    }
  }

  .source-badge {
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    &.badge-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
    &.badge-cyan { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }
    &.badge-purple { background: rgba(168, 85, 247, 0.2); color: #c084fc; }
  }

  .skill-actions {
    display: flex;
    gap: 4px;
    margin-left: 2px;
  }

  .action-btn {
    padding: 2px;
    border-radius: 4px;
    background: transparent;
    border: none;
    color: var(--text-muted, #94a3b8);
    cursor: pointer;
    &:hover { color: var(--text-color, #f8fafc); }
    &.active { color: #38bdf8; }
  }

  .items-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .item-card {
    padding: 12px 14px;
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.15);
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.05));
    font-size: 13px;
    color: var(--text-color, #f8fafc);
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .item-dates {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    margin-bottom: 6px;
  }

  .item-desc {
    font-size: 12px;
    color: var(--text-muted, #cbd5e1);
    line-height: 1.4;
  }

  .item-sub {
    font-size: 12px;
    color: var(--text-muted, #94a3b8);
    margin-top: 2px;
  }

  .languages-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .lang-chip {
    padding: 4px 10px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    font-size: 12px;
    color: var(--text-color, #f8fafc);
  }
`;

const TwoColGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;
