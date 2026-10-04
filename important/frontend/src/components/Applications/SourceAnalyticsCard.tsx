import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { Layers, CheckCircle2 } from 'lucide-react';
import type { SourceAnalyticsItem } from '../../api/client';
import { useTranslation } from '../../i18n';

interface SourceAnalyticsCardProps {
  sources?: SourceAnalyticsItem[];
  selectedSource?: string;
  onSelectSource?: (source: string) => void;
  loading?: boolean;
}

const SOURCE_COLORS: Record<string, string> = {
  linkedin: '#0a66c2',
  indeed: '#2164f3',
  glassdoor: '#0caa41',
  'company website': '#8b5cf6',
  company: '#8b5cf6',
  recruiter: '#f59e0b',
  referral: '#ec4899',
  extension: '#06b6d4',
  'compust capture': '#06b6d4',
  manual: '#64748b',
  other: '#94a3b8',
};

const getSourceColor = (src: string, index: number): string => {
  const normalized = src.toLowerCase();
  for (const [key, color] of Object.entries(SOURCE_COLORS)) {
    if (normalized.includes(key)) return color;
  }
  const fallbackPalette = ['#3b82f6', '#10b981', '#f59e0b', '#a855f7', '#ec4899', '#06b6d4', '#f97316'];
  return fallbackPalette[index % fallbackPalette.length];
};

