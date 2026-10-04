import React, { useState, useEffect, useMemo } from 'react';
import styled from 'styled-components';
import {
  User,
  Building2,
  Mail,
  Phone,
  MapPin,
  Search,
  Plus,
  Download,
  Upload,
  Clock,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../api/client';
import type { ContactItem } from '../../api/client';
import { AddContactModal } from './AddContactModal';
import { ImportContactsModal } from './ImportContactsModal';
import { ContactDetailDrawer } from './ContactDetailDrawer';
import { useTranslation } from '../../i18n';

const LinkedinIcon: React.FC<{ size?: number }> = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

interface ContactsViewProps {
  onOpenApplication?: (applicationId: number) => void;
}

export const ContactsView: React.FC<ContactsViewProps> = ({ onOpenApplication }) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('all');

  // Modals & Drawers
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null);

  const loadContacts = async () => {
    try {
      setLoading(true);
      const data = await api.getContacts();
      setContacts(data);
    } catch (err) {
      console.error('Failed to load contacts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
  }, []);

  const handleExportXlsx = async () => {
    try {
      setExporting(true);
      await api.exportContactsXlsx();
    } catch (err: any) {
      alert('Failed to export contacts to Excel: ' + (err.message || ''));
    } finally {
      setExporting(false);
    }
  };

  const handleContactCreated = (newContact: ContactItem) => {
    setContacts((prev) => [newContact, ...prev]);
  };

  const handleContactUpdated = (updated: ContactItem) => {
    setContacts((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  };

  const handleContactDeleted = (contactId: number) => {
    setContacts((prev) => prev.filter((c) => c.id !== contactId));
    if (selectedContactId === contactId) setSelectedContactId(null);
  };

  // Distinct companies for dropdown filter
  const distinctCompanies = useMemo(() => {
    const s = new Set<string>();
    contacts.forEach((c) => {
      if (c.company) s.add(c.company);
    });
    return Array.from(s).sort();
  }, [contacts]);

  // Filtered contacts
  const filteredContacts = useMemo(() => {
    return contacts.filter((c) => {
      if (selectedCompany !== 'all' && c.company !== selectedCompany) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const nameMatch = `${c.first_name} ${c.last_name || ''}`.toLowerCase().includes(q);
        const emailMatch = (c.email || '').toLowerCase().includes(q);
        const companyMatch = (c.company || '').toLowerCase().includes(q);
        const roleMatch = (c.role || '').toLowerCase().includes(q);
        const tagMatch = (c.tags || '').toLowerCase().includes(q);
        if (!nameMatch && !emailMatch && !companyMatch && !roleMatch && !tagMatch) {
          return false;
        }
      }
      return true;
    });
  }, [contacts, selectedCompany, searchQuery]);

  return (
    <Container id="contacts-top">
      {/* Top Action Bar */}
      <HeaderCard className="glass-panel">
        <div className="header-left">
          <h2>{tApp.contactsTitle}</h2>
          <p className="subtitle">{tApp.contactsSubtitle}</p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="action-btn export-btn"
            onClick={handleExportXlsx}
            disabled={exporting}
            title="Download contacts as styled Excel (.xlsx) file"
          >
            <Download size={15} />
            <span>{exporting ? tApp.exporting : tApp.btnExportContacts}</span>
          </button>

          <button
            type="button"
            className="action-btn import-btn"
            onClick={() => setIsImportModalOpen(true)}
            title="Import contacts from Excel file with smart duplicate prevention"
          >
            <Upload size={15} />
            <span>{tApp.btnImportContacts}</span>
          </button>

          <button
            type="button"
            className="action-btn add-btn"
            onClick={() => setIsAddModalOpen(true)}
          >
            <Plus size={16} />
            <span>{tApp.btnAddContact}</span>
          </button>

          <button
            type="button"
            className="refresh-btn"
            onClick={loadContacts}
            title={tApp.btnRefresh}
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </HeaderCard>

      {/* Control Bar: Search and Filters */}
      <ControlBar className="glass-panel">
        <div className="search-group">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder={tApp.contactsSearchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className="filter-select"
          >
            <option value="all">{tApp.contactsAllCompanies}</option>
            {distinctCompanies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </ControlBar>

      {/* Contacts List / Grid */}
      {loading ? (
        <LoadingBox className="glass-panel">
          <Clock className="spin" size={28} />
          <p>{tApp.contactsLoading}</p>
        </LoadingBox>
      ) : filteredContacts.length === 0 ? (
        <EmptyState className="glass-panel">
          <User size={36} />
          <h4>{tApp.contactsEmptyTitle}</h4>
          <p>
            {contacts.length === 0
              ? tApp.contactsEmptySubtitle
              : tApp.contactsEmptySearch}
          </p>
          {contacts.length === 0 && (
            <div className="empty-actions">
              <button
                type="button"
                className="btn-add-empty"
                onClick={() => setIsAddModalOpen(true)}
              >
                <Plus size={15} />
                <span>{tApp.contactsAddFirstBtn}</span>
              </button>
              <button
                type="button"
                className="btn-import-empty"
                onClick={() => setIsImportModalOpen(true)}
              >
                <Upload size={15} />
                <span>{tApp.contactsImportFirstBtn}</span>
              </button>
            </div>
          )}
        </EmptyState>
      ) : (
        <ContactsGrid>
          {filteredContacts.map((contact) => (
            <ContactCard
              key={contact.id}
              className="glass-panel"
              onClick={() => setSelectedContactId(contact.id)}
            >
              <div className="card-top">
                <div className="avatar-title">
                  <div className="avatar">
                    {contact.first_name ? contact.first_name[0] : (contact.name ? contact.name[0] : 'C')}
                    {contact.last_name ? contact.last_name[0] : ''}
                  </div>
                  <div className="name-block">
                    <h4 className="contact-name">
                      {contact.name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'Unnamed Contact'}
                    </h4>
                    <span className="role-title">
                      {contact.role ? `${contact.role}` : 'Contact'}
                    </span>
                  </div>
                </div>

                <ChevronRight size={16} className="chevron" />
              </div>

              <div className="company-and-location">
                {contact.company && (
                  <span className="company-badge">
                    <Building2 size={12} />
                    <span>{contact.company}</span>
                  </span>
                )}
                {contact.location && (
                  <span className="location-badge">
                    <MapPin size={11} />
                    <span>{contact.location}</span>
                  </span>
                )}
              </div>

              {/* Direct links */}
              <div className="contact-links" onClick={(e) => e.stopPropagation()}>
                {contact.email && (
                  <a href={`mailto:${contact.email}`} className="link-pill" title="Send email">
                    <Mail size={12} />
                    <span>{contact.email}</span>
                  </a>
                )}
                {contact.phone && (
                  <a href={`tel:${contact.phone}`} className="link-pill" title="Call">
                    <Phone size={12} />
                    <span>{contact.phone}</span>
                  </a>
                )}
                {contact.linkedin_url && (
                  <a
                    href={contact.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link-pill linkedin"
                    title="View LinkedIn"
                  >
                    <LinkedinIcon size={12} />
                    <span>LinkedIn</span>
                  </a>
                )}
              </div>

              {/* Factual insights strip */}
              {(() => {
                const isResponded = contact.communication_status === 'responded' || contact.has_responded;
                const isContactedNoResp = !isResponded && (contact.communication_status === 'contacted_no_response' || Boolean(contact.last_contacted_at));
                const badgeClass = isResponded ? 'green' : (isContactedNoResp ? 'amber' : 'slate');
                const badgeLabel = isResponded
                  ? tApp.commResponded
                  : (isContactedNoResp ? tApp.commContactedNoResponse : tApp.commNotContacted);

                return (
                  <div className="card-stats-strip">
                    <div className="stat-col">
                      <span className="stat-num">{contact.applications_count}</span>
                      <span className="stat-lbl">{tApp.funnelApplications}</span>
                    </div>
                    <div className="stat-col">
                      <span className="stat-num text-amber">{contact.responses_count}</span>
                      <span className="stat-lbl">{tApp.statResponseRate}</span>
                    </div>
                    <div className="stat-col">
                      <span className="stat-num text-purple">{contact.interviews_count}</span>
                      <span className="stat-lbl">{tApp.funnelInterviews}</span>
                    </div>
                    <div className="stat-col status-col">
                      <span className={`comm-badge ${badgeClass}`}>
                        {badgeLabel}
                      </span>
                    </div>
                  </div>
                );
              })()}
            </ContactCard>
          ))}
        </ContactsGrid>
      )}

      {/* Add Contact Modal */}
      <AddContactModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onContactCreated={handleContactCreated}
      />

      {/* Import Contacts Modal */}
      <ImportContactsModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImportSuccess={() => loadContacts()}
      />

      {/* Contact Detail Slide-Over Drawer */}
      <ContactDetailDrawer
        contactId={selectedContactId}
        isOpen={Boolean(selectedContactId)}
        onClose={() => setSelectedContactId(null)}
        onContactUpdated={handleContactUpdated}
        onContactDeleted={handleContactDeleted}
        onOpenApplication={(appId) => {
          setSelectedContactId(null);
          if (onOpenApplication) onOpenApplication(appId);
        }}
      />

      {/* Bottom anchor for smooth page navigation */}
      <div id="contacts-bottom" style={{ height: 1 }} />
    </Container>
  );
};

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: 18px;
`;

const HeaderCard = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  backdrop-filter: blur(12px);

  .header-left {
    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      color: #f8fafc;
    }

    .subtitle {
      margin: 4px 0 0;
      font-size: 13px;
      color: #94a3b8;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;

    .action-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;

      &.export-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #cbd5e1;

        &:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.1);
          color: #fff;
        }
      }

      &.import-btn {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #34d399;

        &:hover {
          background: rgba(16, 185, 129, 0.22);
        }
      }

      &.add-btn {
        background: #3b82f6;
        border: none;
        color: #fff;
        font-weight: 600;

        &:hover {
          background: #2563eb;
        }
      }
    }

    .refresh-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #94a3b8;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
      }
    }
  }
`;

const ControlBar = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  backdrop-filter: blur(12px);

  .search-group {
    flex: 1;
    min-width: 260px;
    position: relative;
    display: flex;
    align-items: center;

    .search-icon {
      position: absolute;
      left: 12px;
      color: #64748b;
      pointer-events: none;
    }

    input {
      width: 100%;
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f1f5f9;
      padding: 8px 12px 8px 36px;
      border-radius: 8px;
      font-size: 13px;

      &:focus {
        outline: none;
        border-color: #3b82f6;
      }
    }
  }

  .filter-group {
    .filter-select {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f1f5f9;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      cursor: pointer;

      &:focus {
        outline: none;
        border-color: #3b82f6;
      }
    }
  }
`;

const ContactsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
`;

const ContactCard = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: rgba(30, 41, 59, 0.6);
    border-color: rgba(59, 130, 246, 0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);

    .chevron {
      color: #38bdf8;
      transform: translateX(3px);
    }
  }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .avatar-title {
      display: flex;
      align-items: center;
      gap: 12px;

      .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: #fff;
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .name-block {
        .contact-name {
          margin: 0;
          font-size: 15px;
          font-weight: 600;
          color: #f8fafc;
        }

        .role-title {
          font-size: 12px;
          color: #94a3b8;
        }
      }
    }

    .chevron {
      color: #64748b;
      transition: all 0.15s;
    }
  }

  .company-and-location {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;

    .company-badge {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      font-weight: 500;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.2);
      padding: 2px 8px;
      border-radius: 4px;
    }

    .location-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #94a3b8;
    }
  }

  .contact-links {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    .link-pill {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #cbd5e1;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 3px 8px;
      border-radius: 4px;
      text-decoration: none;

      &.linkedin {
        color: #60a5fa;
        background: rgba(59, 130, 246, 0.08);
        border-color: rgba(59, 130, 246, 0.2);
      }

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
      }
    }
  }

  .card-stats-strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);

    .stat-col {
      display: flex;
      flex-direction: column;
      align-items: center;

      .stat-num {
        font-size: 14px;
        font-weight: 700;
        color: #f1f5f9;
      }

      .stat-lbl {
        font-size: 10px;
        color: #94a3b8;
        text-transform: uppercase;
      }

      .text-amber {
        color: #fbbf24;
      }
      .text-purple {
        color: #c084fc;
      }
    }

    .status-col {
      .comm-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
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
`;

const LoadingBox = styled.div`
  height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #94a3b8;
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

const EmptyState = styled.div`
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #64748b;

  svg {
    margin-bottom: 12px;
  }

  h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #f1f5f9;
  }

  p {
    margin: 6px 0 20px 0;
    font-size: 13px;
    color: #94a3b8;
    max-width: 400px;
  }

  .empty-actions {
    display: flex;
    gap: 12px;

    button {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      cursor: pointer;
    }

    .btn-add-empty {
      background: #3b82f6;
      border: none;
      color: #fff;
      font-weight: 600;
    }

    .btn-import-empty {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #cbd5e1;
    }
  }
`;
