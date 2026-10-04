import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  X,
  Briefcase,
  MapPin,
  ExternalLink,
  Calendar,
  Clock,
  Sparkles,
  User,
  Mail,
  Phone,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Check,
  ChevronRight,
  FileText,
  Bookmark,
  Send,
  Award,
  XCircle,
  TrendingUp,
} from 'lucide-react';

const LinkedinIcon: React.FC<{ size?: number }> = ({ size = 13 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="currentColor"
    style={{ display: 'inline-block', verticalAlign: 'middle' }}
  >
    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.64a1.67 1.67 0 1 0 0 3.34 1.67 1.67 0 0 0 0-3.34Z" />
  </svg>
);
import { api } from '../../api/client';
import type {
  ApplicationItem,
  ApplicationStatus,
  JobIntelligence,
  ContactItem,
} from '../../api/client';
import { useTranslation, getStatusLabel, getPriorityLabel } from '../../i18n';

interface ApplicationDetailDrawerProps {
  applicationId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onApplicationUpdated: (updatedApp: ApplicationItem) => void;
  onApplicationDeleted: (appId: number) => void;
  onOpenContact?: (contactId: number) => void;
  onSelectJob?: (job: any) => void;
}

const ALL_STATUSES: Array<{ value: ApplicationStatus; label: string; color: string; icon: any }> = [
  { value: 'saved', label: 'Saved', color: '#60a5fa', icon: Bookmark },
  { value: 'applied', label: 'Applied', color: '#fbbf24', icon: Send },
  { value: 'interviewing', label: 'Interviewing', color: '#c084fc', icon: Calendar },
  { value: '1st_interview', label: '1st Interview', color: '#a78bfa', icon: Calendar },
  { value: '2nd_interview', label: '2nd Interview', color: '#818cf8', icon: Calendar },
  { value: '3rd_interview', label: '3rd Interview', color: '#f472b6', icon: Calendar },
  { value: 'final_interview', label: 'Final Interview', color: '#e879f9', icon: Calendar },
  { value: 'offer', label: 'Offer Received', color: '#34d399', icon: Award },
  { value: 'accepted', label: 'Accepted 🎉', color: '#10b981', icon: CheckCircle2 },
  { value: 'rejected', label: 'Rejected', color: '#f87171', icon: XCircle },
  { value: 'no_answer', label: 'No Answer / Ghosted', color: '#94a3b8', icon: Clock },
  { value: 'withdrawn', label: 'Withdrawn', color: '#64748b', icon: XCircle },
];

export const ApplicationDetailDrawer: React.FC<ApplicationDetailDrawerProps> = ({
  applicationId,
  isOpen,
  onClose,
  onApplicationUpdated,
  onApplicationDeleted,
  onOpenContact,
  onSelectJob,
}) => {
  const { t, language } = useTranslation();
  const tApp = t.applications;

  const [app, setApp] = useState<ApplicationItem | null>(null);
  const [intelligence, setIntelligence] = useState<JobIntelligence | null>(null);
  const [contact, setContact] = useState<ContactItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);

  // Follow-up state
  const [followUpDate, setFollowUpDate] = useState('');
  const [savingFollowUp, setSavingFollowUp] = useState(false);

  // New timeline event state
  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventNotes, setNewEventNotes] = useState('');
  const [newEventType, setNewEventType] = useState('note_added');
  const [addingEvent, setAddingEvent] = useState(false);
  const [showAddEvent, setShowAddEvent] = useState(false);

  // Notes state
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);

  // Load application details
  useEffect(() => {
    if (!applicationId || !isOpen) {
      setApp(null);
      setIntelligence(null);
      setContact(null);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      try {
        const apps = await api.getApplications();
        const current = apps.find((a) => a.id === applicationId);
        if (current) {
          setApp(current);
          setFollowUpDate(current.next_follow_up || '');
          setNotes(current.notes || '');

          // If linked contact exists, load contact
          if (current.contact_id) {
            try {
              const contacts = await api.getContacts();
              const foundContact = contacts.find((c) => c.id === current.contact_id);
              if (foundContact) setContact(foundContact);
            } catch (cErr) {
              console.warn('Could not fetch linked contact:', cErr);
            }
          } else {
            setContact(null);
          }
        }
      } catch (err) {
        console.error('Failed to load application:', err);
      } finally {
        setLoading(false);
      }

      // Fetch intelligence
      setLoadingIntelligence(true);
      try {
        const intel = await api.getApplicationIntelligence(applicationId);
        setIntelligence(intel);
      } catch (iErr) {
        console.warn('Intelligence not available for this application:', iErr);
      } finally {
        setLoadingIntelligence(false);
      }
    };

    loadData();
  }, [applicationId, isOpen]);

  if (!isOpen) return null;

  const handleStatusChange = async (newStatus: ApplicationStatus) => {
    if (!app) return;
    try {
      const updated = await api.updateApplication(app.id, { status: newStatus });
      setApp(updated);
      onApplicationUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    }
  };

  const handlePriorityChange = async (newPriority: string) => {
    if (!app) return;
    try {
      const updated = await api.updateApplication(app.id, { priority: newPriority });
      setApp(updated);
      onApplicationUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to update priority');
    }
  };

  const handleFollowUpAction = async (action: 'schedule' | 'complete' | 'snooze' | 'cancel', days?: number) => {
    if (!app) return;
    try {
      setSavingFollowUp(true);
      const apiAction = action === 'schedule' ? 'reschedule' : action;
      const targetDate = action === 'schedule' ? followUpDate : undefined;
      const updated = await api.executeFollowUpAction(app.id, {
        action: apiAction,
        new_date: targetDate,
        days: days,
      });
      setApp(updated);
      setFollowUpDate(updated.next_follow_up || '');
      onApplicationUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to update follow-up');
    } finally {
      setSavingFollowUp(false);
    }
  };

  const handleApplyPreset = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    const dateStr = d.toISOString().slice(0, 10);
    setFollowUpDate(dateStr);
    handleFollowUpAction('schedule', days);
  };

  const handleAddCustomEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!app || !newEventTitle.trim()) return;

    try {
      setAddingEvent(true);
      const payload = {
        event_type: newEventType,
        event_title: newEventTitle.trim(),
        notes: newEventNotes.trim() || undefined,
      };
      await api.addApplicationEvent(app.id, payload);
      // Reload application to get refreshed history
      const apps = await api.getApplications();
      const updated = apps.find((a) => a.id === app.id);
      if (updated) {
        setApp(updated);
        onApplicationUpdated(updated);
      }
      setNewEventTitle('');
      setNewEventNotes('');
      setShowAddEvent(false);
    } catch (err: any) {
      alert(err.message || 'Failed to add timeline event');
    } finally {
      setAddingEvent(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!app) return;
    try {
      setSavingNotes(true);
      const updated = await api.updateApplication(app.id, { notes });
      setApp(updated);
      onApplicationUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to save notes');
    } finally {
      setSavingNotes(false);
    }
  };

  const handleDelete = async () => {
    if (!app) return;
    if (!confirm(tApp.drawerConfirmDelete.replace('{title}', app.effective_title) || `Remove application for "${app.effective_title}"?`)) return;
    try {
      await api.deleteApplication(app.id);
      onApplicationDeleted(app.id);
      onClose();
    } catch (err: any) {
      alert(err.message || 'Failed to delete application');
    }
  };

  return (
    <DrawerBackdrop onClick={onClose}>
      <DrawerContainer onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <DrawerHeader>
          <div className="header-top-row">
            <div className="header-badges">
              <span className="source-tag">{app?.source || 'Application'}</span>
              {app?.priority && (
                <span className={`priority-tag ${app.priority}`}>{getPriorityLabel(app.priority, language).toUpperCase()}</span>
              )}
            </div>
            <button type="button" className="close-drawer-btn" onClick={onClose} title="Close drawer">
              <X size={18} />
            </button>
          </div>

          <h2 className="app-title">{app?.effective_title || tApp.drawerTitle}</h2>

          <div className="company-row">
            <span className="company-name">{app?.effective_company}</span>
            {app?.effective_location && (
              <span className="location-info">
                <MapPin size={13} />
                {app.effective_location}
              </span>
            )}
            {app?.effective_job_url && (
              <a
                href={app.effective_job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="external-job-link"
                title="Open original job posting"
              >
                <span>View Posting</span>
                <ExternalLink size={13} />
              </a>
            )}
            {app?.job && onSelectJob && (
              <button
                type="button"
                className="compust-job-btn"
                onClick={() => onSelectJob(app.job)}
                title="View full job analysis & match details"
              >
                <Briefcase size={13} />
                <span>Job Match View</span>
              </button>
            )}
          </div>

          {/* Quick Stage Bar */}
          {app && (
            <StageSelectorRow>
              <label>{tApp.drawerFieldStatus}:</label>
              <select
                value={app.status}
                onChange={(e) => handleStatusChange(e.target.value as ApplicationStatus)}
                className="stage-select-pill"
              >
                {ALL_STATUSES.map((st) => (
                  <option key={st.value} value={st.value}>
                    {getStatusLabel(st.value, language)}
                  </option>
                ))}
              </select>

              <label style={{ marginLeft: '12px' }}>{tApp.drawerFieldPriority}:</label>
              <select
                value={app.priority || 'medium'}
                onChange={(e) => handlePriorityChange(e.target.value)}
                className="priority-select-pill"
              >
                <option value="high">{tApp.priorityHigh}</option>
                <option value="medium">{tApp.priorityMedium}</option>
                <option value="low">{tApp.priorityLow}</option>
              </select>
            </StageSelectorRow>
          )}
        </DrawerHeader>

        {loading ? (
          <DrawerLoading>
            <Clock className="spin" size={28} />
            <p>{tApp.loadingApplications}</p>
          </DrawerLoading>
        ) : !app ? (
          <DrawerEmpty>Application not found.</DrawerEmpty>
        ) : (
          <DrawerBody>
            {/* Section 1: Job Intelligence / Local AI */}
            <SectionCard>
              <SectionHeader>
                <div className="section-title">
                  <Sparkles size={16} className="text-amber" />
                  <h4>Job Intelligence & Match Analysis</h4>
                </div>
                {intelligence?.match_score !== undefined && intelligence.match_score > 0 && (
                  <div className={`score-badge ${intelligence.match_score >= 70 ? 'high' : 'medium'}`}>
                    {intelligence.match_score}% Match
                  </div>
                )}
              </SectionHeader>

              {loadingIntelligence ? (
                <div className="intel-loading">
                  <Sparkles className="spin text-amber" size={16} />
                  <span>Computing profile criteria match...</span>
                </div>
              ) : intelligence ? (
                <div className="intel-content">
                  {intelligence.explanation && (
                    <p className="intel-summary">{intelligence.explanation}</p>
                  )}

                  {/* Skills tags */}
                  {intelligence.strong_matches && intelligence.strong_matches.length > 0 && (
                    <div className="skills-block">
                      <span className="skills-label">
                        <CheckCircle2 size={13} className="text-emerald" /> Strong Skill Matches:
                      </span>
                      <div className="tags-cloud">
                        {intelligence.strong_matches.map((skill: string, i: number) => (
                          <span key={i} className="skill-tag match">
                            ✓ {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {intelligence.potential_gaps && intelligence.potential_gaps.length > 0 && (
                    <div className="skills-block">
                      <span className="skills-label">
                        <AlertCircle size={13} className="text-amber" /> Missing Skills / Growth Gaps:
                      </span>
                      <div className="tags-cloud">
                        {intelligence.potential_gaps.map((skill: string, i: number) => (
                          <span key={i} className="skill-tag gap">
                            ⚠ {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {intelligence.resume_suggestions && intelligence.resume_suggestions.length > 0 && (
                    <div className="suggestions-block">
                      <span className="skills-label">
                        <Sparkles size={13} className="text-purple" /> Tailored Resume Suggestions:
                      </span>
                      <ul className="suggestions-list">
                        {intelligence.resume_suggestions.map((sug: string, i: number) => (
                          <li key={i}>{sug}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="intel-empty">
                  <span>No resume match intelligence available for this manual entry.</span>
                </div>
              )}
            </SectionCard>

            {/* Section 2: Contact / Recruiter */}
            <SectionCard>
              <SectionHeader>
                <div className="section-title">
                  <User size={16} className="text-blue" />
                  <h4>{tApp.drawerFieldRecruiter}</h4>
                </div>
                {contact && onOpenContact && (
                  <button
                    type="button"
                    className="view-contact-btn"
                    onClick={() => onOpenContact(contact.id)}
                    title="Open full contact record in Contacts view"
                  >
                    <span>{tApp.tabContacts}</span>
                    <ChevronRight size={14} />
                  </button>
                )}
              </SectionHeader>

              {contact ? (
                <div className="contact-card-inner">
                  <div className="contact-main-info">
                    <div className="contact-avatar">
                      {(contact.first_name || contact.name || 'C')[0]}
                      {contact.last_name ? contact.last_name[0] : ''}
                    </div>
                    <div className="contact-text">
                      <h5>
                        {contact.first_name || contact.name} {contact.last_name || ''}
                      </h5>
                      <p className="contact-sub">
                        {contact.role ? `${contact.role} — ` : ''}
                        {contact.company || app.effective_company}
                      </p>
                    </div>
                  </div>

                  <div className="contact-links-grid">
                    {contact.email && (
                      <a href={`mailto:${contact.email}`} className="contact-link-item">
                        <Mail size={13} />
                        <span>{contact.email}</span>
                      </a>
                    )}
                    {contact.phone && (
                      <a href={`tel:${contact.phone}`} className="contact-link-item">
                        <Phone size={13} />
                        <span>{contact.phone}</span>
                      </a>
                    )}
                    {contact.linkedin_url && (
                      <a
                        href={contact.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="contact-link-item"
                      >
                        <LinkedinIcon size={13} />
                        <span>LinkedIn Profile</span>
                      </a>
                    )}
                  </div>

                  {/* Factual insights */}
                  <div className="contact-insights-strip">
                    <div className="insight-stat">
                      <span className="num">{contact.applications_count}</span>
                      <span className="lbl">Applications</span>
                    </div>
                    <div className="insight-stat">
                      <span className="num">{contact.responses_count}</span>
                      <span className="lbl">Responses</span>
                    </div>
                    <div className="insight-stat">
                      <span className="num">{contact.interviews_count}</span>
                      <span className="lbl">Interviews</span>
                    </div>
                    {contact.has_responded !== undefined && (
                      <div className="insight-stat">
                        <span className={`badge-status ${contact.has_responded ? 'green' : 'amber'}`}>
                          {contact.has_responded ? 'Responded' : 'Waiting'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : app.contact_name || app.recruiter ? (
                <div className="manual-contact-box">
                  <div className="contact-main-info">
                    <User size={16} className="text-blue" />
                    <div>
                      <h5>{app.contact_name || app.recruiter}</h5>
                      {app.contact_email && <p className="sub">{app.contact_email}</p>}
                      {app.contact_phone && <p className="sub">{app.contact_phone}</p>}
                    </div>
                  </div>
                  <p className="hint">
                    Linked to this application via text record. Use Contacts tab to track communication history.
                  </p>
                </div>
              ) : (
                <div className="contact-empty">
                  <span>No recruiter or contact assigned yet.</span>
                </div>
              )}
            </SectionCard>

            {/* Section 3: Next Action & Follow-up */}
            <SectionCard>
              <SectionHeader>
                <div className="section-title">
                  <Calendar size={16} className="text-purple" />
                  <h4>{tApp.drawerFieldFollowUp}</h4>
                </div>
                {app.next_follow_up && (
                  <span
                    className={`followup-status-badge ${
                      new Date(app.next_follow_up) < new Date(new Date().toISOString().slice(0, 10))
                        ? 'overdue'
                        : 'upcoming'
                    }`}
                  >
                    {new Date(app.next_follow_up) < new Date(new Date().toISOString().slice(0, 10))
                      ? tApp.actionOverdue
                      : tApp.actionFollowUp}
                  </span>
                )}
              </SectionHeader>

              <div className="followup-controls">
                <div className="presets-row">
                  <span className="presets-label">Presets:</span>
                  <button type="button" className="preset-btn" onClick={() => handleApplyPreset(3)}>
                    +3d
                  </button>
                  <button type="button" className="preset-btn" onClick={() => handleApplyPreset(5)}>
                    +5d
                  </button>
                  <button type="button" className="preset-btn" onClick={() => handleApplyPreset(7)}>
                    +7d
                  </button>
                  <button type="button" className="preset-btn" onClick={() => handleApplyPreset(14)}>
                    +14d
                  </button>
                </div>

                <div className="date-input-row">
                  <input
                    type="date"
                    value={followUpDate}
                    onChange={(e) => setFollowUpDate(e.target.value)}
                    className="followup-date-input"
                  />
                  <button
                    type="button"
                    className="btn-save-followup"
                    disabled={savingFollowUp || !followUpDate}
                    onClick={() => handleFollowUpAction('schedule')}
                  >
                    {savingFollowUp ? `${tApp.btnSave}...` : tApp.btnSave}
                  </button>
                </div>

                {app.next_follow_up && (
                  <div className="actions-button-group">
                    <button
                      type="button"
                      className="quick-action-btn complete"
                      onClick={() => handleFollowUpAction('complete')}
                      disabled={savingFollowUp}
                      title={tApp.actionBtnComplete}
                    >
                      <Check size={13} />
                      <span>{tApp.actionBtnComplete}</span>
                    </button>

                    <button
                      type="button"
                      className="quick-action-btn snooze"
                      onClick={() => handleFollowUpAction('snooze', 2)}
                      disabled={savingFollowUp}
                      title={tApp.actionBtnSnooze}
                    >
                      <Clock size={13} />
                      <span>{tApp.actionBtnSnooze} +2d</span>
                    </button>

                    <button
                      type="button"
                      className="quick-action-btn snooze"
                      onClick={() => handleFollowUpAction('snooze', 7)}
                      disabled={savingFollowUp}
                      title={tApp.actionBtnSnooze}
                    >
                      <Clock size={13} />
                      <span>{tApp.actionBtnSnooze} +7d</span>
                    </button>

                    <button
                      type="button"
                      className="quick-action-btn cancel"
                      onClick={() => handleFollowUpAction('cancel')}
                      disabled={savingFollowUp}
                      title={tApp.actionBtnCancel}
                    >
                      <X size={13} />
                      <span>{tApp.actionBtnCancel}</span>
                    </button>
                  </div>
                )}
              </div>
            </SectionCard>

            {/* Section 4: History / Timeline */}
            <SectionCard>
              <SectionHeader>
                <div className="section-title">
                  <TrendingUp size={16} className="text-emerald" />
                  <h4>{tApp.drawerTabTimeline}</h4>
                </div>
                <button
                  type="button"
                  className="add-event-toggle-btn"
                  onClick={() => setShowAddEvent(!showAddEvent)}
                >
                  <Plus size={14} />
                  <span>{showAddEvent ? 'Cancel' : 'Add Event / Note'}</span>
                </button>
              </SectionHeader>

              {/* Add event form */}
              {showAddEvent && (
                <form onSubmit={handleAddCustomEvent} className="add-event-form">
                  <div className="form-row">
                    <select
                      value={newEventType}
                      onChange={(e) => setNewEventType(e.target.value)}
                      className="event-type-select"
                    >
                      <option value="note_added">Note</option>
                      <option value="contact_interaction">Contact Interaction</option>
                      <option value="interview_scheduled">Interview Scheduled</option>
                      <option value="interview_completed">Interview Completed</option>
                      <option value="follow_up_sent">Follow-Up Sent</option>
                      <option value="offer_received">Offer Received</option>
                      <option value="other">Other Event</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Event title (e.g. Phone screen with hiring manager)"
                      value={newEventTitle}
                      onChange={(e) => setNewEventTitle(e.target.value)}
                      required
                      className="event-title-input"
                    />
                  </div>
                  <textarea
                    placeholder="Additional notes / feedback / impressions..."
                    value={newEventNotes}
                    onChange={(e) => setNewEventNotes(e.target.value)}
                    rows={2}
                    className="event-notes-input"
                  />
                  <div className="form-actions">
                    <button
                      type="submit"
                      disabled={addingEvent || !newEventTitle.trim()}
                      className="save-event-btn"
                    >
                      {addingEvent ? 'Saving...' : 'Save to Timeline'}
                    </button>
                  </div>
                </form>
              )}

              {/* Chronological Timeline */}
              <div className="timeline-container">
                {(!app.history || app.history.length === 0) ? (
                  <div className="timeline-empty">
                    <span>Application created on {new Date(app.created_at).toLocaleDateString()}. No further events logged.</span>
                  </div>
                ) : (
                  app.history.map((event, idx) => (
                    <div key={event.id || idx} className="timeline-item">
                      <div className="timeline-marker">
                        <div className="dot" />
                        {idx !== (app.history?.length ?? 0) - 1 && <div className="line" />}
                      </div>
                      <div className="timeline-body">
                        <div className="timeline-header">
                          <span className="event-title">
                            {event.event_title || (
                              event.from_status
                                ? `${event.from_status} → ${event.to_status}`
                                : `Moved to ${event.to_status}`
                            )}
                          </span>
                          <span className="event-date">
                            {new Date(event.changed_at).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        {event.notes && <p className="event-notes">{event.notes}</p>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            {/* Section 5: Notes & Additional Info */}
            <SectionCard>
              <SectionHeader>
                <div className="section-title">
                  <FileText size={16} className="text-slate" />
                  <h4>{tApp.drawerFieldNotes}</h4>
                </div>
              </SectionHeader>

              <div className="notes-editor">
                <textarea
                  rows={4}
                  placeholder={tApp.editNotesPlaceholder}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="notes-textarea"
                />
                <div className="notes-actions">
                  <button
                    type="button"
                    className="btn-save-notes"
                    onClick={handleSaveNotes}
                    disabled={savingNotes}
                  >
                    {savingNotes ? `${tApp.btnSave}...` : tApp.btnSave}
                  </button>
                </div>
              </div>
            </SectionCard>

            {/* Danger Zone: Delete */}
            <DangerZone>
              <button type="button" className="btn-delete-app" onClick={handleDelete}>
                <Trash2 size={14} />
                <span>{tApp.drawerBtnDelete}</span>
              </button>
            </DangerZone>
          </DrawerBody>
        )}
      </DrawerContainer>
    </DrawerBackdrop>
  );
};

// Styled Components
const DrawerBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  animation: fadeIn 0.2s ease-out;

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

const DrawerContainer = styled.div`
  width: 100%;
  max-width: 620px;
  height: 100vh;
  background: #0f172a;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: -10px 0 35px rgba(0, 0, 0, 0.7);
  animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);

  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
`;

const DrawerHeader = styled.div`
  padding: 24px 28px 18px;
  background: rgba(30, 41, 59, 0.7);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  .header-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .header-badges {
      display: flex;
      gap: 8px;

      .source-tag {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 3px 8px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.08);
        color: #94a3b8;
      }

      .priority-tag {
        font-size: 11px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;

        &.high {
          background: rgba(239, 68, 68, 0.15);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }
        &.medium {
          background: rgba(245, 158, 11, 0.15);
          color: #fbbf24;
          border: 1px solid rgba(245, 158, 11, 0.3);
        }
        &.low {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }
      }
    }

    .close-drawer-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;
      border-radius: 8px;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
      }
    }
  }

  .app-title {
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
    margin: 0 0 8px 0;
    line-height: 1.3;
  }

  .company-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 13px;
    color: #cbd5e1;

    .company-name {
      font-weight: 600;
      color: #38bdf8;
    }

    .location-info {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #94a3b8;
    }

    .external-job-link,
    .compust-job-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 500;
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 6px;
      padding: 3px 8px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s;

      &:hover {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
      }
    }
  }
`;

const StageSelectorRow = styled.div`
  display: flex;
  align-items: center;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  label {
    font-size: 12px;
    color: #94a3b8;
    margin-right: 8px;
  }

  .stage-select-pill,
  .priority-select-pill {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #f1f5f9;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }
`;

const DrawerBody = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

const SectionCard = styled.div`
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 18px;

  .text-amber {
    color: #f59e0b;
  }
  .text-emerald {
    color: #10b981;
  }
  .text-blue {
    color: #3b82f6;
  }
  .text-purple {
    color: #a855f7;
  }
  .text-slate {
    color: #94a3b8;
  }

  /* Intelligence block */
  .intel-loading {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #94a3b8;
    padding: 12px 0;
  }

  .intel-content {
    display: flex;
    flex-direction: column;
    gap: 14px;

    .intel-summary {
      font-size: 13px;
      line-height: 1.5;
      color: #e2e8f0;
      background: rgba(15, 23, 42, 0.4);
      padding: 10px 14px;
      border-radius: 8px;
      border-left: 3px solid #f59e0b;
    }

    .skills-block {
      .skills-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #cbd5e1;
        margin-bottom: 8px;
      }

      .tags-cloud {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;

        .skill-tag {
          font-size: 11px;
          padding: 3px 8px;
          border-radius: 4px;
          font-weight: 500;

          &.match {
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.25);
          }
          &.gap {
            background: rgba(245, 158, 11, 0.12);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.25);
          }
        }
      }
    }

    .suggestions-block {
      .skills-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #cbd5e1;
        margin-bottom: 6px;
      }

      .suggestions-list {
        margin: 0;
        padding-left: 18px;
        font-size: 12px;
        color: #cbd5e1;
        line-height: 1.5;
      }
    }
  }

  .intel-empty {
    font-size: 12px;
    color: #64748b;
    padding: 8px 0;
  }

  /* Contact block */
  .contact-card-inner {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .contact-main-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .contact-avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: #fff;
        font-weight: 700;
        font-size: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .contact-text {
        h5 {
          margin: 0;
          font-size: 14px;
          font-weight: 600;
          color: #f1f5f9;
        }

        .contact-sub {
          margin: 2px 0 0;
          font-size: 12px;
          color: #94a3b8;
        }
      }
    }

    .contact-links-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .contact-link-item {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 12px;
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 6px;
        padding: 4px 10px;
        text-decoration: none;

        &:hover {
          background: rgba(56, 189, 248, 0.16);
        }
      }
    }

    .contact-insights-strip {
      display: flex;
      align-items: center;
      gap: 14px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);

      .insight-stat {
        display: flex;
        align-items: baseline;
        gap: 5px;

        .num {
          font-size: 14px;
          font-weight: 700;
          color: #f1f5f9;
        }

        .lbl {
          font-size: 11px;
          color: #94a3b8;
        }

        .badge-status {
          font-size: 11px;
          font-weight: 600;
          padding: 2px 7px;
          border-radius: 4px;

          &.green {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
          }
          &.amber {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
          }
        }
      }
    }
  }

  .manual-contact-box {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .contact-main-info {
      display: flex;
      align-items: flex-start;
      gap: 10px;

      h5 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
        color: #f1f5f9;
      }
      .sub {
        margin: 2px 0 0;
        font-size: 12px;
        color: #94a3b8;
      }
    }

    .hint {
      margin: 0;
      font-size: 11px;
      color: #64748b;
    }
  }

  .contact-empty {
    font-size: 12px;
    color: #64748b;
  }

  /* Follow-up controls */
  .followup-controls {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .presets-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;

      .presets-label {
        font-size: 12px;
        color: #94a3b8;
      }

      .preset-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #cbd5e1;
        font-size: 11px;
        font-weight: 500;
        padding: 4px 9px;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.15s;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #fff;
          border-color: #3b82f6;
        }
      }
    }

    .date-input-row {
      display: flex;
      gap: 8px;
      align-items: center;

      .followup-date-input {
        flex: 1;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #f1f5f9;
        padding: 7px 12px;
        border-radius: 6px;
        font-size: 13px;

        &:focus {
          outline: none;
          border-color: #3b82f6;
        }
      }

      .btn-save-followup {
        background: #3b82f6;
        color: #fff;
        border: none;
        padding: 7px 16px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;

        &:hover:not(:disabled) {
          background: #2563eb;
        }
        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      }
    }

    .actions-button-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 4px;

      .quick-action-btn {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;

        &.complete {
          background: rgba(16, 185, 129, 0.15);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.3);
          &:hover {
            background: rgba(16, 185, 129, 0.25);
          }
        }

        &.snooze {
          background: rgba(245, 158, 11, 0.12);
          color: #fbbf24;
          border: 1px solid rgba(245, 158, 11, 0.25);
          &:hover {
            background: rgba(245, 158, 11, 0.2);
          }
        }

        &.cancel {
          background: rgba(255, 255, 255, 0.05);
          color: #94a3b8;
          border: 1px solid rgba(255, 255, 255, 0.1);
          &:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #f1f5f9;
          }
        }
      }
    }
  }

  /* Add event form */
  .add-event-form {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;

    .form-row {
      display: flex;
      gap: 8px;

      .event-type-select {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #f1f5f9;
        font-size: 12px;
        padding: 6px 10px;
        border-radius: 6px;
      }

      .event-title-input {
        flex: 1;
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #f1f5f9;
        font-size: 12px;
        padding: 6px 10px;
        border-radius: 6px;

        &:focus {
          outline: none;
          border-color: #10b981;
        }
      }
    }

    .event-notes-input {
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #f1f5f9;
      font-size: 12px;
      padding: 8px 10px;
      border-radius: 6px;
      resize: vertical;

      &:focus {
        outline: none;
        border-color: #10b981;
      }
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;

      .save-event-btn {
        background: #10b981;
        color: #fff;
        border: none;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;

        &:hover:not(:disabled) {
          background: #059669;
        }
        &:disabled {
          opacity: 0.5;
        }
      }
    }
  }

  /* Timeline */
  .timeline-container {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-top: 12px;

    .timeline-empty {
      font-size: 12px;
      color: #64748b;
      padding: 8px 0;
    }

    .timeline-item {
      display: flex;
      gap: 14px;
      position: relative;
      padding-bottom: 16px;

      &:last-child {
        padding-bottom: 0;
      }

      .timeline-marker {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 14px;

        .dot {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #3b82f6;
          margin-top: 5px;
          box-shadow: 0 0 6px rgba(59, 130, 246, 0.5);
        }

        .line {
          width: 2px;
          flex: 1;
          background: rgba(255, 255, 255, 0.08);
          margin-top: 4px;
        }
      }

      .timeline-body {
        flex: 1;

        .timeline-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 8px;

          .event-title {
            font-size: 13px;
            font-weight: 600;
            color: #f1f5f9;
          }

          .event-date {
            font-size: 11px;
            color: #64748b;
            white-space: nowrap;
          }
        }

        .event-notes {
          margin: 4px 0 0;
          font-size: 12px;
          color: #94a3b8;
          line-height: 1.4;
        }
      }
    }
  }

  /* Notes */
  .notes-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .notes-textarea {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f1f5f9;
      font-size: 13px;
      line-height: 1.5;
      padding: 10px 12px;
      border-radius: 8px;
      resize: vertical;

      &:focus {
        outline: none;
        border-color: #3b82f6;
      }
    }

    .notes-actions {
      display: flex;
      justify-content: flex-end;

      .btn-save-notes {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #f1f5f9;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;

        &:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.15);
        }
      }
    }
  }
`;

const SectionHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;

    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: #f8fafc;
    }
  }

  .score-badge {
    font-size: 12px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 6px;

    &.high {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    &.medium {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
  }

  .view-contact-btn,
  .add-event-toggle-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    background: transparent;
    border: none;
    color: #38bdf8;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    padding: 0;

    &:hover {
      text-decoration: underline;
    }
  }

  .followup-status-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;

    &.overdue {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    &.upcoming {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
  }
`;

const DrawerLoading = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #94a3b8;
  gap: 12px;
  font-size: 13px;

  .spin {
    animation: spin 1s linear infinite;
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

const DrawerEmpty = styled.div`
  padding: 40px;
  text-align: center;
  color: #64748b;
  font-size: 14px;
`;

const DangerZone = styled.div`
  margin-top: 10px;
  padding-top: 16px;
  border-top: 1px solid rgba(239, 68, 68, 0.2);
  display: flex;
  justify-content: flex-end;

  .btn-delete-app {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.25);
    color: #f87171;
    padding: 7px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: rgba(239, 68, 68, 0.2);
    }
  }
`;
