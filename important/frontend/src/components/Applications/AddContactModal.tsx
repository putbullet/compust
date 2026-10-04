import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  X,
  User,
  Building2,
  Briefcase,
  Mail,
  Phone,
  MapPin,
  Tag,
  AlertTriangle,
  Plus,
  MessageSquare,
  Calendar,
} from 'lucide-react';
import { api } from '../../api/client';
import type { ContactItem, ContactCreatePayload } from '../../api/client';
import { useTranslation } from '../../i18n';

const LinkedinIcon: React.FC<{ size?: number }> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

interface AddContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  onContactCreated: (newContact: ContactItem) => void;
  initialCompany?: string;
  applicationId?: number;
}

export const AddContactModal: React.FC<AddContactModalProps> = ({
  isOpen,
  onClose,
  onContactCreated,
  initialCompany = '',
  applicationId,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  // Basic Information
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState(initialCompany);
  const [role, setRole] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [location, setLocation] = useState('');
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');

  // Communication & Interaction state (distinguish identity from interaction)
  const [haveContacted, setHaveContacted] = useState<boolean>(false);
  const [contactMethod, setContactMethod] = useState<'email' | 'linkedin' | 'phone' | 'other'>('email');
  const [contactDate, setContactDate] = useState('');
  const [emailUsed, setEmailUsed] = useState('');
  const [responseReceived, setResponseReceived] = useState<boolean>(false);
  const [responseDate, setResponseDate] = useState('');
  const [responseNotes, setResponseNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Duplicate warning state
  const [duplicateWarning, setDuplicateWarning] = useState<{
    contact: ContactItem;
    match_reason: string;
  } | null>(null);

  useEffect(() => {
    if (initialCompany) {
      setCompany(initialCompany);
    }
  }, [initialCompany]);

  // When email is updated, auto-sync emailUsed if user hasn't explicitly customized it
  useEffect(() => {
    if (email && !emailUsed) {
      setEmailUsed(email);
    }
  }, [email, emailUsed]);

  // Debounced duplicate check when email, company, or LinkedIn changes
  useEffect(() => {
    if (!isOpen) {
      setDuplicateWarning(null);
      return;
    }

    if (!email.trim() && !linkedinUrl.trim()) {
      setDuplicateWarning(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const matches = await api.checkContactDuplicates({
          email: email.trim() || undefined,
          linkedin_url: linkedinUrl.trim() || undefined,
          company: company.trim() || undefined,
        });

        if (matches && matches.length > 0) {
          setDuplicateWarning(matches[0]);
        } else {
          setDuplicateWarning(null);
        }
      } catch (err) {
        console.warn('Duplicate check check failed:', err);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [email, linkedinUrl, company, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const fn = firstName.trim();
    const ln = lastName.trim();
    const fullName = `${fn} ${ln}`.trim();

    if (!fn) {
      setError(tApp.addContactFirstNameRequired || 'First name is required.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const payload: ContactCreatePayload = {
        name: fullName || fn,
        first_name: fn,
        last_name: ln || undefined,
        company: company.trim() || undefined,
        role: role.trim() || undefined,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        linkedin_url: linkedinUrl.trim() || undefined,
        location: location.trim() || undefined,
        notes: notes.trim() || undefined,
        tags: tags.trim() || undefined,
        application_id: applicationId,
        // Optional communication & relationship tracking
        contacted: haveContacted,
        contact_method: haveContacted ? contactMethod : undefined,
        contact_date: haveContacted && contactDate ? new Date(contactDate).toISOString() : undefined,
        email_used: haveContacted && contactMethod === 'email' ? (emailUsed.trim() || email.trim() || undefined) : undefined,
        response_received: haveContacted ? responseReceived : false,
        response_date: haveContacted && responseReceived && responseDate ? new Date(responseDate).toISOString() : undefined,
        response_notes: haveContacted && responseReceived && responseNotes.trim() ? responseNotes.trim() : undefined,
      };

      const created = await api.createContact(payload);
      onContactCreated(created);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save contact.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalBackdrop onClick={onClose}>
      <ModalContainer onClick={(e) => e.stopPropagation()}>
        <ModalHeader>
          <div className="header-title">
            <div className="icon-wrapper">
              <Plus size={20} />
            </div>
            <div>
              <h3>{tApp.addContactModalTitle}</h3>
              <p>{tApp.addContactModalSubtitle}</p>
            </div>
          </div>
          <button type="button" className="close-btn" onClick={onClose} aria-label={t.common.close}>
            <X size={18} />
          </button>
        </ModalHeader>

        <ModalForm onSubmit={handleSubmit}>
          <ModalBody>
            {error && <div className="error-alert">{error}</div>}

            {/* Smart Duplicate Warning */}
            {duplicateWarning && (
              <DuplicateAlert>
                <AlertTriangle size={18} className="warn-icon" />
                <div className="warn-text">
                  <strong>{tApp.addContactDuplicateWarning}:</strong>{' '}
                  {duplicateWarning.contact.first_name} {duplicateWarning.contact.last_name || ''}
                  {duplicateWarning.contact.company ? ` (${duplicateWarning.contact.company})` : ''}
                  <div className="sub-reason">
                    Matched on {duplicateWarning.match_reason}. Proceeding will create an additional record.
                  </div>
                </div>
              </DuplicateAlert>
            )}

            {/* SECTION 1: Contact Identity */}
            <SectionHeader>
              <User size={14} className="sec-icon text-blue" />
              <span>{tApp.addContactSecIdentity}</span>
            </SectionHeader>

            {/* Name row */}
            <FormRow>
              <FormGroup>
                <label>{tApp.addContactFirstName}</label>
                <div className="input-with-icon">
                  <User size={15} />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sarah"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>{tApp.addContactLastName}</label>
                <div className="input-with-icon">
                  <User size={15} />
                  <input
                    type="text"
                    placeholder="e.g. Connor"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            {/* Company & Role */}
            <FormRow>
              <FormGroup>
                <label>{tApp.addContactCompany}</label>
                <div className="input-with-icon">
                  <Building2 size={15} />
                  <input
                    type="text"
                    placeholder="e.g. Datadog"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>{tApp.addContactRole}</label>
                <div className="input-with-icon">
                  <Briefcase size={15} />
                  <input
                    type="text"
                    placeholder="e.g. Technical Recruiter"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            {/* Email & Phone (Both Optional) */}
            <FormRow>
              <FormGroup>
                <label>{tApp.addContactEmail}</label>
                <div className="input-with-icon">
                  <Mail size={15} />
                  <input
                    type="email"
                    placeholder="sarah@datadog.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>{tApp.addContactPhone}</label>
                <div className="input-with-icon">
                  <Phone size={15} />
                  <input
                    type="tel"
                    placeholder="+1 555 123 4567"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            {/* LinkedIn & Location (Both Optional) */}
            <FormRow>
              <FormGroup>
                <label>{tApp.addContactLinkedIn}</label>
                <div className="input-with-icon">
                  <LinkedinIcon size={15} />
                  <input
                    type="url"
                    placeholder="https://linkedin.com/in/..."
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>{tApp.addContactLocation}</label>
                <div className="input-with-icon">
                  <MapPin size={15} />
                  <input
                    type="text"
                    placeholder="e.g. Paris, France"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            {/* SECTION 2: Communication & Relationship (Optional CRM Tracker) */}
            <SectionHeader className="comm-section">
              <MessageSquare size={14} className="sec-icon text-amber" />
              <span>{tApp.addContactSecCommunication}</span>
            </SectionHeader>

            <CommBox>
              {/* Question: Have you contacted this person? */}
              <div className="comm-question-row">
                <span className="question-text">{tApp.addContactQuestionContacted}</span>
                <div className="toggle-group" role="radiogroup">
                  <button
                    type="button"
                    className={`toggle-btn ${!haveContacted ? 'active' : ''}`}
                    onClick={() => {
                      setHaveContacted(false);
                      setResponseReceived(false);
                    }}
                  >
                    {tApp.addContactOptionNo}
                  </button>
                  <button
                    type="button"
                    className={`toggle-btn ${haveContacted ? 'active' : ''}`}
                    onClick={() => setHaveContacted(true)}
                  >
                    {tApp.addContactOptionYes}
                  </button>
                </div>
              </div>

              {/* Conditional Interaction Fields when Contacted = Yes */}
              {haveContacted && (
                <ConditionalFields className="fade-in">
                  <FormRow>
                    <FormGroup>
                      <label>{tApp.addContactMethodLabel}</label>
                      <div className="method-pill-group">
                        <button
                          type="button"
                          className={`pill-btn ${contactMethod === 'email' ? 'active' : ''}`}
                          onClick={() => setContactMethod('email')}
                        >
                          <Mail size={12} />
                          <span>{tApp.commMethodEmail}</span>
                        </button>
                        <button
                          type="button"
                          className={`pill-btn ${contactMethod === 'linkedin' ? 'active' : ''}`}
                          onClick={() => setContactMethod('linkedin')}
                        >
                          <LinkedinIcon size={12} />
                          <span>{tApp.commMethodLinkedIn}</span>
                        </button>
                        <button
                          type="button"
                          className={`pill-btn ${contactMethod === 'phone' ? 'active' : ''}`}
                          onClick={() => setContactMethod('phone')}
                        >
                          <Phone size={12} />
                          <span>{tApp.commMethodPhone}</span>
                        </button>
                        <button
                          type="button"
                          className={`pill-btn ${contactMethod === 'other' ? 'active' : ''}`}
                          onClick={() => setContactMethod('other')}
                        >
                          <MessageSquare size={12} />
                          <span>{tApp.commMethodOther}</span>
                        </button>
                      </div>
                    </FormGroup>

                    <FormGroup>
                      <label>{tApp.addContactDateLabel}</label>
                      <div className="input-with-icon">
                        <Calendar size={15} />
                        <input
                          type="date"
                          value={contactDate}
                          onChange={(e) => setContactDate(e.target.value)}
                        />
                      </div>
                    </FormGroup>
                  </FormRow>

                  {/* If Email method selected, allow specifying email used */}
                  {contactMethod === 'email' && (
                    <FormGroup className="mt-2">
                      <label>{tApp.addContactEmailUsedLabel}</label>
                      <div className="input-with-icon">
                        <Mail size={15} />
                        <input
                          type="email"
                          placeholder={email || 'recruiter@company.com'}
                          value={emailUsed}
                          onChange={(e) => setEmailUsed(e.target.value)}
                        />
                      </div>
                    </FormGroup>
                  )}

                  {/* Response received question */}
                  <div className="response-question-row mt-3">
                    <span className="question-text">{tApp.addContactQuestionResponse}</span>
                    <div className="toggle-group" role="radiogroup">
                      <button
                        type="button"
                        className={`toggle-btn ${!responseReceived ? 'active' : ''}`}
                        onClick={() => setResponseReceived(false)}
                      >
                        {tApp.addContactOptionNo}
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn ${responseReceived ? 'active green' : ''}`}
                        onClick={() => setResponseReceived(true)}
                      >
                        {tApp.addContactOptionYes}
                      </button>
                    </div>
                  </div>

                  {/* If Response Received = Yes, show response date and notes */}
                  {responseReceived && (
                    <div className="response-details-box fade-in mt-2">
                      <FormRow>
                        <FormGroup>
                          <label>{tApp.addContactResponseDateLabel}</label>
                          <div className="input-with-icon">
                            <Calendar size={15} />
                            <input
                              type="date"
                              value={responseDate}
                              onChange={(e) => setResponseDate(e.target.value)}
                            />
                          </div>
                        </FormGroup>
                      </FormRow>

                      <FormGroup className="mt-2">
                        <label>{tApp.addContactResponseNotesLabel}</label>
                        <textarea
                          rows={2}
                          placeholder="e.g. Replied via email requesting resume and portfolio..."
                          value={responseNotes}
                          onChange={(e) => setResponseNotes(e.target.value)}
                        />
                      </FormGroup>
                    </div>
                  )}
                </ConditionalFields>
              )}
            </CommBox>

            {/* SECTION 3: Tags & Notes */}
            <SectionHeader className="tags-section">
              <Tag size={14} className="sec-icon text-slate" />
              <span>{tApp.addContactSecAdditional}</span>
            </SectionHeader>

            <FormGroup>
              <label>{tApp.addContactTags}</label>
              <div className="input-with-icon">
                <Tag size={15} />
                <input
                  type="text"
                  placeholder="e.g. Recruiter, Security, Referral, High Priority"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                />
              </div>
            </FormGroup>

            <FormGroup>
              <label>{tApp.addContactNotes}</label>
              <textarea
                rows={2}
                placeholder="Met at tech meetup, prefers email, follow-up scheduled..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </FormGroup>
          </ModalBody>

          <ModalFooter>
            <button type="button" className="cancel-btn" onClick={onClose} disabled={saving}>
              {t.common.cancel}
            </button>
            <button type="submit" className="submit-btn" disabled={saving}>
              {saving ? tApp.addContactBtnSaving : tApp.addContactBtnCreate}
            </button>
          </ModalFooter>
        </ModalForm>
      </ModalContainer>
    </ModalBackdrop>
  );
};

// Styled Components
const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 30, 0.78);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.15s ease-out;

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @media (max-width: 640px) {
    padding: 8px;
  }
`;

const ModalContainer = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  width: 100%;
  max-width: 620px;
  max-height: min(92vh, 860px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.65);
  animation: slideUp 0.2s ease-out;

  @keyframes slideUp {
    from {
      transform: translateY(12px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  @media (max-height: 720px) {
    max-height: calc(100vh - 16px);
    border-radius: 12px;
  }
`;

const ModalHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  background: #0f172a;

  @media (max-width: 640px) {
    padding: 14px 16px;
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;

    .icon-wrapper {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    h3 {
      font-size: 16px;
      font-weight: 600;
      color: #f8fafc;
      margin: 0;
    }

    p {
      font-size: 12.5px;
      color: #94a3b8;
      margin: 3px 0 0;
    }
  }

  .close-btn {
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    padding: 6px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    &:hover {
      color: #f8fafc;
      background: rgba(255, 255, 255, 0.08);
    }
  }
`;

const ModalForm = styled.form`
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
`;

const ModalBody = styled.div`
  padding: 20px 24px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scroll-behavior: smooth;

  /* Custom styled scrollbar for dark mode */
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 9999px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.28);
  }

  @media (max-width: 640px) {
    padding: 14px 16px;
    gap: 12px;
  }

  .error-alert {
    padding: 10px 14px;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    color: #fca5a5;
    font-size: 13px;
  }
`;

const SectionHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 4px;

  .sec-icon {
    flex-shrink: 0;
  }

  .text-blue {
    color: #38bdf8;
  }

  .text-amber {
    color: #f59e0b;
  }

  .text-slate {
    color: #a855f7;
  }
`;

const CommBox = styled.div`
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 14px 16px;

  .comm-question-row,
  .response-question-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;

    .question-text {
      font-size: 13px;
      font-weight: 500;
      color: #e2e8f0;
    }
  }

  .toggle-group {
    display: inline-flex;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 2px;
    gap: 2px;

    .toggle-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 12px;
      font-weight: 500;
      padding: 5px 12px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;

      &.active {
        background: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        font-weight: 600;

        &.green {
          background: rgba(16, 185, 129, 0.2);
          color: #34d399;
        }
      }

      &:hover:not(.active) {
        color: #f8fafc;
      }
    }
  }

  .fade-in {
    animation: fadeIn 0.2s ease-out;
  }

  .mt-2 {
    margin-top: 10px;
  }

  .mt-3 {
    margin-top: 14px;
  }
`;

const ConditionalFields = styled.div`
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);

  .method-pill-group {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;

    .pill-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      color: #94a3b8;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover {
        color: #f8fafc;
        border-color: rgba(255, 255, 255, 0.2);
      }

      &.active {
        background: rgba(245, 158, 11, 0.18);
        border-color: rgba(245, 158, 11, 0.4);
        color: #fbbf24;
        font-weight: 600;
      }
    }
  }

  .response-details-box {
    background: rgba(16, 185, 129, 0.04);
    border: 1px solid rgba(16, 185, 129, 0.15);
    border-radius: 8px;
    padding: 12px;
  }
`;

const FormRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;

  @media (max-width: 540px) {
    grid-template-columns: 1fr;
  }
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
  }

  .input-with-icon {
    position: relative;
    display: flex;
    align-items: center;

    svg {
      position: absolute;
      left: 11px;
      color: #64748b;
      pointer-events: none;
    }

    input {
      width: 100%;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 8px 12px 8px 34px;
      font-size: 13px;
      color: #f8fafc;
      transition: all 0.15s ease;

      &:focus {
        outline: none;
        border-color: #38bdf8;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
      }

      &::placeholder {
        color: #475569;
      }

      &[type='date'] {
        color-scheme: dark;
      }
    }
  }

  textarea {
    width: 100%;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #f8fafc;
    resize: vertical;
    transition: all 0.15s ease;

    &:focus {
      outline: none;
      border-color: #38bdf8;
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
    }

    &::placeholder {
      color: #475569;
    }
  }
`;

const DuplicateAlert = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 10px;
  padding: 10px 14px;

  .warn-icon {
    color: #fbbf24;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .warn-text {
    font-size: 12.5px;
    color: #fef3c7;
    line-height: 1.4;

    .sub-reason {
      font-size: 11.5px;
      color: #fde68a;
      margin-top: 2px;
    }
  }
`;

const ModalFooter = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: #0f172a;
  flex-shrink: 0;

  @media (max-width: 640px) {
    padding: 12px 16px;
  }

  button {
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .cancel-btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #94a3b8;

    &:hover {
      color: #f8fafc;
      background: rgba(255, 255, 255, 0.05);
    }
  }

  .submit-btn {
    background: #0284c7;
    border: 1px solid transparent;
    color: #ffffff;
    font-weight: 600;

    &:hover:not(:disabled) {
      background: #0369a1;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
`;
