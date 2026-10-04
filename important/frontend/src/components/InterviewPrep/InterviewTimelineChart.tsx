import React, { useState } from 'react';
import { Clock, ArrowDown } from 'lucide-react';

export interface TimelineTurnItem {
  turn_id: number;
  question_title: string;
  competency?: string;
  start_minute: number;
  end_minute: number;
  duration_seconds: number;
  score: number;
  star_verdict?: string;
  quality_band?: 'high' | 'moderate' | 'needs_improvement' | 'unattempted';
  wpm?: number;
  filler_count?: number;
  longest_pause_seconds?: number;
  flags?: string[];
}

interface InterviewTimelineChartProps {
  timelineData: TimelineTurnItem[];
  totalDurationMinutes?: number;
  selectedTurnId?: number | null;
  onSelectTurn?: (turnId: number) => void;
}

export const InterviewTimelineChart: React.FC<InterviewTimelineChartProps> = ({
  timelineData = [],
  totalDurationMinutes = 15,
  selectedTurnId,
  onSelectTurn,
}) => {
  const [hoveredTurn, setHoveredTurn] = useState<TimelineTurnItem | null>(null);

  // Determine total time axis in minutes
  const maxTurnMinute = timelineData.reduce(
    (max, item) => Math.max(max, item.end_minute || item.start_minute + 1),
    0
  );
  const chartMaxMinutes = Math.max(totalDurationMinutes, Math.ceil(maxTurnMinute + 0.5));

  // Generate tick markers every 1 minute (or 2 mins if duration > 15)
  const tickStep = chartMaxMinutes > 15 ? 2 : 1;
  const tickMarks: number[] = [];
  for (let m = 0; m <= chartMaxMinutes; m += tickStep) {
    tickMarks.push(m);
  }

  const getQualityColor = (band?: string) => {
    switch (band) {
      case 'high':
        return {
          bg: 'linear-gradient(180deg, rgba(16, 185, 129, 0.9) 0%, rgba(5, 150, 105, 0.7) 100%)',
          border: '#34d399',
          glow: 'rgba(52, 211, 153, 0.3)',
          label: 'Strong STAR Answer',
          heightPercent: 88,
        };
      case 'moderate':
        return {
          bg: 'linear-gradient(180deg, rgba(245, 158, 11, 0.9) 0%, rgba(217, 119, 6, 0.7) 100%)',
          border: '#fbbf24',
          glow: 'rgba(251, 191, 36, 0.3)',
          label: 'Partial STAR Elements',
          heightPercent: 62,
        };
      case 'needs_improvement':
        return {
          bg: 'linear-gradient(180deg, rgba(239, 68, 68, 0.9) 0%, rgba(185, 28, 28, 0.7) 100%)',
          border: '#f87171',
          glow: 'rgba(248, 113, 113, 0.3)',
          label: 'Gaps in Structure / Result',
          heightPercent: 40,
        };
      case 'unattempted':
      default:
        return {
          bg: 'linear-gradient(180deg, rgba(148, 163, 184, 0.6) 0%, rgba(100, 116, 139, 0.4) 100%)',
          border: '#94a3b8',
          glow: 'transparent',
          label: 'Skipped / Unattempted',
          heightPercent: 24,
        };
    }
  };

  const handleBarClick = (turn: TimelineTurnItem) => {
    if (onSelectTurn) {
      onSelectTurn(turn.turn_id);
    }
    // Also scroll smoothly to the question review card if present in DOM
    const el = document.getElementById(`turn-review-${turn.turn_id}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="interview-timeline-container">
      <div className="timeline-header-row">
        <div className="timeline-title-group">
          <div className="timeline-main-title">
            <Clock size={18} color="#60a5fa" />
            <span>Minute-by-Minute Interview Progression</span>
          </div>
          <p className="timeline-subtitle">
            Visual pacing of each question across the elapsed interview clock. Height and color reflect answer quality and STAR completeness. Click any segment to jump to detailed evidence.
          </p>
        </div>

        {/* Legend */}
        <div className="timeline-legend">
          <span className="legend-item">
            <span className="legend-color high" />
            <span>Strong (≥75%)</span>
          </span>
          <span className="legend-item">
            <span className="legend-color moderate" />
            <span>Moderate (50-74%)</span>
          </span>
          <span className="legend-item">
            <span className="legend-color needs-improvement" />
            <span>Needs Focus (&lt;50%)</span>
          </span>
          <span className="legend-item">
            <span className="legend-icon silence">⏸</span>
            <span>Pause &gt;5s</span>
          </span>
          <span className="legend-item">
            <span className="legend-icon overlong">⏳</span>
            <span>Answer &gt;2.5m</span>
          </span>
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="timeline-chart-wrapper">
        {/* Background Minute Grid Lines */}
        <div className="timeline-grid-lines">
          {tickMarks.map((m) => {
            const leftPct = (m / chartMaxMinutes) * 100;
            return (
              <div
                key={`grid-${m}`}
                className="timeline-grid-line"
                style={{ left: `${leftPct}%` }}
              >
                <span className="timeline-grid-label">{m}m</span>
              </div>
            );
          })}
        </div>

        {/* Question Segments Track */}
        <div className="timeline-segments-track">
          {timelineData.map((item, idx) => {
            const startPct = Math.max(0, (item.start_minute / chartMaxMinutes) * 100);
            const rawWidthPct = ((item.end_minute - item.start_minute) / chartMaxMinutes) * 100;
            // Ensure minimum clickable width
            const widthPct = Math.max(4.5, Math.min(100 - startPct, rawWidthPct));

            const styling = getQualityColor(item.quality_band);
            const isSelected = selectedTurnId === item.turn_id;
            const hasLongPause = (item.longest_pause_seconds ?? 0) >= 5 || item.flags?.includes('long_silence');
            const isOverlong = item.duration_seconds >= 150 || item.flags?.includes('overlong_answer');

            return (
              <div
                key={item.turn_id || idx}
                className={`timeline-segment-bar ${isSelected ? 'selected' : ''}`}
                style={{
                  left: `${startPct}%`,
                  width: `${widthPct}%`,
                  height: `${styling.heightPercent}%`,
                  background: styling.bg,
                  borderColor: styling.border,
                  boxShadow: isSelected
                    ? `0 0 16px ${styling.border}, 0 4px 12px rgba(0,0,0,0.5)`
                    : `0 2px 8px ${styling.glow}`,
                }}
                onClick={() => handleBarClick(item)}
                onMouseEnter={() => setHoveredTurn(item)}
                onMouseLeave={() => setHoveredTurn(null)}
                title={`Question ${idx + 1}: ${item.question_title} (${Math.round(item.duration_seconds)}s)`}
              >
                {/* Segment Top Markers */}
                <div className="segment-markers-top">
                  {hasLongPause && (
                    <span className="segment-marker-badge pause" title="Pause > 5 seconds detected">
                      ⏸
                    </span>
                  )}
                  {isOverlong && (
                    <span className="segment-marker-badge overlong" title="Extended answer > 2.5 minutes">
                      ⏳
                    </span>
                  )}
                </div>

                {/* Inner label */}
                <div className="segment-inner-content">
                  <span className="segment-q-number">Q{idx + 1}</span>
                  <span className="segment-score-pct">{Math.round((item.score || 0) * 100)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hover or Selected Detail Card */}
      {hoveredTurn && (
        <div className="timeline-tooltip-panel">
          <div className="tooltip-header">
            <span className="tooltip-q-badge">Turn {hoveredTurn.turn_id}</span>
            <span className="tooltip-competency-badge">
              {hoveredTurn.competency || 'General Behavioral'}
            </span>
            <span className="tooltip-time-badge">
              {hoveredTurn.start_minute.toFixed(1)}m – {hoveredTurn.end_minute.toFixed(1)}m ({Math.round(hoveredTurn.duration_seconds)}s)
            </span>
          </div>

          <div className="tooltip-question-title">{hoveredTurn.question_title}</div>

          <div className="tooltip-metrics-row">
            <div className="tooltip-metric">
              <span className="metric-lbl">Score:</span>
              <span className="metric-val" style={{ color: hoveredTurn.score >= 0.75 ? '#34d399' : hoveredTurn.score >= 0.5 ? '#fbbf24' : '#f87171' }}>
                {Math.round((hoveredTurn.score || 0) * 100)}% ({hoveredTurn.star_verdict || 'Assessed'})
              </span>
            </div>

            {hoveredTurn.wpm !== undefined && hoveredTurn.wpm !== null && (
              <div className="tooltip-metric">
                <span className="metric-lbl">Pacing:</span>
                <span className="metric-val">{hoveredTurn.wpm} WPM</span>
              </div>
            )}

            {hoveredTurn.filler_count !== undefined && hoveredTurn.filler_count !== null && (
              <div className="tooltip-metric">
                <span className="metric-lbl">Fillers:</span>
                <span className="metric-val">{hoveredTurn.filler_count}</span>
              </div>
            )}

            {hoveredTurn.longest_pause_seconds !== undefined && hoveredTurn.longest_pause_seconds !== null && (
              <div className="tooltip-metric">
                <span className="metric-lbl">Longest Pause:</span>
                <span className="metric-val">{hoveredTurn.longest_pause_seconds.toFixed(1)}s</span>
              </div>
            )}
          </div>

          <div className="tooltip-action-hint">
            <ArrowDown size={13} />
            <span>Click segment to view STAR evidence breakdown below</span>
          </div>
        </div>
      )}
    </div>
  );
};
