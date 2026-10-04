import React, { useEffect, useState } from 'react';
import { Mic, Volume2, Loader2, Sparkles } from 'lucide-react';
import './VisualInterviewerAvatar.css';

export type InterviewTurnState =
  | 'initializing'
  | 'introducing'
  | 'interviewer_speaking'
  | 'transition_to_listen'
  | 'listening_ready'
  | 'user_speaking'
  | 'detecting_silence'
  | 'processing'
  | 'processing_answer'
  | 'evaluating_answer'
  | 'deciding_next'
  | 'paused'
  | 'idle';

interface VisualInterviewerAvatarProps {
  state: InterviewTurnState;
  audioLevel?: number; // 0 - 100
  silenceSecondsRemaining?: number; // e.g. 2.6 down to 0
  personaName?: string;
  domainTitle?: string;
  isMuted?: boolean;
}

export const VisualInterviewerAvatar: React.FC<VisualInterviewerAvatarProps> = ({
  state,
  audioLevel = 0,
  silenceSecondsRemaining = 0,
  personaName = 'Alex Mercer',
  domainTitle = 'Technical Lead',
  isMuted = false,
}) => {
  const [isBlinking, setIsBlinking] = useState(false);

  // Natural blinking effect every 3.5 to 5.5 seconds
  useEffect(() => {
    let timeoutId: number;
    const triggerBlink = () => {
      setIsBlinking(true);
      setTimeout(() => {
        setIsBlinking(false);
        const nextDelay = 3200 + Math.random() * 2400;
        timeoutId = window.setTimeout(triggerBlink, nextDelay);
      }, 160);
    };

    const initialDelay = 2000 + Math.random() * 2000;
    timeoutId = window.setTimeout(triggerBlink, initialDelay);

    return () => {
      clearTimeout(timeoutId);
    };
  }, []);

  const isSpeaking = state === 'interviewer_speaking' || state === 'introducing';
  const isListening = state === 'listening_ready' || state === 'user_speaking' || state === 'detecting_silence';
  const isUserSpeaking = state === 'user_speaking';
  const isDetectingSilence = state === 'detecting_silence';
  const isProcessing =
    state === 'processing' ||
    state === 'processing_answer' ||
    state === 'evaluating_answer' ||
    state === 'deciding_next';

  // Compute status badge text and color
  let statusText = 'Ready';
  let statusColorClass = 'idle';

  if (state === 'introducing') {
    statusText = isMuted ? 'Introducing Interview (Muted)' : 'Introducing interview & setting context...';
    statusColorClass = 'speaking';
  } else if (state === 'interviewer_speaking') {
    statusText = isMuted ? 'Speaking (Muted)' : 'Asking question...';
    statusColorClass = 'speaking';
  } else if (state === 'transition_to_listen') {
    statusText = 'Preparing microphone...';
    statusColorClass = 'listening';
  } else if (isDetectingSilence) {
    const sec = Math.max(0.1, silenceSecondsRemaining).toFixed(1);
    statusText = `Silence detected (${sec}s) — wrapping up...`;
    statusColorClass = 'silence';
  } else if (isUserSpeaking) {
    statusText = 'Listening — candidate speaking';
    statusColorClass = 'user-speaking';
  } else if (isListening) {
    statusText = 'Listening for your answer...';
    statusColorClass = 'listening';
  } else if (state === 'processing_answer') {
    statusText = 'Transcribing locally (faster-whisper)...';
    statusColorClass = 'processing';
  } else if (state === 'evaluating_answer') {
    statusText = 'Analyzing response with local AI...';
    statusColorClass = 'processing';
  } else if (isProcessing) {
    statusText = 'Processing turn with local AI...';
    statusColorClass = 'processing';
  }

  // Waveform bars derived from candidate audio level
  const waveBars = [
    Math.min(100, Math.max(12, audioLevel * 0.7)),
    Math.min(100, Math.max(18, audioLevel * 1.1)),
    Math.min(100, Math.max(24, audioLevel * 1.4)),
    Math.min(100, Math.max(16, audioLevel * 0.9)),
    Math.min(100, Math.max(20, audioLevel * 1.25)),
    Math.min(100, Math.max(14, audioLevel * 0.8)),
  ];

  return (
    <div className={`visual-interviewer-card ${statusColorClass}`}>
      {/* Background Aura Glow */}
      <div className={`avatar-aura-glow ${statusColorClass}`} />

      {/* SVG Avatar Portrait Frame */}
      <div className="avatar-portrait-viewport">
        <svg
          viewBox="0 0 200 240"
          className={`interviewer-svg ${isSpeaking ? 'speaking-active' : ''} ${isProcessing ? 'processing-active' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#0f172a" />
            </linearGradient>
            <linearGradient id="suitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#334155" />
              <stop offset="100%" stopColor="#1e293b" />
            </linearGradient>
            <linearGradient id="shirtGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#f8fafc" />
              <stop offset="100%" stopColor="#cbd5e1" />
            </linearGradient>
            <linearGradient id="tieGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#1d4ed8" />
            </linearGradient>
            <linearGradient id="skinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fde047" stopOpacity="0.1" />
              <stop offset="0%" stopColor="#fcd34d" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
            <filter id="avatarShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="4" stdDeviation="6" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Background circle inside frame */}
          <circle cx="100" cy="110" r="92" fill="url(#bgGrad)" stroke="rgba(255,255,255,0.08)" strokeWidth="2" />

          {/* Shoulders & Suit */}
          <g filter="url(#avatarShadow)">
            <path
              d="M 30 240 C 30 195, 60 178, 100 178 C 140 178, 170 195, 170 240 Z"
              fill="url(#suitGrad)"
            />
            {/* White Collar / Shirt */}
            <path
              d="M 82 178 L 100 216 L 118 178 L 108 172 L 92 172 Z"
              fill="url(#shirtGrad)"
            />
            {/* Necktie */}
            <path
              d="M 97 190 L 103 190 L 106 235 L 100 240 L 94 235 Z"
              fill="url(#tieGrad)"
            />
            {/* Suit Lapels */}
            <path
              d="M 68 180 L 90 220 L 78 240"
              stroke="#475569"
              strokeWidth="2.5"
              fill="none"
            />
            <path
              d="M 132 180 L 110 220 L 122 240"
              stroke="#475569"
              strokeWidth="2.5"
              fill="none"
            />
          </g>

          {/* Neck */}
          <path
            d="M 88 140 L 88 176 C 96 178, 104 178, 112 176 L 112 140 Z"
            fill="#e29b63"
          />

          {/* Head & Face Group with Micro Breathing */}
          <g className="avatar-head-group">
            {/* Ears */}
            <ellipse cx="62" cy="115" rx="6" ry="11" fill="#e29b63" />
            <ellipse cx="138" cy="115" rx="6" ry="11" fill="#e29b63" />

            {/* Jaw / Face */}
            <path
              d="M 66 95 C 64 140, 80 162, 100 162 C 120 162, 136 140, 134 95 C 134 60, 66 60, 66 95 Z"
              fill="#f1ae79"
            />

            {/* Hair */}
            <path
              d="M 63 92 C 60 62, 75 44, 100 44 C 125 44, 140 62, 137 92 C 131 72, 120 62, 100 62 C 80 62, 69 72, 63 92 Z"
              fill="#1e1e24"
            />
            <path
              d="M 64 88 C 65 70, 80 50, 105 48 C 128 47, 138 65, 136 82 C 130 68, 115 58, 98 60 C 82 62, 72 74, 64 88 Z"
              fill="#2e2e38"
            />

            {/* Eyebrows */}
            <path
              d={isProcessing ? "M 74 88 Q 85 85 92 89" : "M 74 89 Q 85 86 92 88"}
              stroke="#2e2e38"
              strokeWidth="2.8"
              strokeLinecap="round"
              fill="none"
            />
            <path
              d={isProcessing ? "M 108 89 Q 115 85 126 88" : "M 108 88 Q 115 86 126 89"}
              stroke="#2e2e38"
              strokeWidth="2.8"
              strokeLinecap="round"
              fill="none"
            />

            {/* Eyes (Blinking state or Open) */}
            {isBlinking ? (
              // Blinked eyes (horizontal slit)
              <g stroke="#1e1e24" strokeWidth="2.5" strokeLinecap="round">
                <line x1="77" y1="102" x2="89" y2="102" />
                <line x1="111" y1="102" x2="123" y2="102" />
              </g>
            ) : (
              // Open focused eyes
              <g>
                <ellipse cx="83" cy="102" rx="6.5" ry="4.5" fill="#ffffff" />
                <circle cx="84" cy="102" r="3" fill="#1e293b" />
                <circle cx="85" cy="101" r="1" fill="#ffffff" />

                <ellipse cx="117" cy="102" rx="6.5" ry="4.5" fill="#ffffff" />
                <circle cx="116" cy="102" r="3" fill="#1e293b" />
                <circle cx="117" cy="101" r="1" fill="#ffffff" />
              </g>
            )}

            {/* Glasses Frames (Executive Modern Style) */}
            <g stroke="#3b82f6" strokeWidth="1.8" fill="none" opacity="0.85">
              <rect x="73" y="94" width="20" height="15" rx="4" />
              <rect x="107" y="94" width="20" height="15" rx="4" />
              <line x1="93" y1="100" x2="107" y2="100" />
              <line x1="64" y1="99" x2="73" y2="99" />
              <line x1="127" y1="99" x2="136" y2="99" />
            </g>

            {/* Nose */}
            <path
              d="M 98 108 Q 100 120 96 124 L 104 124"
              stroke="#d98246"
              strokeWidth="1.8"
              strokeLinecap="round"
              fill="none"
            />

            {/* Dynamic Animated Mouth */}
            <g className="mouth-container">
              {isSpeaking ? (
                // Speaking: animated mouth aperture
                <ellipse
                  cx="100"
                  cy="142"
                  rx="7.5"
                  ry="5"
                  className="interviewer-speaking-mouth"
                  fill="#7f1d1d"
                  stroke="#b91c1c"
                  strokeWidth="1.5"
                />
              ) : isUserSpeaking ? (
                // Attentive candidate listening expression (subtle interested smile)
                <path
                  d="M 92 140 Q 100 146 108 140"
                  stroke="#a14e21"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  fill="none"
                />
              ) : (
                // Neutral pleasant professional expression
                <path
                  d="M 93 141 Q 100 144 107 141"
                  stroke="#a14e21"
                  strokeWidth="2"
                  strokeLinecap="round"
                  fill="none"
                />
              )}
            </g>
          </g>
        </svg>

        {/* Ambient Acoustic / Speech Waveform Overlay */}
        {(isListening || isSpeaking) && (
          <div className="avatar-audio-indicator-overlay">
            {waveBars.map((h, idx) => (
              <span
                key={idx}
                className="acoustic-bar"
                style={{
                  height: `${isSpeaking ? 30 + (idx % 3) * 20 : h}%`,
                  background: isSpeaking ? '#818cf8' : isDetectingSilence ? '#f59e0b' : '#34d399',
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Persona Info & Turn State Badge */}
      <div className="avatar-details">
        <div className="interviewer-identity">
          <span className="persona-name">{personaName}</span>
          <span className="persona-role">
            <Sparkles size={11} className="role-sparkle" />
            {domainTitle}
          </span>
        </div>

        {/* Turn State Indicator Badge */}
        <div className={`interviewer-turn-badge ${statusColorClass}`}>
          {isSpeaking && <Volume2 size={14} className="badge-icon-pulse" />}
          {isListening && !isDetectingSilence && <Mic size={14} className="badge-icon-pulse" />}
          {isDetectingSilence && <Mic size={14} className="badge-icon-amber" />}
          {isProcessing && <Loader2 size={14} className="spin-icon" />}
          <span>{statusText}</span>
        </div>
      </div>
    </div>
  );
};
