import React, { useState } from 'react';
import styled from 'styled-components';
import { X, Plus, DollarSign, User, Mail, Phone, ExternalLink, Briefcase, Building2, MapPin, Flag } from 'lucide-react';
import { api } from '../../api/client';
import type { ApplicationItem, ApplicationStatus, ManualApplicationPayload } from '../../api/client';

interface AddApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplicationCreated: (app: ApplicationItem) => void;
}

const SOURCES = [
  'LinkedIn',
  'Indeed',
  'Company Website',
  'Referral',
  'Recruiter',
  'Glassdoor',
  'Welcome to the Jungle',
  'JobTeaser',
  'Email',
  'Other',
];

const STATUS_OPTIONS: Array<{ value: ApplicationStatus; label: string }> = [
  { value: 'applied', label: 'Applied' },
  { value: 'saved', label: 'Saved / Bookmarked' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: '1st_interview', label: '1st Interview' },
  { value: '2nd_interview', label: '2nd Interview' },
  { value: 'final_interview', label: 'Final Interview' },
  { value: 'offer', label: 'Offer Received' },
  { value: 'accepted', label: 'Offer Accepted' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'no_answer', label: 'No Answer / Ghosted' },
  { value: 'withdrawn', label: 'Withdrawn' },
];

export const AddApplicationModal: React.FC<AddApplicationModalProps> = ({
  isOpen,
  onClose,
  onApplicationCreated,
}) => {
  const [formData, setFormData] = useState<ManualApplicationPayload>({
    job_title: '',
    company_name: '',
    source: 'LinkedIn',
    status: 'applied',
    location: '',
    country: '',
    job_url: '',
    salary: '',
    employment_type: 'Full-time',
    priority: 'medium',
    recruiter: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    referral: '',
    notes: '',
    applied_at: new Date().toISOString().slice(0, 10),
    next_follow_up: '',
    interview_date: '',
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleChange = (field: keyof ManualApplicationPayload, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.job_title.trim() || !formData.company_name.trim()) {
      setError('Job title and Company name are required.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const payload: ManualApplicationPayload = {
        ...formData,
        job_title: formData.job_title.trim(),
        company_name: formData.company_name.trim(),
        applied_at: formData.applied_at ? `${formData.applied_at}T00:00:00` : undefined,
        interview_date: formData.interview_date ? `${formData.interview_date}:00` : undefined,
        next_follow_up: formData.next_follow_up || undefined,
      };

      const created = await api.createManualApplication(payload);
      onApplicationCreated(created);
      onClose();
    } catch (err: any) {
      console.error('Failed to create manual application:', err);
      setError(err.message || 'Failed to save application.');
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
              <h3>Add Tracked Application</h3>
              <p>Log a job application from LinkedIn, Indeed, Company Site, or a Recruiter.</p>
            </div>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </ModalHeader>

        <form onSubmit={handleSubmit}>
          <ModalBody>
            {error && <div className="error-alert">{error}</div>}

            {/* Core Job Details */}
            <SectionTitle>Position & Company</SectionTitle>
            <FormRow>
              <FormGroup className="flex-2">
                <label>Job Title *</label>
                <div className="input-with-icon">
                  <Briefcase size={16} />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Senior Frontend Engineer"
                    value={formData.job_title}
                    onChange={(e) => handleChange('job_title', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup className="flex-2">
                <label>Company Name *</label>
                <div className="input-with-icon">
                  <Building2 size={16} />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Stripe"
                    value={formData.company_name}
                    onChange={(e) => handleChange('company_name', e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            <FormRow>
              <FormGroup>
                <label>Application Source</label>
                <select
                  value={formData.source}
                  onChange={(e) => handleChange('source', e.target.value)}
                >
                  {SOURCES.map((src) => (
                    <option key={src} value={src}>
                      {src}
                    </option>
                  ))}
                </select>
              </FormGroup>

              <FormGroup>
                <label>Initial Status / Stage</label>
                <select
                  value={formData.status}
                  onChange={(e) => handleChange('status', e.target.value as ApplicationStatus)}
                >
                  {STATUS_OPTIONS.map((st) => (
                    <option key={st.value} value={st.value}>
                      {st.label}
                    </option>
                  ))}
                </select>
              </FormGroup>

              <FormGroup>
                <label>Priority</label>
                <select
                  value={formData.priority}
                  onChange={(e) => handleChange('priority', e.target.value)}
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </FormGroup>
            </FormRow>

            <FormRow>
              <FormGroup className="flex-2">
                <label>Job Posting URL</label>
                <div className="input-with-icon">
                  <ExternalLink size={16} />
                  <input
                    type="url"
                    placeholder="https://..."
                    value={formData.job_url || ''}
                    onChange={(e) => handleChange('job_url', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Application Date</label>
                <input
                  type="date"
                  value={formData.applied_at || ''}
                  onChange={(e) => handleChange('applied_at', e.target.value)}
                />
              </FormGroup>
            </FormRow>

            {/* Location & Compensation */}
            <SectionTitle>Location & Compensation</SectionTitle>
            <FormRow>
              <FormGroup>
                <label>Location (City / Remote)</label>
                <div className="input-with-icon">
                  <MapPin size={16} />
                  <input
                    type="text"
                    placeholder="e.g. Paris, France or Remote"
                    value={formData.location || ''}
                    onChange={(e) => handleChange('location', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Country</label>
                <div className="input-with-icon">
                  <Flag size={16} />
                  <input
                    type="text"
                    placeholder="e.g. France"
                    value={formData.country || ''}
                    onChange={(e) => handleChange('country', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Salary / Compensation</label>
                <div className="input-with-icon">
                  <DollarSign size={16} />
                  <input
                    type="text"
                    placeholder="e.g. €65,000 - €75,000"
                    value={formData.salary || ''}
                    onChange={(e) => handleChange('salary', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Employment Type</label>
                <select
                  value={formData.employment_type || 'Full-time'}
                  onChange={(e) => handleChange('employment_type', e.target.value)}
                >
                  <option value="Full-time">Full-time</option>
                  <option value="Part-time">Part-time</option>
                  <option value="Contract">Contract / Freelance</option>
                  <option value="Internship">Internship</option>
                  <option value="Apprenticeship">Apprenticeship</option>
                </select>
              </FormGroup>
            </FormRow>

            {/* Contacts & Dates */}
            <SectionTitle>Contacts & Follow-Up</SectionTitle>
            <FormRow>
              <FormGroup>
                <label>Contact / Recruiter Name</label>
                <div className="input-with-icon">
                  <User size={16} />
                  <input
                    type="text"
                    placeholder="e.g. Sarah Jenkins"
                    value={formData.contact_name || ''}
                    onChange={(e) => handleChange('contact_name', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Contact Email</label>
                <div className="input-with-icon">
                  <Mail size={16} />
                  <input
                    type="email"
                    placeholder="sarah@company.com"
                    value={formData.contact_email || ''}
                    onChange={(e) => handleChange('contact_email', e.target.value)}
                  />
                </div>
              </FormGroup>

              <FormGroup>
                <label>Contact Phone</label>
                <div className="input-with-icon">
                  <Phone size={16} />
                  <input
                    type="text"
                    placeholder="+33 6 12 34 56 78"
                    value={formData.contact_phone || ''}
                    onChange={(e) => handleChange('contact_phone', e.target.value)}
                  />
                </div>
              </FormGroup>
            </FormRow>

            <FormRow>
              <FormGroup>
                <label>Next Follow-up Date</label>
                <input
                  type="date"
                  value={formData.next_follow_up || ''}
                  onChange={(e) => handleChange('next_follow_up', e.target.value)}
                />
              </FormGroup>

              <FormGroup>
                <label>Interview Scheduled</label>
                <input
                  type="datetime-local"
                  value={formData.interview_date || ''}
                  onChange={(e) => handleChange('interview_date', e.target.value)}
                />
              </FormGroup>

              <FormGroup>
                <label>Referral / Referred By</label>
                <input
                  type="text"
                  placeholder="e.g. John Doe (Alumni)"
                  value={formData.referral || ''}
                  onChange={(e) => handleChange('referral', e.target.value)}
                />
              </FormGroup>
            </FormRow>

            <FormGroup>
              <label>Notes & Strategy</label>
              <textarea
                rows={3}
                placeholder="Key requirements, conversation notes, tech stack highlights, next steps..."
                value={formData.notes || ''}
                onChange={(e) => handleChange('notes', e.target.value)}
              />
            </FormGroup>
          </ModalBody>

          <ModalFooter>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Adding...' : 'Add Application'}
            </button>
          </ModalFooter>
        </form>
      </ModalContainer>
    </ModalBackdrop>
  );
};

const ModalBackdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 29, 0.75);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  overflow-y: auto;
`;

const ModalContainer = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  width: 100%;
  max-width: 780px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
  animation: modalFadeIn 0.2s ease-out;

  @keyframes modalFadeIn {
    from {
      opacity: 0;
      transform: translateY(12px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
`;

const ModalHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.8);

  .header-title {
    display: flex;
    align-items: center;
    gap: 0.875rem;

    .icon-wrapper {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #6366f1, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }

    h3 {
      margin: 0;
      font-size: 1.15rem;
      font-weight: 700;
      color: #f8fafc;
    }

    p {
      margin: 0.15rem 0 0;
      font-size: 0.8rem;
      color: #94a3b8;
    }
  }

  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 0.4rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #f8fafc;
    }
  }
`;

const ModalBody = styled.div`
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.15rem;

  .error-alert {
    padding: 0.75rem 1rem;
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    color: #fca5a5;
    font-size: 0.85rem;
  }
`;

const SectionTitle = styled.h4`
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6366f1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 0.4rem;
`;

const FormRow = styled.div`
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;

  @media (max-width: 640px) {
    flex-direction: column;
  }
`;

const FormGroup = styled.div<{ className?: string }>`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 140px;

  &.flex-2 {
    flex: 2;
  }

  label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #cbd5e1;
  }

  input,
  select,
  textarea {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
    color: #f8fafc;
    font-size: 0.875rem;
    outline: none;
    transition: all 0.15s ease;

    &:focus {
      border-color: #6366f1;
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
      background: rgba(30, 41, 59, 0.95);
    }
  }

  .input-with-icon {
    position: relative;
    display: flex;
    align-items: center;

    svg {
      position: absolute;
      left: 0.75rem;
      color: #94a3b8;
      pointer-events: none;
    }

    input {
      width: 100%;
      padding-left: 2.3rem;
    }
  }

  textarea {
    resize: vertical;
    min-height: 70px;
    font-family: inherit;
  }
`;

const ModalFooter = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.8);

  button {
    padding: 0.65rem 1.25rem;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    outline: none;

    &.btn-secondary {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #cbd5e1;

      &:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.12);
        color: #f8fafc;
      }
    }

    &.btn-primary {
      background: linear-gradient(135deg, #6366f1, #3b82f6);
      border: none;
      color: white;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);

      &:hover:not(:disabled) {
        opacity: 0.95;
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }
`;
