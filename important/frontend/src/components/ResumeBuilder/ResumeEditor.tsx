import React, { useState } from 'react';
import {
  User,
  Briefcase,
  GraduationCap,
  Wrench,
  FolderGit2,
  Globe,
  Plus,
  Trash2,
  Palette,
  Eye,
  EyeOff,
  ArrowUp,
  ArrowDown,
  DownloadCloud,
} from 'lucide-react';
import type {
  StructuredResumeData,
  ResumeSettings,
  ResumeExperienceEntry,
  ResumeEducationEntry,
  ResumeSkillEntry,
  ResumeProjectEntry,
  ResumeLanguageEntry,
} from '../../api/client';
import './ResumeEditor.css';

interface ResumeEditorProps {
  data: StructuredResumeData;
  settings: ResumeSettings;
  onChangeData: (data: StructuredResumeData) => void;
  onChangeSettings: (settings: ResumeSettings) => void;
  onImportProfile: () => void;
}

const PRESET_COLORS = [
  { name: 'Royal Blue', hex: '#2563eb' },
  { name: 'Sky Cyan', hex: '#0284c7' },
  { name: 'Emerald', hex: '#059669' },
  { name: 'Violet', hex: '#7c3aed' },
  { name: 'Rose', hex: '#e11d48' },
  { name: 'Slate', hex: '#334155' },
];

