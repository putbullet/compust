import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { Target } from 'lucide-react';
import type { ApplicationItem, ApplicationStats } from '../../api/client';
import { useTranslation } from '../../i18n';

interface PipelineRadarCardProps {
  stats?: ApplicationStats | null;
  applications: ApplicationItem[];
  loading?: boolean;
}

interface RadarDimension {
  id: string;
  label: string;
  shortLabel: string;
  value: number; // 0 - 100
  rawValueFormatted: string;
  description: string;
}

export const PipelineRadarCard: React.FC<PipelineRadarCardProps> = ({
  stats,
  applications,
  loading,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  const [hoveredDim, setHoveredDim] = useState<RadarDimension | null>(null);

  const dimensions: RadarDimension[] = useMemo(() => {
    const total = applications.length;
    const active = applications.filter((a) => a.status !== 'rejected' && a.status !== 'withdrawn' && a.status !== 'no_answer').length;

    // 1. Volume Velocity (normalized against active search benchmark of 25 applications)
    const volumeScore = Math.min(100, Math.round((total / 25) * 100));

    // 2. Response Velocity
    const responseScore = Math.min(100, Math.round(stats?.response_rate_percent || 0));

    // 3. Interview Conversion
    const interviewScore = Math.min(100, Math.round(stats?.interview_rate_percent || 0));

    // 4. Offer Conversion
    const offerScore = Math.min(100, Math.round(stats?.offer_rate_percent || 0));

    // 5. Follow-up Discipline (% of active applications with follow-up set or completed)
    const withFollowUp = applications.filter((a) => a.next_follow_up || a.history?.some((h) => h.event_type?.includes('follow_up'))).length;
    const followUpScore = active > 0 ? Math.min(100, Math.round((withFollowUp / active) * 100)) : 0;

    // 6. Contact Engagement (% of applications with recruiter / contact identified)
    const withContact = applications.filter((a) => a.contact_id || a.contact_name || a.recruiter).length;
    const contactScore = total > 0 ? Math.min(100, Math.round((withContact / total) * 100)) : 0;

    return [
      {
        id: 'volume',
        label: tApp.analyticsRadarVolume,
        shortLabel: tApp.analyticsRadarVolume,
        value: volumeScore,
        rawValueFormatted: `${total} apps`,
        description: 'Application volume normalized against an active 25-application pipeline benchmark.',
      },
      {
        id: 'response',
        label: tApp.analyticsRadarResponseRate,
        shortLabel: tApp.analyticsRadarResponseRate,
        value: responseScore,
        rawValueFormatted: `${stats?.response_rate_percent || 0}%`,
        description: 'Percentage of submitted applications that received employer contact or screening signals.',
      },
      {
        id: 'interview',
        label: tApp.analyticsRadarInterviewYield,
        shortLabel: tApp.analyticsRadarInterviewYield,
        value: interviewScore,
        rawValueFormatted: `${stats?.interview_rate_percent || 0}%`,
        description: 'Conversion percentage from submitted applications to first-round technical or recruiter interviews.',
      },
      {
        id: 'offer',
        label: tApp.analyticsRadarOfferRate,
        shortLabel: tApp.analyticsRadarOfferRate,
        value: offerScore,
        rawValueFormatted: `${stats?.offer_rate_percent || 0}%`,
        description: 'Conversion percentage of applications resulting in formal job offers.',
      },
      {
        id: 'follow_up',
        label: tApp.actionFollowUp,
        shortLabel: tApp.actionFollowUp,
        value: followUpScore,
        rawValueFormatted: `${followUpScore}%`,
        description: 'Discipline in scheduling and completing follow-ups on active job opportunities.',
      },
      {
        id: 'contact',
        label: tApp.tabContacts,
        shortLabel: tApp.tabContacts,
        value: contactScore,
        rawValueFormatted: `${contactScore}%`,
        description: 'Proportion of applications with an identified recruiter, hiring manager, or HR contact.',
      },
    ];
  }, [applications, stats, tApp]);

  // Overall Health Score (average of normalized dimensions)
  const healthScore = useMemo(() => {
    if (dimensions.length === 0 || applications.length === 0) return 0;
    const sum = dimensions.reduce((acc, d) => acc + d.value, 0);
    return Math.round(sum / dimensions.length);
  }, [dimensions, applications.length]);

  const cx = 135;
  const cy = 130;
  const maxR = 85;
  const numAxes = dimensions.length;

  // Concentric polygon grids
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];

  const getCoordinates = (index: number, valNorm: number) => {
    const angle = (index * 2 * Math.PI) / numAxes - Math.PI / 2;
    const r = maxR * valNorm;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // Polygon points
  const polygonPoints = dimensions
    .map((dim, idx) => {
      const { x, y } = getCoordinates(idx, Math.max(dim.value / 100, 0.05));
      return `${x},${y}`;
    })
    .join(' ');

  if (loading) {
    return (
      <CardContainer className="glass-panel">
        <LoadingText>Synthesizing pipeline intelligence...</LoadingText>
      </CardContainer>
    );
  }

  return (
    <CardContainer className="glass-panel">
      <CardHeader>
        <div className="title-row">
          <Target size={16} className="header-icon" />
          <h4>{tApp.analyticsRadarTitle}</h4>
        </div>
        <p className="subtitle">
          {tApp.analyticsRadarSubtitle}
        </p>
      </CardHeader>

      <ContentGrid>
        {/* Radar Graphic */}
        <RadarSvgWrapper>
          <svg width="270" height="260" viewBox="0 0 270 260" className="radar-svg">
            <defs>
              <linearGradient id="radarFillGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.15" />
              </linearGradient>
            </defs>

            {/* Concentric grid polygons */}
            {gridLevels.map((lvl) => {
              const pts = Array.from({ length: numAxes })
                .map((_, i) => {
                  const { x, y } = getCoordinates(i, lvl);
                  return `${x},${y}`;
                })
                .join(' ');
              return (
                <polygon
                  key={lvl}
                  points={pts}
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.06)"
                  strokeWidth="1"
                  strokeDasharray={lvl === 1 ? 'none' : '3,3'}
                />
              );
            })}

            {/* Axis spokes */}
            {dimensions.map((dim, i) => {
              const { x, y } = getCoordinates(i, 1.0);
              return (
                <line
                  key={dim.id}
                  x1={cx}
                  y1={cy}
                  x2={x}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeWidth="1"
                />
              );
            })}

            {/* Filled data polygon */}
            {applications.length > 0 && (
              <polygon
                points={polygonPoints}
                fill="url(#radarFillGrad)"
                stroke="#06b6d4"
                strokeWidth="2"
                strokeLinejoin="round"
                className="radar-polygon"
              />
            )}

            {/* Data point dots & axis text */}
            {dimensions.map((dim, i) => {
              const pt = getCoordinates(i, Math.max(dim.value / 100, 0.05));
              const labelPt = getCoordinates(i, 1.22);
              const isHovered = hoveredDim?.id === dim.id;

              return (
                <g key={dim.id} className="axis-group">
                  {/* Point dot */}
                  {applications.length > 0 && (
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r={isHovered ? 5 : 3.5}
                      fill={isHovered ? '#38bdf8' : '#06b6d4'}
                      stroke="#0f172a"
                      strokeWidth="2"
                      className="point-dot"
                      onMouseEnter={() => setHoveredDim(dim)}
                      onMouseLeave={() => setHoveredDim(null)}
                    />
                  )}

                  {/* Axis label */}
                  <text
                    x={labelPt.x}
                    y={labelPt.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className={`axis-label ${isHovered ? 'active' : ''}`}
                    onMouseEnter={() => setHoveredDim(dim)}
                    onMouseLeave={() => setHoveredDim(null)}
                  >
                    {dim.shortLabel}
                  </text>
                </g>
              );
            })}
          </svg>
        </RadarSvgWrapper>

        {/* Dimension Breakdown Metrics */}
        <DimensionsBreakdown>
          <div className="health-score-banner">
            <div className="score-number-box">
              <span className="score-num">{healthScore}</span>
              <span className="score-max">/100</span>
            </div>
            <div className="score-desc">
              <span className="score-title">
                {healthScore >= 70
                  ? 'Strong Search Momentum'
                  : healthScore >= 45
                  ? 'Active Search Cadence'
                  : 'Early Search Pipeline'}
              </span>
              <span className="score-sub">Multidimensional job-search index score</span>
            </div>
          </div>

          <DimList>
            {dimensions.map((dim) => {
              const isHovered = hoveredDim?.id === dim.id;
              return (
                <DimItem
                  key={dim.id}
                  className={isHovered ? 'hovered' : ''}
                  onMouseEnter={() => setHoveredDim(dim)}
                  onMouseLeave={() => setHoveredDim(null)}
                  title={dim.description}
                >
                  <div className="dim-row">
                    <span className="dim-name">{dim.label}</span>
                    <span className="dim-raw">{dim.rawValueFormatted}</span>
                  </div>
                  <div className="dim-bar-wrap">
                    <div className="dim-bar-fill" style={{ width: `${Math.min(dim.value, 100)}%` }} />
                  </div>
                </DimItem>
              );
            })}
          </DimList>
        </DimensionsBreakdown>
      </ContentGrid>
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
  margin-bottom: 12px;

  .title-row {
    display: flex;
    align-items: center;
    gap: 8px;

    .header-icon {
      color: #06b6d4;
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

const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 20px;
  align-items: center;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
    justify-items: center;
  }
`;

const RadarSvgWrapper = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;

  .radar-svg {
    overflow: visible;

    .radar-polygon {
      filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.3));
      transition: all 0.3s ease;
    }

    .point-dot {
      cursor: pointer;
      transition: all 0.2s ease;
      &:hover {
        transform: scale(1.3);
      }
    }

    .axis-label {
      font-size: 10.5px;
      font-weight: 500;
      fill: #94a3b8;
      cursor: pointer;
      transition: fill 0.15s ease;

      &.active,
      &:hover {
        fill: #38bdf8;
        font-weight: 600;
      }
    }
  }
`;

const DimensionsBreakdown = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;

  .health-score-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(6, 182, 212, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 8px;
    padding: 9px 14px;

    .score-number-box {
      display: flex;
      align-items: baseline;
      gap: 2px;

      .score-num {
        font-size: 24px;
        font-weight: 800;
        color: #38bdf8;
      }

      .score-max {
        font-size: 12px;
        color: #64748b;
        font-weight: 600;
      }
    }

    .score-desc {
      display: flex;
      flex-direction: column;
      gap: 2px;

      .score-title {
        font-size: 13px;
        font-weight: 600;
        color: #f1f5f9;
      }

      .score-sub {
        font-size: 11px;
        color: #94a3b8;
      }
    }
  }
`;

const DimList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

const DimItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.15s ease;
  cursor: default;

  &.hovered,
  &:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .dim-row {
    display: flex;
    justify-content: space-between;
    font-size: 11.5px;

    .dim-name {
      color: #cbd5e1;
      font-weight: 500;
    }

    .dim-raw {
      color: #38bdf8;
      font-weight: 600;
      font-size: 11px;
    }
  }

  .dim-bar-wrap {
    height: 4px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
    overflow: hidden;

    .dim-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #06b6d4, #3b82f6);
      border-radius: 2px;
      transition: width 0.3s ease;
    }
  }
`;

const LoadingText = styled.p`
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 30px;
`;
