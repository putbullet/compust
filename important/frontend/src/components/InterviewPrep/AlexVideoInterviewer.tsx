import React, { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX, Mic, Loader2, Video, FastForward } from 'lucide-react';
import type { InterviewTurnState } from './VisualInterviewerAvatar';
import './AlexVideoInterviewer.css';

interface AlexVideoInterviewerProps {
  videoUrl: string;
  posterUrl?: string;
  state: InterviewTurnState;
  isMuted?: boolean;
  audioLevel?: number; // 0 - 100 (candidate mic level)
  silenceSecondsRemaining?: number;
  personaName?: string;
  domainTitle?: string;
  onVideoEnded: () => void;
  onErrorFallback: (error: string) => void;
  onReadyToAnswer?: () => void;
}

export const AlexVideoInterviewer: React.FC<AlexVideoInterviewerProps> = ({
  videoUrl,
  posterUrl = '/interviewer/alex/identity/reference.jpg',
  state,
  isMuted = false,
  audioLevel = 0,
  silenceSecondsRemaining = 0,
  personaName = 'Alex',
  domainTitle = 'Lead Technical Interviewer',
  onVideoEnded,
  onErrorFallback,
  onReadyToAnswer,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasPlaybackError, setHasPlaybackError] = useState(false);

  const isSpeaking = state === 'interviewer_speaking' || state === 'introducing';
  const isListening = state === 'listening_ready' || state === 'user_speaking' || state === 'detecting_silence';
  const isUserSpeaking = state === 'user_speaking';
  const isDetectingSilence = state === 'detecting_silence';
  const isProcessing =
    state === 'processing' ||
    state === 'processing_answer' ||
    state === 'evaluating_answer' ||
    state === 'deciding_next';

  // Handle video element play / pause according to interview state
  useEffect(() => {
    const video = videoRef.current;
    if (!video || hasPlaybackError) return;

    if (isSpeaking) {
      video.currentTime = 0;
      video.muted = isMuted;
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsPlaying(true);
          })
          .catch((err) => {
            console.warn('[AlexVideoInterviewer] Autoplay failed or blocked:', err);
            // If autoplay with sound is blocked by browser policy, try muted or trigger fallback
            if (!isMuted) {
              video.muted = true;
              video
                .play()
                .then(() => setIsPlaying(true))
                .catch((e2) => {
                  console.error('[AlexVideoInterviewer] Playback error after muted retry:', e2);
                  setHasPlaybackError(true);
                  onErrorFallback('Autoplay blocked or media error');
                });
            } else {
              setHasPlaybackError(true);
              onErrorFallback('Autoplay error');
            }
          });
      }
    } else {
      // Pause video when turn advances to listening or processing
      video.pause();
      setIsPlaying(false);
    }
  }, [videoUrl, isSpeaking, isMuted, hasPlaybackError, onErrorFallback]);

  // Synchronize mute state directly with HTML5 video
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = isMuted;
    }
  }, [isMuted]);

  const handleEnded = () => {
    setIsPlaying(false);
    onVideoEnded();
  };

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.warn('[AlexVideoInterviewer] Video error on URL:', videoUrl, e);
    setHasPlaybackError(true);
    onErrorFallback('Failed to load video stream');
  };

  const handleLoadedData = () => {
    setHasPlaybackError(false);
  };

  // Status badge calculation
  let statusBadgeText = 'Ready';
  let statusClass = 'idle';

  if (state === 'introducing') {
    statusBadgeText = isMuted ? 'Alex introducing (Muted)' : 'Alex introducing interview & setting context...';
    statusClass = 'speaking';
  } else if (state === 'interviewer_speaking') {
    statusBadgeText = isMuted ? 'Alex speaking (Muted)' : 'Alex is asking question...';
    statusClass = 'speaking';
  } else if (state === 'transition_to_listen') {
    statusBadgeText = 'Preparing microphone...';
    statusClass = 'listening';
  } else if (isDetectingSilence) {
    statusBadgeText = `Silence detected (${Math.max(0.1, silenceSecondsRemaining).toFixed(1)}s) — wrapping up...`;
    statusClass = 'silence';
  } else if (isUserSpeaking) {
    statusBadgeText = 'Listening — candidate speaking';
    statusClass = 'user-speaking';
  } else if (isListening) {
    statusBadgeText = 'Listening for your answer...';
    statusClass = 'listening';
  } else if (state === 'processing_answer') {
    statusBadgeText = 'Transcribing locally (faster-whisper)...';
    statusClass = 'processing';
  } else if (state === 'evaluating_answer') {
    statusBadgeText = 'Analyzing response with local AI...';
    statusClass = 'processing';
  } else if (isProcessing) {
    statusBadgeText = 'Processing turn with local AI...';
    statusClass = 'processing';
  }

  return (
    <div className={`alex-video-interviewer ${statusClass}`}>
      <div className="alex-video-frame">
        {/* Synchronized video element */}
        <video
          ref={videoRef}
          key={videoUrl}
          src={videoUrl}
          poster={posterUrl}
          playsInline
          preload="auto"
          onEnded={handleEnded}
          onError={handleError}
          onLoadedData={handleLoadedData}
          className={`alex-native-video ${isPlaying ? 'is-playing' : 'is-idle'}`}
        />

        {/* Ambient subtle glow ring reacting to candidate audio or interviewer speech */}
        <div
          className={`alex-ambient-glow ${isSpeaking ? 'interviewer-active' : isUserSpeaking ? 'candidate-active' : ''}`}
          style={{
            opacity: isSpeaking ? 0.8 : isListening ? Math.min(0.9, 0.2 + (audioLevel / 100) * 0.7) : 0.3,
          }}
        />

        {/* Header Overlay: Persona & Stream Badge */}
        <div className="alex-video-overlay-header">
          <div className="alex-persona-info">
            <span className="alex-live-indicator">
              <span className="live-dot" />
              <Video size={13} className="live-icon" />
              HD Video
            </span>
            <div className="alex-persona-names">
              <span className="alex-name">{personaName}</span>
              <span className="alex-title">{domainTitle}</span>
            </div>
          </div>

          <div className="alex-header-controls">
            {isSpeaking && onReadyToAnswer && (
              <button
                type="button"
                className="alex-skip-speech-btn"
                onClick={onReadyToAnswer}
                title="Skip to answering immediately"
              >
                <FastForward size={14} />
                <span>I'm Ready to Answer</span>
              </button>
            )}
            {isMuted && (
              <span className="alex-muted-tag" title="Interviewer is muted">
                <VolumeX size={14} />
              </span>
            )}
          </div>
        </div>

        {/* Footer Overlay: Turn state badge & candidate acoustic meter */}
        <div className="alex-video-overlay-footer">
          <div className={`alex-turn-badge ${statusClass}`}>
            {isSpeaking && <Volume2 size={14} className="badge-icon pulse-icon" />}
            {isListening && <Mic size={14} className={`badge-icon ${isUserSpeaking ? 'voice-active' : ''}`} />}
            {isProcessing && <Loader2 size={14} className="badge-icon spin-icon" />}
            <span>{statusBadgeText}</span>
          </div>

          {isListening && (
            <div className="alex-candidate-meter" title={`Microphone Level: ${Math.round(audioLevel)}%`}>
              <div className="meter-bar-track">
                <div
                  className="meter-bar-fill"
                  style={{ width: `${Math.min(100, Math.max(4, audioLevel))}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