export const SourceAnalyticsCard: React.FC<SourceAnalyticsCardProps> = ({
  sources = [],
  selectedSource = 'all',
  onSelectSource,
  loading,
}) => {
  const { t } = useTranslation();
  const tApp = t.applications;

  const [hoveredSource, setHoveredSource] = useState<string | null>(null);

  const totalApplications = useMemo(() => {
    return sources.reduce((acc, s) => acc + s.applications, 0);
  }, [sources]);

  // Donut chart segments
  const donutSegments = useMemo(() => {
    if (totalApplications === 0) return [];
    let currentAngle = -Math.PI / 2; // Start from top
    const radius = 68;
    const innerRadius = 46;
    const center = 85;

    return sources.map((item, idx) => {
      const share = item.applications / totalApplications;
      const angle = share * 2 * Math.PI;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      currentAngle = endAngle;

      // Arc calculation
      const x1 = center + radius * Math.cos(startAngle);
      const y1 = center + radius * Math.sin(startAngle);
      const x2 = center + radius * Math.cos(endAngle);
      const y2 = center + radius * Math.sin(endAngle);

      const ix1 = center + innerRadius * Math.cos(endAngle);
      const iy1 = center + innerRadius * Math.sin(endAngle);
      const ix2 = center + innerRadius * Math.cos(startAngle);
      const iy2 = center + innerRadius * Math.sin(startAngle);

      const largeArc = angle > Math.PI ? 1 : 0;

      const pathData =
        share >= 0.999
          ? `M ${center} ${center - radius} A ${radius} ${radius} 0 1 1 ${center - 0.01} ${center - radius} M ${center} ${center - innerRadius} A ${innerRadius} ${innerRadius} 0 1 0 ${center - 0.01} ${center - innerRadius} Z`
          : `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;

      const color = getSourceColor(item.source, idx);
      const percent = Math.round(share * 100);

      return {
        source: item.source,
        applications: item.applications,
        percent,
        pathData,
        color,
      };
    });
  }, [sources, totalApplications]);

  if (loading) {
    return (
      <CardContainer className="glass-panel">
        <LoadingText>Analyzing source channels...</LoadingText>
      </CardContainer>
    );
  }

  if (!sources || sources.length === 0) {
    return (
      <CardContainer className="glass-panel">
        <CardHeader>
          <div className="title-row">
            <Layers size={16} className="header-icon" />
            <h4>Source Distribution & Analytics</h4>
          </div>
        </CardHeader>
        <EmptyText>No application sources recorded yet. When you add applications with sources, channels will appear here.</EmptyText>
      </CardContainer>
    );
  }

  const activeHoverItem = hoveredSource ? sources.find((s) => s.source === hoveredSource) : null;

  return (
    <CardContainer className="glass-panel">
      <CardHeader>
        <div className="title-row">
          <Layers size={16} className="header-icon" />
          <h4>{tApp.analyticsSourceTitle}</h4>
        </div>
        <p className="subtitle">
          {tApp.analyticsSourceSubtitle}
        </p>
      </CardHeader>

      <AnalyticsLayout>
        {/* Donut Chart Visual */}
        <DonutWrapper>
          <svg width="170" height="170" viewBox="0 0 170 170" className="donut-svg">
            <g>
              {donutSegments.map((seg) => {
                const isHovered = hoveredSource === seg.source;
                const isSelected = selectedSource.toLowerCase() === seg.source.toLowerCase();
                return (
                  <path
                    key={seg.source}
                    d={seg.pathData}
                    fill={seg.color}
                    opacity={hoveredSource ? (isHovered ? 1 : 0.4) : isSelected ? 1 : 0.85}
                    stroke="rgba(15, 23, 42, 0.9)"
                    strokeWidth="2"
                    className="donut-segment"
                    onMouseEnter={() => setHoveredSource(seg.source)}
                    onMouseLeave={() => setHoveredSource(null)}
                    onClick={() => onSelectSource && onSelectSource(isSelected ? 'all' : seg.source)}
                  />
                );
              })}
            </g>
            <text x="85" y="80" textAnchor="middle" className="center-count">
              {activeHoverItem ? activeHoverItem.applications : totalApplications}
            </text>
            <text x="85" y="97" textAnchor="middle" className="center-label">
              {activeHoverItem ? activeHoverItem.source.slice(0, 10) : tApp.statTotalApplications}
            </text>
          </svg>

          {/* Quick Legend Chips */}
          <LegendList>
            {donutSegments.slice(0, 4).map((seg) => (
              <LegendChip
                key={seg.source}
                onClick={() => onSelectSource && onSelectSource(selectedSource === seg.source ? 'all' : seg.source)}
                className={selectedSource === seg.source ? 'active' : ''}
              >
                <span className="dot" style={{ background: seg.color }} />
                <span className="name">{seg.source}</span>
                <span className="share">{seg.percent}%</span>
              </LegendChip>
            ))}
          </LegendList>
        </DonutWrapper>

        {/* Channel Conversion Table */}
        <TableScroll>
          <SourceTable>
            <thead>
              <tr>
                <th className="th-source">{tApp.colSource}</th>
                <th className="th-num">{tApp.statTotalApplications}</th>
                <th className="th-num">{tApp.statResponseRate}</th>
                <th className="th-num">{tApp.funnelInterviews}</th>
                <th className="th-rate">{tApp.statInterviewRate}</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((item, idx) => {
                const isSelected = selectedSource.toLowerCase() === item.source.toLowerCase();
                const isHovered = hoveredSource === item.source;
                const color = getSourceColor(item.source, idx);

                return (
                  <tr
                    key={item.source}
                    className={`${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
                    onClick={() => onSelectSource && onSelectSource(isSelected ? 'all' : item.source)}
                    onMouseEnter={() => setHoveredSource(item.source)}
                    onMouseLeave={() => setHoveredSource(null)}
                    title={`Click to ${isSelected ? 'clear filter' : `filter by ${item.source}`}`}
                  >
                    <td className="td-source">
                      <div className="source-title-cell">
                        <span className="color-indicator" style={{ background: color }} />
                        <span className="source-name">{item.source}</span>
                        {isSelected && (
                          <span className="active-pill">
                            <CheckCircle2 size={10} /> Active
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="td-num">
                      <strong>{item.applications}</strong>
                    </td>
                    <td className="td-num">{item.responses}</td>
                    <td className="td-num text-purple">{item.interviews}</td>
                    <td className="td-rate">
                      <div className="rate-bar-container">
                        <div
                          className="rate-bar-fill"
                          style={{
                            width: `${Math.min(item.interview_rate_percent, 100)}%`,
                            background: color,
                          }}
                        />
                        <span className="rate-label">{item.interview_rate_percent}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </SourceTable>
        </TableScroll>
      </AnalyticsLayout>
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
      color: #38bdf8;
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

const AnalyticsLayout = styled.div`
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 20px;
  align-items: center;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
    justify-items: center;
  }
`;

const DonutWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;

  .donut-svg {
    filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.3));

    .donut-segment {
      cursor: pointer;
      transition: all 0.2s ease;
      &:hover {
        transform: scale(1.03);
        transform-origin: 85px 85px;
      }
    }

    .center-count {
      font-size: 20px;
      font-weight: 700;
      fill: #f8fafc;
    }

    .center-label {
      font-size: 11px;
      font-weight: 500;
      fill: #94a3b8;
    }
  }
`;

const LegendList = styled.div`
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  max-width: 220px;
`;

const LegendChip = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 9999px;
  padding: 3px 8px;
  font-size: 11px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover,
  &.active {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    color: #fff;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .name {
    font-weight: 500;
  }

  .share {
    color: #94a3b8;
  }
`;

const TableScroll = styled.div`
  overflow-x: auto;
  width: 100%;
`;

const SourceTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th {
    text-align: left;
    padding: 8px 10px;
    font-weight: 600;
    color: #64748b;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
  }

  .th-num,
  .td-num {
    text-align: right;
    width: 65px;
  }

  .th-rate {
    text-align: right;
    width: 130px;
  }

  td {
    padding: 9px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    color: #e2e8f0;
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.15s ease;

    &:hover,
    &.hovered {
      background: rgba(255, 255, 255, 0.04);
    }

    &.selected {
      background: rgba(56, 189, 248, 0.1);
      td {
        color: #38bdf8;
      }
    }
  }

  .source-title-cell {
    display: flex;
    align-items: center;
    gap: 7px;

    .color-indicator {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .source-name {
      font-weight: 500;
    }

    .active-pill {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      font-size: 10px;
      font-weight: 600;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 1px 5px;
      border-radius: 4px;
    }
  }

  .text-purple {
    color: #c084fc;
    font-weight: 600;
  }

  .td-rate {
    text-align: right;
  }

  .rate-bar-container {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: flex-end;

    .rate-bar-fill {
      height: 6px;
      border-radius: 3px;
      min-width: 4px;
      max-width: 60px;
      background: #38bdf8;
    }

    .rate-label {
      font-size: 11px;
      font-weight: 600;
      color: #94a3b8;
      min-width: 32px;
      text-align: right;
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

const EmptyText = styled.p`
  margin: 0;
  font-size: 13px;
  color: #64748b;
  text-align: center;
  padding: 24px 0;
`;
