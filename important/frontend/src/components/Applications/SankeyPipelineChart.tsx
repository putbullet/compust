import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { GitFork, Info } from 'lucide-react';
import type { SankeyData, SankeyNode, SankeyLink } from '../../api/client';

interface SankeyPipelineChartProps {
  data: SankeyData | null;
  loading?: boolean;
}

export const SankeyPipelineChart: React.FC<SankeyPipelineChartProps> = ({
  data,
  loading,
}) => {
  const [hoveredLink, setHoveredLink] = useState<SankeyLink | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SankeyNode | null>(null);

  // Layout calculation
  const layout = useMemo(() => {
    if (!data || !data.nodes || data.nodes.length === 0) return null;

    const width = 960;
    const height = 480;
    const paddingX = 40;
    const paddingY = 40;
    const usableWidth = width - paddingX * 2;
    const usableHeight = height - paddingY * 2;

    // Group nodes by stage_index
    const stageGroups: Record<number, SankeyNode[]> = {};
    data.nodes.forEach((n) => {
      stageGroups[n.stage_index] = stageGroups[n.stage_index] || [];
      stageGroups[n.stage_index].push(n);
    });

    const stageIndices = Object.keys(stageGroups)
      .map(Number)
      .sort((a, b) => a - b);
    const numStages = stageIndices.length;
    const colStep = numStages > 1 ? usableWidth / (numStages - 1) : usableWidth;

    const nodePositions: Record<
      string,
      { x: number; y: number; width: number; height: number; node: SankeyNode }
    > = {};

    const nodeWidth = 24;

    stageIndices.forEach((stageIdx, colIndex) => {
      const stageNodes = stageGroups[stageIdx];
      const x = paddingX + colIndex * colStep - (colIndex === 0 ? 0 : colIndex === numStages - 1 ? nodeWidth : nodeWidth / 2);

      const totalStageCount = stageNodes.reduce((acc, n) => acc + n.count, 0) || 1;
      const availableHeight = usableHeight - (stageNodes.length - 1) * 20;

      let currentY = paddingY;
      stageNodes.forEach((node) => {
        const hRatio = Math.max(node.count / totalStageCount, 0.08);
        const nodeH = Math.max(availableHeight * hRatio, 32);

        nodePositions[node.id] = {
          x,
          y: currentY,
          width: nodeWidth,
          height: nodeH,
          node,
        };

        currentY += nodeH + 20;
      });
    });

    // Compute link paths (ribbons)
    const linksWithPaths = data.links.map((link) => {
      const srcPos = nodePositions[link.source];
      const tgtPos = nodePositions[link.target];

      if (!srcPos || !tgtPos) return null;

      const x0 = srcPos.x + srcPos.width;
      const y0_mid = srcPos.y + srcPos.height / 2;
      const x1 = tgtPos.x;
      const y1_mid = tgtPos.y + tgtPos.height / 2;

      // Thickness proportional to value
      const totalSourceCount = srcPos.node.count || 1;
      const ribbonThickness = Math.max((link.value / totalSourceCount) * srcPos.height * 0.7, 4);

      const y0_top = y0_mid - ribbonThickness / 2;
      const y0_bot = y0_mid + ribbonThickness / 2;
      const y1_top = y1_mid - ribbonThickness / 2;
      const y1_bot = y1_mid + ribbonThickness / 2;

      const dx = (x1 - x0) * 0.5;

      const path = `
        M ${x0} ${y0_top}
        C ${x0 + dx} ${y0_top}, ${x1 - dx} ${y1_top}, ${x1} ${y1_top}
        L ${x1} ${y1_bot}
        C ${x1 - dx} ${y1_bot}, ${x0 + dx} ${y0_bot}, ${x0} ${y0_bot}
        Z
      `;

      return {
        link,
        path,
        sourcePos: srcPos,
        targetPos: tgtPos,
      };
    }).filter(Boolean);

    return {
      width,
      height,
      stageIndices,
      nodePositions,
      linksWithPaths,
    };
  }, [data]);

  if (loading) {
    return (
      <PipelineCard>
        <div className="chart-loading">
          <GitFork size={28} className="spin" />
          <p>Calculating live Sankey pipeline flows...</p>
        </div>
      </PipelineCard>
    );
  }

  if (!data || data.total === 0 || !layout) {
    return (
      <PipelineCard>
        <EmptyPipeline>
          <GitFork size={36} />
          <h4>No Pipeline Data Yet</h4>
          <p>
            Track more job applications and update their stages (Interviewing, Offers, Outcomes) to
            generate your interactive recruitment funnel.
          </p>
        </EmptyPipeline>
      </PipelineCard>
    );
  }

  const STAGE_TITLES: Record<number, string> = {
    0: 'Sources',
    1: 'Applied',
    2: 'Screening / 1st Round',
    3: 'Advanced Interviews',
    4: 'Offer Extended',
    5: 'Outcomes',
  };

  return (
    <PipelineCard>
      <ChartHeader>
        <div className="header-info">
          <div className="title-with-badge">
            <GitFork size={18} className="chart-icon" />
            <h4>Application Conversion Pipeline</h4>
            <span className="total-badge">{data.total} Applications</span>
          </div>
          <p className="caption">
            Dynamic horizontal Sankey flow mapping actual stage progression and conversion rates.
          </p>
        </div>
      </ChartHeader>

      <SvgWrapper>
        <svg
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          preserveAspectRatio="xMidYMid meet"
          className="sankey-svg"
        >
          <defs>
            <linearGradient id="link-grad-default" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.35" />
            </linearGradient>
            <linearGradient id="link-grad-active" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#818cf8" stopOpacity="0.75" />
              <stop offset="100%" stopColor="#60a5fa" stopOpacity="0.75" />
            </linearGradient>
          </defs>

          {/* Render Stage Column Headers */}
          {layout.stageIndices.map((stIdx, i) => {
            const x = 40 + i * ((layout.width - 80) / (layout.stageIndices.length - 1));
            return (
              <text
                key={stIdx}
                x={x}
                y={24}
                textAnchor={i === 0 ? 'start' : i === layout.stageIndices.length - 1 ? 'end' : 'middle'}
                className="stage-header-label"
              >
                {STAGE_TITLES[stIdx] || `Stage ${stIdx}`}
              </text>
            );
          })}

          {/* Render Link Ribbons */}
          <g className="links-layer">
            {layout.linksWithPaths.map((item, idx) => {
              if (!item) return null;
              const isHovered = hoveredLink === item.link;
              const isConnectedToHoveredNode =
                hoveredNode &&
                (hoveredNode.id === item.link.source || hoveredNode.id === item.link.target);

              return (
                <path
                  key={idx}
                  d={item.path}
                  fill={isHovered || isConnectedToHoveredNode ? 'url(#link-grad-active)' : 'url(#link-grad-default)'}
                  stroke={isHovered ? '#818cf8' : 'none'}
                  strokeWidth={isHovered ? 1 : 0}
                  onMouseEnter={() => setHoveredLink(item.link)}
                  onMouseLeave={() => setHoveredLink(null)}
                  className="sankey-ribbon"
                >
                  <title>{`${item.link.source} → ${item.link.target}: ${item.link.value} candidates`}</title>
                </path>
              );
            })}
          </g>

          {/* Render Nodes */}
          <g className="nodes-layer">
            {Object.values(layout.nodePositions).map(({ x, y, width, height, node }) => {
              const isHovered = hoveredNode?.id === node.id;

              return (
                <g
                  key={node.id}
                  className="sankey-node"
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    rx={6}
                    fill={node.color}
                    fillOpacity={isHovered ? 1 : 0.85}
                    stroke={isHovered ? '#ffffff' : 'rgba(255, 255, 255, 0.2)'}
                    strokeWidth={isHovered ? 2 : 1}
                  />

                  {/* Node Label & Count */}
                  <text
                    x={node.stage_index === 0 ? x + width + 8 : x - 8}
                    y={y + height / 2 + 4}
                    textAnchor={node.stage_index === 0 ? 'start' : 'end'}
                    className="node-text"
                  >
                    <tspan className="node-title">{node.label}</tspan>{' '}
                    <tspan className="node-count" fill={node.color}>
                      ({node.count})
                    </tspan>
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </SvgWrapper>

      {/* Interactive Tooltip Footer */}
      <TooltipRow>
        {hoveredLink ? (
          <div className="tooltip-badge">
            <span className="source-target">
              {hoveredLink.source} ➔ {hoveredLink.target}
            </span>
            <span className="count-val">
              <strong>{hoveredLink.value}</strong> transitions (
              {Math.round((hoveredLink.value / (data.total || 1)) * 100)}% of total)
            </span>
          </div>
        ) : hoveredNode ? (
          <div className="tooltip-badge">
            <span className="source-target">{hoveredNode.label}</span>
            <span className="count-val">
              <strong>{hoveredNode.count}</strong> applications in this stage (
              {Math.round((hoveredNode.count / (data.total || 1)) * 100)}%)
            </span>
          </div>
        ) : (
          <div className="tooltip-hint">
            <Info size={13} />
            <span>Hover over ribbons and stages to inspect candidate volume and drop-off rates</span>
          </div>
        )}
      </TooltipRow>
    </PipelineCard>
  );
};

const PipelineCard = styled.div`
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
  margin-bottom: 1.5rem;
`;

const ChartHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;

  .header-info {
    .title-with-badge {
      display: flex;
      align-items: center;
      gap: 0.65rem;

      .chart-icon {
        color: #818cf8;
      }

      h4 {
        margin: 0;
        font-size: 1.05rem;
        font-weight: 700;
        color: #f8fafc;
      }

      .total-badge {
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
      }
    }

    .caption {
      margin: 0.25rem 0 0;
      font-size: 0.8rem;
      color: #94a3b8;
    }
  }
`;

const SvgWrapper = styled.div`
  width: 100%;
  overflow-x: auto;

  .sankey-svg {
    width: 100%;
    min-width: 720px;
    height: auto;
    max-height: 480px;

    .stage-header-label {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      fill: #94a3b8;
    }

    .sankey-ribbon {
      cursor: pointer;
      transition: fill 0.15s ease, stroke 0.15s ease;
    }

    .sankey-node {
      cursor: pointer;

      rect {
        transition: fill-opacity 0.15s ease, stroke 0.15s ease;
      }

      .node-text {
        font-size: 0.75rem;
        font-family: inherit;

        .node-title {
          font-weight: 600;
          fill: #f8fafc;
        }

        .node-count {
          font-weight: 700;
        }
      }
    }
  }
`;

const TooltipRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.75rem;
  min-height: 28px;

  .tooltip-badge {
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 9999px;
    padding: 0.3rem 0.85rem;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;

    .source-target {
      color: #818cf8;
      font-weight: 600;
    }

    .count-val {
      color: #e2e8f0;
    }
  }

  .tooltip-hint {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.775rem;
    color: #64748b;
  }
`;

const EmptyPipeline = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
  color: #64748b;
  text-align: center;
  gap: 0.5rem;

  h4 {
    margin: 0;
    font-size: 1rem;
    color: #94a3b8;
  }

  p {
    margin: 0;
    font-size: 0.825rem;
    max-width: 440px;
  }
`;
