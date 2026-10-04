import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { Flame, Activity } from 'lucide-react';
import type { ApplicationItem } from '../../api/client';
import { useTranslation } from '../../i18n';

interface ActivityHeatmapCardProps {
  applications: ApplicationItem[];
  loading?: boolean;
}

interface ActivityEvent {
  title: string;
  type: 'applied' | 'interview' | 'follow_up' | 'status_change' | 'interaction';
}

interface DayData {
  date: Date;
  dateKey: string; // YYYY-MM-DD
  dayOfWeek: number; // 0 = Mon, 6 = Sun
  events: ActivityEvent[];
  count: number;
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAY_LABELS = ['Mon', '', 'Wed', '', 'Fri', '', ''];

export const ActivityHeatmapCard: React.FC<ActivityHeatmapCardProps> = ({
  applications,
  loading,
}) => {
  const { t, language } = useTranslation();
  const tApp = t.applications;

  const [hoveredDay, setHoveredDay] = useState<{
    day: DayData;
    x: number;
    y: number;
  } | null>(null);

  // Compute 20 weeks of daily activity map
  const { weeks, totalActions, activeDays, currentStreak, bestStreak, monthHeaders } = useMemo(() => {
    const today = new Date();
    today.setHours(23, 59, 59, 999);

    // Number of weeks to show
    const NUM_WEEKS = 20;

    // Determine current day of week (Monday as 0, Sunday as 6)
    const currentDayOfWeek = (today.getDay() + 6) % 7;

    // Start date: Monday of 20 weeks ago
    const start = new Date(today);
    start.setDate(today.getDate() - (NUM_WEEKS * 7 - 1) - currentDayOfWeek + currentDayOfWeek);
    start.setHours(0, 0, 0, 0);

    // Map of dateKey -> Array of ActivityEvent
    const eventMap = new Map<string, ActivityEvent[]>();

    const addEvent = (rawDate: string | Date | null | undefined, event: ActivityEvent) => {
      if (!rawDate) return;
      const d = new Date(rawDate);
      if (isNaN(d.getTime())) return;
      const key = d.toISOString().slice(0, 10);
      const list = eventMap.get(key) || [];
      list.push(event);
      eventMap.set(key, list);
    };

    // Scan applications for genuine operational activities
    applications.forEach((app) => {
      // 1. Applications submitted / saved
      const appDate = app.applied_at || app.created_at;
      if (appDate) {
        addEvent(appDate, {
          title: `Applied: ${app.effective_title} at ${app.effective_company}`,
          type: 'applied',
        });
      }

      // 2. Scheduled / logged interviews
      if (app.interview_date) {
        addEvent(app.interview_date, {
          title: `Interview scheduled/held: ${app.effective_title}`,
          type: 'interview',
        });
      }

      // 3. Follow-ups
      if (app.next_follow_up) {
        addEvent(app.next_follow_up, {
          title: `Follow-up on ${app.effective_title} (${app.effective_company})`,
          type: 'follow_up',
        });
      }

      // 4. Status history events
      if (app.history && app.history.length > 0) {
        app.history.forEach((h) => {
          if (h.changed_at) {
            const label = h.event_title || `Status updated to ${h.to_status.replace(/_/g, ' ')}`;
            addEvent(h.changed_at, {
              title: `${label} (${app.effective_title})`,
              type: h.event_type?.includes('follow') ? 'follow_up' : 'status_change',
            });
          }
        });
      }

      // 5. Contact interactions
      if (app.contact && app.contact.interactions) {
        app.contact.interactions.forEach((inter) => {
          if (inter.interaction_date) {
            addEvent(inter.interaction_date, {
              title: `${inter.summary || inter.type} with ${app.contact?.name || 'recruiter'}`,
              type: 'interaction',
            });
          }
        });
      }
    });

    // Build grid structure: columns of weeks (7 days each, Mon=0 to Sun=6)
    const weeksList: DayData[][] = [];
    const monthsMeta: Array<{ month: string; colIndex: number }> = [];

    const cursor = new Date(start);
    let currentWeek: DayData[] = [];
    let lastMonth = -1;

    let totalRecorded = 0;
    let daysWithActivity = 0;

    // Daily activity sequence for streak calculation
    const dailyCounts: Array<{ dateKey: string; count: number }> = [];

    while (cursor <= today || currentWeek.length > 0) {
      const dayOfWeek = (cursor.getDay() + 6) % 7;
      const dateKey = cursor.toISOString().slice(0, 10);
      const isPastToday = cursor > today;

      const events = isPastToday ? [] : eventMap.get(dateKey) || [];
      const count = events.length;

      if (!isPastToday) {
        totalRecorded += count;
        if (count > 0) daysWithActivity++;
        dailyCounts.push({ dateKey, count });
      }

      // Check month boundary
      const m = cursor.getMonth();
      if (m !== lastMonth && cursor.getDate() <= 7) {
        monthsMeta.push({
          month: MONTH_NAMES[m],
          colIndex: weeksList.length,
        });
        lastMonth = m;
      }

      currentWeek.push({
        date: new Date(cursor),
        dateKey,
        dayOfWeek,
        events,
        count,
      });

      if (dayOfWeek === 6 || isPastToday) {
        // End of week (Sunday)
        while (currentWeek.length < 7) {
          // pad empty
          currentWeek.push({
            date: new Date(cursor),
            dateKey: '',
            dayOfWeek: currentWeek.length,
            events: [],
            count: 0,
          });
        }
        weeksList.push(currentWeek);
        currentWeek = [];
      }

      cursor.setDate(cursor.getDate() + 1);
      if (cursor > today && dayOfWeek === 6) break;
    }

    // Streak calculations
    let currentS = 0;
    let bestS = 0;
    let tempStreak = 0;

    for (let i = 0; i < dailyCounts.length; i++) {
      if (dailyCounts[i].count > 0) {
        tempStreak++;
        if (tempStreak > bestS) bestS = tempStreak;
      } else {
        tempStreak = 0;
      }
    }

    // Current streak (counting backwards from today)
    for (let i = dailyCounts.length - 1; i >= 0; i--) {
      if (dailyCounts[i].count > 0) {
        currentS++;
      } else {
        // If today has 0 but yesterday had >0, keep yesterday's streak
        if (i === dailyCounts.length - 1) continue;
        break;
      }
    }

    return {
      weeks: weeksList,
      totalActions: totalRecorded,
      activeDays: daysWithActivity,
      currentStreak: currentS,
      bestStreak: bestS,
      monthHeaders: monthsMeta,
    };
  }, [applications]);

  const getIntensityLevel = (count: number): number => {
    if (count === 0) return 0;
    if (count === 1) return 1;
    if (count === 2) return 2;
    if (count <= 4) return 3;
    return 4;
  };

  if (loading) {
    return (
      <CardContainer className="glass-panel">
        <LoadingText>Mapping activity timeline...</LoadingText>
      </CardContainer>
    );
  }

  return (
    <CardContainer className="glass-panel">
      <CardHeader>
        <div className="title-left">
          <div className="title-row">
            <Activity size={16} className="header-icon" />
            <h4>{tApp.analyticsHeatmapTitle}</h4>
          </div>
          <p className="subtitle">
            {tApp.analyticsHeatmapSubtitle}
          </p>
        </div>

        {/* Summary Stat Badges */}
        <StatsBadges>
          <div className="stat-badge">
            <span className="badge-num">{totalActions}</span>
            <span className="badge-lbl">Actions</span>
          </div>
          <div className="stat-badge">
            <span className="badge-num">{activeDays}</span>
            <span className="badge-lbl">Active Days</span>
          </div>
          <div className="stat-badge highlight">
            <Flame size={12} className="flame-icon" />
            <span className="badge-num">{currentStreak}d</span>
            <span className="badge-lbl">Streak</span>
          </div>
        </StatsBadges>
      </CardHeader>

      {/* Heatmap Grid */}
      <HeatmapScrollWrapper>
        <HeatmapContainer>
          {/* Month labels row */}
          <MonthLabelsRow>
            <div className="day-axis-spacer" />
            <div className="months-container">
              {monthHeaders.map((m, idx) => (
                <span
                  key={idx}
                  className="month-tag"
                  style={{ left: `${m.colIndex * 15}px` }}
                >
                  {m.month}
                </span>
              ))}
            </div>
          </MonthLabelsRow>

          <GridBody>
            {/* Weekday labels */}
            <WeekdayLabelsCol>
              {DAY_LABELS.map((lbl, idx) => (
                <span key={idx} className="day-label">
                  {lbl}
                </span>
              ))}
            </WeekdayLabelsCol>

            {/* Weeks Columns */}
            <WeeksGrid>
              {weeks.map((week, wIdx) => (
                <WeekColumn key={wIdx}>
                  {week.map((day, dIdx) => {
                    if (!day.dateKey) {
                      return <EmptyCell key={dIdx} />;
                    }

                    const level = getIntensityLevel(day.count);
                    const isToday =
                      day.date.toDateString() === new Date().toDateString();

                    return (
                      <DayCell
                        key={day.dateKey}
                        className={`level-${level} ${isToday ? 'is-today' : ''}`}
                        onMouseEnter={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setHoveredDay({
                            day,
                            x: rect.left + rect.width / 2,
                            y: rect.top,
                          });
                        }}
                        onMouseLeave={() => setHoveredDay(null)}
                      />
                    );
                  })}
                </WeekColumn>
              ))}
            </WeeksGrid>
          </GridBody>

          {/* Footer with Legend */}
          <HeatmapFooter>
            <span className="streak-note">
              Longest momentum streak: <strong>{bestStreak} consecutive active days</strong>
            </span>

            <div className="legend">
              <span className="legend-lbl">{tApp.analyticsHeatmapLess}</span>
              <span className="legend-cell level-0" />
              <span className="legend-cell level-1" />
              <span className="legend-cell level-2" />
              <span className="legend-cell level-3" />
              <span className="legend-cell level-4" />
              <span className="legend-lbl">{tApp.analyticsHeatmapMore}</span>
            </div>
          </HeatmapFooter>
        </HeatmapContainer>
      </HeatmapScrollWrapper>

      {/* Floating Hover Tooltip */}
      {hoveredDay && (
        <FloatingTooltip
          style={{
            left: `${hoveredDay.x}px`,
            top: `${hoveredDay.y - 8}px`,
          }}
        >
          <div className="tooltip-date">
            {hoveredDay.day.date.toLocaleDateString(language === 'de' ? 'de-DE' : (language === 'fr' ? 'fr-FR' : 'en-US'), {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </div>
          <div className="tooltip-count">
            {hoveredDay.day.count === 0
              ? 'No activity recorded'
              : `${hoveredDay.day.count} operational ${
                  hoveredDay.day.count === 1 ? 'activity' : 'activities'
                }`}
          </div>
          {hoveredDay.day.events.length > 0 && (
            <div className="tooltip-events">
              {hoveredDay.day.events.slice(0, 4).map((ev, i) => (
                <div key={i} className="event-line">
                  • {ev.title}
                </div>
              ))}
              {hoveredDay.day.events.length > 4 && (
                <div className="event-more">
                  +{hoveredDay.day.events.length - 4} more actions
                </div>
              )}
            </div>
          )}
        </FloatingTooltip>
      )}
    </CardContainer>
  );
};

const CardContainer = styled.div`
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 18px 22px;
  backdrop-filter: blur(12px);
  position: relative;
  display: flex;
  flex-direction: column;
`;

const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 12px;

  .title-left {
    .title-row {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        color: #10b981;
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
  }
`;

const StatsBadges = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;

  .stat-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 3px 8px;

    .badge-num {
      font-size: 13px;
      font-weight: 700;
      color: #f8fafc;
    }

    .badge-lbl {
      font-size: 11px;
      color: #94a3b8;
    }

    &.highlight {
      background: rgba(245, 158, 11, 0.12);
      border-color: rgba(245, 158, 11, 0.3);

      .flame-icon {
        color: #f59e0b;
      }

      .badge-num {
        color: #f59e0b;
      }
    }
  }
`;

const HeatmapScrollWrapper = styled.div`
  overflow-x: auto;
  padding-bottom: 4px;
  width: 100%;
`;

const HeatmapContainer = styled.div`
  display: inline-flex;
  flex-direction: column;
  min-width: 450px;
`;

const MonthLabelsRow = styled.div`
  display: flex;
  margin-bottom: 4px;

  .day-axis-spacer {
    width: 24px;
    flex-shrink: 0;
  }

  .months-container {
    position: relative;
    height: 14px;
    width: 100%;

    .month-tag {
      position: absolute;
      font-size: 10.5px;
      font-weight: 500;
      color: #64748b;
    }
  }
`;

const GridBody = styled.div`
  display: flex;
  gap: 4px;
`;

const WeekdayLabelsCol = styled.div`
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 24px;
  flex-shrink: 0;

  .day-label {
    height: 11px;
    font-size: 9.5px;
    line-height: 11px;
    color: #64748b;
    text-align: right;
    padding-right: 4px;
  }
`;

const WeeksGrid = styled.div`
  display: flex;
  gap: 3px;
`;

const WeekColumn = styled.div`
  display: flex;
  flex-direction: column;
  gap: 3px;
`;

const DayCell = styled.div`
  width: 11px;
  height: 11px;
  border-radius: 2px;
  cursor: pointer;
  transition: transform 0.1s ease;

  &:hover {
    transform: scale(1.3);
    z-index: 10;
    box-shadow: 0 0 5px rgba(16, 185, 129, 0.6);
  }

  &.is-today {
    outline: 1.5px solid #38bdf8;
  }

  &.level-0 {
    background: rgba(255, 255, 255, 0.04);
  }

  &.level-1 {
    background: rgba(16, 185, 129, 0.35);
  }

  &.level-2 {
    background: rgba(16, 185, 129, 0.6);
  }

  &.level-3 {
    background: #10b981;
  }

  &.level-4 {
    background: #34d399;
    box-shadow: 0 0 4px rgba(52, 211, 153, 0.5);
  }
`;

const EmptyCell = styled.div`
  width: 11px;
  height: 11px;
`;

const HeatmapFooter = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  font-size: 11px;
  color: #94a3b8;
  padding-left: 24px;

  .streak-note {
    strong {
      color: #e2e8f0;
    }
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 4px;

    .legend-lbl {
      color: #64748b;
      font-size: 10px;
    }

    .legend-cell {
      width: 10px;
      height: 10px;
      border-radius: 2px;

      &.level-0 {
        background: rgba(255, 255, 255, 0.04);
      }
      &.level-1 {
        background: rgba(16, 185, 129, 0.35);
      }
      &.level-2 {
        background: rgba(16, 185, 129, 0.6);
      }
      &.level-3 {
        background: #10b981;
      }
      &.level-4 {
        background: #34d399;
      }
    }
  }
`;

const FloatingTooltip = styled.div`
  position: fixed;
  transform: translate(-50%, -100%);
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 11.5px;
  color: #e2e8f0;
  pointer-events: none;
  z-index: 1000;
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  max-width: 260px;
  white-space: normal;

  .tooltip-date {
    font-weight: 600;
    color: #f8fafc;
    font-size: 11.5px;
  }

  .tooltip-count {
    color: #10b981;
    font-weight: 500;
    margin: 2px 0 5px 0;
  }

  .tooltip-events {
    display: flex;
    flex-direction: column;
    gap: 3px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 4px;

    .event-line {
      font-size: 10.5px;
      color: #94a3b8;
      line-height: 1.3;
    }

    .event-more {
      font-size: 10px;
      color: #64748b;
      font-style: italic;
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
