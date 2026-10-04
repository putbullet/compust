import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  X,
  Briefcase,
  Mail,
  Phone,
  MapPin,
  Clock,
  Plus,
  Trash2,
  ExternalLink,
  MessageSquare,
  CheckCircle2,
  Tag,
  ArrowRight,
  Edit2,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  ContactItem,
  ContactUpdatePayload,
  ContactInteractionPayload,
} from '../../api/client';
import { useTranslation } from '../../i18n';

const LinkedinIcon: React.FC<{ size?: number }> = ({ size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

interface ContactDetailDrawerProps {
  contactId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onContactUpdated: (updated: ContactItem) => void;
  onContactDeleted: (contactId: number) => void;
  onOpenApplication?: (applicationId: number) => void;
}

const INTERACTION_TYPES = [
  { value: 'email_sent', label: 'Email Sent' },
  { value: 'email_received', label: 'Email Received' },
  { value: 'linkedin_message', label: 'LinkedIn Message' },
  { value: 'phone_call', label: 'Phone Call' },
  { value: 'meeting', label: 'Meeting / Screen' },
  { value: 'interview', label: 'Interview' },
  { value: 'follow_up', label: 'Follow-Up' },
  { value: 'note', label: 'General Note' },
];

export const ContactDetailDrawer: React.FC<ContactDetailDrawerProps> = ({
  contactId,
  isOpen,
  onClose,
  onContactUpdated,
  onContactDeleted,
  onOpenApplication,
}) => {
  const { t, language } = useTranslation();
  const tApp = t.applications;
  const localeCode = language === 'fr' ? 'fr-FR' : (language === 'de' ? 'de-DE' : 'en-US');

  const [contact, setContact] = useState<ContactItem | null>(null);
  const [loading, setLoading] = useState(false);

  // Interaction logging form state
  const [showLogInteraction, setShowLogInteraction] = useState(false);
  const [interactionType, setInteractionType] = useState('email_sent');
  const [interactionNotes, setInteractionNotes] = useState('');
  const [interactionResponded, setInteractionResponded] = useState(false);
  const [loggingInteraction, setLoggingInteraction] = useState(false);

  // Edit contact state
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<ContactUpdatePayload>({});
  const [savingEdit, setSavingEdit] = useState(false);

  const loadContact = async () => {
    if (!contactId) return;
    setLoading(true);
    try {
      const data = await api.getContact(contactId);
      setContact(data);
      setEditFormData({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        name: data.name || '',
        email: data.email || '',
        phone: data.phone || '',
        company: data.company || '',
        role: data.role || '',
        linkedin_url: data.linkedin_url || '',
        location: data.location || '',
        notes: data.notes || '',
        tags: data.tags || '',
      });
    } catch (err: any) {
      console.error('Failed to load contact details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (contactId && isOpen) {
      loadContact();
      setShowLogInteraction(false);
      setIsEditing(false);
    } else {
      setContact(null);
    }
  }, [contactId, isOpen]);

  if (!isOpen) return null;

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contact) return;
    try {
      setSavingEdit(true);
      const updated = await api.updateContact(contact.id, editFormData);
      setContact(updated);
      setIsEditing(false);
      onContactUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to update contact');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleLogInteraction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contact) return;

    try {
      setLoggingInteraction(true);
      const payload: ContactInteractionPayload = {
        type: interactionType,
        summary: interactionNotes.trim()
          ? interactionNotes.trim().slice(0, 100)
          : interactionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        details: interactionNotes.trim() || undefined,
        interaction_date: new Date().toISOString(),
      };

      await api.logContactInteraction(contact.id, payload);
      await loadContact();
      // Inform parent view of updated contact insights
      if (contact) {
        const fresh = await api.getContact(contact.id);
        onContactUpdated(fresh);
      }
      setInteractionNotes('');
      setShowLogInteraction(false);
    } catch (err: any) {
      alert(err.message || 'Failed to log interaction');
    } finally {
      setLoggingInteraction(false);
    }
  };

  const handleDeleteInteraction = async (interactionId: number) => {
    if (!confirm('Delete this interaction log?')) return;
    try {
      await api.deleteContactInteraction(interactionId);
      await loadContact();
    } catch (err: any) {
      alert('Failed to delete interaction');
    }
  };

  const handleDeleteContact = async () => {
    if (!contact) return;
    if (!confirm(`Are you sure you want to remove contact ${contact.first_name} ${contact.last_name || ''}?`)) return;

    try {
      await api.deleteContact(contact.id);
      onContactDeleted(contact.id);
      onClose();
    } catch (err: any) {
      alert('Failed to delete contact');
    }
  };

  return (
    <DrawerBackdrop onClick={onClose}>
      <DrawerContainer onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <DrawerHeader>
          <div className="header-top-row">
            <div className="avatar-and-name">
              <div className="contact-avatar-lg">
                {contact?.first_name ? contact.first_name[0] : (contact?.name ? contact.name[0] : 'C')}
                {contact?.last_name ? contact.last_name[0] : ''}
              </div>
              <div>
                <h3 className="name">
                  {contact?.name || `${contact?.first_name || ''} ${contact?.last_name || ''}`.trim() || 'Unnamed Contact'}
                </h3>
                <p className="role-company">
                  {contact?.role ? `${contact.role} — ` : ''}
                  <span className="company">{contact?.company || 'No Company'}</span>
                </p>
              </div>
            </div>

            <div className="header-actions">
              <button
                type="button"
                className="edit-contact-btn"
                onClick={() => setIsEditing(!isEditing)}
                title="Edit contact info"
              >
                <Edit2 size={15} />
              </button>
              <button type="button" className="close-btn" onClick={onClose} title="Close drawer">
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Quick contact buttons */}
          <div className="quick-contact-links">
            {contact?.email && (
              <a href={`mailto:${contact.email}`} className="quick-link">
                <Mail size={13} />
                <span>{contact.email}</span>
              </a>
            )}
            {contact?.phone && (
              <a href={`tel:${contact.phone}`} className="quick-link">
                <Phone size={13} />
                <span>{contact.phone}</span>
              </a>
            )}
            {contact?.linkedin_url && (
              <a
                href={contact.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="quick-link linkedin"
              >
                <LinkedinIcon size={13} />
                <span>LinkedIn</span>
                <ExternalLink size={11} />
              </a>
            )}
            {contact?.location && (
              <span className="location-chip">
                <MapPin size={12} />
                <span>{contact.location}</span>
              </span>
            )}
          </div>
        </DrawerHeader>

        {loading ? (
          <DrawerLoading>
            <Clock className="spin" size={28} />
            <p>Loading contact details & history...</p>
          </DrawerLoading>
        ) : !contact ? (
          <DrawerEmpty>Contact not found.</DrawerEmpty>
        ) : (
          <DrawerBody>
            {/* Inline Edit Form */}
            {isEditing && (
              <EditCard>
                <div className="edit-header">
                  <h4>Edit Contact Info</h4>
                  <button type="button" onClick={() => setIsEditing(false)} className="close-edit">
                    <X size={14} />
                  </button>
                </div>
                <form onSubmit={handleSaveEdit}>
                  <div className="grid-2">
                    <div className="form-field">
                      <label>First Name</label>
                      <input
                        type="text"
                        value={editFormData.first_name || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, first_name: e.target.value })}
                        required
                      />
                    </div>
                    <div className="form-field">
                      <label>Last Name</label>
                      <input
                        type="text"
                        value={editFormData.last_name || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, last_name: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="grid-2">
                    <div className="form-field">
                      <label>Company</label>
                      <input
                        type="text"
                        value={editFormData.company || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, company: e.target.value })}
                      />
                    </div>
                    <div className="form-field">
                      <label>Role / Title</label>
                      <input
                        type="text"
                        value={editFormData.role || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="grid-2">
                    <div className="form-field">
                      <label>Email</label>
                      <input
                        type="email"
                        value={editFormData.email || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                      />
                    </div>
                    <div className="form-field">
                      <label>Phone</label>
                      <input
                        type="tel"
                        value={editFormData.phone || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="form-field">
                    <label>LinkedIn URL</label>
                    <input
                      type="url"
                      value={editFormData.linkedin_url || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, linkedin_url: e.target.value })}
                    />
                  </div>

                  <div className="form-field">
                    <label>Tags (comma separated)</label>
                    <input
                      type="text"
                      value={editFormData.tags || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, tags: e.target.value })}
                    />
                  </div>

                  <div className="form-field">
                    <label>Notes</label>
                    <textarea
                      rows={2}
                      value={editFormData.notes || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, notes: e.target.value })}
                    />
                  </div>

                  <div className="edit-actions">
                    <button type="button" onClick={() => setIsEditing(false)} className="btn-cancel">
                      Cancel
                    </button>
                    <button type="submit" disabled={savingEdit} className="btn-save">
                      {savingEdit ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </EditCard>
            )}

            {/* Factual Insights Strip */}
            {(() => {
              const isResponded = contact.communication_status === 'responded' || contact.has_responded;
              const isContactedNoResp = !isResponded && (contact.communication_status === 'contacted_no_response' || Boolean(contact.last_contacted_at));
              const pillClass = isResponded ? 'green' : (isContactedNoResp ? 'amber' : 'slate');
              const pillLabel = isResponded
                ? tApp.commResponded
                : (isContactedNoResp ? tApp.commContactedNoResponse : tApp.commNotContacted);

              return (
                <InsightsStrip>
                  <div className="insight-item">
                    <span className="num">{contact.applications_count}</span>
                    <span className="lbl">{tApp.funnelApplications}</span>
                  </div>
                  <div className="insight-item">
                    <span className="num text-amber">{contact.responses_count}</span>
                    <span className="lbl">{tApp.statResponseRate}</span>
                  </div>
                  <div className="insight-item">
                    <span className="num text-purple">{contact.interviews_count}</span>
                    <span className="lbl">{tApp.funnelInterviews}</span>
                  </div>
                  <div className="insight-item">
                    <span className={`status-pill ${pillClass}`}>
                      {pillLabel}
                    </span>
                    <span className="lbl">{tApp.commStateLabel}</span>
                  </div>
                </InsightsStrip>
              );
            })()}

            {/* Communication Response Tracking Summary */}
            <ResponseSummaryCard>
              <div className="summary-col">
                <span className="col-label">{tApp.commLastContacted}</span>
                <span className="col-val">
                  {contact.last_contacted_at
                    ? new Date(contact.last_contacted_at).toLocaleDateString(localeCode, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })
                    : tApp.commNotContacted}
                </span>
              </div>
              <div className="summary-col">
                <span className="col-label">{tApp.commLastResponse}</span>
                <span className="col-val">
                  {contact.last_response_at
                    ? new Date(contact.last_response_at).toLocaleDateString(localeCode, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })
                    : tApp.actionNoResponse}
                </span>
              </div>
              <div className="summary-col">
                <span className="col-label">{tApp.commNextAction}</span>
                <span className="col-val text-blue">
                  {contact.next_action || tApp.actionNextStep}
                </span>
              </div>
            </ResponseSummaryCard>

            {/* Related Applications (2-Way Navigation) */}
            <SectionCard>
              <SectionHeader>
                <div className="title-with-icon">
                  <Briefcase size={16} className="text-blue" />
                  <h4>Related Applications ({contact.related_applications?.length || 0})</h4>
                </div>
              </SectionHeader>

              {(!contact.related_applications || contact.related_applications.length === 0) ? (
                <EmptySubSection>
                  <p>No job applications directly linked to this contact yet.</p>
                </EmptySubSection>
              ) : (
                <div className="related-apps-list">
                  {contact.related_applications.map((app) => (
                    <div
                      key={app.id}
                      className="related-app-item"
                      onClick={() => onOpenApplication && onOpenApplication(app.id)}
                      title="Click to view application workspace"
                    >
                      <div className="app-info">
                        <span className="app-title">{app.job_title}</span>
                        <span className="app-company">{app.company_name}</span>
                      </div>
                      <div className="app-meta">
                        <span className={`stage-badge ${app.status}`}>{app.status}</span>
                        <ArrowRight size={14} className="arrow-icon" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            {/* Contact Activity / Interactions */}
            <SectionCard>
              <SectionHeader>
                <div className="title-with-icon">
                  <MessageSquare size={16} className="text-purple" />
                  <h4>Contact Activity & Interactions</h4>
                </div>
                <button
                  type="button"
                  className="btn-toggle-log"
                  onClick={() => setShowLogInteraction(!showLogInteraction)}
                >
                  <Plus size={14} />
                  <span>{showLogInteraction ? 'Cancel' : 'Log Interaction'}</span>
                </button>
              </SectionHeader>

              {/* Log interaction form */}
              {showLogInteraction && (
                <LogForm onSubmit={handleLogInteraction}>
                  <div className="form-row">
                    <select
                      value={interactionType}
                      onChange={(e) => setInteractionType(e.target.value)}
                      className="select-type"
                    >
                      {INTERACTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>

                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={interactionResponded}
                        onChange={(e) => setInteractionResponded(e.target.checked)}
                      />
                      <span>Mark as Response Received</span>
                    </label>
                  </div>

                  <textarea
                    rows={2}
                    placeholder="Details about the email, discussion points, recruiter questions..."
                    value={interactionNotes}
                    onChange={(e) => setInteractionNotes(e.target.value)}
                    className="notes-area"
                  />

                  <div className="form-actions">
                    <button type="submit" disabled={loggingInteraction} className="btn-save-interaction">
                      {loggingInteraction ? 'Saving...' : 'Record Interaction'}
                    </button>
                  </div>
                </LogForm>
              )}

              {/* Interactions list */}
              <div className="interactions-timeline">
                {(!contact.interactions || contact.interactions.length === 0) ? (
                  <EmptySubSection>
                    <p>No interactions logged yet. Log calls, emails sent, or interview notes above.</p>
                  </EmptySubSection>
                ) : (
                  contact.interactions.map((inter) => (
                    <div key={inter.id} className="interaction-row">
                      <div className="interaction-icon-box">
                        <MessageSquare size={14} />
                      </div>
                      <div className="interaction-content">
                        <div className="content-top">
                          <span className="interaction-type">
                            {inter.type.replace(/_/g, ' ').toUpperCase()}
                          </span>
                          <div className="top-right">
                            <span className="timestamp">
                              {new Date(inter.interaction_date).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            <button
                              type="button"
                              className="delete-inter-btn"
                              onClick={() => handleDeleteInteraction(inter.id)}
                              title="Delete log"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>
                        {inter.summary && <p className="notes-text" style={{ fontWeight: 600, marginBottom: 2 }}>{inter.summary}</p>}
                        {inter.details && <p className="notes-text" style={{ opacity: 0.85 }}>{inter.details}</p>}
                        {(inter.type === 'email_received' || inter.summary?.toLowerCase().includes('response')) && (
                          <span className="response-flag">
                            <CheckCircle2 size={11} /> Response Received
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            {/* Notes Section */}
            {contact.notes && (
              <SectionCard>
                <SectionHeader>
                  <div className="title-with-icon">
                    <Tag size={16} className="text-slate" />
                    <h4>Contact Notes</h4>
                  </div>
                </SectionHeader>
                <p className="notes-box">{contact.notes}</p>
              </SectionCard>
            )}

            {/* Danger Zone */}
            <DangerZone>
              <button type="button" className="btn-delete" onClick={handleDeleteContact}>
                <Trash2 size={14} />
                <span>Remove Contact</span>
              </button>
            </DangerZone>
          </DrawerBody>
        )}
      </DrawerContainer>
    </DrawerBackdrop>
  );
};

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
    align-items: flex-start;
    margin-bottom: 16px;

    .avatar-and-name {
      display: flex;
      align-items: center;
      gap: 14px;

      .contact-avatar-lg {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: #ffffff;
        font-size: 17px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
      }

      .name {
        margin: 0;
        font-size: 19px;
        font-weight: 700;
        color: #f8fafc;
      }

      .role-company {
        margin: 2px 0 0;
        font-size: 13px;
        color: #94a3b8;

        .company {
          color: #38bdf8;
          font-weight: 500;
        }
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;

      button {
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
  }

  .quick-contact-links {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .quick-link {
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

      &.linkedin {
        color: #60a5fa;
        background: rgba(59, 130, 246, 0.08);
        border-color: rgba(59, 130, 246, 0.2);
      }

      &:hover {
        filter: brightness(1.2);
      }
    }

    .location-chip {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #94a3b8;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 4px 10px;
    }
  }
`;

const DrawerBody = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
`;

const InsightsStrip = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 12px 14px;

  .insight-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;

    .num {
      font-size: 18px;
      font-weight: 700;
      color: #f1f5f9;
    }

    .lbl {
      font-size: 10px;
      color: #94a3b8;
      margin-top: 2px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .text-amber {
      color: #fbbf24;
    }
    .text-purple {
      color: #c084fc;
    }

    .status-pill {
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

  @media (max-width: 500px) {
    grid-template-columns: 1fr 1fr;
  }
`;

const ResponseSummaryCard = styled.div`
  display: flex;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 10px 16px;

  .summary-col {
    display: flex;
    flex-direction: column;

    .col-label {
      font-size: 10px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .col-val {
      font-size: 12px;
      font-weight: 600;
      color: #f1f5f9;
      margin-top: 2px;

      &.text-blue {
        color: #38bdf8;
      }
    }
  }
`;

const SectionCard = styled.div`
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 16px 18px;

  .text-blue {
    color: #38bdf8;
  }
  .text-purple {
    color: #a855f7;
  }
  .text-slate {
    color: #94a3b8;
  }

  .notes-box {
    margin: 0;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.5;
  }

  .related-apps-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 10px;

    .related-app-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 9px 12px;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        background: rgba(59, 130, 246, 0.1);
        border-color: rgba(59, 130, 246, 0.3);

        .arrow-icon {
          transform: translateX(3px);
          color: #38bdf8;
        }
      }

      .app-info {
        display: flex;
        flex-direction: column;

        .app-title {
          font-size: 13px;
          font-weight: 600;
          color: #f1f5f9;
        }

        .app-company {
          font-size: 11px;
          color: #94a3b8;
        }
      }

      .app-meta {
        display: flex;
        align-items: center;
        gap: 8px;

        .stage-badge {
          font-size: 11px;
          padding: 2px 7px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.08);
          color: #cbd5e1;
        }

        .arrow-icon {
          color: #64748b;
          transition: transform 0.15s;
        }
      }
    }
  }

  .interactions-timeline {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 12px;

    .interaction-row {
      display: flex;
      gap: 12px;
      background: rgba(15, 23, 42, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 10px 12px;

      .interaction-icon-box {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .interaction-content {
        flex: 1;

        .content-top {
          display: flex;
          justify-content: space-between;
          align-items: baseline;

          .interaction-type {
            font-size: 11px;
            font-weight: 700;
            color: #c084fc;
            letter-spacing: 0.5px;
          }

          .top-right {
            display: flex;
            align-items: center;
            gap: 8px;

            .timestamp {
              font-size: 11px;
              color: #64748b;
            }

            .delete-inter-btn {
              background: transparent;
              border: none;
              color: #64748b;
              cursor: pointer;
              padding: 2px;

              &:hover {
                color: #f87171;
              }
            }
          }
        }

        .notes-text {
          margin: 4px 0 0;
          font-size: 12px;
          color: #cbd5e1;
          line-height: 1.4;
        }

        .response-flag {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 10px;
          color: #34d399;
          margin-top: 6px;
          background: rgba(16, 185, 129, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
        }
      }
    }
  }
`;

const SectionHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

  .title-with-icon {
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

  .btn-toggle-log {
    display: flex;
    align-items: center;
    gap: 4px;
    background: transparent;
    border: none;
    color: #a855f7;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
`;

const LogForm = styled.form`
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;

  .form-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;

    .select-type {
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #f1f5f9;
      font-size: 12px;
      padding: 6px 10px;
      border-radius: 6px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #cbd5e1;
      cursor: pointer;
    }
  }

  .notes-area {
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #f1f5f9;
    font-size: 12px;
    padding: 8px 10px;
    border-radius: 6px;
    resize: vertical;

    &:focus {
      outline: none;
      border-color: #a855f7;
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;

    .btn-save-interaction {
      background: #a855f7;
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;

      &:hover:not(:disabled) {
        background: #9333ea;
      }
      &:disabled {
        opacity: 0.5;
      }
    }
  }
`;

const EditCard = styled.div`
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  padding: 16px;

  .edit-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    h4 {
      margin: 0;
      font-size: 14px;
      color: #f8fafc;
    }

    .close-edit {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
    }
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: 4px;

      label {
        font-size: 11px;
        color: #94a3b8;
      }

      input,
      textarea {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f1f5f9;
        font-size: 12px;
        padding: 6px 8px;
        border-radius: 6px;

        &:focus {
          outline: none;
          border-color: #3b82f6;
        }
      }
    }

    .edit-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 6px;

      button {
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 12px;
        cursor: pointer;
      }

      .btn-cancel {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #94a3b8;
      }

      .btn-save {
        background: #3b82f6;
        border: none;
        color: #fff;
        font-weight: 600;
      }
    }
  }
`;

const EmptySubSection = styled.div`
  padding: 12px 0;
  p {
    margin: 0;
    font-size: 12px;
    color: #64748b;
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

  .btn-delete {
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

    &:hover {
      background: rgba(239, 68, 68, 0.2);
    }
  }
`;
