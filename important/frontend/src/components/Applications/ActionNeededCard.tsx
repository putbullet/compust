import React, { useState } from 'react';
import styled from 'styled-components';
import {
  Clock,
  Calendar,
  Award,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Bell,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import type { ApplicationItem } from '../../api/client';
import { useTranslation } from '../../i18n';

interface ActionNeededCardProps {
  applications: ApplicationItem[];
  onSelectApplication: (app: ApplicationItem) => void;
  onFollowUpAction?: (appId: number, action: 'complete' | 'snooze', days?: number) => Promise<void>;
}

export const ActionNeededCard: React.FC<ActionNeededCardProps> = ({
  applications,
  onSelectApplication,
  onFollowUpAction,
}) => {
  const { t, language } = useTranslation();
  const tApp = t.applications;

  const [collapsed, setCollapsed] = useState(false);
  const [processingId, setProcessingId] = useState<number | null>(null);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const overdueFollowUps: Array<{ app: ApplicationItem; daysOverdue: number }> = [];
  const upcomingFollowUps: Array<{ app: ApplicationItem; daysUntil: number }> = [];
  const upcomingInterviews: Array<{ app: ApplicationItem; dateStr: string }> = [];
  const waitingResponse: Array<{ app: ApplicationItem; daysWaiting: number }> = [];
  const pendingOffers: ApplicationItem[] = [];

  applications.forEach((app) => {
    // 1. Follow-up checks
    if (app.next_follow_up) {
      const fuDate = new Date(app.next_follow_up);
      fuDate.setHours(0, 0, 0, 0);
      const diffDays = Math.round((fuDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays < 0) {
        overdueFollowUps.push({ app, daysOverdue: Math.abs(diffDays) });
      } else if (diffDays <= 7) {
        upcomingFollowUps.push({ app, daysUntil: diffDays });
      }
    }

    // 2. Upcoming Interviews
    if (app.interview_date) {
      const intDate = new Date(app.interview_date);
      if (intDate >= today) {
        upcomingInterviews.push({
          app,
          dateStr: intDate.toLocaleDateString(language === 'de' ? 'de-DE' : (language === 'fr' ? 'fr-FR' : 'en-US'), {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }),
        });
      }
    } else if (app.status === 'interviewing' || app.status === '1st_interview' || app.status === '2nd_interview') {
      // In interview status without explicit date
      if (!app.next_follow_up) {
        upcomingInterviews.push({
          app,
          dateStr: tApp.actionUpcomingInterviews,
        });
      }
    }

    // 3. Waiting Response (Applied > 7 days ago, still in 'applied' or 'no_answer')
    if (app.status === 'applied' || app.status === 'no_answer') {
      const appDate = app.applied_at ? new Date(app.applied_at) : new Date(app.created_at);
      const daysWaiting = Math.round((today.getTime() - appDate.getTime()) / (1000 * 60 * 60 * 24));
      if (daysWaiting >= 7 && !app.next_follow_up) {
        waitingResponse.push({ app, daysWaiting });
      }
    }

    // 4. Pending Offers
    if (app.status === 'offer') {
      pendingOffers.push(app);
    }
  });

  const totalActions =
    overdueFollowUps.length +
    upcomingFollowUps.length +
    upcomingInterviews.length +
    waitingResponse.length +
    pendingOffers.length;

  const handleQuickComplete = async (e: React.MouseEvent, appId: number) => {
    e.stopPropagation();
    if (!onFollowUpAction) return;
    try {
      setProcessingId(appId);
      await onFollowUpAction(appId, 'complete');
    } finally {
      setProcessingId(null);
    }
  };

  const handleQuickSnooze = async (e: React.MouseEvent, appId: number) => {
    e.stopPropagation();
    if (!onFollowUpAction) return;
    try {
      setProcessingId(appId);
      await onFollowUpAction(appId, 'snooze', 3);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <CardContainer className="glass-panel">
      <CardHeader onClick={() => setCollapsed(!collapsed)}>
        <div className="header-left">
          <div className="title-icon-badge">
            <Bell size={16} />
          </div>
          <div>
            <div className="title-row">
              <h4>{tApp.actionNeededTitle}</h4>
              {totalActions > 0 ? (
                <span className={`badge-counter ${overdueFollowUps.length > 0 ? 'urgent' : ''}`}>
                  {totalActions}
                </span>
              ) : (
                <span className="badge-all-clear">{tApp.actionNoActionsNeeded}</span>
              )}
            </div>
            <p className="subtitle">
              {tApp.actionNeededSubtitle}
            </p>
          </div>
        </div>

        <button type="button" className="collapse-toggle-btn" aria-label="Toggle section">
          {collapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </button>
      </CardHeader>

      {!collapsed && (
        <CardBody>
          {totalActions === 0 ? (
            <AllCaughtUpState>
              <div className="caught-up-icon">
                <Sparkles size={20} />
              </div>
              <div className="caught-up-text">
                <h5>{tApp.actionNoActionsNeeded}</h5>
                <p>{tApp.actionNeededSubtitle}</p>
              </div>
            </AllCaughtUpState>
          ) : (
            <ActionGrid>
              {/* Overdue Column */}
              {overdueFollowUps.length > 0 && (
                <ActionGroup className="overdue-group">
                  <div className="group-heading">
                    <span className="indicator-dot red" />
                    <span className="group-title">{overdueFollowUps.length} {tApp.actionOverdue}</span>
                  </div>
                  <div className="items-list">
                    {overdueFollowUps.map(({ app, daysOverdue }) => (
                      <ActionItem
                        key={app.id}
                        className="overdue"
                        onClick={() => onSelectApplication(app)}
                      >
                        <div className="item-main">
                          <div className="item-title">{app.effective_title}</div>
                          <div className="item-company">{app.effective_company}</div>
                          <div className="item-reason red-text">
                            {tApp.timeOverdueBy.replace('{n}', String(daysOverdue))}
                          </div>
                        </div>
                        <div className="quick-actions">
                          <button
                            type="button"
                            className="btn-quick done"
                            title={tApp.actionBtnComplete}
                            disabled={processingId === app.id}
                            onClick={(e) => handleQuickComplete(e, app.id)}
                          >
                            <CheckCircle size={13} />
                            <span>{tApp.actionBtnComplete}</span>
                          </button>
                          <button
                            type="button"
                            className="btn-quick snooze"
                            title={tApp.actionBtnSnooze}
                            disabled={processingId === app.id}
                            onClick={(e) => handleQuickSnooze(e, app.id)}
                          >
                            <Clock size={13} />
                            <span>+3d</span>
                          </button>
                        </div>
                      </ActionItem>
                    ))}
                  </div>
                </ActionGroup>
              )}

              {/* Upcoming Follow-ups */}
              {upcomingFollowUps.length > 0 && (
                <ActionGroup>
                  <div className="group-heading">
                    <span className="indicator-dot amber" />
                    <span className="group-title">{upcomingFollowUps.length} {tApp.actionFollowUp}</span>
                  </div>
                  <div className="items-list">
                    {upcomingFollowUps.map(({ app, daysUntil }) => (
                      <ActionItem
                        key={app.id}
                        onClick={() => onSelectApplication(app)}
                      >
                        <div className="item-main">
                          <div className="item-title">{app.effective_title}</div>
                          <div className="item-company">{app.effective_company}</div>
                          <div className="item-reason amber-text">
                            {daysUntil === 0
                              ? tApp.timeToday
                              : tApp.timeInDays.replace('{n}', String(daysUntil))}
                          </div>
                        </div>
                        <div className="quick-actions">
                          <button
                            type="button"
                            className="btn-quick done"
                            title={tApp.actionBtnComplete}
                            disabled={processingId === app.id}
                            onClick={(e) => handleQuickComplete(e, app.id)}
                          >
                            <CheckCircle size={13} />
                          </button>
                        </div>
                      </ActionItem>
                    ))}
                  </div>
                </ActionGroup>
              )}

              {/* Upcoming Interviews */}
              {upcomingInterviews.length > 0 && (
                <ActionGroup>
                  <div className="group-heading">
                    <span className="indicator-dot purple" />
                    <span className="group-title">{upcomingInterviews.length} {tApp.actionUpcomingInterviews}</span>
                  </div>
                  <div className="items-list">
                    {upcomingInterviews.map(({ app, dateStr }) => (
                      <ActionItem
                        key={app.id}
                        onClick={() => onSelectApplication(app)}
                      >
                        <div className="item-main">
                          <div className="item-title">{app.effective_title}</div>
                          <div className="item-company">{app.effective_company}</div>
                          <div className="item-reason purple-text">
                            <Calendar size={11} />
                            <span>{dateStr}</span>
                          </div>
                        </div>
                        <ArrowRight size={14} className="hover-arrow" />
                      </ActionItem>
                    ))}
                  </div>
                </ActionGroup>
              )}

              {/* Offers Awaiting Decision */}
              {pendingOffers.length > 0 && (
                <ActionGroup>
                  <div className="group-heading">
                    <span className="indicator-dot green" />
                    <span className="group-title">{pendingOffers.length} {tApp.stageOffer}</span>
                  </div>
                  <div className="items-list">
                    {pendingOffers.map((app) => (
                      <ActionItem
                        key={app.id}
                        className="offer-item"
                        onClick={() => onSelectApplication(app)}
                      >
                        <div className="item-main">
                          <div className="item-title">{app.effective_title}</div>
                          <div className="item-company">{app.effective_company}</div>
                          <div className="item-reason green-text">
                            <Award size={11} />
                            <span>{tApp.stageOffer} • {tApp.statOffers}</span>
                          </div>
                        </div>
                        <ArrowRight size={14} className="hover-arrow" />
                      </ActionItem>
                    ))}
                  </div>
                </ActionGroup>
              )}

              {/* Waiting For Response */}
              {waitingResponse.length > 0 && (
                <ActionGroup>
                  <div className="group-heading">
                    <span className="indicator-dot slate" />
                    <span className="group-title">{waitingResponse.length} {tApp.actionWaitingResponse}</span>
                  </div>
                  <div className="items-list">
                    {waitingResponse.slice(0, 4).map(({ app, daysWaiting }) => (
                      <ActionItem
                        key={app.id}
                        onClick={() => onSelectApplication(app)}
                      >
                        <div className="item-main">
                          <div className="item-title">{app.effective_title}</div>
                          <div className="item-company">{app.effective_company}</div>
                          <div className="item-reason slate-text">
                            {tApp.timeDaysAgo.replace('{n}', String(daysWaiting))} • {tApp.actionFollowUp}
                          </div>
                        </div>
                        <ArrowRight size={14} className="hover-arrow" />
                      </ActionItem>
                    ))}
                  </div>
                </ActionGroup>
              )}
            </ActionGrid>
          )}
        </CardBody>
      )}
    </CardContainer>
  );
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const CardContainer = styled.div`
  margin-bottom: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(12px);
  overflow: hidden;
  transition: all 0.2s ease;

  &:hover {
    border-color: rgba(255, 255, 255, 0.14);
  }
`;

const CardHeader = styled.div`
  padding: 1rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.85rem;
  }

  .title-icon-badge {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;

    h4 {
      margin: 0;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #e2e8f0;
    }
  }

  .subtitle {
    margin: 0.2rem 0 0;
    font-size: 0.78rem;
    color: #94a3b8;
  }

  .badge-counter {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.15rem 0.55rem;
    border-radius: 9999px;
    background: rgba(59, 130, 246, 0.18);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.3);

    &.urgent {
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border-color: rgba(239, 68, 68, 0.35);
    }
  }

  .badge-all-clear {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.15rem 0.55rem;
    border-radius: 9999px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }

  .collapse-toggle-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.4rem;
    border-radius: 6px;
    transition: all 0.15s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
    }
  }
`;

const CardBody = styled.div`
  padding: 0 1.25rem 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
`;

const ActionGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
`;

const ActionGroup = styled.div`
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 0.75rem;

  &.overdue-group {
    border-color: rgba(239, 68, 68, 0.2);
    background: rgba(239, 68, 68, 0.03);
  }

  .group-heading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }

  .group-title {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #cbd5e1;
  }

  .indicator-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;

    &.red {
      background: #ef4444;
      box-shadow: 0 0 6px #ef4444;
    }
    &.amber {
      background: #f59e0b;
    }
    &.purple {
      background: #a855f7;
    }
    &.green {
      background: #10b981;
    }
    &.slate {
      background: #64748b;
    }
  }

  .items-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
`;

const ActionItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(30, 41, 59, 0.85);
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateY(-1px);

    .hover-arrow {
      opacity: 1;
      transform: translateX(2px);
    }
  }

  &.overdue {
    border-left: 3px solid #ef4444;
  }

  &.offer-item {
    border-left: 3px solid #10b981;
  }

  .item-main {
    min-width: 0;
    flex: 1;
  }

  .item-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #f1f5f9;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .item-company {
    font-size: 0.72rem;
    color: #94a3b8;
    margin-top: 0.1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .item-reason {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.7rem;
    font-weight: 500;
    margin-top: 0.25rem;

    &.red-text {
      color: #f87171;
    }
    &.amber-text {
      color: #fbbf24;
    }
    &.purple-text {
      color: #c084fc;
    }
    &.green-text {
      color: #34d399;
    }
    &.slate-text {
      color: #94a3b8;
    }
  }

  .hover-arrow {
    color: #94a3b8;
    opacity: 0.4;
    transition: all 0.15s ease;
  }

  .quick-actions {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin-left: 0.6rem;
  }

  .btn-quick {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all 0.15s ease;

    &.done {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);

      &:hover {
        background: rgba(16, 185, 129, 0.25);
      }
    }

    &.snooze {
      background: rgba(148, 163, 184, 0.15);
      color: #cbd5e1;
      border: 1px solid rgba(148, 163, 184, 0.3);

      &:hover {
        background: rgba(148, 163, 184, 0.25);
      }
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
`;

const AllCaughtUpState = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1rem 0.5rem;

  .caught-up-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }

  .caught-up-text {
    h5 {
      margin: 0;
      font-size: 0.88rem;
      font-weight: 600;
      color: #f1f5f9;
    }
    p {
      margin: 0.2rem 0 0;
      font-size: 0.78rem;
      color: #94a3b8;
    }
  }
`;
