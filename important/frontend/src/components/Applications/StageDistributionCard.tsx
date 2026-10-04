import React from 'react';
import styled from 'styled-components';
import {
  GitCommit,
  Bookmark,
  Send,
  Calendar,
  Award,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { useTranslation } from '../../i18n';

interface StageDistributionCardProps {
  statusBreakdown?: Record<string, number>;
  totalApplications: number;
  selectedStatus?: string;
  onSelectStatus?: (status: string) => void;
  loading?: boolean;
}

interface StageConfig {
  id: string;
  label: string;
  icon: any;
  color: string;
  bg: string;
  description: string;
}

const STAGE_CONFIGS: StageConfig[] = [
  {
    id: 'applied',
    label: 'Applied',
    icon: Send,
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.15)',
    description: 'Submitted applications awaiting employer response',
  },
  {
    id: 'interviewing',
    label: '1st Interview',
    icon: Calendar,
    color: '#a855f7',
    bg: 'rgba(168, 85, 247, 0.15)',
    description: 'Initial recruiter screen or first technical round',
  },
  {
    id: '2nd_interview',
    label: '2nd / Technical Interview',
    icon: Clock,
    color: '#818cf8',
    bg: 'rgba(129, 140, 248, 0.15)',
    description: 'In-depth technical screen, take-home, or panel interview',
  },
  {
    id: 'final_interview',
    label: 'Final Interview',
    icon: GitCommit,
    color: '#c084fc',
    bg: 'rgba(192, 132, 252, 0.15)',
    description: 'Executive, leadership, or team-fit final evaluation',
  },
  {
    id: 'offer',
    label: 'Offer Received',
    icon: Award,
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.15)',
    description: 'Formal job offer extended awaiting decision',
  },
  {
    id: 'accepted',
    label: 'Accepted',
    icon: CheckCircle2,
    color: '#059669',
    bg: 'rgba(5, 150, 105, 0.15)',
    description: 'Offer signed and accepted',
  },
  {
    id: 'saved',
    label: 'Saved / Bookmarked',
    icon: Bookmark,
    color: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.15)',
    description: 'Bookmarked opportunities to tailor resume for',
  },
  {
    id: 'rejected',
    label: 'Archived / Rejected',
    icon: XCircle,
    color: '#64748b',
    bg: 'rgba(100, 116, 139, 0.15)',
    description: 'Positions closed, withdrawn, or rejected',
  },
];

export const StageDistributionCard: React.FC<StageDistributionCardProps> = ({
  statusBreakdown = {},
  totalApplications,
  selectedStatus = 'all',
  onSelectStatus,
  loading,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  const getStageLabel = (id: string, defaultLabel: string): string => {
    switch (id) {
      case 'applied': return tApp.stageApplied;
      case 'interviewing': return tApp.stage1stInterview;
      case '2nd_interview': return tApp.stage2ndInterview;
      case 'final_interview': return tApp.stageFinalInterview;
      case 'offer': return tApp.stageOffer;
      case 'accepted': return tApp.stageAccepted;
      case 'saved': return tApp.stageSaved;
      case 'rejected': return tApp.stageRejected;
      default: return defaultLabel;
    }
  };

  if (loading) {
    return (
      <CardContainer className="glass-panel">
        <LoadingText>Calculating stage progression distribution...</LoadingText>
      </CardContainer>
    );
  }

  // Aggregate interviewing counts
  const getStageCount = (stageId: string): number => {
    if (stageId === 'interviewing') {
      return (statusBreakdown['interviewing'] || 0) + (statusBreakdown['1st_interview'] || 0);
    }
    if (stageId === 'rejected') {
      return (
        (statusBreakdown['rejected'] || 0) +
        (statusBreakdown['withdrawn'] || 0) +
        (statusBreakdown['no_answer'] || 0)
      );
    }
    return statusBreakdown[stageId] || 0;
  };

  const denominator = Math.max(totalApplications, 1);

  return (
    <CardContainer className="glass-panel">
      <CardHeader>
        <div className="title-row">
          <GitCommit size={16} className="header-icon" />
          <h4>{tApp.analyticsStageTitle}</h4>
        </div>
        <p className="subtitle">
          {tApp.analyticsStageSubtitle}
        </p>
      </CardHeader>

      <StagesList>
        {STAGE_CONFIGS.map((stage) => {
          const count = getStageCount(stage.id);
          const percent = totalApplications > 0 ? Math.round((count / denominator) * 100) : 0;
          const isSelected = selectedStatus === stage.id;
          const Icon = stage.icon;
          const displayLabel = getStageLabel(stage.id, stage.label);

          return (
            <StageRow
              key={stage.id}
              className={isSelected ? 'selected' : ''}
              onClick={() => onSelectStatus && onSelectStatus(isSelected ? 'all' : stage.id)}
              title={`${displayLabel}: ${count} applications (${percent}%). ${stage.description}`}
            >
              <div className="stage-meta">
                <div className="icon-and-label">
                  <div className="stage-icon-box" style={{ background: stage.bg, color: stage.color }}>
                    <Icon size={13} />
                  </div>
                  <span className="stage-label">{displayLabel}</span>
                  {isSelected && <span className="active-tag">Active</span>}
                </div>

                <div className="count-and-pct">
                  <span className="count">{count}</span>
                  <span className="pct">{percent}%</span>
                </div>
              </div>

              <ProgressBarContainer>
                <ProgressBarFill
                  style={{
                    width: `${Math.min(percent, 100)}%`,
                    background: stage.color,
                  }}
                />
              </ProgressBarContainer>
            </StageRow>
          );
        })}
      </StagesList>
    </CardContainer>
  );
};

const CardContainer = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 18px 22px;
  backdrop-filter: blur(12px);
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const CardHeader = styled.div`
  margin-bottom: 14px;

  .title-row {
    display: flex;
    align-items: center;
    gap: 8px;

    .header-icon {
      color: #a855f7;
    }

    h4 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #f1f5f9;
    }
  }

  .subtitle {
    margin: 4px 0 0 0;
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.4;
  }
`;

const StagesList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 4px;
`;

const StageRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 7px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
  }

  &.selected {
    background: rgba(168, 85, 247, 0.12);
    border-color: rgba(168, 85, 247, 0.3);
  }

  .stage-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .icon-and-label {
    display: flex;
    align-items: center;
    gap: 8px;

    .stage-icon-box {
      width: 22px;
      height: 22px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .stage-label {
      font-size: 12px;
      font-weight: 500;
      color: #e2e8f0;
    }

    .active-tag {
      font-size: 10px;
      font-weight: 600;
      color: #a855f7;
      background: rgba(168, 85, 247, 0.2);
      border: 1px solid rgba(168, 85, 247, 0.35);
      padding: 0 5px;
      border-radius: 4px;
    }
  }

  .count-and-pct {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;

    .count {
      font-weight: 700;
      color: #f8fafc;
    }

    .pct {
      color: #64748b;
      font-size: 11px;
      width: 32px;
      text-align: right;
    }
  }
`;

const ProgressBarContainer = styled.div`
  width: 100%;
  height: 5px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
`;

const ProgressBarFill = styled.div`
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
`;

const LoadingText = styled.p`
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 30px;
`;
