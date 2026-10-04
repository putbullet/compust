import React, { useState, useEffect } from 'react';
import { AlexVideoInterviewer } from './AlexVideoInterviewer';
import { VisualInterviewerAvatar, type InterviewTurnState } from './VisualInterviewerAvatar';
import { Volume2, Mic, Loader2 } from 'lucide-react';

export type PresentationMode = 'auto' | 'video' | 'visual' | 'minimal';

export interface InterviewerPresentationProps {
  mode?: PresentationMode;
  videoUrl?: string | null;
  posterUrl?: string;
  state: InterviewTurnState;
  isMuted?: boolean;
  audioLevel?: number;
  silenceSecondsRemaining?: number;
  personaName?: string;
  domainTitle?: string;
  onSpeakingFinished: () => void;
  onFallbackTriggered?: (reason: string) => void;
  onReadyToAnswer?: () => void;
}

export const InterviewerPresentation: React.FC<InterviewerPresentationProps> = ({
  mode = 'auto',
  videoUrl,
  posterUrl = '/interviewer/alex/identity/reference.jpg',
  state,
  isMuted = false,
  audioLevel = 0,
  silenceSecondsRemaining = 0,
  personaName = 'Alex',
  domainTitle = 'Technical Lead',
  onSpeakingFinished,
  onFallbackTriggered,
  onReadyToAnswer,
}) => {
  const [videoError, setVideoError] = useState(false);

  // Reset video error state whenever videoUrl changes
  useEffect(() => {
    setVideoError(false);
  }, [videoUrl]);

  const handleVideoError = (errorMsg: string) => {
    console.warn(`[InterviewerPresentation] Falling back to visual avatar: ${errorMsg}`);
    setVideoError(true);
    if (onFallbackTriggered) {
      onFallbackTriggered(errorMsg);
    }
  };

  // Determine which presentation provider to render
  const canPlayVideo = Boolean(videoUrl) && !videoError;
  const resolvedMode =
    mode === 'auto'
      ? canPlayVideo
        ? 'video'
        : 'visual'
      : mode === 'video' && !canPlayVideo
      ? 'visual'
      : mode;

  if (resolvedMode === 'video' && videoUrl) {
    return (
      <AlexVideoInterviewer
        videoUrl={videoUrl}
        posterUrl={posterUrl}
        state={state}
        isMuted={isMuted}
        audioLevel={audioLevel}
        silenceSecondsRemaining={silenceSecondsRemaining}
        personaName={personaName}
        domainTitle={domainTitle}
        onVideoEnded={onSpeakingFinished}
        onErrorFallback={handleVideoError}
        onReadyToAnswer={onReadyToAnswer}
      />
    );
  }

  if (resolvedMode === 'minimal') {
    return (
      <div className="interviewer-orb-container">
        <div
          className={`interviewer-orb ${
            state === 'introducing' || state === 'interviewer_speaking'
              ? 'speaking'
              : state === 'listening_ready' || state === 'user_speaking'
              ? 'listening'
              : state === 'detecting_silence'
              ? 'listening'
              : 'processing'
          }`}
        >
          {(state === 'interviewer_speaking' || state === 'introducing') && <Volume2 size={32} color="#ffffff" />}
          {(state === 'listening_ready' || state === 'user_speaking') && <Mic size={32} color="#ffffff" />}
          {state === 'detecting_silence' && <Mic size={32} color="#fcd34d" />}
          {(state === 'processing' ||
            state === 'processing_answer' ||
            state === 'evaluating_answer' ||
            state === 'deciding_next') && <Loader2 size={32} color="#ffffff" className="spin-icon" />}
        </div>

        <div className="interviewer-state-label">
          {state === 'introducing' && 'Interviewer Introduction & Setting Context...'}
          {state === 'interviewer_speaking' && 'Interviewer is speaking...'}
          {state === 'transition_to_listen' && 'Preparing microphone...'}
          {state === 'listening_ready' && 'Listening for your answer... (Speak naturally)'}
          {state === 'user_speaking' && 'Candidate voice detected'}
          {state === 'detecting_silence' && `Silence detected (${silenceSecondsRemaining.toFixed(1)}s)...`}
          {state === 'processing_answer' && 'Transcribing audio with local faster-whisper...'}
          {state === 'evaluating_answer' && 'Analyzing response with local AI...'}
          {state === 'deciding_next' && 'Preparing next question...'}
          {state === 'processing' && 'Processing answer with local AI...'}
        </div>
      </div>
    );
  }

  // Default / Fallback: VisualInterviewerAvatar
  return (
    <VisualInterviewerAvatar
      state={state}
      audioLevel={audioLevel}
      silenceSecondsRemaining={silenceSecondsRemaining}
      personaName={personaName}
      domainTitle={domainTitle}
      isMuted={isMuted}
    />
  );
};
