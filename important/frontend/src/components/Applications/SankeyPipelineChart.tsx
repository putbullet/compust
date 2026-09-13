import React, { useState, useMemo, useRef } from 'react';
import styled from 'styled-components';
import { Download, Sun, Moon, Sparkles, Info } from 'lucide-react';
import type { SankeyData, SankeyNode, SankeyLink } from '../../api/client';

interface SankeyPipelineChartProps {
  data: SankeyData | null;
  loading?: boolean;
}

interface ComputedNode {
  id: string;
  label: string;
  stage_index: number;
  count: number;
  color: string;
  x: number;
  y: number;
  width: number;
  height: number;
  alignLeftLabel?: boolean;
}

interface ComputedRibbon {
  link: SankeyLink;
  path: string;
  sourceNode: ComputedNode;
  targetNode: ComputedNode;
  color: string;
}

export const SankeyPipelineChart: React.FC<SankeyPipelineChartProps> = ({
  data,
  loading,
}) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [hoveredRibbon, setHoveredRibbon] = useState<SankeyLink | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Colors accurately reflecting SankeyMATIC screenshot
  const NODE_COLORS: Record<string, string> = {
    stage_applications: '#f97316', // Orange
    stage_1st_interview: '#4ade80', // Green
    stage_rejected_init: '#f87171', // Coral Red
    stage_no_answer: '#c084fc', // Lavender Purple
    stage_withdrawn_init: '#94a3b8',
    stage_2nd_interview: '#b48a78', // Warm Brown / Tan
    stage_rejected_1st: '#f87171',
    stage_in_progress_1st: '#38bdf8',
    stage_3rd_interview: '#f472b6', // Pink
    stage_rejected_2nd: '#f87171',
    stage_in_progress_2nd: '#38bdf8',
    stage_4th_interview: '#7dd3fc', // Light Cyan
    stage_rejected_3rd: '#f87171',
    stage_in_progress_3rd: '#38bdf8',
    stage_offers: '#facc15', // Yellow / Gold
    stage_rejected_final: '#2dd4bf', // Aqua / Cyan Rejection
    stage_in_progress_final: '#38bdf8',
    stage_accepted: '#38bdf8', // Royal / Cyan Blue
    stage_declined: '#94a3b8',
    stage_pending_offer: '#fef08a',
  };

  const layout = useMemo(() => {
    if (!data || !data.nodes || data.nodes.length === 0 || !data.links || data.links.length === 0) {
      return null;
    }

    const svgWidth = 1200;
    const svgHeight = 700;
    const nodeWidth = 9;
    const minNodeHeight = 4;

    // ── Guaranteed whitespace between each stage-1 ribbon band ───────────────
    // Every flow from Applications is separated from its neighbours by this many
    // px of blank space, preventing thick ribbons from colliding.
    const GAP_BETWEEN_FLOWS = 55;
    const TOP_MARGIN = 40;
    const BOTTOM_MARGIN = 80;

    // Filter active nodes
    const activeNodeIds = new Set<string>();
    data.links.forEach((l) => {
      activeNodeIds.add(l.source);
      activeNodeIds.add(l.target);
    });
    const activeNodes = data.nodes.filter((n) => activeNodeIds.has(n.id));

    // Group nodes by stage_index
    const stageCols: Record<number, SankeyNode[]> = {};
    activeNodes.forEach((n) => {
      stageCols[n.stage_index] = stageCols[n.stage_index] || [];
      stageCols[n.stage_index].push(n);
    });
    const stages = Object.keys(stageCols).map(Number).sort((a, b) => a - b);

    // X layout
    const startX = 145;
    const availableW = svgWidth - startX - 200;
    const colCount = Math.max(stages.length - 1, 1);
    const colStep = availableW / colCount;

    // Root node
    const rootNode = activeNodes.find((n) => n.id === 'stage_applications') || activeNodes[0];
    const totalVal = Math.max(rootNode ? rootNode.count : data.total, 1);

    // Build link maps
    const outLinks: Record<string, SankeyLink[]> = {};
    const inLinks: Record<string, SankeyLink[]> = {};
    data.links.forEach((l) => {
      outLinks[l.source] = outLinks[l.source] || [];
      outLinks[l.source].push(l);
      inLinks[l.target] = inLinks[l.target] || [];
      inLinks[l.target].push(l);
    });

    // Sort stage-1 links: Interviews → Rejected → No Answer → Withdrawn
    const stage1Order = ['stage_1st_interview', 'stage_rejected_init', 'stage_no_answer', 'stage_withdrawn_init'];
    const finalStageOrder = ['stage_offers', 'stage_rejected_final', 'stage_in_progress_final'];
    if (outLinks['stage_applications']) {
      outLinks['stage_applications'].sort((a, b) => {
        const idxA = stage1Order.indexOf(a.target);
        const idxB = stage1Order.indexOf(b.target);
        return (idxA >= 0 ? idxA : 99) - (idxB >= 0 ? idxB : 99);
      });
    }
    if (outLinks['stage_4th_interview']) {
      outLinks['stage_4th_interview'].sort((a, b) => {
        const idxA = finalStageOrder.indexOf(a.target);
        const idxB = finalStageOrder.indexOf(b.target);
        return (idxA >= 0 ? idxA : 99) - (idxB >= 0 ? idxB : 99);
      });
    }

    // ── DYNAMIC SCALE ────────────────────────────────────────────────────────
    // Compute scale so ALL ribbon bands + all inter-band gaps fit the canvas.
    // This prevents thick ribbons from overrunning bands below them.
    const stage1Links = outLinks['stage_applications'] || [];
    const numGaps = Math.max(stage1Links.length - 1, 0);
    const totalGapH = numGaps * GAP_BETWEEN_FLOWS;
    const availableForBars = svgHeight - TOP_MARGIN - BOTTOM_MARGIN - totalGapH;
    const scale = Math.max(availableForBars / totalVal, 2);

    const computedNodes: Record<string, ComputedNode> = {};

    // ── STAGE-1 NODES: stack top-to-bottom with explicit gap ─────────────────
    // Each node's Y is placed immediately after the previous band's bottom + GAP.
    // This guarantees zero ribbon collision regardless of data proportions.
    let stageY = TOP_MARGIN;
    stage1Links.forEach((link) => {
      const targetId = link.target;
      const targetNode = activeNodes.find((n) => n.id === targetId);
      if (!targetNode) return;
      const nodeH = Math.max(link.value * scale, minNodeHeight);
      const x = startX + targetNode.stage_index * colStep;
      computedNodes[targetId] = {
        id: targetId,
        label: targetNode.label,
        stage_index: targetNode.stage_index,
        count: link.value,
        color: NODE_COLORS[targetId] || targetNode.color || '#64748b',
        x,
        y: stageY,
        width: nodeWidth,
        height: nodeH,
        alignLeftLabel: false,
      };
      stageY += nodeH + GAP_BETWEEN_FLOWS;
    });

    // ── ROOT (APPLICATIONS) BAR: centered on the full stage-1 stack ──────────
    // rootH = sum of all band heights (no gaps). stackTotalH includes the gaps.
    // We vertically center rootH within stackTotalH so bezier curves are smooth.
    const rootH = Math.max(totalVal * scale, 36);
    const stackTotalH = rootH + totalGapH;
    const stackCenterY = TOP_MARGIN + stackTotalH / 2;
    const rootY = Math.max(stackCenterY - rootH / 2, TOP_MARGIN);

    computedNodes['stage_applications'] = {
      id: 'stage_applications',
      label: rootNode.label || 'Applications',
      stage_index: 0,
      count: totalVal,
      color: NODE_COLORS['stage_applications'] || '#f97316',
      x: startX,
      y: rootY,
      width: nodeWidth,
      height: rootH,
      alignLeftLabel: true,
    };

    // ── CASCADE CHAIN (2nd → 3rd → 4th interviews) ───────────────────────────
    // Runs horizontally to the right of 1st Interview, aligned to its Y.
    const cascadeChain = [
      { id: 'stage_2nd_interview', yOffset: 0 },
      { id: 'stage_3rd_interview', yOffset: 6 },
      { id: 'stage_4th_interview', yOffset: 12 },
    ];
    cascadeChain.forEach(({ id, yOffset }) => {
      const nodeObj = activeNodes.find((n) => n.id === id);
      if (!nodeObj) return;
      const inL = inLinks[id]?.[0];
      const prevNode = inL ? computedNodes[inL.source] : null;
      const baseY = prevNode ? prevNode.y + yOffset : TOP_MARGIN + yOffset;
      const nodeH = Math.max(nodeObj.count * scale, minNodeHeight);
      const x = startX + nodeObj.stage_index * colStep;
      computedNodes[id] = {
        id, label: nodeObj.label, stage_index: nodeObj.stage_index, count: nodeObj.count,
        color: NODE_COLORS[id] || nodeObj.color, x, y: baseY, width: nodeWidth, height: nodeH,
        alignLeftLabel: false,
      };
    });

    // ── TERMINAL NODES (Offers, Final Rejections, Accepted) ──────────────────
    const prevToOffers =
      activeNodes.find((n) => n.id === 'stage_4th_interview') ||
      activeNodes.find((n) => n.id === 'stage_3rd_interview') ||
      activeNodes.find((n) => n.id === 'stage_2nd_interview') ||
      activeNodes.find((n) => n.id === 'stage_1st_interview');
    const prevNodeComputed = prevToOffers ? computedNodes[prevToOffers.id] : null;
    const prevY = prevNodeComputed ? prevNodeComputed.y : TOP_MARGIN;
    const prevNodeH = prevNodeComputed ? prevNodeComputed.height : 0;

    const offersNode = activeNodes.find((n) => n.id === 'stage_offers');
    if (offersNode) {
      const x = startX + offersNode.stage_index * colStep;
      const y = Math.max(prevY - 40, 10);
      computedNodes['stage_offers'] = {
        id: 'stage_offers', label: offersNode.label, stage_index: offersNode.stage_index,
        count: offersNode.count, color: NODE_COLORS['stage_offers'] || '#facc15',
        x, y, width: nodeWidth, height: Math.max(offersNode.count * scale, minNodeHeight),
        alignLeftLabel: false,
      };
    }
    const finalRejNode = activeNodes.find((n) => n.id === 'stage_rejected_final');
    if (finalRejNode) {
      const x = startX + finalRejNode.stage_index * colStep;
      const y = prevY + prevNodeH + 70;
      computedNodes['stage_rejected_final'] = {
        id: 'stage_rejected_final', label: finalRejNode.label, stage_index: finalRejNode.stage_index,
        count: finalRejNode.count, color: NODE_COLORS['stage_rejected_final'] || '#2dd4bf',
        x, y, width: nodeWidth, height: Math.max(finalRejNode.count * scale, minNodeHeight),
        alignLeftLabel: false,
      };
    }
    const acceptedNode = activeNodes.find((n) => n.id === 'stage_accepted');
    if (acceptedNode) {
      const offersComputed = computedNodes['stage_offers'];
      const x = startX + acceptedNode.stage_index * colStep;
      const y = offersComputed ? offersComputed.y : TOP_MARGIN;
      computedNodes['stage_accepted'] = {
        id: 'stage_accepted', label: acceptedNode.label, stage_index: acceptedNode.stage_index,
        count: acceptedNode.count, color: NODE_COLORS['stage_accepted'] || '#38bdf8',
        x, y, width: nodeWidth, height: Math.max(acceptedNode.count * scale, minNodeHeight),
        alignLeftLabel: false,
      };
    }

    // ── AUXILIARY NODES (in-progress, pending-offer, declined, etc.) ─────────
    activeNodes.forEach((n) => {
      if (!computedNodes[n.id]) {
        const inL = inLinks[n.id]?.[0];
        const srcPos = inL ? computedNodes[inL.source] : null;
        const x = startX + n.stage_index * colStep;
        const y = srcPos ? srcPos.y + srcPos.height + 60 : 200;
        computedNodes[n.id] = {
          id: n.id, label: n.label, stage_index: n.stage_index, count: n.count,
          color: NODE_COLORS[n.id] || n.color, x, y, width: nodeWidth,
          height: Math.max(n.count * scale, minNodeHeight), alignLeftLabel: false,
        };
      }
    });

    // 4. Compute exact Sankey Ribbon Paths with top-to-bottom slice stacking
    const sourceOutOffsets: Record<string, number> = {};
    const targetInOffsets: Record<string, number> = {};

    const computedRibbons: ComputedRibbon[] = [];

    data.links.forEach((link) => {
      const srcNode = computedNodes[link.source];
      const tgtNode = computedNodes[link.target];
      if (!srcNode || !tgtNode) return;

      const srcOffset = sourceOutOffsets[link.source] || 0;
      const tgtOffset = targetInOffsets[link.target] || 0;

      // Slice height proportional to link value
      const srcSliceH = Math.max((link.value / (srcNode.count || 1)) * srcNode.height, 2);
      const tgtSliceH = Math.max((link.value / (tgtNode.count || 1)) * tgtNode.height, 2);

      const x0 = srcNode.x + srcNode.width;
      const y0_top = srcNode.y + srcOffset;
      const y0_bot = y0_top + srcSliceH;

      const x1 = tgtNode.x;
      const y1_top = tgtNode.y + tgtOffset;
      const y1_bot = y1_top + tgtSliceH;

      sourceOutOffsets[link.source] = srcOffset + srcSliceH;
      targetInOffsets[link.target] = tgtOffset + tgtSliceH;

      const dx = (x1 - x0) * 0.5;

      const path = `
        M ${x0} ${y0_top}
        C ${x0 + dx} ${y0_top}, ${x1 - dx} ${y1_top}, ${x1} ${y1_top}
        L ${x1} ${y1_bot}
        C ${x1 - dx} ${y1_bot}, ${x0 + dx} ${y0_bot}, ${x0} ${y0_bot}
        Z
      `;

      computedRibbons.push({
        link,
        path,
        sourceNode: srcNode,
        targetNode: tgtNode,
        color: srcNode.color,
      });
    });

    return {
      svgWidth,
      svgHeight,
      nodes: Object.values(computedNodes),
      ribbons: computedRibbons,
    };
  }, [data]);

  const handleDownloadSvg = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `compust_sankey_pipeline_${new Date().toISOString().slice(0, 10)}.svg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <ChartCard themeMode={theme}>
        <div className="state-message">
          <Sparkles className="spin" size={28} />
          <p>Generating your Sankey recruitment pipeline...</p>
        </div>
      </ChartCard>
    );
  }

  if (!data || data.total === 0 || !layout || layout.nodes.length === 0) {
    return (
      <ChartCard themeMode={theme}>
        <div className="state-message">
          <h4>No Application Funnel Data</h4>
          <p>
            Add applications and log stage transitions (1st Interview, 2nd Round, Offers, Accepted) to
            generate your interactive SankeyMATIC job search diagram.
          </p>
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard themeMode={theme}>
      {/* Top Toolbar */}
      <CardHeader themeMode={theme}>
        <div className="header-left">
          <div className="title-row">
            <h4>Application Conversion Pipeline</h4>
            <span className="source-pill">SankeyMATIC Funnel</span>
          </div>
          <p className="subtitle">
            Visual recruitment progression showing stage transitions, screening drop-offs, and offer conversions.
          </p>
        </div>

        <div className="header-right">
          <button
            type="button"
            className="tool-btn theme-toggle"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            title={`Switch to ${theme === 'light' ? 'Compust Dark' : 'SankeyMATIC Light'} mode`}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
            <span>{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
          </button>

          <button
            type="button"
            className="tool-btn export-btn"
            onClick={handleDownloadSvg}
            title="Download vector graphic of this Sankey diagram"
          >
            <Download size={15} />
            <span>Download SVG</span>
          </button>
        </div>
      </CardHeader>

      {/* SVG Canvas */}
      <SvgCanvasContainer themeMode={theme}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${layout.svgWidth} ${layout.svgHeight}`}
          preserveAspectRatio="xMidYMid meet"
          className="sankey-svg"
        >
          {/* Background rect for clean SVG export */}
          <rect
            x={0}
            y={0}
            width={layout.svgWidth}
            height={layout.svgHeight}
            fill={theme === 'light' ? '#ffffff' : '#0b1329'}
          />

          {/* Ribbons Layer */}
          <g className="ribbons-layer">
            {layout.ribbons.map((ribbon, idx) => {
              const isHovered = hoveredRibbon === ribbon.link;
              const isConnectedToNode =
                hoveredNodeId &&
                (ribbon.sourceNode.id === hoveredNodeId || ribbon.targetNode.id === hoveredNodeId);

              const opacity = isHovered || isConnectedToNode ? 0.88 : 0.55;

              return (
                <path
                  key={idx}
                  d={ribbon.path}
                  fill={ribbon.color}
                  fillOpacity={opacity}
                  stroke={isHovered ? '#1e293b' : 'none'}
                  strokeWidth={isHovered ? 1 : 0}
                  onMouseEnter={() => setHoveredRibbon(ribbon.link)}
                  onMouseLeave={() => setHoveredRibbon(null)}
                  className="sankey-ribbon"
                >
                  <title>{`${ribbon.sourceNode.label} → ${ribbon.targetNode.label}: ${ribbon.link.value}`}</title>
                </path>
              );
            })}
          </g>

          {/* Nodes Layer */}
          <g className="nodes-layer">
            {layout.nodes.map((node) => {
              const isHovered = hoveredNodeId === node.id;

              return (
                <g
                  key={node.id}
                  className="sankey-node"
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                >
                  {/* Vertical Node Bar */}
                  <rect
                    x={node.x}
                    y={node.y}
                    width={node.width}
                    height={node.height}
                    fill={node.color}
                    rx={1}
                    ry={1}
                    stroke={isHovered ? (theme === 'light' ? '#000000' : '#ffffff') : 'none'}
                    strokeWidth={isHovered ? 1.5 : 0}
                  />

                  {/* Two-line Text Label (Number on top, Label on bottom) */}
                  {node.alignLeftLabel ? (
                    <text
                      x={node.x - 14}
                      y={node.y + node.height / 2 - 6}
                      textAnchor="end"
                      className={`sankey-label ${theme}`}
                    >
                      <tspan className="count-text" x={node.x - 14}>
                        {node.count}
                      </tspan>
                      <tspan className="name-text" x={node.x - 14} dy="18">
                        {node.label}
                      </tspan>
                    </text>
                  ) : (
                    <text
                      x={node.x + node.width + 12}
                      y={node.y + Math.min(node.height / 2, 10) - 6}
                      textAnchor="start"
                      className={`sankey-label ${theme}`}
                    >
                      <tspan className="count-text" x={node.x + node.width + 12}>
                        {node.count}
                      </tspan>
                      <tspan className="name-text" x={node.x + node.width + 12} dy="18">
                        {node.label}
                      </tspan>
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </SvgCanvasContainer>

      {/* Info Tooltip Footer */}
      <TooltipFooter themeMode={theme}>
        {hoveredRibbon ? (
          <div className="tooltip-content">
            <span className="badge">Flow</span>
            <span className="text">
              <strong>{hoveredRibbon.source.replace('stage_', '').replace(/_/g, ' ')}</strong> ➔{' '}
              <strong>{hoveredRibbon.target.replace('stage_', '').replace(/_/g, ' ')}</strong>:{' '}
              {hoveredRibbon.value} candidates ({Math.round((hoveredRibbon.value / (data.total || 1)) * 100)}% of total)
            </span>
          </div>
        ) : hoveredNodeId ? (
          <div className="tooltip-content">
            <span className="badge">Stage</span>
            <span className="text">
              <strong>{hoveredNodeId.replace('stage_', '').replace(/_/g, ' ')}</strong>
            </span>
          </div>
        ) : (
          <div className="hint-content">
            <Info size={14} />
            <span>Hover over ribbons or stage bars to inspect exact candidate counts and progression rates</span>
          </div>
        )}
      </TooltipFooter>
    </ChartCard>
  );
};

const ChartCard = styled.div<{ themeMode: 'light' | 'dark' }>`
  background: ${(props) => (props.themeMode === 'light' ? '#ffffff' : '#0f172a')};
  border: 1px solid ${(props) => (props.themeMode === 'light' ? '#e2e8f0' : 'rgba(255, 255, 255, 0.08)')};
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  transition: background 0.2s ease, border-color 0.2s ease;
  margin-bottom: 1.5rem;

  .state-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 12px;
    text-align: center;
    color: #94a3b8;

    .spin {
      animation: spin 1.2s linear infinite;
      color: #6366f1;
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const CardHeader = styled.div<{ themeMode: 'light' | 'dark' }>`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid ${(props) => (props.themeMode === 'light' ? '#f1f5f9' : 'rgba(255, 255, 255, 0.06)')};
  flex-wrap: wrap;
  gap: 12px;

  .header-left {
    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;

      h4 {
        margin: 0;
        font-size: 1.15rem;
        font-weight: 700;
        color: ${(props) => (props.themeMode === 'light' ? '#0f172a' : '#f8fafc')};
      }

      .source-pill {
        background: ${(props) => (props.themeMode === 'light' ? 'rgba(99, 102, 241, 0.1)' : 'rgba(99, 102, 241, 0.2)')};
        color: #6366f1;
        font-size: 0.725rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
      }
    }

    .subtitle {
      margin: 4px 0 0;
      font-size: 0.8rem;
      color: ${(props) => (props.themeMode === 'light' ? '#64748b' : '#94a3b8')};
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;

    .tool-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.775rem;
      font-weight: 600;
      cursor: pointer;
      outline: none;
      transition: all 0.15s ease;

      &.theme-toggle {
        background: ${(props) => (props.themeMode === 'light' ? '#f1f5f9' : 'rgba(255, 255, 255, 0.06)')};
        border: 1px solid ${(props) => (props.themeMode === 'light' ? '#e2e8f0' : 'rgba(255, 255, 255, 0.1)')};
        color: ${(props) => (props.themeMode === 'light' ? '#334155' : '#cbd5e1')};

        &:hover {
          background: ${(props) => (props.themeMode === 'light' ? '#e2e8f0' : 'rgba(255, 255, 255, 0.12)')};
          color: ${(props) => (props.themeMode === 'light' ? '#0f172a' : '#ffffff')};
        }
      }

      &.export-btn {
        background: ${(props) => (props.themeMode === 'light' ? '#0f172a' : 'linear-gradient(135deg, #6366f1, #3b82f6)')};
        border: none;
        color: #ffffff;

        &:hover {
          opacity: 0.92;
        }
      }
    }
  }
`;

const SvgCanvasContainer = styled.div<{ themeMode: 'light' | 'dark' }>`
  width: 100%;
  overflow-x: auto;
  background: ${(props) => (props.themeMode === 'light' ? '#ffffff' : '#0b1329')};
  padding: 16px 0;

  .sankey-svg {
    width: 100%;
    min-width: 900px;
    height: auto;
    display: block;

    .sankey-ribbon {
      cursor: pointer;
      transition: fill-opacity 0.15s ease;
    }

    .sankey-node {
      cursor: pointer;

      rect {
        transition: stroke 0.15s ease;
      }
    }

    .sankey-label {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      user-select: none;

      .count-text {
        font-size: 15px;
        font-weight: 700;
      }

      .name-text {
        font-size: 12px;
        font-weight: 500;
      }

      &.light {
        .count-text { fill: #0f172a; }
        .name-text { fill: #334155; }
      }

      &.dark {
        .count-text { fill: #f8fafc; }
        .name-text { fill: #94a3b8; }
      }
    }
  }
`;

const TooltipFooter = styled.div<{ themeMode: 'light' | 'dark' }>`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 20px;
  background: ${(props) => (props.themeMode === 'light' ? '#f8fafc' : 'rgba(0, 0, 0, 0.25)')};
  border-top: 1px solid ${(props) => (props.themeMode === 'light' ? '#e2e8f0' : 'rgba(255, 255, 255, 0.05)')};
  min-height: 42px;

  .tooltip-content {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    color: ${(props) => (props.themeMode === 'light' ? '#1e293b' : '#e2e8f0')};

    .badge {
      background: #6366f1;
      color: #ffffff;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
    }
  }

  .hint-content {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.775rem;
    color: #64748b;
  }
`;