export const ResumeEditor: React.FC<ResumeEditorProps> = ({
  data,
  settings,
  onChangeData,
  onChangeSettings,
  onImportProfile,
}) => {
  const [activeTab, setActiveTab] = useState<
    'settings' | 'profile' | 'experience' | 'education' | 'skills' | 'projects' | 'certifications' | 'languages'
  >('profile');

  // Personal Info helpers
  const handleProfileChange = (field: keyof typeof data.profile, value: string) => {
    onChangeData({
      ...data,
      profile: {
        ...data.profile,
        [field]: value,
      },
    });
  };

  // Experience helpers
  const handleAddExperience = () => {
    const newExp: ResumeExperienceEntry = {
      id: `exp-${Date.now()}`,
      company: '',
      title: '',
      location: '',
      employment_type: 'full_time',
      start_date: '',
      end_date: '',
      is_current: false,
      description: '',
      highlights: [''],
    };
    onChangeData({
      ...data,
      experience: [newExp, ...(data.experience || [])],
    });
  };

  const handleUpdateExperience = (id: string, updates: Partial<ResumeExperienceEntry>) => {
    onChangeData({
      ...data,
      experience: data.experience.map((e) => (e.id === id ? { ...e, ...updates } : e)),
    });
  };

  const handleRemoveExperience = (id: string) => {
    onChangeData({
      ...data,
      experience: data.experience.filter((e) => e.id !== id),
    });
  };

  // Education helpers
  const handleAddEducation = () => {
    const newEdu: ResumeEducationEntry = {
      id: `edu-${Date.now()}`,
      institution: '',
      degree: '',
      field: '',
      location: '',
      start_date: '',
      end_date: '',
      gpa: '',
      description: '',
    };
    onChangeData({
      ...data,
      education: [newEdu, ...(data.education || [])],
    });
  };

  const handleUpdateEducation = (id: string, updates: Partial<ResumeEducationEntry>) => {
    onChangeData({
      ...data,
      education: data.education.map((edu) => (edu.id === id ? { ...edu, ...updates } : edu)),
    });
  };

  const handleRemoveEducation = (id: string) => {
    onChangeData({
      ...data,
      education: data.education.filter((edu) => edu.id !== id),
    });
  };

  // Skills helpers
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory] = useState('Core & Technical');
  const [newSkillProficiency, setNewSkillProficiency] = useState('Intermediate');

  const handleAddSkill = () => {
    if (!newSkillName.trim()) return;
    const newSkill: ResumeSkillEntry = {
      id: `sk-${Date.now()}`,
      name: newSkillName.trim(),
      category: newSkillCategory,
      proficiency: newSkillProficiency,
    };
    onChangeData({
      ...data,
      skills: [...(data.skills || []), newSkill],
    });
    setNewSkillName('');
  };

  const handleRemoveSkill = (id: string) => {
    onChangeData({
      ...data,
      skills: data.skills.filter((s) => s.id !== id),
    });
  };

  // Projects helpers
  const handleAddProject = () => {
    const newProj: ResumeProjectEntry = {
      id: `proj-${Date.now()}`,
      name: '',
      description: '',
      technologies: '',
      url: '',
      start_date: '',
      end_date: '',
    };
    onChangeData({
      ...data,
      projects: [newProj, ...(data.projects || [])],
    });
  };

  const handleUpdateProject = (id: string, updates: Partial<ResumeProjectEntry>) => {
    onChangeData({
      ...data,
      projects: data.projects.map((p) => (p.id === id ? { ...p, ...updates } : p)),
    });
  };

  const handleRemoveProject = (id: string) => {
    onChangeData({
      ...data,
      projects: data.projects.filter((p) => p.id !== id),
    });
  };

  // Languages helpers
  const [newLangName, setNewLangName] = useState('');
  const [newLangProf, setNewLangProf] = useState('Fluent');

  const handleAddLanguage = () => {
    if (!newLangName.trim()) return;
    const newLang: ResumeLanguageEntry = {
      id: `lang-${Date.now()}`,
      language: newLangName.trim(),
      proficiency: newLangProf,
    };
    onChangeData({
      ...data,
      languages: [...(data.languages || []), newLang],
    });
    setNewLangName('');
  };

  const handleRemoveLanguage = (id: string) => {
    onChangeData({
      ...data,
      languages: data.languages.filter((l) => l.id !== id),
    });
  };

  // Settings & Reordering helpers
  const toggleSectionVisibility = (secKey: string) => {
    onChangeSettings({
      ...settings,
      section_visibility: {
        ...settings.section_visibility,
        [secKey]: settings.section_visibility[secKey] === false ? true : false,
      },
    });
  };

  const moveSection = (index: number, direction: 'up' | 'down') => {
    const newOrder = [...settings.section_order];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= newOrder.length) return;
    const temp = newOrder[index];
    newOrder[index] = newOrder[targetIdx];
    newOrder[targetIdx] = temp;
    onChangeSettings({
      ...settings,
      section_order: newOrder,
    });
  };

  return (
    <div className="resume-editor-container">
      {/* Editor Navigation Tabs */}
      <div className="editor-nav-bar">
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <User size={15} />
          <span>Profile</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'experience' ? 'active' : ''}`}
          onClick={() => setActiveTab('experience')}
        >
          <Briefcase size={15} />
          <span>Experience ({data.experience?.length || 0})</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'education' ? 'active' : ''}`}
          onClick={() => setActiveTab('education')}
        >
          <GraduationCap size={15} />
          <span>Education ({data.education?.length || 0})</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          <Wrench size={15} />
          <span>Skills ({data.skills?.length || 0})</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          <FolderGit2 size={15} />
          <span>Projects ({data.projects?.length || 0})</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'languages' ? 'active' : ''}`}
          onClick={() => setActiveTab('languages')}
        >
          <Globe size={15} />
          <span>Languages ({data.languages?.length || 0})</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Palette size={15} />
          <span>Template & Style</span>
        </button>
      </div>

      {/* Editor Tab Content */}
      <div className="editor-tab-body">
        {/* TAB: Personal Profile */}
        {activeTab === 'profile' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Personal Information & Summary</h3>
                <p>Headline and contact information rendered in the header.</p>
              </div>
              <button
                type="button"
                className="import-profile-btn"
                onClick={onImportProfile}
                title="Populate missing fields from your account profile"
              >
                <DownloadCloud size={14} />
                <span>Import Profile Info</span>
              </button>
            </div>

            <div className="form-grid-2">
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="e.g. Amine El Amrani"
                  value={data.profile?.full_name || ''}
                  onChange={(e) => handleProfileChange('full_name', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Professional Headline</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="e.g. Senior Software Architect"
                  value={data.profile?.headline || ''}
                  onChange={(e) => handleProfileChange('headline', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  className="editor-input"
                  placeholder="candidate@example.com"
                  value={data.profile?.email || ''}
                  onChange={(e) => handleProfileChange('email', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Phone Number</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="+212 600-000000"
                  value={data.profile?.phone || ''}
                  onChange={(e) => handleProfileChange('phone', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Location / City</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="Casablanca, Morocco"
                  value={data.profile?.location || ''}
                  onChange={(e) => handleProfileChange('location', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>LinkedIn URL or Handle</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="https://linkedin.com/in/username"
                  value={data.profile?.linkedin || ''}
                  onChange={(e) => handleProfileChange('linkedin', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>GitHub Profile URL</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="https://github.com/username"
                  value={data.profile?.github || ''}
                  onChange={(e) => handleProfileChange('github', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Portfolio / Personal Website</label>
                <input
                  type="text"
                  className="editor-input"
                  placeholder="https://myportfolio.dev"
                  value={data.profile?.website || ''}
                  onChange={(e) => handleProfileChange('website', e.target.value)}
                />
              </div>
            </div>

            <div className="form-group full-width" style={{ marginTop: '16px' }}>
              <label>Professional Summary</label>
              <textarea
                className="editor-textarea"
                rows={4}
                placeholder="A concise, high-impact summary highlighting your qualifications, experience, and value..."
                value={data.profile?.summary || ''}
                onChange={(e) => handleProfileChange('summary', e.target.value)}
              />
            </div>
          </div>
        )}

        {/* TAB: Work Experience */}
        {activeTab === 'experience' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Work Experience & Tenure</h3>
                <p>Add full-time tenure, internships, and relevant roles.</p>
              </div>
              <div className="action-button-group">
                <button
                  type="button"
                  className="import-profile-btn"
                  onClick={onImportProfile}
                  title="Import experiences saved in your Profile"
                >
                  <DownloadCloud size={14} />
                  <span>Import from Profile</span>
                </button>
                <button type="button" className="add-item-btn" onClick={handleAddExperience}>
                  <Plus size={14} />
                  <span>Add Experience</span>
                </button>
              </div>
            </div>

            {(!data.experience || data.experience.length === 0) ? (
              <div className="empty-state-box">
                <Briefcase size={28} className="empty-icon" />
                <p>No work experiences added yet. Click &quot;Add Experience&quot; or import from your profile.</p>
              </div>
            ) : (
              <div className="items-accordion-list">
                {data.experience.map((exp, idx) => (
                  <div key={exp.id} className="item-edit-card">
                    <div className="card-top-bar">
                      <span className="card-index-tag">#{idx + 1}</span>
                      <span className="card-summary-title">
                        {exp.title || 'Untitled Role'} {exp.company ? `@ ${exp.company}` : ''}
                      </span>
                      <button
                        type="button"
                        className="delete-item-icon"
                        onClick={() => handleRemoveExperience(exp.id)}
                        title="Delete entry"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>

                    <div className="form-grid-2">
                      <div className="form-group">
                        <label>Job Title</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Lead Engineer"
                          value={exp.title}
                          onChange={(e) => handleUpdateExperience(exp.id, { title: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Company Name</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Tech Solutions Inc."
                          value={exp.company}
                          onChange={(e) => handleUpdateExperience(exp.id, { company: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Location</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Casablanca / Remote"
                          value={exp.location || ''}
                          onChange={(e) => handleUpdateExperience(exp.id, { location: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Employment Type</label>
                        <select
                          className="editor-select"
                          value={exp.employment_type || 'full_time'}
                          onChange={(e) => handleUpdateExperience(exp.id, { employment_type: e.target.value })}
                        >
                          <option value="full_time">Full-time</option>
                          <option value="internship">Internship</option>
                          <option value="part_time">Part-time</option>
                          <option value="freelance">Contract / Freelance</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Start Date</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="YYYY-MM (e.g. 2021-03)"
                          value={exp.start_date || ''}
                          onChange={(e) => handleUpdateExperience(exp.id, { start_date: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>End Date</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="YYYY-MM or Present"
                          disabled={exp.is_current}
                          value={exp.is_current ? 'Present' : (exp.end_date || '')}
                          onChange={(e) => handleUpdateExperience(exp.id, { end_date: e.target.value })}
                        />
                        <label className="inline-checkbox">
                          <input
                            type="checkbox"
                            checked={exp.is_current || false}
                            onChange={(e) =>
                              handleUpdateExperience(exp.id, {
                                is_current: e.target.checked,
                                end_date: e.target.checked ? 'Present' : '',
                              })
                            }
                          />
                          <span>Currently working here</span>
                        </label>
                      </div>
                    </div>

                    <div className="form-group full-width" style={{ marginTop: '10px' }}>
                      <label>Role Overview / Description</label>
                      <textarea
                        className="editor-textarea"
                        rows={2}
                        placeholder="Brief overview of responsibilities and technical context..."
                        value={exp.description || ''}
                        onChange={(e) => handleUpdateExperience(exp.id, { description: e.target.value })}
                      />
                    </div>

                    {/* Key Highlights / Bullets */}
                    <div className="bullet-points-section">
                      <div className="bullet-head">
                        <label>Accomplishment Bullets</label>
                        <button
                          type="button"
                          className="add-bullet-btn"
                          onClick={() => {
                            const hl = [...(exp.highlights || []), ''];
                            handleUpdateExperience(exp.id, { highlights: hl });
                          }}
                        >
                          <Plus size={12} />
                          <span>Add Bullet</span>
                        </button>
                      </div>
                      {(exp.highlights || []).map((b, bIdx) => (
                        <div key={bIdx} className="bullet-input-row">
                          <span className="bullet-marker">•</span>
                          <input
                            type="text"
                            className="editor-input"
                            placeholder="e.g. Engineered distributed cache reducing latency by 35%..."
                            value={b}
                            onChange={(e) => {
                              const hl = [...(exp.highlights || [])];
                              hl[bIdx] = e.target.value;
                              handleUpdateExperience(exp.id, { highlights: hl });
                            }}
                          />
                          <button
                            type="button"
                            className="remove-bullet-btn"
                            onClick={() => {
                              const hl = (exp.highlights || []).filter((_, i) => i !== bIdx);
                              handleUpdateExperience(exp.id, { highlights: hl });
                            }}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB: Education */}
        {activeTab === 'education' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Education & Academic Background</h3>
                <p>Degrees, universities, diplomas, and academic honors.</p>
              </div>
              <div className="action-button-group">
                <button
                  type="button"
                  className="import-profile-btn"
                  onClick={onImportProfile}
                  title="Import education items from your profile"
                >
                  <DownloadCloud size={14} />
                  <span>Import from Profile</span>
                </button>
                <button type="button" className="add-item-btn" onClick={handleAddEducation}>
                  <Plus size={14} />
                  <span>Add Education</span>
                </button>
              </div>
            </div>

            {(!data.education || data.education.length === 0) ? (
              <div className="empty-state-box">
                <GraduationCap size={28} className="empty-icon" />
                <p>No education records added. Add academic degrees or import from your profile.</p>
              </div>
            ) : (
              <div className="items-accordion-list">
                {data.education.map((edu, idx) => (
                  <div key={edu.id} className="item-edit-card">
                    <div className="card-top-bar">
                      <span className="card-index-tag">#{idx + 1}</span>
                      <span className="card-summary-title">
                        {edu.degree || 'Degree'} in {edu.field || 'Field'} — {edu.institution || 'Institution'}
                      </span>
                      <button
                        type="button"
                        className="delete-item-icon"
                        onClick={() => handleRemoveEducation(edu.id)}
                        title="Delete entry"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>

                    <div className="form-grid-2">
                      <div className="form-group">
                        <label>Degree Level</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Master of Science / Bachelor"
                          value={edu.degree || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { degree: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Field of Study / Major</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Computer Science"
                          value={edu.field || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { field: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>University / Institution</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. ENSEIRB-MATMECA"
                          value={edu.institution || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { institution: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Location</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Casablanca, Morocco"
                          value={edu.location || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { location: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Start Date</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. 2017"
                          value={edu.start_date || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { start_date: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>End Date</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. 2020"
                          value={edu.end_date || ''}
                          onChange={(e) => handleUpdateEducation(edu.id, { end_date: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB: Skills */}
        {activeTab === 'skills' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Technical & Core Skills</h3>
                <p>Curate technologies and proficiencies represented on this resume.</p>
              </div>
              <button
                type="button"
                className="import-profile-btn"
                onClick={onImportProfile}
                title="Import skills saved in your profile"
              >
                <DownloadCloud size={14} />
                <span>Import from Profile</span>
              </button>
            </div>

            {/* Quick Add Bar */}
            <div className="skill-add-bar">
              <input
                type="text"
                className="editor-input"
                placeholder="Skill name (e.g. Python, Docker, FastAPI)..."
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
              />
              <select
                className="editor-select"
                value={newSkillProficiency}
                onChange={(e) => setNewSkillProficiency(e.target.value)}
              >
                <option value="Beginner">Beginner</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Advanced">Advanced</option>
                <option value="Expert">Expert</option>
              </select>
              <button type="button" className="add-btn" onClick={handleAddSkill}>
                <Plus size={15} />
                <span>Add Skill</span>
              </button>
            </div>

            {/* Current Skills Cloud */}
            <div className="skills-cloud-editor">
              {(!data.skills || data.skills.length === 0) ? (
                <p className="empty-subtext">No skills added yet. Add some above or import from your profile.</p>
              ) : (
                data.skills.map((s) => (
                  <div key={s.id} className="skill-edit-pill">
                    <span className="skill-pill-name">{s.name}</span>
                    <span className="skill-pill-level">({s.proficiency})</span>
                    <button
                      type="button"
                      className="remove-pill-btn"
                      onClick={() => handleRemoveSkill(s.id)}
                      title="Remove skill"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB: Projects */}
        {activeTab === 'projects' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Projects & Practical Work</h3>
                <p>Showcase technical initiatives, open-source repositories, or client projects.</p>
              </div>
              <button type="button" className="add-item-btn" onClick={handleAddProject}>
                <Plus size={14} />
                <span>Add Project</span>
              </button>
            </div>

            {(!data.projects || data.projects.length === 0) ? (
              <div className="empty-state-box">
                <FolderGit2 size={28} className="empty-icon" />
                <p>No projects documented. Highlight key engineering achievements here.</p>
              </div>
            ) : (
              <div className="items-accordion-list">
                {data.projects.map((proj, idx) => (
                  <div key={proj.id} className="item-edit-card">
                    <div className="card-top-bar">
                      <span className="card-index-tag">#{idx + 1}</span>
                      <span className="card-summary-title">{proj.name || 'Untitled Project'}</span>
                      <button
                        type="button"
                        className="delete-item-icon"
                        onClick={() => handleRemoveProject(proj.id)}
                        title="Delete project"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>

                    <div className="form-grid-2">
                      <div className="form-group">
                        <label>Project Name</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Distributed Crawler Engine"
                          value={proj.name}
                          onChange={(e) => handleUpdateProject(proj.id, { name: e.target.value })}
                        />
                      </div>

                      <div className="form-group">
                        <label>Technologies Used</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="e.g. Python, Redis, Docker, FastAPI"
                          value={proj.technologies || ''}
                          onChange={(e) => handleUpdateProject(proj.id, { technologies: e.target.value })}
                        />
                      </div>

                      <div className="form-group full-width">
                        <label>Project Link / Repository URL</label>
                        <input
                          type="text"
                          className="editor-input"
                          placeholder="https://github.com/user/project"
                          value={proj.url || ''}
                          onChange={(e) => handleUpdateProject(proj.id, { url: e.target.value })}
                        />
                      </div>

                      <div className="form-group full-width">
                        <label>Description & Outcomes</label>
                        <textarea
                          className="editor-textarea"
                          rows={3}
                          placeholder="Describe the architectural problem, your solution, and measurable results..."
                          value={proj.description || ''}
                          onChange={(e) => handleUpdateProject(proj.id, { description: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB: Languages */}
        {activeTab === 'languages' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Languages</h3>
                <p>Spoken languages and working proficiencies.</p>
              </div>
              <button
                type="button"
                className="import-profile-btn"
                onClick={onImportProfile}
                title="Import languages from profile"
              >
                <DownloadCloud size={14} />
                <span>Import from Profile</span>
              </button>
            </div>

            <div className="skill-add-bar">
              <input
                type="text"
                className="editor-input"
                placeholder="Language (e.g. French, English, Arabic)..."
                value={newLangName}
                onChange={(e) => setNewLangName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddLanguage())}
              />
              <select
                className="editor-select"
                value={newLangProf}
                onChange={(e) => setNewLangProf(e.target.value)}
              >
                <option value="Native">Native / Bilingual</option>
                <option value="Fluent">Fluent</option>
                <option value="Professional">Professional Working</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Basic">Basic</option>
              </select>
              <button type="button" className="add-btn" onClick={handleAddLanguage}>
                <Plus size={15} />
                <span>Add</span>
              </button>
            </div>

            <div className="skills-cloud-editor">
              {(!data.languages || data.languages.length === 0) ? (
                <p className="empty-subtext">No languages added yet.</p>
              ) : (
                data.languages.map((l) => (
                  <div key={l.id} className="skill-edit-pill">
                    <span className="skill-pill-name">{l.language}</span>
                    <span className="skill-pill-level">({l.proficiency})</span>
                    <button
                      type="button"
                      className="remove-pill-btn"
                      onClick={() => handleRemoveLanguage(l.id)}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB: Template & Styling */}
        {activeTab === 'settings' && (
          <div className="editor-section-card">
            <div className="section-head-row">
              <div className="head-title">
                <h3>Template & Document Presentation</h3>
                <p>Select ATS-friendly templates, typography, and section order.</p>
              </div>
            </div>

            {/* Template Chooser */}
            <div className="settings-block">
              <label className="block-label">Choose Resume Template</label>
              <div className="template-grid">
                {[
                  { id: 'modern', name: 'Modern', desc: 'Clean header with accent bar & contemporary layout' },
                  { id: 'classic', name: 'Classic', desc: 'Traditional serif typography with centered header' },
                  { id: 'minimal', name: 'Minimal', desc: 'High whitespace, subtle rules, and concise layout' },
                  { id: 'technical', name: 'Technical', desc: 'High-density format emphasizing technical skills' },
                ].map((t) => (
                  <div
                    key={t.id}
                    className={`template-card ${settings.template === t.id ? 'active' : ''}`}
                    onClick={() => onChangeSettings({ ...settings, template: t.id as any })}
                  >
                    <div className="template-card-header">
                      <span className="template-name">{t.name}</span>
                      {settings.template === t.id && <span className="active-badge">Active</span>}
                    </div>
                    <p className="template-desc">{t.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Accent Color Palette */}
            <div className="settings-block">
              <label className="block-label">Accent Theme Color</label>
              <div className="colors-swatch-row">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c.hex}
                    type="button"
                    className={`color-swatch-btn ${settings.theme_color === c.hex ? 'selected' : ''}`}
                    style={{ backgroundColor: c.hex }}
                    onClick={() => onChangeSettings({ ...settings, theme_color: c.hex })}
                    title={c.name}
                  />
                ))}
                <div className="custom-hex-picker">
                  <span className="hex-prefix">#</span>
                  <input
                    type="text"
                    className="hex-input"
                    value={settings.theme_color.replace('#', '')}
                    onChange={(e) =>
                      onChangeSettings({ ...settings, theme_color: `#${e.target.value.replace(/[^0-9a-fA-F]/g, '').slice(0, 6)}` })
                    }
                  />
                </div>
              </div>
            </div>

            {/* Document Sizing & Typography */}
            <div className="form-grid-2" style={{ marginTop: '16px' }}>
              <div className="form-group">
                <label>Page Size</label>
                <select
                  className="editor-select"
                  value={settings.document_size}
                  onChange={(e) => onChangeSettings({ ...settings, document_size: e.target.value as any })}
                >
                  <option value="A4">A4 (Standard International)</option>
                  <option value="LETTER">US Letter</option>
                </select>
              </div>

              <div className="form-group">
                <label>Base Typography Size</label>
                <select
                  className="editor-select"
                  value={settings.font_size}
                  onChange={(e) => onChangeSettings({ ...settings, font_size: e.target.value })}
                >
                  <option value="9.5">9.5 pt (Compact)</option>
                  <option value="10.0">10.0 pt (Default Standard)</option>
                  <option value="10.5">10.5 pt (Readable)</option>
                  <option value="11.0">11.0 pt (Large)</option>
                </select>
              </div>
            </div>

            {/* Section Ordering & Visibility */}
            <div className="settings-block" style={{ marginTop: '24px' }}>
              <label className="block-label">Section Ordering & Visibility</label>
              <div className="sections-order-list">
                {settings.section_order.map((secKey, idx) => {
                  const isVis = settings.section_visibility[secKey] !== false;
                  const secLabel =
                    secKey === 'summary'
                      ? 'Professional Summary'
                      : secKey === 'experience'
                      ? 'Work Experience'
                      : secKey === 'education'
                      ? 'Education & Academics'
                      : secKey === 'skills'
                      ? 'Technical Skills'
                      : secKey === 'projects'
                      ? 'Projects'
                      : secKey === 'certifications'
                      ? 'Certifications'
                      : secKey === 'languages'
                      ? 'Languages'
                      : secKey;

                  return (
                    <div key={secKey} className={`sec-order-row ${!isVis ? 'disabled' : ''}`}>
                      <span className="sec-order-name">{secLabel}</span>
                      <div className="sec-order-controls">
                        <button
                          type="button"
                          className="control-btn"
                          disabled={idx === 0}
                          onClick={() => moveSection(idx, 'up')}
                          title="Move up"
                        >
                          <ArrowUp size={14} />
                        </button>
                        <button
                          type="button"
                          className="control-btn"
                          disabled={idx === settings.section_order.length - 1}
                          onClick={() => moveSection(idx, 'down')}
                          title="Move down"
                        >
                          <ArrowDown size={14} />
                        </button>
                        <button
                          type="button"
                          className={`control-btn toggle-vis ${isVis ? 'visible' : 'hidden'}`}
                          onClick={() => toggleSectionVisibility(secKey)}
                          title={isVis ? 'Hide section' : 'Show section'}
                        >
                          {isVis ? <Eye size={14} /> : <EyeOff size={14} />}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
