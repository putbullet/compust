import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  User,
  Check,
  Plus,
  X,
  Sparkles,
  Building2,
  MapPin,
  DollarSign,
  Briefcase,
  GraduationCap,
  Languages,
  Trash2,
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Search,
  BrainCircuit,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import type { UserProfile, Country, ResumeItem } from '../api/client';
import { ResumeBuilderView } from './ResumeBuilder/ResumeBuilderView';

interface ProfileViewProps {
  user: UserProfile;
  onUpdate: (updated: UserProfile) => void;
  initialJobTarget?: { role: string; description: string; companyName: string } | null;
  onClearJobTarget?: () => void;
  onNavigateToApplications?: () => void;
  onNavigateToInterviewPrep?: () => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({
  user,
  onUpdate,
  initialJobTarget,
  onClearJobTarget,
  onNavigateToApplications,
  onNavigateToInterviewPrep,
}) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'builder'>('profile');

  useEffect(() => {
    if (initialJobTarget) {
      setActiveTab('builder');
    }
  }, [initialJobTarget]);
  const [preferredWorkMode, setPreferredWorkMode] = useState(
    user.preferences?.preferred_work_mode || 'Hybrid'
  );
  const [preferredLocation, setPreferredLocation] = useState(
    user.preferences?.preferred_location || 'Global / Remote'
  );
  const [minSalary, setMinSalary] = useState(
    user.preferences?.min_salary?.toString() || '18000'
  );
  const [salaryCurrency, setSalaryCurrency] = useState(
    user.preferences?.salary_currency || 'USD'
  );

