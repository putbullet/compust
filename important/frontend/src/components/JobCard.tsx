import React, { useRef, useState } from 'react';
import styled from 'styled-components';
import { MapPin, Building2, Bookmark, Sparkles, ArrowUpRight } from 'lucide-react';
import type { Job } from '../api/client';

interface JobCardProps {
  job: Job;
  companyName: string;
  isSaved?: boolean;
  onToggleSave?: () => void;
  onSelect: () => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  companyName,
  isSaved = false,
  onToggleSave,
  onSelect,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState({ x: 0, y: 0 });
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Normalize coordinates (-1 to 1)
    const normX = (x / rect.width) * 2 - 1;
    const normY = (y / rect.height) * 2 - 1;

    // Restrained 3D tilt: max 5deg to maintain professional elegance without layout shift
    const rotX = -normY * 4.5;
    const rotY = normX * 4.5;

    setRotate({ x: rotX, y: rotY });
    setGlare({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.15,
    });
  };

  const handleMouseLeave = () => {
    setRotate({ x: 0, y: 0 });
    setGlare((prev) => ({ ...prev, opacity: 0 }));
  };

  const formatSalary = () => {
    if (!job.salary_min && !job.salary_max) return null;
    const currency = job.salary_currency || 'MAD';
    const period = job.salary_period ? `/${job.salary_period}` : '';
    if (job.salary_min && job.salary_max) {
      return `${Number(job.salary_min).toLocaleString()} - ${Number(job.salary_max).toLocaleString()} ${currency} ${period}`;
    }
    if (job.salary_min) {
      return `From ${Number(job.salary_min).toLocaleString()} ${currency} ${period}`;
    }
    return `Up to ${Number(job.salary_max).toLocaleString()} ${currency} ${period}`;
  };

  const salaryString = formatSalary();

  return (
    <CardPerspectiveWrapper>
      <StyledCard
        ref={cardRef}
        onClick={onSelect}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          transform: `perspective(900px) rotateX(${rotate.x}deg) rotateY(${rotate.y}deg)`,
        }}
      >
        {/* Cowardly Eagle subtle dynamic lighting / glare overlay */}
        <div
          className="card-glare"
          style={{
            background: `radial-gradient(circle at ${glare.x}% ${glare.y}%, rgba(59, 130, 246, 0.25) 0%, rgba(14, 165, 233, 0.1) 40%, transparent 80%)`,
            opacity: glare.opacity,
          }}
        />

        <div className="card-inner">
          {/* Header: Company & Match / Save */}
          <div className="card-header">
            <div className="company-badge">
              <Building2 size={16} className="company-icon" />
              <span>{companyName}</span>
            </div>

            <div className="header-actions" onClick={(e) => e.stopPropagation()}>
              {job.match_score !== undefined && job.match_score !== null && (
                <div className={`match-badge ${job.match_score >= 70 ? 'high' : (job.match_score >= 45 ? 'mid' : 'low')}`}>
                  <Sparkles size={12} />
                  <span>{job.match_score}% Match</span>
                </div>
              )}
              <button
                className={`bookmark-btn ${isSaved ? 'saved' : ''}`}
                onClick={onToggleSave}
                aria-label="Save Job"
              >
                <Bookmark size={16} fill={isSaved ? '#3b82f6' : 'none'} />
              </button>
            </div>
          </div>

          {/* Title */}
          <h3 className="job-title">{job.title}</h3>

          {/* Location & Tags */}
          <div className="tags-row">
            {job.location && (
              <div className="location-tag">
                <MapPin size={13} />
                <span>{job.location}</span>
              </div>
            )}
            {job.remote_type && (
              <span className="badge badge-purple">{job.remote_type}</span>
            )}
            {job.employment_type && (
              <span className="badge badge-blue">{job.employment_type}</span>
            )}
          </div>

          {/* Salary */}
          {salaryString && (
            <div className="salary-pill">
              <span className="salary-text">{salaryString}</span>
            </div>
          )}

          {/* Footer */}
          <div className="card-footer">
            <span className="source-tag">Source: {job.source || 'Direct'}</span>
            <span className="view-detail-btn">
              <span>Explore</span>
              <ArrowUpRight size={14} />
            </span>
          </div>
        </div>
      </StyledCard>
    </CardPerspectiveWrapper>
  );
};

const CardPerspectiveWrapper = styled.div`
  perspective: 1000px;
  width: 100%;
`;

const StyledCard = styled.div`
  position: relative;
  border-radius: var(--radius-lg);
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  padding: 22px;
  cursor: pointer;
  transition: transform 180ms ease-out, border-color 200ms ease, box-shadow 200ms ease, background 200ms ease;
  box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  transform-style: preserve-3d;
  will-change: transform;

  @media (prefers-reduced-motion: reduce) {
    transform: none !important;
    transition: none !important;
  }

  &:hover {
    border-color: rgba(59, 130, 246, 0.45);
    box-shadow: 0 16px 36px -8px rgba(0, 0, 0, 0.6), 0 0 24px rgba(59, 130, 246, 0.18);
    background: rgba(20, 30, 52, 0.88);

    .view-detail-btn {
      color: #60a5fa;
      transform: translateX(3px);
    }
  }

  .card-glare {
    position: absolute;
    inset: 0;
    pointer-events: none;
    transition: opacity 250ms ease;
    z-index: 1;
  }

  .card-inner {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 14px;
    height: 100%;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .company-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #94a3b8;
  }

  .company-icon {
    color: #60a5fa;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .match-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;

    &.high {
      background: rgba(16, 185, 129, 0.18);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }
    &.mid {
      background: rgba(245, 158, 11, 0.18);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
    }
    &.low {
      background: rgba(148, 163, 184, 0.15);
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.25);
    }
  }

  .bookmark-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    color: #64748b;
    background: rgba(255, 255, 255, 0.04);
    transition: all 0.2s;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }

    &.saved {
      color: #3b82f6;
      background: rgba(59, 130, 246, 0.15);
    }
  }

  .job-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .tags-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .location-tag {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .badge {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 500;

    &.badge-purple {
      background: rgba(168, 85, 247, 0.12);
      color: #c084fc;
      border: 1px solid rgba(168, 85, 247, 0.2);
    }
    &.badge-blue {
      background: rgba(59, 130, 246, 0.12);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.2);
    }
  }

  .salary-pill {
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.2);
    width: fit-content;

    .salary-text {
      font-size: 0.78rem;
      font-weight: 600;
      color: #34d399;
    }
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);

    .source-tag {
      font-size: 0.75rem;
      color: #64748b;
    }

    .view-detail-btn {
      display: flex;
      align-items: center;
      gap: 3px;
      font-size: 0.8rem;
      font-weight: 600;
      color: #94a3b8;
      transition: all 0.2s;
    }
  }
`;
