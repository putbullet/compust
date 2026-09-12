import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Plus,
  Copy,
  Star,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import type { StructuredResumeItem, StructuredResumeData, ResumeSettings, UserProfile } from '../../api/client';
import { api } from '../../api/client';
import { ResumeEditor } from './ResumeEditor';
import { ResumePreview } from './ResumePreview';
import './ResumeBuilderView.css';

interface ResumeBuilderViewProps {
  currentUser?: UserProfile | null;
}

export const ResumeBuilderView: React.FC<ResumeBuilderViewProps> = ({ currentUser }) => {
  const [resumes, setResumes] = useState<StructuredResumeItem[]>([]);
  const [activeResumeId, setActiveResumeId] = useState<number | null>(null);
  const [currentData, setCurrentData] = useState<StructuredResumeData | null>(null);
  const [currentSettings, setCurrentSettings] = useState<ResumeSettings | null>(null);
  const [currentTitle, setCurrentTitle] = useState<string>('My Resume');
  const [isDefault, setIsDefault] = useState<boolean>(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Fetch all resumes on load
  const loadResumes = useCallback(async () => {
    try {
      setLoading(true);
      const list = await api.listStructuredResumes();
      if (list.length === 0) {
        // Create initial default resume
        const initial = await api.createStructuredResume({
          title: 'Master Professional Resume',
          is_default: true,
        });
        setResumes([initial]);
        selectResume(initial);
      } else {
        setResumes(list);
        const defaultResume = list.find((r) => r.is_default) || list[0];
        selectResume(defaultResume);
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to load resumes' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResumes();
  }, [loadResumes]);

  const selectResume = (res: StructuredResumeItem) => {
    setActiveResumeId(res.id);
    setCurrentTitle(res.title);
    setIsDefault(res.is_default);
    setCurrentData(res.structured_data || {
      profile: {
        full_name: currentUser ? `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() : '',
        headline: '',
        email: currentUser?.email || '',
        phone: currentUser?.phone || '',
        location: '',
        website: '',
        github: '',
        linkedin: '',
        summary: '',
      },
      experience: [],
      education: [],
      skills: [],
      projects: [],
      certifications: [],
      languages: [],
      custom_sections: [],
    });
    setCurrentSettings(res.settings || {
      template: 'modern',
      theme_color: '#2563eb',
      font_family: 'Inter',
      font_size: '10.5',
      document_size: 'A4',
      section_order: ['summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'languages', 'custom_sections'],
      section_visibility: {},
    });
    setDirty(false);
  };

  const handleSelectChange = (idStr: string) => {
    const id = parseInt(idStr, 10);
    const found = resumes.find((r) => r.id === id);
    if (found) {
      selectResume(found);
    }
  };

  // Live real-time updates
  const handleDataChange = (newData: StructuredResumeData) => {
    setCurrentData(newData);
    setDirty(true);
  };

  const handleSettingsChange = (newSettings: ResumeSettings) => {
    setCurrentSettings(newSettings);
    setDirty(true);
  };

  // Save changes to backend
  const handleSave = async () => {
    if (!activeResumeId || !currentData || !currentSettings) return;
    setSaving(true);
    setStatusMsg(null);
    try {
      const updated = await api.updateStructuredResume(activeResumeId, {
        title: currentTitle,
        structured_data: currentData,
        settings: currentSettings,
      });
      setResumes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setDirty(false);
      setStatusMsg({ type: 'success', text: 'Resume saved successfully!' });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to save resume' });
    } finally {
      setSaving(false);
    }
  };

  // Create new resume
  const handleCreateNew = async () => {
    const title = prompt('Enter a name for the new resume (e.g. Cybersecurity Resume):');
    if (!title || !title.trim()) return;

    try {
      setLoading(true);
      const created = await api.createStructuredResume({
        title: title.trim(),
        is_default: false,
      });
      setResumes((prev) => [created, ...prev]);
      selectResume(created);
      setStatusMsg({ type: 'success', text: `Created "${created.title}"` });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to create resume' });
    } finally {
      setLoading(false);
    }
  };

  // Duplicate current resume
  const handleDuplicate = async () => {
    if (!activeResumeId) return;
    try {
      setLoading(true);
      const duplicated = await api.duplicateStructuredResume(activeResumeId);
      setResumes((prev) => [duplicated, ...prev]);
      selectResume(duplicated);
      setStatusMsg({ type: 'success', text: `Duplicated as "${duplicated.title}"` });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to duplicate resume' });
    } finally {
      setLoading(false);
    }
  };

  // Set as default
  const handleSetDefault = async () => {
    if (!activeResumeId) return;
    try {
      const res = await api.setDefaultStructuredResume(activeResumeId);
      setResumes((prev) =>
        prev.map((r) => ({
          ...r,
          is_default: r.id === res.id,
        }))
      );
      setIsDefault(true);
      setStatusMsg({ type: 'success', text: 'Set as default resume' });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to set default' });
    }
  };

  // Delete resume
  const handleDelete = async () => {
    if (!activeResumeId) return;
    if (resumes.length <= 1) {
      alert('You must keep at least one resume in your profile.');
      return;
    }
    if (!window.confirm(`Delete resume "${currentTitle}"?`)) return;

    try {
      await api.deleteStructuredResume(activeResumeId);
      const remaining = resumes.filter((r) => r.id !== activeResumeId);
      setResumes(remaining);
      selectResume(remaining[0]);
      setStatusMsg({ type: 'success', text: 'Resume deleted.' });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to delete resume' });
    }
  };

  // Import profile into current resume
  const handleImportProfile = async () => {
    if (!activeResumeId) return;
    try {
      const res = await api.importProfileToResume(activeResumeId);
      selectResume(res);
      setStatusMsg({ type: 'success', text: 'Profile data imported into resume!' });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to import profile' });
    }
  };

  if (loading && !currentData) {
    return (
      <div className="builder-loading-state">
        <Loader2 size={32} className="animate-spin text-primary" />
        <p>Loading your resume builder...</p>
      </div>
    );
  }

  return (
    <div className="resume-builder-wrapper">
      {/* Top Controls Header */}
      <header className="builder-top-bar">
        <div className="top-left-controls">
          <div className="resume-select-wrapper">
            <FileText size={16} className="text-primary" />
            <select
              className="resume-dropdown"
              value={activeResumeId || ''}
              onChange={(e) => handleSelectChange(e.target.value)}
            >
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title} {r.is_default ? '★ (Default)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="title-inline-edit">
            <input
              type="text"
              className="title-input"
              value={currentTitle}
              onChange={(e) => {
                setCurrentTitle(e.target.value);
                setDirty(true);
              }}
              title="Click to rename this resume"
            />
          </div>

          {isDefault && (
            <span className="default-badge" title="This resume is selected automatically for job applications">
              <Star size={12} fill="#f59e0b" color="#f59e0b" />
              <span>Default Master</span>
            </span>
          )}
        </div>

        <div className="top-right-actions">
          {statusMsg && (
            <div className={`status-pill ${statusMsg.type}`}>
              {statusMsg.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
              <span>{statusMsg.text}</span>
            </div>
          )}

          {!isDefault && (
            <button
              type="button"
              className="action-btn secondary"
              onClick={handleSetDefault}
              title="Make this your default resume"
            >
              <Star size={14} />
              <span>Set as Default</span>
            </button>
          )}

          <button
            type="button"
            className="action-btn secondary"
            onClick={handleDuplicate}
            title="Duplicate this resume as a new copy"
          >
            <Copy size={14} />
            <span>Duplicate</span>
          </button>

          <button
            type="button"
            className="action-btn secondary"
            onClick={handleCreateNew}
            title="Create a fresh resume"
          >
            <Plus size={14} />
            <span>New Resume</span>
          </button>

          {resumes.length > 1 && (
            <button
              type="button"
              className="action-btn danger"
              onClick={handleDelete}
              title="Delete this resume"
            >
              <Trash2 size={14} />
            </button>
          )}

          <button
            type="button"
            className={`action-btn primary save-btn ${dirty ? 'dirty' : ''}`}
            disabled={saving}
            onClick={handleSave}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            <span>{saving ? 'Saving...' : dirty ? 'Save Changes *' : 'Saved'}</span>
          </button>
        </div>
      </header>

      {/* Two-Panel Main Body */}
      <div className="builder-two-panel-grid">
        {/* Left Panel: Editor */}
        <div className="builder-panel left-panel">
          {currentData && currentSettings && (
            <ResumeEditor
              data={currentData}
              settings={currentSettings}
              onChangeData={handleDataChange}
              onChangeSettings={handleSettingsChange}
              onImportProfile={handleImportProfile}
            />
          )}
        </div>

        {/* Right Panel: Live WYSIWYG Preview */}
        <div className="builder-panel right-panel">
          {activeResumeId && currentData && currentSettings && (
            <ResumePreview
              resumeId={activeResumeId}
              resumeTitle={currentTitle}
              data={currentData}
              settings={currentSettings}
            />
          )}
        </div>
      </div>
    </div>
  );
};