  const [availableCountries, setAvailableCountries] = useState<Country[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<number[]>(
    (user.country_preferences || []).map((c) => c.id)
  );
  const [countrySearch, setCountrySearch] = useState('');

  useEffect(() => {
    api.getCountries().then(setAvailableCountries).catch(() => {});
    api.getActiveResume().then(setActiveResume).catch(() => setActiveResume(null));
  }, []);

  // Resume state
  const [activeResume, setActiveResume] = useState<ResumeItem | null>(null);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [resumeSuccess, setResumeSuccess] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setResumeError('Only PDF files are supported.');
      return;
    }
    try {
      setUploadingResume(true);
      setResumeError(null);
      setResumeSuccess(null);
      const res = await api.uploadResume(file);
      setActiveResume(res);
      setResumeSuccess(`Resume "${file.name}" successfully parsed and structured.`);
      setTimeout(() => setResumeSuccess(null), 4000);
    } catch (err: any) {
      setResumeError(err.message || 'Failed to parse resume.');
    } finally {
      setUploadingResume(false);
      e.target.value = '';
    }
  };

  const handleDeleteResume = async () => {
    if (!activeResume) return;
    if (!window.confirm('Delete your active resume?')) return;
    try {
      await api.deleteResume(activeResume.id);
      setActiveResume(null);
      setResumeSuccess('Resume removed.');
      setTimeout(() => setResumeSuccess(null), 3000);
    } catch (err: any) {
      setResumeError(err.message || 'Failed to delete resume.');
    }
  };

  const toggleCountry = async (countryId: number) => {
    const next = selectedCountries.includes(countryId)
      ? selectedCountries.filter((id) => id !== countryId)
      : [...selectedCountries, countryId];
    setSelectedCountries(next);
    try {
      const updated = await api.updateCountryPreferences(next);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to update country preferences');
    }
  };

  const [skills, setSkills] = useState<string[]>(user.skills || []);
  const [newSkill, setNewSkill] = useState('');
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Experience form state
  const [showExpForm, setShowExpForm] = useState(false);
  const [expTitle, setExpTitle] = useState('');
  const [expCompany, setExpCompany] = useState('');
  const [expType, setExpType] = useState('professional');
  const [expStartDate, setExpStartDate] = useState('');
  const [expEndDate, setExpEndDate] = useState('');
  const [expDesc, setExpDesc] = useState('');

  // Education form state
  const [showEduForm, setShowEduForm] = useState(false);
  const [eduInstitution, setEduInstitution] = useState('');
  const [eduDegree, setEduDegree] = useState('');
  const [eduField, setEduField] = useState('');
  const [eduStartDate, setEduStartDate] = useState('');
  const [eduEndDate, setEduEndDate] = useState('');

  // Language form state
  const [showLangForm, setShowLangForm] = useState(false);
  const [langName, setLangName] = useState('');
  const [langProficiency, setLangProficiency] = useState('fluent');

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);

    try {
      const updated = await api.updatePreferences({
        preferred_work_mode: preferredWorkMode,
        preferred_location: preferredLocation,
        min_salary: minSalary ? parseFloat(minSalary) : null,
        salary_currency: salaryCurrency,
      });
      onUpdate(updated);
      setSuccessMsg('Preferences saved! Job match percentages are updated.');
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err: any) {
      alert(err.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleAddSkill = async () => {
    if (!newSkill.trim()) return;
    const updatedSkills = [...skills, newSkill.trim()];
    setSkills(updatedSkills);
    setNewSkill('');

    try {
      const updated = await api.updateSkills(updatedSkills);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to update skills');
    }
  };

  const handleRemoveSkill = async (skillToRemove: string) => {
    const updatedSkills = skills.filter((s) => s !== skillToRemove);
    setSkills(updatedSkills);

    try {
      const updated = await api.updateSkills(updatedSkills);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to update skills');
    }
  };

  const handleAddExperience = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expTitle.trim() || !expCompany.trim()) return;
    try {
      const updated = await api.addExperience({
        title: expTitle.trim(),
        company_name: expCompany.trim(),
        experience_type: expType,
        start_date: expStartDate || null,
        end_date: expEndDate || null,
        description: expDesc.trim() || null,
      });
      onUpdate(updated);
      setExpTitle('');
      setExpCompany('');
      setExpDesc('');
      setExpStartDate('');
      setExpEndDate('');
      setShowExpForm(false);
    } catch (err: any) {
      alert(err.message || 'Failed to add experience');
    }
  };

  const handleDeleteExperience = async (id: number) => {
    try {
      const updated = await api.deleteExperience(id);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to remove experience');
    }
  };

  const handleAddEducation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eduInstitution.trim()) return;
    try {
      const updated = await api.addEducation({
        institution: eduInstitution.trim(),
        degree: eduDegree.trim() || null,
        field_of_study: eduField.trim() || null,
        start_date: eduStartDate || null,
        end_date: eduEndDate || null,
      });
      onUpdate(updated);
      setEduInstitution('');
      setEduDegree('');
      setEduField('');
      setEduStartDate('');
      setEduEndDate('');
      setShowEduForm(false);
    } catch (err: any) {
      alert(err.message || 'Failed to add education');
    }
  };

  const handleDeleteEducation = async (id: number) => {
    try {
      const updated = await api.deleteEducation(id);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to remove education');
    }
  };

  const handleAddLanguage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!langName.trim()) return;
    try {
      const updated = await api.addLanguage({
        language: langName.trim(),
        proficiency: langProficiency,
      });
      onUpdate(updated);
      setLangName('');
      setShowLangForm(false);
    } catch (err: any) {
      alert(err.message || 'Failed to add language');
    }
  };

  const handleDeleteLanguage = async (id: number) => {
    try {
      const updated = await api.deleteLanguage(id);
      onUpdate(updated);
    } catch (err: any) {
      alert('Failed to remove language');
    }
  };

  const getExperienceBadgeClass = (type: string | null) => {
    switch (type) {
      case 'professional':
        return 'badge-blue';
      case 'internship':
        return 'badge-amber';
      case 'project':
        return 'badge-purple';
      case 'transferable':
        return 'badge-emerald';
      default:
        return 'badge-blue';
    }
  };

  const experiences = user.experience || [];
  const educations = user.education || [];
  const languages = user.languages || [];

  return (
    <StyledProfileContainer $isBuilder={activeTab === 'builder'}>
      {/* User Hero Card */}
      <div className="user-hero-card glass-panel">
        <div className="avatar-ring">
          <User size={44} className="avatar-icon" />
        </div>
        <div className="user-meta">
          <div className="name-line">
            <h2>{user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.email}</h2>
            <span className="badge badge-emerald">Active Seeker</span>
          </div>
          <p className="email">{user.email}</p>
          <div className="status-chips">
            <span className="chip">
              <MapPin size={13} />
              <span>{preferredLocation || 'Worldwide / Remote'}</span>
            </span>
            <span className="chip">
              <Building2 size={13} />
              <span>{preferredWorkMode || 'Flexible'}</span>
            </span>
            <span className="chip">
              <Briefcase size={13} />
              <span>{experiences.length} Experience(s)</span>
            </span>
            <span className="chip">
              <Languages size={13} />
              <span>{languages.length} Language(s)</span>
            </span>
          </div>
        </div>
      </div>

      {successMsg && <div className="success-banner">{successMsg}</div>}

      {/* Tab Navigation */}
      <div className="profile-tab-bar glass-panel">
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <User size={16} />
          <span>Profile & Career Data</span>
        </button>
        <button
          type="button"
          className={`profile-tab-btn ${activeTab === 'builder' ? 'active' : ''}`}
          onClick={() => setActiveTab('builder')}
        >
          <Sparkles size={16} />
          <span>Resume Builder Studio</span>
          <span className="studio-pill">Interactive</span>
        </button>
        {onNavigateToInterviewPrep && (
          <button
            type="button"
            className="profile-tab-btn interview-prep-nav-tab"
            onClick={onNavigateToInterviewPrep}
            title="Prepare for technical and behavioral interviews"
          >
            <BrainCircuit size={16} />
            <span>Interview Prep</span>
            <span className="prep-pill">Knowledge Center</span>
          </button>
        )}
      </div>

      {activeTab === 'builder' ? (
        <ResumeBuilderView
          currentUser={user}
          initialJobTarget={initialJobTarget}
          onClearJobTarget={onClearJobTarget}
          onNavigateToApplications={onNavigateToApplications}
        />
      ) : (
        <>
          {/* Interview Preparation Entry Banner */}
          <div className="interview-prep-banner glass-panel">
            <div className="prep-banner-main">
              <div className="prep-banner-badge">
                <BrainCircuit size={22} />
              </div>
              <div className="prep-banner-content">
                <div className="prep-banner-heading">
                  <h3>Interview Preparation Knowledge Center</h3>
                  <span className="prep-lang-badge">Multilingual: EN • FR • DE</span>
                </div>
                <p>
                  Prepare for technical engineering rounds and behavioral HR assessments using the STAR method, structured answer frameworks, and domain-specific knowledge banks.
                </p>
              </div>
            </div>
            {onNavigateToInterviewPrep && (
              <button
                type="button"
                className="open-prep-cta-btn"
                onClick={onNavigateToInterviewPrep}
              >
                <span>Open Interview Prep</span>
                <ArrowRight size={16} />
              </button>
            )}
          </div>

          <div className="profile-grid">
        {/* Match Preferences Column */}
        <div className="card-box glass-panel">
          <div className="card-title-row">
            <Sparkles size={18} className="icon-highlight" />
            <h3>Matching Parameters</h3>
          </div>
          <p className="section-desc">
            Define your preferences to calibrate rule-based match scores across scraped jobs.
          </p>

          <form onSubmit={handleSavePreferences} className="pref-form">
            <div className="field-group">
              <label>Preferred Work Mode</label>
              <div className="toggle-group">
                {['Remote', 'Hybrid', 'On-site'].map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    className={`toggle-btn ${preferredWorkMode === mode ? 'active' : ''}`}
                    onClick={() => setPreferredWorkMode(mode)}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <div className="field-group">
              <div className="label-with-count">
                <label>Target Countries ({selectedCountries.length} selected)</label>
                {selectedCountries.length > 0 && (
                  <button
                    type="button"
                    className="text-link-btn"
                    onClick={async () => {
                      setSelectedCountries([]);
                      try {
                        const updated = await api.updateCountryPreferences([]);
                        onUpdate(updated);
                      } catch {}
                    }}
                  >
                    Clear All
                  </button>
                )}
              </div>
              <div className="country-search-box">
                <Search size={13} className="c-search-icon" />
                <input
                  type="text"
                  placeholder="Filter countries (e.g. Germany, UAE)..."
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  className="country-search-input"
                />
              </div>
              <div className="country-chips-container">
                {availableCountries
                  .filter(
                    (c) =>
                      !countrySearch ||
                      c.name.toLowerCase().includes(countrySearch.toLowerCase()) ||
                      c.code.toLowerCase().includes(countrySearch.toLowerCase())
                  )
                  .map((c) => {
                    const isSelected = selectedCountries.includes(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        className={`country-chip ${isSelected ? 'active' : ''}`}
                        onClick={() => toggleCountry(c.id)}
                      >
                        <span className="c-code">{c.code}</span>
                        <span className="c-name">{c.name}</span>
                        {isSelected && <Check size={12} className="c-check" />}
                      </button>
                    );
                  })}
              </div>
            </div>

            <div className="field-group">
              <label>Preferred City / Location</label>
              <input
                type="text"
                className="text-input"
                placeholder="e.g. Casablanca, Rabat, Paris"
                value={preferredLocation}
                onChange={(e) => setPreferredLocation(e.target.value)}
              />
            </div>

            <div className="salary-row">
              <div className="field-group" style={{ flex: 2 }}>
                <label>Minimum Expected Salary</label>
                <div className="salary-input-wrapper">
                  <DollarSign size={16} className="sal-icon" />
                  <input
                    type="number"
                    className="text-input with-icon"
                    placeholder="18000"
                    value={minSalary}
                    onChange={(e) => setMinSalary(e.target.value)}
                  />
                </div>
              </div>

              <div className="field-group" style={{ flex: 1 }}>
                <label>Currency</label>
                <select
                  className="select-input"
                  value={salaryCurrency}
                  onChange={(e) => setSalaryCurrency(e.target.value)}
                >
                  <option value="MAD">MAD</option>
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                </select>
              </div>
            </div>

            <button type="submit" className="save-btn" disabled={saving}>
              <Check size={16} />
              <span>{saving ? 'Saving...' : 'Save Preferences'}</span>
            </button>
          </form>
        </div>

        {/* Skills Management Column */}
        <div className="card-box glass-panel">
          <div className="card-title-row">
            <User size={18} className="icon-highlight" />
            <h3>Your Skill Profile</h3>
          </div>
          <p className="section-desc">
            Add core technologies to match against vacancy skill tags and calculate match scores.
          </p>

          <div className="add-skill-bar">
            <input
              type="text"
              placeholder="Add skill (e.g. Python, Docker, Spring, React)..."
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
              className="text-input"
            />
            <button type="button" onClick={handleAddSkill} className="add-btn">
              <Plus size={16} />
              <span>Add</span>
            </button>
          </div>

          <div className="skills-cloud">
            {skills.length === 0 ? (
              <p className="empty-skills">No skills added yet. Add a few above to improve match precision.</p>
            ) : (
              skills.map((skill) => (
                <div key={skill} className="skill-pill">
                  <span>{skill}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="remove-icon"
                  >
                    <X size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Resume Intelligence & Structuring Card */}
      <div className="card-box glass-panel full-width">
        <div className="section-header-row">
          <div className="card-title-row">
            <FileText size={20} className="icon-highlight" />
            <div>
              <h3>Resume Intelligence (Text-based PDF)</h3>
              <p className="section-desc">
                Upload your resume to power instant tailored match suggestions. Zero OCR is used; text layers are extracted and structured deterministically.
              </p>
            </div>
          </div>
          <div className="resume-header-actions">
            <button
              type="button"
              className="studio-shortcut-btn"
              onClick={() => setActiveTab('builder')}
            >
              <Sparkles size={15} />
              <span>Open in Resume Studio</span>
            </button>
            <label className="upload-resume-btn">
              <UploadCloud size={16} />
              <span>{uploadingResume ? 'Parsing PDF...' : activeResume ? 'Upload New PDF' : 'Upload Resume'}</span>
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileUpload}
                disabled={uploadingResume}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>

        {resumeError && (
          <div className="resume-alert error">
            <AlertCircle size={16} />
            <span>{resumeError}</span>
          </div>
        )}

        {resumeSuccess && (
          <div className="resume-alert success">
            <CheckCircle2 size={16} />
            <span>{resumeSuccess}</span>
          </div>
        )}

        {activeResume ? (
          <div className="active-resume-card">
            <div className="resume-top">
              <div className="resume-file-info">
                <FileText size={28} className="pdf-icon" />
                <div>
                  <div className="resume-filename">{activeResume.filename}</div>
                  <div className="resume-date">
                    Uploaded on {new Date(activeResume.created_at).toLocaleDateString()} · Active for AI Customization
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="delete-resume-btn"
                onClick={handleDeleteResume}
                title="Delete resume"
              >
                <Trash2 size={16} />
                <span>Remove</span>
              </button>
            </div>

            {/* Structured Sections Overview */}
            <div className="structured-sections-box">
              <div className="sections-title">Structured Sections Detected:</div>
              <div className="sections-tags">
                <span className={`sec-pill ${activeResume.parsed_sections?.summary || (activeResume as any).structured_data?.profile?.summary ? 'present' : 'missing'}`}>
                  Summary {activeResume.parsed_sections?.summary || (activeResume as any).structured_data?.profile?.summary ? '✓' : '—'}
                </span>
                <span className={`sec-pill ${activeResume.parsed_sections?.experience || (activeResume as any).structured_data?.experience?.length ? 'present' : 'missing'}`}>
                  Experience {activeResume.parsed_sections?.experience || (activeResume as any).structured_data?.experience?.length ? '✓' : '—'}
                </span>
                <span className={`sec-pill ${activeResume.parsed_sections?.education || (activeResume as any).structured_data?.education?.length ? 'present' : 'missing'}`}>
                  Education {activeResume.parsed_sections?.education || (activeResume as any).structured_data?.education?.length ? '✓' : '—'}
                </span>
                <span className={`sec-pill ${(activeResume.parsed_sections?.skills?.length || (activeResume as any).structured_data?.skills?.length) ? 'present' : 'missing'}`}>
                  Skills ({activeResume.parsed_sections?.skills?.length ?? (activeResume as any).structured_data?.skills?.length ?? 0}) {(activeResume.parsed_sections?.skills?.length || (activeResume as any).structured_data?.skills?.length) ? '✓' : '—'}
                </span>
                <span className={`sec-pill ${activeResume.parsed_sections?.projects || (activeResume as any).structured_data?.projects?.length ? 'present' : 'missing'}`}>
                  Projects {activeResume.parsed_sections?.projects || (activeResume as any).structured_data?.projects?.length ? '✓' : '—'}
                </span>
                <span className={`sec-pill ${(activeResume.parsed_sections?.languages?.length || (activeResume as any).structured_data?.languages?.length) ? 'present' : 'missing'}`}>
                  Languages ({activeResume.parsed_sections?.languages?.length ?? (activeResume as any).structured_data?.languages?.length ?? 0}) {(activeResume.parsed_sections?.languages?.length || (activeResume as any).structured_data?.languages?.length) ? '✓' : '—'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="no-resume-box">
            <UploadCloud size={32} className="no-resume-icon" />
            <p>No active resume uploaded. Upload a text-based PDF to receive AI-assisted vacancy tailoring suggestions.</p>
          </div>
        )}
      </div>

      {/* Experience Section */}
      <div className="card-box glass-panel full-width">
        <div className="section-header-row">
          <div className="card-title-row">
            <Briefcase size={20} className="icon-highlight" />
            <div>
              <h3>Work Experience</h3>
              <p className="section-desc">
                Distinguishes full-time professional tenure from internships, projects, and transferable skills.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="add-section-btn"
            onClick={() => setShowExpForm(!showExpForm)}
          >
            <Plus size={16} />
            <span>{showExpForm ? 'Cancel' : 'Add Experience'}</span>
          </button>
        </div>

        {showExpForm && (
          <form onSubmit={handleAddExperience} className="inline-add-form">
            <div className="form-row">
              <div className="field-group">
                <label>Job Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Senior Software Engineer"
                  value={expTitle}
                  onChange={(e) => setExpTitle(e.target.value)}
                  className="text-input"
                />
              </div>
              <div className="field-group">
                <label>Company / Organization *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Capgemini, Inwi, OCP"
                  value={expCompany}
                  onChange={(e) => setExpCompany(e.target.value)}
                  className="text-input"
                />
              </div>
              <div className="field-group">
                <label>Experience Type</label>
                <select
                  value={expType}
                  onChange={(e) => setExpType(e.target.value)}
                  className="select-input"
                >
                  <option value="professional">Professional (Full-time)</option>
                  <option value="internship">Internship (Stage)</option>
                  <option value="project">Project / Portfolio</option>
                  <option value="transferable">Transferable Experience</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="field-group">
                <label>Start Date</label>
                <input
                  type="date"
                  value={expStartDate}
                  onChange={(e) => setExpStartDate(e.target.value)}
                  className="text-input"
                />
              </div>
              <div className="field-group">
                <label>End Date (Leave blank if present)</label>
                <input
                  type="date"
                  value={expEndDate}
                  onChange={(e) => setExpEndDate(e.target.value)}
                  className="text-input"
                />
              </div>
            </div>
            <div className="field-group">
              <label>Role Description</label>
              <textarea
                placeholder="Key responsibilities and achievements..."
                value={expDesc}
                onChange={(e) => setExpDesc(e.target.value)}
                className="text-input"
                rows={2}
              />
            </div>
            <button type="submit" className="save-btn" style={{ width: '200px' }}>
              <Check size={16} />
              <span>Save Entry</span>
            </button>
          </form>
        )}

        <div className="entries-list">
          {experiences.length === 0 ? (
            <p className="empty-state">No experience records yet. Add your past roles to calibrate career seniority matching.</p>
          ) : (
            experiences.map((exp) => (
              <div key={exp.id} className="entry-card">
                <div className="entry-header">
                  <div>
                    <div className="entry-title-row">
                      <span className="entry-title">{exp.title}</span>
                      <span className={`type-tag ${getExperienceBadgeClass(exp.experience_type)}`}>
                        {exp.experience_type || 'professional'}
                      </span>
                    </div>
                    <span className="entry-sub">{exp.company_name}</span>
                    <span className="entry-dates">
                      {exp.start_date || 'N/A'} — {exp.end_date || 'Present'}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteExperience(exp.id)}
                    className="delete-entry-btn"
                    title="Delete entry"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                {exp.description && <p className="entry-desc">{exp.description}</p>}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Education & Languages Row */}
      <div className="profile-grid">
        {/* Education Box */}
        <div className="card-box glass-panel">
          <div className="section-header-row">
            <div className="card-title-row">
              <GraduationCap size={18} className="icon-highlight" />
              <h3>Education</h3>
            </div>
            <button
              type="button"
              className="add-section-btn small"
              onClick={() => setShowEduForm(!showEduForm)}
            >
              <Plus size={14} />
              <span>{showEduForm ? 'Cancel' : 'Add'}</span>
            </button>
          </div>

          {showEduForm && (
            <form onSubmit={handleAddEducation} className="inline-add-form">
              <div className="field-group">
                <label>Institution *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. EMI, ENSIAS, Hassan II"
                  value={eduInstitution}
                  onChange={(e) => setEduInstitution(e.target.value)}
                  className="text-input"
                />
              </div>
              <div className="form-row">
                <div className="field-group">
                  <label>Degree</label>
                  <input
                    type="text"
                    placeholder="Master, Engineer, Bachelor"
                    value={eduDegree}
                    onChange={(e) => setEduDegree(e.target.value)}
                    className="text-input"
                  />
                </div>
                <div className="field-group">
                  <label>Field of Study</label>
                  <input
                    type="text"
                    placeholder="e.g. Computer Science"
                    value={eduField}
                    onChange={(e) => setEduField(e.target.value)}
                    className="text-input"
                  />
                </div>
              </div>
              <button type="submit" className="save-btn">
                <Check size={14} />
                <span>Save Education</span>
              </button>
            </form>
          )}

          <div className="entries-list">
            {educations.length === 0 ? (
              <p className="empty-state">No education listed yet.</p>
            ) : (
              educations.map((edu) => (
                <div key={edu.id} className="entry-card compact">
                  <div className="entry-header">
                    <div>
                      <span className="entry-title">{edu.degree ? `${edu.degree} in ` : ''}{edu.field_of_study || 'General Studies'}</span>
                      <span className="entry-sub">{edu.institution}</span>
                      {(edu.start_date || edu.end_date) && (
                        <span className="entry-dates">
                          {edu.start_date || ''} — {edu.end_date || 'Present'}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteEducation(edu.id)}
                      className="delete-entry-btn"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Languages Box */}
        <div className="card-box glass-panel">
          <div className="section-header-row">
            <div className="card-title-row">
              <Languages size={18} className="icon-highlight" />
              <h3>Languages</h3>
            </div>
            <button
              type="button"
              className="add-section-btn small"
              onClick={() => setShowLangForm(!showLangForm)}
            >
              <Plus size={14} />
              <span>{showLangForm ? 'Cancel' : 'Add'}</span>
            </button>
          </div>

          {showLangForm && (
            <form onSubmit={handleAddLanguage} className="inline-add-form">
              <div className="form-row">
                <div className="field-group" style={{ flex: 2 }}>
                  <label>Language *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. French, English, Arabic"
                    value={langName}
                    onChange={(e) => setLangName(e.target.value)}
                    className="text-input"
                  />
                </div>
                <div className="field-group" style={{ flex: 2 }}>
                  <label>Proficiency</label>
                  <select
                    value={langProficiency}
                    onChange={(e) => setLangProficiency(e.target.value)}
                    className="select-input"
                  >
                    <option value="native">Native / Bilingual</option>
                    <option value="fluent">Fluent (Professional)</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="basic">Basic (Elementary)</option>
                  </select>
                </div>
              </div>
              <button type="submit" className="save-btn">
                <Check size={14} />
                <span>Save Language</span>
              </button>
            </form>
          )}

          <div className="entries-list">
            {languages.length === 0 ? (
              <p className="empty-state">No languages recorded. Add languages to qualify for multilingual postings.</p>
            ) : (
              languages.map((l) => (
                <div key={l.id} className="entry-card compact language-card">
                  <div className="entry-header">
                    <div className="lang-info">
                      <span className="entry-title capitalize">{l.language}</span>
                      <span className="lang-prof-badge">{l.proficiency || 'fluent'}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteLanguage(l.id)}
                      className="delete-entry-btn"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        </div>
        </>
      )}
    </StyledProfileContainer>
  );
};

const StyledProfileContainer = styled.div<{ $isBuilder?: boolean }>`
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: ${(props) => (props.$isBuilder ? '1520px' : '960px')};
  margin: 0 auto;
  transition: max-width 0.3s ease;

  .profile-tab-bar {
    display: flex;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 14px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .profile-tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 10px;
    background: transparent;
    border: 1px solid transparent;
    color: #94a3b8;
    font-size: 0.92rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      color: #f1f5f9;
      background: rgba(255, 255, 255, 0.04);
    }

    &.active {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
      border-color: rgba(99, 102, 241, 0.4);
      color: #ffffff;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }
  }

  .studio-pill {
    padding: 2px 8px;
    border-radius: 999px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .prep-pill {
    padding: 2px 8px;
    border-radius: 999px;
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.3px;
  }

  .interview-prep-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 20px 24px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 27, 75, 0.6) 100%);
    border: 1px solid rgba(139, 92, 246, 0.25);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: flex-start;
    }
  }

  .prep-banner-main {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }

  .prep-banner-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25));
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: #c084fc;
    flex-shrink: 0;
  }

  .prep-banner-content {
    display: flex;
    flex-direction: column;
    gap: 4px;

    p {
      margin: 0;
      font-size: 0.88rem;
      color: #94a3b8;
      line-height: 1.5;
      max-width: 680px;
    }
  }

  .prep-banner-heading {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;

    h3 {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 700;
      color: #ffffff;
    }
  }

  .prep-lang-badge {
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(139, 92, 246, 0.18);
    border: 1px solid rgba(139, 92, 246, 0.35);
    color: #d8b4fe;
    font-size: 0.72rem;
    font-weight: 600;
  }

  .open-prep-cta-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 10px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    color: #ffffff;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
      background: linear-gradient(135deg, #4f46e5, #7c3aed);
    }
  }

  .studio-shortcut-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 9px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.25));
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: #c084fc;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.4));
      color: #ffffff;
      border-color: rgba(139, 92, 246, 0.6);
      transform: translateY(-1px);
    }
  }

  .user-hero-card {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 28px;
  }

  .avatar-ring {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: #ffffff;
    box-shadow: 0 0 24px rgba(59, 130, 246, 0.4);
    flex-shrink: 0;
  }

  .user-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .name-line {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 { font-size: 1.5rem; }
  }

  .email {
    font-size: 0.9rem;
    color: #94a3b8;
  }

  .status-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
    font-size: 0.78rem;
    color: #cbd5e1;
  }

  .success-banner {
    padding: 12px 18px;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 12px;
    color: #34d399;
    font-size: 0.88rem;
    font-weight: 500;
  }

  .profile-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
    gap: 24px;
  }

  .card-box {
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;

    &.full-width {
      width: 100%;
    }
  }

  .section-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .card-title-row {
    display: flex;
    align-items: center;
    gap: 10px;

    h3 { font-size: 1.2rem; }
    .icon-highlight { color: #60a5fa; }
  }

  .section-desc {
    font-size: 0.84rem;
    color: #94a3b8;
    line-height: 1.5;
  }

  .add-section-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 8px;
    color: #60a5fa;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #2563eb;
      color: #ffffff;
    }

    &.small {
      padding: 6px 10px;
      font-size: 0.78rem;
    }
  }

  .inline-add-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-bottom: 8px;
  }

  .form-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;

    .field-group {
      flex: 1;
      min-width: 180px;
    }
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 6px;

    label {
      font-size: 0.8rem;
      font-weight: 600;
      color: #cbd5e1;
    }
  }

  .label-with-count {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .text-link-btn {
      background: none;
      border: none;
      color: #60a5fa;
      font-size: 0.75rem;
      cursor: pointer;
      padding: 0;
      &:hover {
        text-decoration: underline;
      }
    }
  }

  .country-search-box {
    position: relative;
    display: flex;
    align-items: center;
    margin-bottom: 6px;

    .c-search-icon {
      position: absolute;
      left: 10px;
      color: #64748b;
      pointer-events: none;
    }

    .country-search-input {
      width: 100%;
      padding: 6px 12px 6px 30px;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      color: #ffffff;
      font-size: 0.8rem;
      outline: none;

      &:focus {
        border-color: #3b82f6;
      }
    }
  }

  .country-chips-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    max-height: 180px;
    overflow-y: auto;
    padding: 6px;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
  }

  .country-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    font-size: 0.78rem;
    font-weight: 500;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    flex: 0 0 auto;

    .c-code {
      font-size: 0.7rem;
      font-weight: 700;
      opacity: 0.6;
    }

    .c-check {
      color: #ffffff;
    }

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.15);
    }

    &.active {
      background: #2563eb;
      color: #ffffff;
      border-color: #3b82f6;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);

      .c-code {
        opacity: 0.9;
      }
    }
  }

  .toggle-group {
    display: flex;
    gap: 8px;

    &.wrap {
      flex-wrap: wrap;

      .toggle-btn {
        flex: 0 0 auto;
      }
    }
  }

  .toggle-btn {
    flex: 1;
    padding: 8px 12px;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #94a3b8;
    font-size: 0.82rem;
    font-weight: 600;
    transition: all 0.2s;

    &.active {
      background: #2563eb;
      color: #ffffff;
      border-color: #3b82f6;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
    }
  }

  .text-input {
    width: 100%;
    padding: 10px 14px;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #f8fafc;
    font-size: 0.9rem;
    outline: none;

    &:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
    }
  }

  .salary-row {
    display: flex;
    gap: 12px;
  }

  .salary-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;

    .sal-icon {
      position: absolute;
      left: 12px;
      color: #64748b;
    }

    .with-icon {
      padding-left: 36px;
    }
  }

  .select-input {
    width: 100%;
    padding: 10px;
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #f8fafc;
    font-size: 0.9rem;
    outline: none;

    option { background: #0f172a; }
  }

  .save-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 16px;
    background: #2563eb;
    color: #ffffff;
    font-weight: 600;
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    transition: all 0.2s;
    cursor: pointer;

    &:hover:not(:disabled) {
      background: #1d4ed8;
      transform: translateY(-1px);
    }
  }

  .add-skill-bar {
    display: flex;
    gap: 8px;
  }

  .add-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 18px;
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 10px;
    color: #60a5fa;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.2s;

    &:hover {
      background: #2563eb;
      color: #ffffff;
    }
  }

  .skills-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 120px;
    padding: 14px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 12px;
    border: 1px dashed rgba(255, 255, 255, 0.08);
  }

  .skill-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 16px;
    color: #93c5fd;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .remove-icon {
    display: flex;
    color: #94a3b8;
    cursor: pointer;

    &:hover { color: #f43f5e; }
  }

  .entries-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .entry-card {
    padding: 16px;
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;

    &.compact {
      padding: 12px 16px;
    }
  }

  .entry-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .entry-title-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .entry-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f8fafc;

    &.capitalize {
      text-transform: capitalize;
    }
  }

  .entry-sub {
    display: block;
    font-size: 0.85rem;
    color: #94a3b8;
  }

  .entry-dates {
    display: block;
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 2px;
  }

  .entry-desc {
    font-size: 0.82rem;
    color: #cbd5e1;
    line-height: 1.4;
    margin-top: 4px;
  }

  .type-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;

    &.badge-blue {
      background: rgba(59, 130, 246, 0.2);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    &.badge-amber {
      background: rgba(245, 158, 11, 0.2);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    &.badge-purple {
      background: rgba(168, 85, 247, 0.2);
      color: #d8b4fe;
      border: 1px solid rgba(168, 85, 247, 0.3);
    }
    &.badge-emerald {
      background: rgba(16, 185, 129, 0.2);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
  }

  .lang-info {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .lang-prof-badge {
    padding: 3px 8px;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 6px;
    font-size: 0.74rem;
    color: #a5b4fc;
    text-transform: capitalize;
  }

  .delete-entry-btn {
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    transition: all 0.2s;

    &:hover {
      color: #f43f5e;
      background: rgba(244, 63, 94, 0.1);
    }
  }

  .empty-state, .empty-skills {
    font-size: 0.85rem;
    color: #64748b;
    text-align: center;
    padding: 12px;
  }

  /* Resume Section Styles */
  .upload-resume-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.8rem;
    font-weight: 600;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
    }
  }

  .resume-alert {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 0.82rem;
    margin: 12px 0;

    &.error {
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid rgba(244, 63, 94, 0.3);
      color: #fda4af;
    }

    &.success {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #6ee7b7;
    }
  }

  .active-resume-card {
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px;
    margin-top: 14px;
  }

  .resume-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }

  .resume-file-info {
    display: flex;
    align-items: center;
    gap: 12px;

    .pdf-icon {
      color: #ef4444;
    }

    .resume-filename {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f8fafc;
    }

    .resume-date {
      font-size: 0.75rem;
      color: #94a3b8;
      margin-top: 2px;
    }
  }

  .delete-resume-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(244, 63, 94, 0.1);
    border: 1px solid rgba(244, 63, 94, 0.25);
    color: #f43f5e;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(244, 63, 94, 0.2);
    }
  }

  .structured-sections-box {
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding-top: 12px;

    .sections-title {
      font-size: 0.75rem;
      font-weight: 600;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }

    .sections-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .sec-pill {
      padding: 3px 9px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 500;

      &.present {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #6ee7b7;
      }

      &.missing {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: #64748b;
      }
    }
  }

  .no-resume-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(0, 0, 0, 0.15);
    border: 1px dashed rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-top: 14px;
    text-align: center;

    .no-resume-icon {
      color: #64748b;
      margin-bottom: 8px;
    }

    p {
      margin: 0;
      font-size: 0.82rem;
      color: #94a3b8;
      max-width: 480px;
    }
  }

  @media (max-width: 640px) {
    .user-hero-card {
      flex-direction: column;
      align-items: flex-start;
      padding: 20px;
      gap: 16px;
    }

    .card-box {
      padding: 20px 16px;
    }

    .profile-tab-bar {
      flex-direction: column;
      gap: 6px;
    }

    .section-header-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .resume-header-actions {
      flex-direction: column;
      width: 100%;
      align-items: stretch;
      gap: 8px;

      button, label {
        width: 100%;
        justify-content: center;
      }
    }
  }
`;
