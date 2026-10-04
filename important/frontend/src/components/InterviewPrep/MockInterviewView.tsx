import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  Volume2,
  VolumeX,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RotateCcw,
  History,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Cpu,
  FileText,
  Loader2,
  Play,
  Award,
  BookOpen,
  ArrowLeft,
  Database,
  Shield,
  BrainCircuit,
  User,
  MessageSquare,
  Check,
  FastForward,
  Video,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  MockInterviewSetupResponse,
  NextQuestionItem,
  MockInterviewAssessmentResponse,
  SessionHistorySummary,
  ResumeDomainDetectResponse,
  STTStatusResponse,
  TTSStatusResponse,
} from '../../api/client';
import { useTranslation } from '../../i18n';
import { InterviewerPresentation, type PresentationMode } from './InterviewerPresentation';
import type { InterviewTurnState } from './VisualInterviewerAvatar';
import './MockInterviewView.css';

type Phase = 'setup' | 'permission' | 'interview' | 'evaluating' | 'assessment' | 'history';

interface MockInterviewViewProps {
  initialDomainId?: string;
  onNavigateBack?: () => void;
}

const DOMAIN_OPTIONS = [
  {
    id: 'data_engineering',
    name: 'Data Engineering',
    desc: 'SQL, Spark, Distributed Systems, Data Modeling, Warehousing & Streaming',
    icon: Database,
  },
  {
    id: 'security_engineering',
    name: 'Security Engineering',
    desc: 'OAuth2/OIDC, AppSec, Cryptography, Cloud Security & Threat Modeling',
    icon: Shield,
  },
  {
    id: 'ai_tech_interview',
    name: 'AI Engineering',
    desc: 'LLMs, Prompt Engineering, RAG Systems, Vectors, Embeddings & Fine-tuning',
    icon: BrainCircuit,
  },
];

const DIFFICULTY_OPTIONS = ['Fundamental', 'Intermediate', 'Advanced', 'Mixed'];
const DURATION_OPTIONS = [10, 20, 30, 45];

