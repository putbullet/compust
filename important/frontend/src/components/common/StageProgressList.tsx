import React, { useState, useEffect } from 'react';
import './StageProgressList.css';

export interface StageProgressListProps {
  stages: string[];
  currentStage: number;
  title?: string;
  className?: string;
}

export const StageProgressList: React.FC<StageProgressListProps> = ({
  stages,
  currentStage,
  title = 'Running Analysis...',
  className = '',
}) => {
  return (
    <div className={`compust-progress-container ${className}`}>
      <div className="compust-progress-header">
        <div className="compust-stage-spinner" />
        <span>{title}</span>
      </div>
      <div className="compust-stage-list">
        {stages.map((stage, idx) => {
          const isCompleted = idx < currentStage;
          const isActive = idx === currentStage;

          return (
            <div
              key={idx}
              className={`compust-stage-item ${
                isCompleted ? 'completed' : isActive ? 'active' : 'pending'
              }`}
            >
              <div className="compust-stage-icon">
                {isCompleted ? '✓' : isActive ? '●' : '○'}
              </div>
              <div className="compust-stage-label">{stage}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * Hook to automatically progress through stages at a timed interval while running,
 * stopping at the penultimate stage until the action completes.
 */
export function useStageProgress(
  stages: string[],
  isRunning: boolean,
  intervalMs: number = 450
): number {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    if (!isRunning) {
      setCurrentStage(0);
      return;
    }

    setCurrentStage(0);
    const maxAutoStage = Math.max(0, stages.length - 2);

    const timer = setInterval(() => {
      setCurrentStage((prev) => {
        if (prev < maxAutoStage) {
          return prev + 1;
        }
        return prev;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isRunning, stages.length, intervalMs]);

  return currentStage;
}