export const MockInterviewView: React.FC<MockInterviewViewProps> = ({
  initialDomainId = 'data_engineering',
  onNavigateBack,
}) => {
  const { t } = useTranslation();
  const tr = t.mockInterview;

  // Phase State
  const [phase, setPhase] = useState<Phase>('setup');

  // Presentation Mode: Alex Video / Visual Interviewer / Minimal Orb
  const [presentationMode, setPresentationMode] = useState<PresentationMode>('auto');

  // Setup Form State
  const [domainId, setDomainId] = useState<string>(initialDomainId);
  const [role, setRole] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('Mixed');
  const [durationMinutes, setDurationMinutes] = useState<number>(20);
  const [resumeSuggestion, setResumeSuggestion] = useState<ResumeDomainDetectResponse | null>(null);
  const [analyzingResume, setAnalyzingResume] = useState<boolean>(false);
  const [creatingSession, setCreatingSession] = useState<boolean>(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  // Active Session State
  const [sessionId, setSessionId] = useState<number | null>(null);
  const sessionIdRef = useRef<number | null>(null);
  const [setupInfo, setSetupInfo] = useState<MockInterviewSetupResponse | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<NextQuestionItem | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(1200);
  const [questionsAsked, setQuestionsAsked] = useState<number>(0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [confirmEndModal, setConfirmEndModal] = useState<boolean>(false);
  const [submittingTurn, setSubmittingTurn] = useState<boolean>(false);
  const submittingTurnRef = useRef<boolean>(false);

  // STT Status
  const [sttStatus, setSttStatus] = useState<STTStatusResponse | null>(null);

  // Turn-Taking State Machine
  const [turnState, setTurnState] = useState<InterviewTurnState>('interviewer_speaking');
  const turnStateRef = useRef<InterviewTurnState>('interviewer_speaking');

  // TTS Voice Engine State
  const [ttsStatus, setTtsStatus] = useState<TTSStatusResponse | null>(null);
  const [selectedVoiceMode, setSelectedVoiceMode] = useState<'neural' | 'browser'>('neural');
  const [selectedNeuralVoice, setSelectedNeuralVoice] = useState<string>('en-US-AndrewMultilingualNeural');
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>('');
  const [isPlayingPreview, setIsPlayingPreview] = useState<boolean>(false);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);

  // Audio Recording & Activity Detection State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const recordingSecondsRef = useRef<number>(0);
  const [candidateTranscript, setCandidateTranscript] = useState<string>('');
  const [micAudioLevel, setMicAudioLevel] = useState<number>(0);
  const [silenceThresholdSec, setSilenceThresholdSec] = useState<number>(2.8);
  const silenceThresholdSecRef = useRef<number>(2.8);
  const [silenceSecondsRemaining, setSilenceSecondsRemaining] = useState<number>(2.8);
  const [micTesting, setMicTesting] = useState<boolean>(false);
  const [micReady, setMicReady] = useState<boolean>(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [startingInterview, setStartingInterview] = useState<boolean>(false);
  const [startError, setStartError] = useState<string | null>(null);

  // Post-Interview Evaluation State
  const [evaluatingStage, setEvaluatingStage] = useState<number>(1);
  const [assessment, setAssessment] = useState<MockInterviewAssessmentResponse | null>(null);
  const [expandedTurnId, setExpandedTurnId] = useState<number | null>(null);

  // History State
  const [historySessions, setHistorySessions] = useState<SessionHistorySummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // References
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const recTimerIntervalRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const silenceCountdownIntervalRef = useRef<number | null>(null);
  const analyserLoopIdRef = useRef<number | null>(null);
  const hasSpokenThisTurnRef = useRef<boolean>(false);

  // Sync ref mirrors
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    submittingTurnRef.current = submittingTurn;
  }, [submittingTurn]);

  useEffect(() => {
    turnStateRef.current = turnState;
  }, [turnState]);

  useEffect(() => {
    recordingSecondsRef.current = recordingSeconds;
  }, [recordingSeconds]);

  useEffect(() => {
    silenceThresholdSecRef.current = silenceThresholdSec;
  }, [silenceThresholdSec]);

  // --------------------------------------------------------------------------
  // Check Local STT & Neural TTS Status on Mount
  // --------------------------------------------------------------------------
  useEffect(() => {
    api.getMockInterviewSTTStatus()
      .then((status: STTStatusResponse) => setSttStatus(status))
      .catch((err: any) => console.warn('Could not query STT status:', err));

    api.getMockInterviewTTSStatus()
      .then((status: TTSStatusResponse) => {
        setTtsStatus(status);
        if (status.default_voice) {
          setSelectedNeuralVoice(status.default_voice);
        }
      })
      .catch((err: any) => console.warn('Could not query TTS status:', err));
  }, []);

  // --------------------------------------------------------------------------
  // TTS Voice Selection Engine: Discover and prioritize Natural/Online voices
  // --------------------------------------------------------------------------
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const populateVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      if (!voices || voices.length === 0) return;
      setAvailableVoices(voices);

      setSelectedVoiceName((current) => {
        if (current && voices.some((v) => v.name === current)) {
          return current;
        }
        // Priority 1: Natural / Online English voices (e.g. Microsoft Jenny / Guy Online (Natural))
        const naturalVoice = voices.find(
          (v) =>
            v.lang.startsWith('en') &&
            (v.name.includes('Natural') || v.name.includes('Online'))
        );
        if (naturalVoice) return naturalVoice.name;

        // Priority 2: Google US English or Google UK English
        const googleVoice = voices.find(
          (v) => v.lang.startsWith('en') && v.name.includes('Google')
        );
        if (googleVoice) return googleVoice.name;

        // Priority 3: Non-legacy desktop English voice (avoid robotic Microsoft David)
        const modernVoice = voices.find(
          (v) => v.lang.startsWith('en') && !v.name.includes('David')
        );
        if (modernVoice) return modernVoice.name;

        // Priority 4: Any English voice
        const anyEnVoice = voices.find((v) => v.lang.startsWith('en'));
        if (anyEnVoice) return anyEnVoice.name;

        return voices[0]?.name || '';
      });
    };

    populateVoices();
    window.speechSynthesis.onvoiceschanged = populateVoices;

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, []);

  // --------------------------------------------------------------------------
  // Interview Timer Management
  // --------------------------------------------------------------------------
  useEffect(() => {
    if (phase === 'interview') {
      timerIntervalRef.current = window.setInterval(() => {
        setRemainingSeconds((prev) => {
          if (prev <= 1) {
            handleNaturalConclusion();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [phase]);

  // Clean up all resources on unmount
  useEffect(() => {
    return () => {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (silenceCountdownIntervalRef.current) clearInterval(silenceCountdownIntervalRef.current);
      if (analyserLoopIdRef.current) cancelAnimationFrame(analyserLoopIdRef.current);
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  // --------------------------------------------------------------------------
  // Audio Activity & VAD Level Monitoring
  // --------------------------------------------------------------------------
  const startAudioLevelMonitoring = useCallback(() => {
    if (analyserLoopIdRef.current) {
      cancelAnimationFrame(analyserLoopIdRef.current);
      analyserLoopIdRef.current = null;
    }

    const checkLevel = () => {
      if (!analyserRef.current) return;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserRef.current.getByteFrequencyData(dataArray);

      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const avg = sum / bufferLength;
      const level = Math.min(100, Math.round((avg / 128) * 100));
      setMicAudioLevel(level);

      const SPEECH_THRESHOLD = 15; // Percent volume threshold for candidate speech

      if (level >= SPEECH_THRESHOLD) {
        // Candidate voice active!
        hasSpokenThisTurnRef.current = true;
        setTurnState('user_speaking');

        // Cancel any silence timer
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        if (silenceCountdownIntervalRef.current) {
          clearInterval(silenceCountdownIntervalRef.current);
          silenceCountdownIntervalRef.current = null;
        }
        setSilenceSecondsRemaining(silenceThresholdSecRef.current);
      } else if (level < SPEECH_THRESHOLD && hasSpokenThisTurnRef.current) {
        // Candidate has spoken and is now silent
        // Only trigger sustained silence timer if candidate has been speaking for at least ~2s to avoid cutoffs on brief opening pauses
        if (turnStateRef.current === 'user_speaking' && recordingSecondsRef.current >= 2) {
          setTurnState('detecting_silence');

          // Start sustained silence timer
          if (!silenceTimerRef.current) {
            const startTime = Date.now();
            const thresholdMs = Math.round(silenceThresholdSecRef.current * 1000);
            silenceCountdownIntervalRef.current = window.setInterval(() => {
              const elapsed = Date.now() - startTime;
              const remaining = Math.max(0, (thresholdMs - elapsed) / 1000);
              setSilenceSecondsRemaining(remaining);
            }, 100);

            silenceTimerRef.current = window.setTimeout(() => {
              if (silenceCountdownIntervalRef.current) {
                clearInterval(silenceCountdownIntervalRef.current);
                silenceCountdownIntervalRef.current = null;
              }
              silenceTimerRef.current = null;
              // Sustained silence reached -> automatically submit turn!
              handleAutoFinalizeAnswer();
            }, thresholdMs);
          }
        }
      }

      analyserLoopIdRef.current = requestAnimationFrame(checkLevel);
    };

    analyserLoopIdRef.current = requestAnimationFrame(checkLevel);
  }, []);

  // --------------------------------------------------------------------------
  // Automatic Listening: Starts mic recording after AI speech finishes
  // --------------------------------------------------------------------------
  const startAutoListening = useCallback(async () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setCandidateTranscript('');
    audioChunksRef.current = [];
    hasSpokenThisTurnRef.current = false;
    setSilenceSecondsRemaining(silenceThresholdSecRef.current);

    try {
      let stream = audioStreamRef.current;
      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioStreamRef.current = stream;
      }

      // Initialize or resume AudioContext for live frequency analysis
      if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioCtx;
        const analyser = audioCtx.createAnalyser();
        analyserRef.current = analyser;
        analyser.fftSize = 256;
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
      } else if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      // Initialize MediaRecorder
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);
      setTurnState('listening_ready');

      if (recTimerIntervalRef.current) clearInterval(recTimerIntervalRef.current);
      recTimerIntervalRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);

      // Begin voice activity level loop
      startAudioLevelMonitoring();
    } catch (err: any) {
      console.error('Failed to start automatic microphone listening:', err);
      setTurnState('listening_ready');
    }
  }, [startAudioLevelMonitoring]);

  // Derive avatar persona name from current voice
  const getPersonaName = () => {
    if (selectedNeuralVoice.includes('Aria')) return 'Elena Vance';
    if (selectedNeuralVoice.includes('Guy')) return 'Marcus Stone';
    if (selectedNeuralVoice.includes('Jenny')) return 'Sarah Chen';
    if (selectedNeuralVoice.includes('Ryan')) return 'David Sterling';
    if (selectedNeuralVoice.includes('Sonia')) return 'Victoria Croft';
    return 'Alex Mercer';
  };

  // --------------------------------------------------------------------------
  // Voice Preview Engine
  // --------------------------------------------------------------------------
  const handlePreviewVoice = (voiceId: string) => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    setIsPlayingPreview(true);
    const sampleText = "Hello! It's great to meet you. I'm looking forward to our interview today.";

    if (selectedVoiceMode === 'neural' || voiceId.includes('Neural')) {
      const url = api.getMockInterviewTTSUrl(sampleText, voiceId, '-3%');
      const audio = new Audio(url);
      activeAudioRef.current = audio;
      audio.onended = () => {
        setIsPlayingPreview(false);
        activeAudioRef.current = null;
      };
      audio.onerror = () => {
        setIsPlayingPreview(false);
        activeAudioRef.current = null;
      };
      audio.play().catch(() => setIsPlayingPreview(false));
    } else {
      if (!window.speechSynthesis) {
        setIsPlayingPreview(false);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(sampleText);
      const match = availableVoices.find((v) => v.name === voiceId);
      if (match) utterance.voice = match;
      utterance.onend = () => setIsPlayingPreview(false);
      utterance.onerror = () => setIsPlayingPreview(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleInterruptInterviewer = useCallback(() => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setTurnState('transition_to_listen');
    setTimeout(() => {
      startAutoListening();
    }, 150);
  }, [startAutoListening]);

  // --------------------------------------------------------------------------
  // TTS (Neural Edge-TTS + SpeechSynthesis Fallback) with Automatic Turn Hand-off
  // --------------------------------------------------------------------------
  const speakInterviewer = useCallback(
    (text: string, onSpeechFinished?: () => void, isIntro: boolean = false) => {
      if (isMuted) {
        setTurnState('transition_to_listen');
        setTimeout(() => {
          if (onSpeechFinished) {
            onSpeechFinished();
          } else {
            startAutoListening();
          }
        }, 350);
        return;
      }

      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }

      setTurnState(isIntro ? 'introducing' : 'interviewer_speaking');

      const handleSpeechComplete = () => {
        setTurnState('transition_to_listen');
        setTimeout(() => {
          if (onSpeechFinished) {
            onSpeechFinished();
          } else {
            startAutoListening();
          }
        }, 380);
      };

      const fallbackSpeak = () => {
        if (!window.speechSynthesis) {
          handleSpeechComplete();
          return;
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.96;
        utterance.pitch = 1.0;
        if (selectedVoiceName && availableVoices.length > 0) {
          const match = availableVoices.find((v) => v.name === selectedVoiceName);
          if (match) utterance.voice = match;
        }
        utterance.onend = handleSpeechComplete;
        utterance.onerror = handleSpeechComplete;
        window.speechSynthesis.speak(utterance);
      };

      // Try Studio Neural TTS first
      if (selectedVoiceMode === 'neural' && selectedNeuralVoice) {
        try {
          const ttsUrl = api.getMockInterviewTTSUrl(text, selectedNeuralVoice, '-3%');
          const audio = new Audio(ttsUrl);
          activeAudioRef.current = audio;

          audio.onended = () => {
            activeAudioRef.current = null;
            handleSpeechComplete();
          };

          audio.onerror = () => {
            console.warn('Neural audio playback failed, falling back to browser SpeechSynthesis');
            activeAudioRef.current = null;
            fallbackSpeak();
          };

          audio.play().catch((playErr) => {
            console.warn('Audio autoplay failed or interrupted, fallback to SpeechSynthesis:', playErr);
            activeAudioRef.current = null;
            fallbackSpeak();
          });
          return;
        } catch (e) {
          console.warn('Neural TTS initialization error, fallback:', e);
        }
      }

      fallbackSpeak();
    },
    [isMuted, selectedVoiceMode, selectedNeuralVoice, selectedVoiceName, availableVoices, startAutoListening]
  );

  // --------------------------------------------------------------------------
  // Answer Submission & Question Progression
  // --------------------------------------------------------------------------
  const uploadAndAdvanceTurn = async (audioBlob: Blob) => {
    const curSessionId = sessionIdRef.current;
    if (!curSessionId || submittingTurnRef.current) return;
    setSubmittingTurn(true);
    submittingTurnRef.current = true;
    setTurnState('processing_answer');

    try {
      let finalTranscript = candidateTranscript.trim();

      // Transcribe via local faster-whisper if audio recorded
      if (audioBlob.size > 200) {
        try {
          const sttRes = await api.uploadMockInterviewAudio(audioBlob);
          if (sttRes.transcript && sttRes.transcript.trim()) {
            finalTranscript = sttRes.transcript.trim();
            setCandidateTranscript(finalTranscript);
          } else if (sttRes.error) {
            console.warn('STT notice:', sttRes.error);
          }
        } catch (sttErr) {
          console.error('STT upload error:', sttErr);
        }
      }

      setTurnState('evaluating_answer');

      // Submit turn to backend engine
      const response = await api.submitMockInterviewTurn(curSessionId, {
        session_id: curSessionId,
        transcript: finalTranscript,
        stt_engine: 'faster-whisper',
        answer_duration_seconds: recordingSecondsRef.current || 20,
      });

      setTurnState('deciding_next');

      if (response.interview_complete) {
        // Natural closing spoken message
        if (response.message && !isMuted) {
          speakInterviewer(response.message, () => {
            startEvaluationPoll();
          });
        } else {
          startEvaluationPoll();
        }
      } else {
        setCurrentQuestion(response.next_question || null);
        setQuestionsAsked(response.questions_asked);
        setCandidateTranscript('');
        setRecordingSeconds(0);

        if (response.next_question?.interviewer_video_url) {
          setTurnState('interviewer_speaking');
        } else if (response.next_question?.tts_text) {
          speakInterviewer(response.next_question.tts_text, () => {
            startAutoListening();
          });
        } else {
          startAutoListening();
        }
      }
    } catch (err: any) {
      console.error('Turn submission error:', err);
      alert(err.message || 'Error processing turn.');
      setTurnState('listening_ready');
    } finally {
      setSubmittingTurn(false);
      submittingTurnRef.current = false;
    }
  };

  // Called automatically when silence detected OR manually via [ Finish Answer ]
  const handleAutoFinalizeAnswer = useCallback(() => {
    if (analyserLoopIdRef.current) {
      cancelAnimationFrame(analyserLoopIdRef.current);
      analyserLoopIdRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (silenceCountdownIntervalRef.current) {
      clearInterval(silenceCountdownIntervalRef.current);
      silenceCountdownIntervalRef.current = null;
    }

    if (recTimerIntervalRef.current) {
      clearInterval(recTimerIntervalRef.current);
      recTimerIntervalRef.current = null;
    }

    setTurnState('processing');
    setIsRecording(false);

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await uploadAndAdvanceTurn(audioBlob);
      };
      mediaRecorderRef.current.stop();
    } else {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      uploadAndAdvanceTurn(audioBlob);
    }
  }, [candidateTranscript]);

  const handleSkipQuestion = async () => {
    const curSessionId = sessionIdRef.current;
    if (!curSessionId || submittingTurnRef.current) return;

    if (analyserLoopIdRef.current) {
      cancelAnimationFrame(analyserLoopIdRef.current);
      analyserLoopIdRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (silenceCountdownIntervalRef.current) {
      clearInterval(silenceCountdownIntervalRef.current);
      silenceCountdownIntervalRef.current = null;
    }
    if (recTimerIntervalRef.current) {
      clearInterval(recTimerIntervalRef.current);
      recTimerIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    setSubmittingTurn(true);
    submittingTurnRef.current = true;
    setTurnState('processing');

    try {
      const response = await api.submitMockInterviewTurn(curSessionId, {
        session_id: curSessionId,
        transcript: '',
        stt_engine: 'faster-whisper',
        answer_duration_seconds: 5,
      });

      if (response.interview_complete) {
        if (response.message && !isMuted) {
          speakInterviewer(response.message, () => {
            startEvaluationPoll();
          });
        } else {
          startEvaluationPoll();
        }
      } else {
        setCurrentQuestion(response.next_question || null);
        setQuestionsAsked(response.questions_asked);
        setCandidateTranscript('');
        setRecordingSeconds(0);
        if (response.next_question?.interviewer_video_url) {
          setTurnState('interviewer_speaking');
        } else if (response.next_question?.tts_text) {
          speakInterviewer(response.next_question.tts_text, () => {
            startAutoListening();
          });
        } else {
          startAutoListening();
        }
      }
    } catch (err: any) {
      alert(err.message || 'Error skipping question.');
    } finally {
      setSubmittingTurn(false);
      submittingTurnRef.current = false;
    }
  };

  // --------------------------------------------------------------------------
  // Resume Analysis
  // --------------------------------------------------------------------------
  const handleAnalyzeResume = async () => {
    setAnalyzingResume(true);
    try {
      const res = await api.detectMockInterviewDomain();
      setResumeSuggestion(res);
      if (res.suggested_domain_id) {
        setDomainId(res.suggested_domain_id);
      }
      if (res.suggested_difficulty) {
        setDifficulty(res.suggested_difficulty);
      }
    } catch {
      // Fallback
    } finally {
      setAnalyzingResume(false);
    }
  };

  // --------------------------------------------------------------------------
  // Session Creation & Progression
  // --------------------------------------------------------------------------
  const handleProceedToPermission = async () => {
    setCreatingSession(true);
    setSetupError(null);
    try {
      const res = await api.createMockInterviewSession({
        domain_id: domainId,
        role: role.trim() || undefined,
        difficulty,
        duration_minutes: durationMinutes,
      });
      setSetupInfo(res);
      setSessionId(res.session_id);
      sessionIdRef.current = res.session_id;
      setRemainingSeconds(durationMinutes * 60);
      setPhase('permission');
    } catch (err: any) {
      console.error('Failed to create mock interview session:', err);
      setSetupError(err.message || 'Failed to initialize session.');
    } finally {
      setCreatingSession(false);
    }
  };

  // --------------------------------------------------------------------------
  // Mic Testing in Pre-Interview Screen
  // --------------------------------------------------------------------------
  const handleTestMic = async () => {
    setMicTesting(true);
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      setMicReady(true);

      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyserRef.current = analyser;
      analyser.fftSize = 256;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const checkVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        setMicAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
        requestAnimationFrame(checkVolume);
      };
      checkVolume();
    } catch {
      setMicError(tr.permission.micError);
      setMicReady(false);
    } finally {
      setMicTesting(false);
    }
  };

  // --------------------------------------------------------------------------
  // Start Interview: Begins with Natural Introduction and Automatic Turn Taking
  // --------------------------------------------------------------------------
  const handleStartInterview = async () => {
    if (!sessionId) return;
    setStartingInterview(true);
    setStartError(null);
    try {
      const firstTurn = await api.startMockInterviewSession(sessionId);
      setCurrentQuestion(firstTurn.next_question || null);
      setQuestionsAsked(1);
      setCandidateTranscript('');
      setPhase('interview');

      // AI Speaks Natural Introduction & Opening Question
      if (firstTurn.next_question?.interviewer_video_url) {
        setTurnState('introducing');
      } else if (firstTurn.next_question?.tts_text) {
        speakInterviewer(firstTurn.next_question.tts_text, () => {
          // Automatic transition to listening mode when speech finishes
          startAutoListening();
        }, true);
      } else {
        startAutoListening();
      }
    } catch (err: any) {
      console.error('Failed to start mock interview session:', err);
      const msg = err.message || 'Failed to start interview session.';
      setStartError(msg);
    } finally {
      setStartingInterview(false);
    }
  };

  const handleNaturalConclusion = async () => {
    if (!sessionId) return;
    try {
      await api.endMockInterviewSession(sessionId, {
        session_id: sessionId,
        reason: 'time_expired',
      });
      startEvaluationPoll();
    } catch {
      startEvaluationPoll();
    }
  };

  const handleEndEarlyConfirm = async () => {
    if (!sessionId) return;
    setConfirmEndModal(false);
    try {
      await api.endMockInterviewSession(sessionId, {
        session_id: sessionId,
        reason: 'user_ended',
      });
      startEvaluationPoll();
    } catch (err: any) {
      alert(err.message || 'Failed to end session.');
    }
  };

  // --------------------------------------------------------------------------
  // Evaluating Screen & Background Polling
  // --------------------------------------------------------------------------
  const startEvaluationPoll = () => {
    setPhase('evaluating');
    setEvaluatingStage(1);
    let stage = 1;

    const stageInterval = window.setInterval(() => {
      stage = Math.min(4, stage + 1);
      setEvaluatingStage(stage);
    }, 4500);

    const pollInterval = window.setInterval(async () => {
      if (!sessionIdRef.current) return;
      try {
        const assessmentRes = await api.getMockInterviewAssessment(sessionIdRef.current);
        if (assessmentRes.evaluation_status === 'completed' || assessmentRes.evaluation_status === 'failed') {
          clearInterval(stageInterval);
          clearInterval(pollInterval);
          setAssessment(assessmentRes);
          setPhase('assessment');
        }
      } catch {
        // Keep polling
      }
    }, 3000);
  };

  // --------------------------------------------------------------------------
  // Re-practice Weak Areas
  // --------------------------------------------------------------------------
  const handleRepracticeWeakAreas = async () => {
    if (!sessionId) return;
    try {
      const res = await api.createMockInterviewRepractice(sessionId, {
        source_session_id: sessionId,
        duration_minutes: durationMinutes,
      });
      setSessionId(res.new_session_id);
      sessionIdRef.current = res.new_session_id;
      setRemainingSeconds(durationMinutes * 60);
      setPhase('permission');
    } catch (err: any) {
      alert(err.message || 'Failed to create re-practice session.');
    }
  };

  // --------------------------------------------------------------------------
  // History View
  // --------------------------------------------------------------------------
  const handleOpenHistory = async () => {
    setLoadingHistory(true);
    setPhase('history');
    try {
      const res = await api.listMockInterviewSessions();
      setHistorySessions(res.sessions);
    } catch {
      // ignore
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleViewHistoricalAssessment = async (pastSessionId: number) => {
    try {
      const res = await api.getMockInterviewAssessment(pastSessionId);
      setAssessment(res);
      setPhase('assessment');
    } catch (err: any) {
      alert(err.message || 'Could not load past assessment.');
    }
  };

  // --------------------------------------------------------------------------
  // Formatting Helpers
  // --------------------------------------------------------------------------
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // ==========================================================================
  // RENDER: SETUP SCREEN
  // ==========================================================================
  if (phase === 'setup') {
    return (
      <div className="mock-interview-wrapper">
        <div className="mock-card">
          <div className="mock-card-header">
            <div className="mock-header-titles">
              <h2 className="mock-title">
                <Sparkles size={22} color="#60a5fa" />
                {tr.setup.title}
              </h2>
              <p className="mock-subtitle">{tr.setup.subtitle}</p>
            </div>
            <button type="button" className="mock-btn-secondary" onClick={handleOpenHistory}>
              <History size={16} />
              {tr.setup.historyBtn}
            </button>
          </div>

          <div className="setup-grid">
            <div className="setup-section">
              {/* Domain / Track Selector */}
              <div className="setup-field">
                <label className="setup-field-label">
                  <BookOpen size={15} />
                  {tr.setup.domainLabel}
                </label>
                <div className="tracks-grid">
                  {DOMAIN_OPTIONS.map((track) => {
                    const IconComp = track.icon;
                    return (
                      <button
                        key={track.id}
                        type="button"
                        className={`track-card-btn ${domainId === track.id ? 'active' : ''}`}
                        onClick={() => setDomainId(track.id)}
                      >
                        <div className="track-icon-wrapper">
                          <IconComp size={18} />
                        </div>
                        <span className="track-name">{track.name}</span>
                        <span className="track-desc">{track.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Target Role (Optional) */}
              <div className="setup-field">
                <label className="setup-field-label">{tr.setup.roleLabel}</label>
                <input
                  type="text"
                  placeholder="e.g. Senior Data Engineer / Staff Security Architect"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="transcript-textarea"
                  style={{ minHeight: '44px', padding: '10px 14px' }}
                />
              </div>

              {/* Difficulty Level */}
              <div className="setup-field">
                <label className="setup-field-label">{tr.setup.difficultyLabel}</label>
                <div className="pill-options-group">
                  {DIFFICULTY_OPTIONS.map((diff) => (
                    <button
                      key={diff}
                      type="button"
                      className={`pill-option-btn ${difficulty === diff ? 'active' : ''}`}
                      onClick={() => setDifficulty(diff)}
                    >
                      {diff === 'Mixed' ? tr.setup.difficultyMixed : diff}
                    </button>
                  ))}
                </div>
              </div>

              {/* Duration */}
              <div className="setup-field">
                <label className="setup-field-label">
                  <Clock size={15} />
                  {tr.setup.durationLabel}
                </label>
                <div className="pill-options-group">
                  {DURATION_OPTIONS.map((mins) => (
                    <button
                      key={mins}
                      type="button"
                      className={`pill-option-btn ${durationMinutes === mins ? 'active' : ''}`}
                      onClick={() => setDurationMinutes(mins)}
                    >
                      {mins} {tr.setup.minutes}
                    </button>
                  ))}
                </div>
              </div>

              {/* Presentation Mode Selector */}
              <div className="setup-field">
                <label className="setup-field-label">
                  <User size={15} />
                  Interviewer Presentation Mode
                </label>
                <div className="pill-options-group">
                  <button
                    type="button"
                    className={`pill-option-btn ${presentationMode === 'auto' || presentationMode === 'video' ? 'active' : ''}`}
                    onClick={() => setPresentationMode('auto')}
                  >
                    <Video size={13} style={{ display: 'inline', marginRight: '6px' }} />
                    Alex Video (Realistic AI Interviewer)
                  </button>
                  <button
                    type="button"
                    className={`pill-option-btn ${presentationMode === 'visual' ? 'active' : ''}`}
                    onClick={() => setPresentationMode('visual')}
                  >
                    <User size={13} style={{ display: 'inline', marginRight: '6px' }} />
                    Visual Avatar
                  </button>
                  <button
                    type="button"
                    className={`pill-option-btn ${presentationMode === 'minimal' ? 'active' : ''}`}
                    onClick={() => setPresentationMode('minimal')}
                  >
                    <MessageSquare size={13} style={{ display: 'inline', marginRight: '6px' }} />
                    Minimal Wave
                  </button>
                </div>
              </div>
            </div>

            {/* AI Resume Analyzer Side Panel & STT Local Guarantee */}
            <div className="setup-section">
              <div className="resume-assist-panel">
                <div className="resume-assist-header">
                  <div className="setup-field-label">
                    <FileText size={16} color="#c084fc" />
                    <span>Smart Resume Match</span>
                  </div>
                  <span className="ai-badge">
                    <Sparkles size={11} />
                    {tr.setup.aiSuggestedBadge}
                  </span>
                </div>

                <p className="mock-subtitle" style={{ fontSize: '0.82rem' }}>
                  Analyze your stored profile resume to automatically identify the most aligned technical track and
                  difficulty level.
                </p>

                {resumeSuggestion && (
                  <div className="ai-suggestion-box">
                    <strong>Suggested: {resumeSuggestion.suggested_domain_title}</strong>
                    <div style={{ marginTop: '4px', fontSize: '0.8rem', color: '#94a3b8' }}>
                      {resumeSuggestion.reasoning}
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  className="resume-detect-btn"
                  onClick={handleAnalyzeResume}
                  disabled={analyzingResume}
                >
                  {analyzingResume ? (
                    <>
                      <Loader2 size={14} className="spin-icon" />
                      {tr.setup.analyzingResume}
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      {tr.setup.detectDomainBtn}
                    </>
                  )}
                </button>

                <p style={{ fontSize: '0.74rem', color: '#64748b', margin: 0 }}>
                  {tr.setup.aiSuggestedNote}
                </p>
              </div>

              {/* TTS Voice Quality & Persona Picker */}
              <div className="voice-picker-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="setup-field-label">
                    <Volume2 size={15} color="#60a5fa" />
                    <span>Interviewer Voice & Persona</span>
                  </div>
                  <button
                    type="button"
                    className="voice-preview-btn"
                    onClick={() => handlePreviewVoice(selectedNeuralVoice)}
                    disabled={isPlayingPreview}
                    title="Listen to a voice sample"
                  >
                    {isPlayingPreview ? (
                      <Loader2 size={13} className="spin-icon" />
                    ) : (
                      <Play size={13} />
                    )}
                    <span>{isPlayingPreview ? 'Playing...' : 'Preview Voice'}</span>
                  </button>
                </div>

                <select
                  className="voice-picker-select"
                  value={selectedVoiceMode === 'browser' ? `browser:${selectedVoiceName}` : selectedNeuralVoice}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val.startsWith('browser:')) {
                      setSelectedVoiceMode('browser');
                      setSelectedVoiceName(val.replace('browser:', ''));
                    } else {
                      setSelectedVoiceMode('neural');
                      setSelectedNeuralVoice(val);
                    }
                  }}
                >
                  <optgroup label="✨ Neural AI Voices (Studio Quality - Recommended)">
                    {(ttsStatus?.voices || [
                      { id: 'en-US-AndrewMultilingualNeural', name: 'Alex Mercer (Male - Natural & Conversational)' },
                      { id: 'en-US-AriaNeural', name: 'Elena Vance (Female - Crisp & Professional)' },
                      { id: 'en-US-GuyNeural', name: 'Marcus Stone (Male - Calm & Authoritative)' },
                      { id: 'en-US-JennyNeural', name: 'Sarah Chen (Female - Warm & Articulate)' },
                      { id: 'en-GB-RyanNeural', name: 'David Sterling (Male UK - Precise & Formal)' },
                      { id: 'en-GB-SoniaNeural', name: 'Victoria Croft (Female UK - Professional)' },
                    ]).map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </optgroup>
                  {availableVoices.length > 0 && (
                    <optgroup label="🌐 Browser-Native Voices (Fallback)">
                      {availableVoices
                        .filter((v) => v.lang.startsWith('en'))
                        .map((v) => (
                          <option key={`browser:${v.name}`} value={`browser:${v.name}`}>
                            {v.name} ({v.lang})
                          </option>
                        ))}
                    </optgroup>
                  )}
                </select>
                <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                  Conversational neural voices with professional pacing.
                </div>
              </div>

              {/* STT Status Indicator */}
              <div className="stt-status-banner">
                <ShieldCheck size={16} color={sttStatus?.available !== false ? '#34d399' : '#f59e0b'} />
                <div>
                  <div style={{ fontWeight: 600, color: sttStatus?.available !== false ? '#34d399' : '#fcd34d', fontSize: '0.82rem' }}>
                    {sttStatus?.available !== false ? 'Local Speech Recognition Ready' : 'Speech Recognition Notice'}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                    Engine: {sttStatus?.engine || 'faster-whisper'} ({sttStatus?.model_size || 'tiny'} CPU) • 100% Private & zero audio retained
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                {setupError && (
                  <div style={{ color: '#ef4444', marginBottom: '8px', fontSize: '0.8rem', textAlign: 'center' }}>
                    {setupError}
                  </div>
                )}
                <button
                  type="button"
                  id="mock-continue-btn"
                  className="mock-btn-primary"
                  style={{ width: '100%' }}
                  disabled={creatingSession}
                  onClick={handleProceedToPermission}
                >
                  {creatingSession ? (
                    <>
                      <Loader2 size={17} className="animate-spin" />
                      <span>{tr.setup.startBtn}...</span>
                    </>
                  ) : (
                    <>
                      <span>{tr.setup.startBtn}</span>
                      <ArrowRight size={17} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // RENDER: PERMISSION & PRE-INTERVIEW CHECK SCREEN
  // ==========================================================================
  if (phase === 'permission') {
    return (
      <div className="mock-interview-wrapper">
        <div className="mock-card">
          <div className="permission-content">
            <button
              type="button"
              className="mock-btn-secondary"
              style={{ alignSelf: 'flex-start' }}
              onClick={() => setPhase('setup')}
            >
              <ArrowLeft size={15} />
              {tr.permission.backBtn}
            </button>

            <div className="mock-header-titles" style={{ textAlign: 'center', alignItems: 'center' }}>
              <h2 className="mock-title">{tr.permission.title}</h2>
              <p className="mock-subtitle">
                {setupInfo?.domain_title} • {difficulty} • {durationMinutes} min • {presentationMode === 'visual' ? 'Visual Interviewer' : 'Voice+Text'}
              </p>
            </div>

            {/* Privacy Guarantee Box */}
            <div className="privacy-notice-box">
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} />
                {tr.permission.privacyHeader}
              </div>
              <div className="privacy-notice-item">
                <span>✓</span>
                <span>{tr.permission.sttLocal} (faster-whisper CPU)</span>
              </div>
              <div className="privacy-notice-item">
                <span>✓</span>
                <span>{tr.permission.audioDiscarded}</span>
              </div>
              <div className="privacy-notice-item">
                <span>✓</span>
                <span>Automatic turn-taking: Speaks questions, automatically listens, and detects silence when you finish answering.</span>
              </div>
              <div className="privacy-notice-item" style={{ color: '#93c5fd' }}>
                <span>ℹ</span>
                <span>{tr.permission.cameraNotice}</span>
              </div>
            </div>

            {/* Microphone Verification Panel */}
            <div className="mic-test-panel">
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e2e8f0' }}>
                {tr.permission.micRequired}
              </div>
              <p className="mock-subtitle" style={{ textAlign: 'center', fontSize: '0.82rem' }}>
                {tr.permission.micDesc}
              </p>

              <div className="mic-level-bar-wrapper">
                <div className="mic-level-bar" style={{ width: `${micAudioLevel}%` }} />
              </div>

              {micReady ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399', fontSize: '0.85rem', fontWeight: 600 }}>
                  <CheckCircle2 size={16} />
                  {tr.permission.micReady}
                </div>
              ) : (
                <button
                  type="button"
                  className="mock-btn-secondary"
                  onClick={handleTestMic}
                  disabled={micTesting}
                >
                  {micTesting ? <Loader2 size={15} className="spin-icon" /> : <Mic size={15} />}
                  {tr.permission.testMicBtn}
                </button>
              )}

              {micError && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171', fontSize: '0.8rem' }}>
                  <AlertCircle size={15} />
                  {micError}
                </div>
              )}
            </div>

            {startError && (
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.12)',
                  border: '1px solid rgba(239, 68, 68, 0.35)',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  color: '#fca5a5',
                  fontSize: '0.88rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginTop: '12px',
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0, color: '#f87171' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#f87171' }}>Failed to start interview session</div>
                  <div style={{ marginTop: '2px', fontSize: '0.82rem', wordBreak: 'break-word' }}>{startError}</div>
                </div>
              </div>
            )}

            {/* Begin Interview Button */}
            <button
              type="button"
              className="mock-btn-primary"
              style={{ width: '100%', marginTop: '12px' }}
              onClick={handleStartInterview}
              disabled={startingInterview}
            >
              {startingInterview ? (
                <>
                  <Loader2 size={18} className="spin-icon" />
                  <span>Starting Interview...</span>
                </>
              ) : (
                <>
                  <Play size={18} />
                  <span>{tr.permission.beginInterviewBtn}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // RENDER: LIVE INTERVIEW STAGE
  // ==========================================================================
  if (phase === 'interview') {
    const isWarningTime = remainingSeconds <= 300 && remainingSeconds > 60;
    const isDangerTime = remainingSeconds <= 60;

    return (
      <div className="mock-interview-wrapper">
        <div className="interview-stage-container">
          {/* Top Bar: Progress, Timer & Controls */}
          <div className="interview-top-bar">
            <div className="interview-meta-badges">
              <span className="question-category-tag">{setupInfo?.domain_title || domainId}</span>
              <span className="question-difficulty-tag">{difficulty}</span>
              <span className="question-difficulty-tag">
                {tr.interview.turnIndicator} {questionsAsked}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* Presentation Mode Toggle */}
              <button
                type="button"
                className="mock-btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                onClick={() => {
                  setPresentationMode((prev) =>
                    prev === 'auto' || prev === 'video' ? 'visual' : prev === 'visual' ? 'minimal' : 'auto'
                  );
                }}
                title="Cycle presentation mode: Video (Alex) / Avatar / Minimal"
              >
                {presentationMode === 'minimal' ? (
                  <MessageSquare size={14} />
                ) : presentationMode === 'visual' ? (
                  <User size={14} />
                ) : (
                  <Video size={14} />
                )}
                <span>
                  {presentationMode === 'minimal'
                    ? 'Minimal Orb'
                    : presentationMode === 'visual'
                    ? 'Avatar Mode'
                    : 'Alex (Video)'}
                </span>
              </button>

              {/* Timer Pill */}
              <div className={`timer-pill ${isDangerTime ? 'danger' : isWarningTime ? 'warning' : ''}`}>
                <Clock size={15} />
                <span>{formatTime(remainingSeconds)}</span>
              </div>

              {/* TTS Mute Toggle */}
              <button
                type="button"
                className="mock-btn-secondary"
                style={{ padding: '6px 10px' }}
                onClick={() => {
                  const newMuted = !isMuted;
                  setIsMuted(newMuted);
                  if (newMuted) {
                    if (activeAudioRef.current) {
                      activeAudioRef.current.pause();
                      activeAudioRef.current = null;
                    }
                    if (window.speechSynthesis) {
                      window.speechSynthesis.cancel();
                    }
                  }
                }}
                title={isMuted ? tr.interview.ttsUnmute : tr.interview.ttsMute}
              >
                {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>

              {/* End Interview Early */}
              <button
                type="button"
                className="mock-btn-secondary"
                style={{ color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                onClick={() => setConfirmEndModal(true)}
              >
                {tr.interview.endInterviewBtn}
              </button>
            </div>
          </div>

          {/* Central Interviewer Presentation: Alex Video / Visual Avatar / Minimal Orb */}
          <InterviewerPresentation
            mode={presentationMode}
            videoUrl={currentQuestion?.interviewer_video_url}
            posterUrl="/interviewer/alex/identity/reference.jpg"
            state={turnState}
            audioLevel={micAudioLevel}
            silenceSecondsRemaining={silenceSecondsRemaining}
            personaName={getPersonaName()}
            domainTitle={setupInfo?.domain_title || 'Lead Technical Interviewer'}
            isMuted={isMuted}
            onSpeakingFinished={() => {
              setTurnState('transition_to_listen');
              setTimeout(() => {
                startAutoListening();
              }, 350);
            }}
            onFallbackTriggered={(reason) => {
              console.warn('[MockInterviewView] Video fallback triggered:', reason);
              if (currentQuestion?.tts_text && (turnState === 'interviewer_speaking' || turnState === 'introducing')) {
                speakInterviewer(
                  currentQuestion.tts_text,
                  () => {
                    startAutoListening();
                  },
                  turnState === 'introducing'
                );
              }
            }}
            onReadyToAnswer={() => {
              if (activeAudioRef.current) {
                activeAudioRef.current.pause();
                activeAudioRef.current = null;
              }
              if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
              }
              setTurnState('transition_to_listen');
              setTimeout(() => {
                startAutoListening();
              }, 200);
            }}
          />

          {/* Current Spoken Question Box */}
          {currentQuestion && (
            <div className="interview-question-box">
              <div className="question-tags-row">
                <span className="question-category-tag">{currentQuestion.category}</span>
                <span className="question-difficulty-tag">{currentQuestion.topic}</span>
                {currentQuestion.question_type && currentQuestion.question_type !== 'technical' && (
                  <span className={`question-type-badge ${currentQuestion.question_type === 'behavioral' ? 'behavioral' : 'introductory'}`}>
                    {currentQuestion.question_type === 'introductory' ? 'Introduction' : 'Behavioral & STAR'}
                  </span>
                )}
                {currentQuestion.is_follow_up && (
                  <span className="followup-indicator-tag">
                    <Sparkles size={11} style={{ display: 'inline', marginRight: '4px' }} />
                    {tr.interview.followUpBadge}
                  </span>
                )}
              </div>

              <h3 className="interview-question-title">{currentQuestion.question_title}</h3>

              {currentQuestion.is_follow_up && currentQuestion.follow_up_focus && (
                <div className="followup-focus-note">
                  <strong>Follow-up Focus: </strong>
                  {currentQuestion.follow_up_focus}
                </div>
              )}
            </div>
          )}

          {/* Automatic Turn Taking Controls & Candidate Answer Section */}
          <div className="candidate-answer-section">
            <div className="turn-taking-status-bar">
              <div className="turn-status-left">
                {isRecording ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div className="mic-active-indicator">
                      <span className="recording-dot" />
                      <span>Microphone Active (Automatic Listening)</span>
                      <span className="recording-timer">{formatTime(recordingSeconds)}</span>
                    </div>
                    <div className="soft-guidance-pill">
                      <Clock size={12} />
                      <span>
                        Suggested: ~{currentQuestion?.expected_duration_seconds || 60}s (
                        {currentQuestion?.question_type === 'behavioral'
                          ? 'Behavioral / STAR'
                          : currentQuestion?.question_type === 'introductory'
                          ? 'Introductory'
                          : 'Technical'}
                        )
                      </span>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <div className="mic-inactive-indicator">
                      <Volume2 size={15} color="#818cf8" />
                      <span>{turnState === 'introducing' ? 'Interviewer Introduction' : 'Interviewer Speaking'}</span>
                    </div>
                    <button
                      type="button"
                      className="interrupt-btn"
                      onClick={handleInterruptInterviewer}
                      title="Skip interviewer speech and begin answering immediately"
                    >
                      <Mic size={13} />
                      <span>I'm Ready to Answer (Skip to Mic)</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Silence Detection Countdown & Config */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                {turnState === 'detecting_silence' && (
                  <div className="silence-countdown-pill">
                    <Clock size={13} />
                    <span>Wrapping up answer in {silenceSecondsRemaining.toFixed(1)}s (or keep speaking)</span>
                  </div>
                )}
                <div className="silence-config-inline">
                  <span className="silence-label">Silence Delay:</span>
                  {[2.2, 2.8, 3.5].map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      className={`silence-pill ${silenceThresholdSec === sec ? 'active' : ''}`}
                      onClick={() => setSilenceThresholdSec(sec)}
                      title={`Auto-wrap after ${sec} seconds of sustained silence`}
                    >
                      {sec}s
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Transcript Preview & Edit */}
            <div className="transcript-display-box">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="setup-field-label">{tr.interview.liveTranscript}</label>
                <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                  Processed locally via faster-whisper
                </span>
              </div>
              <textarea
                className="transcript-textarea"
                value={candidateTranscript}
                onChange={(e) => setCandidateTranscript(e.target.value)}
                placeholder="Speak naturally. When you finish speaking, the system will detect silence and automatically advance. You can also edit your answer here or click 'Finish Answer' below."
                disabled={submittingTurn}
              />
            </div>

            {/* Action Buttons: Manual Finish Answer Override & Skip */}
            <div className="interview-actions-footer">
              <button
                type="button"
                className="mock-btn-secondary"
                onClick={handleSkipQuestion}
                disabled={submittingTurn}
              >
                <FastForward size={15} />
                <span>{tr.interview.skipBtn}</span>
              </button>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  className="mock-btn-primary finish-answer-btn"
                  onClick={handleAutoFinalizeAnswer}
                  disabled={submittingTurn}
                >
                  {submittingTurn ? (
                    <>
                      <Loader2 size={16} className="spin-icon" />
                      <span>Processing Answer...</span>
                    </>
                  ) : (
                    <>
                      <Check size={17} />
                      <span>Finish Answer</span>
                      <ArrowRight size={17} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Early End Confirmation Modal */}
        {confirmEndModal && (
          <div className="mock-modal-backdrop">
            <div className="mock-modal-card">
              <h3 style={{ margin: 0, color: '#ffffff' }}>{tr.interview.confirmEndTitle}</h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
                {tr.interview.confirmEndDesc}
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="mock-btn-secondary"
                  onClick={() => setConfirmEndModal(false)}
                >
                  {tr.interview.confirmEndCancel}
                </button>
                <button
                  type="button"
                  className="mock-btn-primary"
                  style={{ background: '#ef4444', borderColor: '#f87171' }}
                  onClick={handleEndEarlyConfirm}
                >
                  {tr.interview.confirmEndYes}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ==========================================================================
  // RENDER: EVALUATING SCREEN
  // ==========================================================================
  if (phase === 'evaluating') {
    return (
      <div className="mock-interview-wrapper">
        <div className="mock-card evaluating-card">
          <div className="evaluating-spinner-wrapper">
            <Cpu size={48} color="#60a5fa" />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <h2 className="mock-title" style={{ justifyContent: 'center' }}>
              {tr.evaluating.title}
            </h2>
            <p className="mock-subtitle">{tr.evaluating.subtitle}</p>
          </div>

          <div className="evaluating-progress-list">
            <div className={`evaluating-stage-item ${evaluatingStage > 1 ? 'completed' : evaluatingStage === 1 ? 'active' : ''}`}>
              {evaluatingStage > 1 ? <CheckCircle2 size={16} color="#34d399" /> : <Loader2 size={16} className="spin-icon" />}
              <span>{tr.evaluating.stage1}</span>
            </div>

            <div className={`evaluating-stage-item ${evaluatingStage > 2 ? 'completed' : evaluatingStage === 2 ? 'active' : ''}`}>
              {evaluatingStage > 2 ? <CheckCircle2 size={16} color="#34d399" /> : evaluatingStage === 2 ? <Loader2 size={16} className="spin-icon" /> : <Clock size={16} />}
              <span>Technical Concept & Semantic Analysis</span>
            </div>

            <div className={`evaluating-stage-item ${evaluatingStage > 3 ? 'completed' : evaluatingStage === 3 ? 'active' : ''}`}>
              {evaluatingStage > 3 ? <CheckCircle2 size={16} color="#34d399" /> : evaluatingStage === 3 ? <Loader2 size={16} className="spin-icon" /> : <Clock size={16} />}
              <span>Behavioral & STAR Communication Framework Scoring</span>
            </div>

            <div className={`evaluating-stage-item ${evaluatingStage >= 4 ? 'active' : ''}`}>
              {evaluatingStage >= 4 ? <Loader2 size={16} className="spin-icon" /> : <Clock size={16} />}
              <span>Synthesizing Practice Assessment Report</span>
            </div>
          </div>

          <p style={{ fontSize: '0.78rem', color: '#64748b', margin: 0 }}>
            {tr.evaluating.waitNotice}
          </p>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // RENDER: ASSESSMENT SCREEN (POLISHED REPORT WITH BEHAVIORAL + TECHNICAL)
  // ==========================================================================
  if (phase === 'assessment' && assessment) {
    const overallScoreVal = Math.round(assessment.overall_score || 0);
    const techScoreVal = Math.round(assessment.technical_score ?? assessment.overall_score ?? 0);
    const behScoreVal = Math.round(assessment.behavioral_score ?? assessment.overall_score ?? 0);

    const getScoreClass = (v: number) => (v >= 75 ? 'high' : v >= 50 ? 'mid' : 'low');

    return (
      <div className="mock-interview-wrapper">
        <div className="mock-card assessment-layout">
          {/* Top Banner Disclaimer */}
          <div className="disclaimer-banner">
            <ShieldCheck size={16} />
            <span>
              AI-generated practice assessment. Evaluated using local AI against the configured interview rubric. This does not predict real-world hiring decisions.
            </span>
          </div>

          {/* Header & Actions */}
          <div className="mock-card-header">
            <div className="mock-header-titles">
              <h2 className="mock-title">
                <Award size={24} color="#60a5fa" />
                {tr.assessment.title}
              </h2>
              <p className="mock-subtitle">
                Generated via {assessment.ai_model_used || 'Local AI'} • Evaluated across technical & behavioral criteria
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="mock-btn-primary"
                onClick={handleRepracticeWeakAreas}
              >
                <RotateCcw size={16} />
                <span>{tr.assessment.repracticeBtn}</span>
              </button>

              <button
                type="button"
                className="mock-btn-secondary"
                onClick={() => setPhase('setup')}
              >
                <span>{tr.assessment.newInterviewBtn}</span>
              </button>

              {onNavigateBack && (
                <button
                  type="button"
                  className="mock-btn-secondary"
                  onClick={onNavigateBack}
                >
                  {tr.assessment.backToPrepBtn}
                </button>
              )}
            </div>
          </div>

          {/* 3-Pillar Score Cards: Overall, Technical, Behavioral */}
          <div className="assessment-pillars-grid">
            {/* Overall Score */}
            <div className="pillar-score-card overall">
              <div className="pillar-header">
                <Award size={18} color="#60a5fa" />
                <span>Overall Practice Assessment</span>
              </div>
              <div className={`score-number ${getScoreClass(overallScoreVal)}`}>
                {overallScoreVal}%
              </div>
              <span className="pillar-subtext">Calibrated combined score</span>
            </div>

            {/* Technical Score */}
            <div className="pillar-score-card">
              <div className="pillar-header">
                <Cpu size={18} color="#34d399" />
                <span>Technical Knowledge</span>
              </div>
              <div className={`score-number ${getScoreClass(techScoreVal)}`}>
                {techScoreVal}%
              </div>
              <span className="pillar-subtext">Concepts, depth & accuracy</span>
            </div>

            {/* Behavioral Score */}
            <div className="pillar-score-card">
              <div className="pillar-header">
                <MessageSquare size={18} color="#c084fc" />
                <span>Behavioral & Communication</span>
              </div>
              <div className={`score-number ${getScoreClass(behScoreVal)}`}>
                {behScoreVal}%
              </div>
              <span className="pillar-subtext">STAR structure & clarity</span>
            </div>
          </div>

          {/* Narrative Summary Box */}
          <div className="summary-narrative-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#ffffff' }}>
                {tr.assessment.summaryTitle}
              </h4>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className="soft-guidance-pill" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  Questions Asked: {assessment.questions_asked ?? assessment.answer_details.length}
                </span>
                <span className="soft-guidance-pill" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  Questions Answered: {assessment.questions_answered ?? assessment.answer_details.filter(a => !!a.transcript).length}
                </span>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.55 }}>
              {assessment.summary_text}
            </p>
          </div>

          {/* Strengths & Weak Areas Grid */}
          <div className="strengths-weakness-grid">
            {/* Strengths */}
            <div className="strengths-box">
              <h3 style={{ fontSize: '1.02rem', color: '#34d399', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} />
                Key Demonstrated Strengths
              </h3>
              {assessment.strengths && assessment.strengths.length > 0 ? (
                <div className="pill-options-group">
                  {assessment.strengths.map((str, idx) => (
                    <span key={idx} className="rating-badge strong" style={{ fontSize: '0.82rem', padding: '6px 12px' }}>
                      ✓ {str}
                    </span>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: 0 }}>
                  Solid engagement across the interview turns.
                </p>
              )}
            </div>

            {/* Weak Areas */}
            <div className="weak-areas-box">
              <h3 style={{ fontSize: '1.02rem', color: '#f87171', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={18} />
                Identified Areas to Strengthen
              </h3>
              {assessment.weak_areas && assessment.weak_areas.length > 0 ? (
                <div className="pill-options-group">
                  {assessment.weak_areas.map((area) => (
                    <span key={area} className="rating-badge weak" style={{ fontSize: '0.82rem', padding: '6px 12px' }}>
                      ⚠ {area}
                    </span>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: 0 }}>
                  No significant gaps detected for the configured difficulty level.
                </p>
              )}
            </div>
          </div>

          {/* Unassessed Topics in this Session (Section 7 & 22) */}
          {assessment.unassessed_domains && assessment.unassessed_domains.length > 0 && (
            <div className="unassessed-topics-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={16} color="#94a3b8" />
                <h4 style={{ margin: 0, fontSize: '0.96rem', color: '#cbd5e1' }}>
                  Topics Not Assessed in this Session
                </h4>
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.45 }}>
                {assessment.unassessed_disclaimer ||
                  'These topics were not assessed during this interview, so no conclusion about proficiency can be drawn from this session.'}
              </p>
              <div className="pill-options-group" style={{ marginTop: '4px' }}>
                {assessment.unassessed_domains.map((dom) => (
                  <span key={dom} className="rating-badge not-assessed" style={{ fontSize: '0.8rem', padding: '5px 11px' }}>
                    ○ {dom}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Skill Matrix Table */}
          <div>
            <h3 style={{ fontSize: '1.05rem', color: '#ffffff', marginBottom: '8px' }}>
              {tr.assessment.skillMatrixTitle}
            </h3>
            <table className="skill-matrix-table">
              <thead>
                <tr>
                  <th>Topic / Subdomain</th>
                  <th>Rating</th>
                  <th>Score</th>
                  <th>Basis</th>
                </tr>
              </thead>
              <tbody>
                {assessment.skill_matrix.map((row) => {
                  const ratingLower = (row.rating || '').toLowerCase().replace(/\s+/g, '-');
                  return (
                    <tr key={row.category_name}>
                      <td style={{ fontWeight: 600, color: '#f1f5f9' }}>{row.category_name}</td>
                      <td>
                        <span className={`rating-badge ${ratingLower}`}>
                          {row.rating}
                        </span>
                      </td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                        {row.score !== null && row.score !== undefined ? `${Math.round(row.score * 100)}%` : '—'}
                      </td>
                      <td style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{row.basis}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Targeted Study Recommendations */}
          {assessment.recommendations && assessment.recommendations.length > 0 && (
            <div>
              <h3 style={{ fontSize: '1.05rem', color: '#ffffff', marginBottom: '12px' }}>
                {tr.assessment.recommendationsTitle}
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {assessment.recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '10px',
                      padding: '14px',
                    }}
                  >
                    <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: '#60a5fa', fontWeight: 700, marginBottom: '4px' }}>
                      {rec.priority} Priority • {rec.area}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: 1.45 }}>
                      {rec.action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Question-by-Question Review with Behavioral STAR Breakdown */}
          <div>
            <h3 style={{ fontSize: '1.05rem', color: '#ffffff', marginBottom: '12px' }}>
              {tr.assessment.questionReviewTitle}
            </h3>
            <div className="review-questions-list">
              {assessment.answer_details.map((q) => {
                const isExpanded = expandedTurnId === q.turn_id;
                const isBehavioral = q.question_type === 'behavioral' || q.question_type === 'introductory';

                return (
                  <div key={q.turn_id} className="review-question-card">
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        cursor: 'pointer',
                      }}
                      onClick={() => setExpandedTurnId(isExpanded ? null : q.turn_id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <span className={`question-type-badge ${isBehavioral ? 'behavioral' : 'technical'}`}>
                          {isBehavioral ? 'Behavioral & STAR' : 'Technical'}
                        </span>
                        <span className="question-category-tag">{q.category}</span>
                        {q.is_follow_up && <span className="followup-indicator-tag">Follow-up</span>}
                        <span style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.95rem' }}>
                          {q.question_title}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {q.correctness !== null && q.correctness !== undefined && (
                          <span style={{ fontWeight: 700, color: q.correctness >= 0.7 ? '#34d399' : '#fbbf24', fontSize: '0.85rem' }}>
                            {Math.round(q.correctness * 100)}%
                          </span>
                        )}
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </div>
                    </div>

                    {isExpanded && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                        {/* Scores row */}
                        <div className="review-dimensions-grid">
                          <div className="dimension-mini-box">
                            <span className="dim-name">{tr.assessment.correctness}</span>
                            <span className="dim-val">{q.correctness !== null ? `${Math.round((q.correctness || 0) * 100)}%` : 'N/A'}</span>
                          </div>
                          <div className="dimension-mini-box">
                            <span className="dim-name">{tr.assessment.completeness}</span>
                            <span className="dim-val">{q.completeness !== null ? `${Math.round((q.completeness || 0) * 100)}%` : 'N/A'}</span>
                          </div>
                          <div className="dimension-mini-box">
                            <span className="dim-name">{tr.assessment.technicalDepth}</span>
                            <span className="dim-val">{q.technical_depth !== null && q.technical_depth !== undefined ? `${Math.round(q.technical_depth * 100)}%` : 'N/A'}</span>
                          </div>
                          <div className="dimension-mini-box">
                            <span className="dim-name">{tr.assessment.clarity}</span>
                            <span className="dim-val">{q.clarity !== null ? `${Math.round((q.clarity || 0) * 100)}%` : 'N/A'}</span>
                          </div>
                        </div>

                        {/* STAR Framework Coverage Bars for Behavioral Questions */}
                        {isBehavioral && q.star_breakdown && (
                          <div className="star-breakdown-card">
                            <div className="star-breakdown-title">
                              <Sparkles size={14} color="#c084fc" />
                              <span>STAR Framework Coverage Analysis</span>
                            </div>
                            <div className="star-bars-grid">
                              <div className="star-bar-item">
                                <span className="star-part-label">Situation</span>
                                <div className="star-bar-track">
                                  <div className="star-bar-fill situation" style={{ width: `${Math.round((q.star_breakdown.situation || 0) * 100)}%` }} />
                                </div>
                                <span className="star-part-pct">{Math.round((q.star_breakdown.situation || 0) * 100)}%</span>
                              </div>
                              <div className="star-bar-item">
                                <span className="star-part-label">Task</span>
                                <div className="star-bar-track">
                                  <div className="star-bar-fill task" style={{ width: `${Math.round((q.star_breakdown.task || 0) * 100)}%` }} />
                                </div>
                                <span className="star-part-pct">{Math.round((q.star_breakdown.task || 0) * 100)}%</span>
                              </div>
                              <div className="star-bar-item">
                                <span className="star-part-label">Action</span>
                                <div className="star-bar-track">
                                  <div className="star-bar-fill action" style={{ width: `${Math.round((q.star_breakdown.action || 0) * 100)}%` }} />
                                </div>
                                <span className="star-part-pct">{Math.round((q.star_breakdown.action || 0) * 100)}%</span>
                              </div>
                              <div className="star-bar-item">
                                <span className="star-part-label">Result</span>
                                <div className="star-bar-track">
                                  <div className="star-bar-fill result" style={{ width: `${Math.round((q.star_breakdown.result || 0) * 100)}%` }} />
                                </div>
                                <span className="star-part-pct">{Math.round((q.star_breakdown.result || 0) * 100)}%</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Candidate Answer Transcript */}
                        <div>
                          <div className="setup-field-label" style={{ marginBottom: '4px' }}>{tr.assessment.yourAnswer}:</div>
                          <div style={{ padding: '10px 14px', borderRadius: '8px', background: 'rgba(0, 0, 0, 0.25)', fontSize: '0.85rem', color: '#e2e8f0', fontStyle: (q.canonical_transcript || q.transcript) ? 'normal' : 'italic' }}>
                            {q.canonical_transcript || q.transcript || 'No answer provided (question skipped).'}
                          </div>
                          {q.canonical_transcript && q.raw_transcript && q.canonical_transcript !== q.raw_transcript && (
                            <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#94a3b8' }}>
                              <span style={{ color: '#818cf8', fontWeight: 600 }}>Acoustic Normalization: </span>
                              Evaluated contextually for speech recognition clarity (original ASR: <em>"{q.raw_transcript}"</em>)
                            </div>
                          )}
                        </div>

                        {/* Positive points */}
                        {q.positive_points && q.positive_points.length > 0 && (
                          <div>
                            <div className="setup-field-label" style={{ color: '#34d399', marginBottom: '4px' }}>
                              ✓ {isBehavioral ? 'Demonstrated Strengths' : tr.assessment.positivePoints}
                            </div>
                            <ul className="points-list">
                              {q.positive_points.map((pt, i) => (
                                <li key={i}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Missing Concepts or Structural Gaps */}
                        {q.missing_concepts && q.missing_concepts.length > 0 && (
                          <div>
                            <div className="setup-field-label" style={{ color: '#f59e0b', marginBottom: '4px' }}>
                              ! {isBehavioral ? 'Observable Gaps (e.g. Missing Result Metrics or Personal Ownership)' : tr.assessment.missingConcepts}
                            </div>
                            <ul className="points-list">
                              {q.missing_concepts.map((pt, i) => (
                                <li key={i} style={{ color: '#fde68a' }}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Incorrect claims */}
                        {q.incorrect_claims && q.incorrect_claims.length > 0 && (
                          <div>
                            <div className="setup-field-label" style={{ color: '#f87171', marginBottom: '4px' }}>
                              ✗ {tr.assessment.incorrectClaims}
                            </div>
                            <ul className="points-list">
                              {q.incorrect_claims.map((pt, i) => (
                                <li key={i} style={{ color: '#fca5a5' }}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Better Answer Guidance */}
                        {q.better_answer_notes && (
                          <div className="better-answer-box">
                            <strong>{isBehavioral ? 'Stronger STAR Framing Guidance' : tr.assessment.betterAnswer}: </strong>
                            {q.better_answer_notes}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // RENDER: HISTORY SCREEN
  // ==========================================================================
  return (
    <div className="mock-interview-wrapper">
      <div className="mock-card">
        <div className="mock-card-header">
          <div className="mock-header-titles">
            <h2 className="mock-title">
              <History size={22} color="#60a5fa" />
              {tr.history.title}
            </h2>
          </div>
          <button
            type="button"
            className="mock-btn-secondary"
            onClick={() => setPhase('setup')}
          >
            <ArrowLeft size={15} />
            {tr.history.backBtn}
          </button>
        </div>

        {loadingHistory ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Loader2 size={24} className="spin-icon" />
          </div>
        ) : historySessions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
            <p>{tr.history.empty}</p>
            <button
              type="button"
              className="mock-btn-primary"
              style={{ marginTop: '14px' }}
              onClick={() => setPhase('setup')}
            >
              {tr.history.startFirstBtn}
            </button>
          </div>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>{tr.history.date}</th>
                <th>Track</th>
                <th>{tr.history.duration}</th>
                <th>{tr.history.questions}</th>
                <th>{tr.history.score}</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {historySessions.map((s) => (
                <tr key={s.session_id}>
                  <td>{new Date(s.created_at).toLocaleDateString()}</td>
                  <td style={{ fontWeight: 600, color: '#ffffff' }}>{s.domain_title}</td>
                  <td>{s.duration_minutes} min</td>
                  <td>{s.questions_asked}</td>
                  <td>
                    {s.overall_score !== null && s.overall_score !== undefined ? (
                      <span className={`rating-badge ${s.overall_score >= 75 ? 'strong' : s.overall_score >= 50 ? 'moderate' : 'weak'}`}>
                        {Math.round(s.overall_score)}%
                      </span>
                    ) : (
                      <span style={{ color: '#64748b' }}>Pending</span>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="mock-btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                      onClick={() => handleViewHistoricalAssessment(s.session_id)}
                    >
                      {tr.history.viewAssessment}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
