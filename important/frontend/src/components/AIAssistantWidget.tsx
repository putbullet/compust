import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import {
  Send,
  Sparkles,
  Bot,
  User,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import type { AIStatus } from '../api/client';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  provider?: string;
  timestamp: string;
}

const QUICK_PROMPTS = [
  'New jobs today?',
  'Jobs by country?',
  'Jobs by company?',
  'My applications?',
  'Recent scraping?',
  'Active companies?',
];

export const AIAssistantWidget: React.FC<{ onOpenSettings?: () => void }> = ({ onOpenSettings }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am your COMPUST local career assistant. Ask me anything about current jobs, companies, scraping runs, or your applications.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check runtime status periodically when open
    if (isOpen) {
      api.getAIStatus().then(setAiStatus).catch(() => setAiStatus(null));
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || input).trim();
    if (!textToSend || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput('');
    setLoading(true);

    try {
      const response = await api.sendAIChat(textToSend);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: response.answer,
        provider: response.provider,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: `Sorry, I encountered an error: ${err.message || 'Unable to process query'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const isConnected = aiStatus?.status === 'connected';

  return (
    <WidgetWrapper>
      {isOpen ? (
        <ChatCard>
          {/* Header */}
          <div className="chat-header">
            <div className="header-left">
              <Bot size={18} className="bot-icon" />
              <div>
                <div className="title-row">
                  <span className="bot-title">COMPUST AI</span>
                  <span
                    className={`status-pill ${isConnected ? 'online' : 'offline'}`}
                    onClick={onOpenSettings}
                    title="Click to view AI Settings"
                  >
                    <span className="dot" />
                    <span>{isConnected ? 'Ollama' : 'Deterministic'}</span>
                  </span>
                </div>
              </div>
            </div>
            <button className="minimize-btn" onClick={() => setIsOpen(false)} title="Minimize assistant">
              <ChevronDown size={18} />
            </button>
          </div>

          {/* Messages Area */}
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-bubble ${msg.sender}`}>
                <div className="avatar">
                  {msg.sender === 'user' ? <User size={13} /> : <Sparkles size={13} />}
                </div>
                <div className="content">
                  <p>{msg.text}</p>
                  <div className="msg-footer">
                    <span className="timestamp">{msg.timestamp}</span>
                    {msg.provider && <span className="provider-tag">({msg.provider})</span>}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="message-bubble assistant loading">
                <div className="avatar">
                  <RefreshCw size={13} className="spin" />
                </div>
                <div className="content">
                  <p>Consulting database...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Bar */}
          <div className="quick-prompts">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="prompt-chip"
                onClick={() => handleSendMessage(prompt)}
                disabled={loading}
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="chat-input-area">
            <input
              type="text"
              placeholder="Ask about jobs, companies, or applications..."
              aria-label="Ask COMPUST AI Assistant"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSendMessage();
              }}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={() => handleSendMessage()}
              disabled={loading || !input.trim()}
              title="Send message"
              aria-label="Send message"
            >
              <Send size={15} />
            </button>
          </div>
        </ChatCard>
      ) : (
        <FloatingTrigger onClick={() => setIsOpen(true)} title="Open COMPUST AI Assistant">
          <Sparkles size={20} />
          <span className="trigger-label">AI Assistant</span>
          <span className={`status-indicator ${isConnected ? 'online' : 'offline'}`} />
        </FloatingTrigger>
      )}
    </WidgetWrapper>
  );
};

const WidgetWrapper = styled.div`
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
`;

const FloatingTrigger = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: #0f172a;
  color: #f8fafc;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 30px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(59, 130, 246, 0.2);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-2px);
    border-color: #3b82f6;
    box-shadow: 0 14px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(59, 130, 246, 0.4);
  }

  .trigger-label {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.online {
      background: #10b981;
      box-shadow: 0 0 6px #10b981;
    }

    &.offline {
      background: #f59e0b;
    }
  }
`;

const ChatCard = styled.div`
  width: 360px;
  height: 480px;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: popIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;

      .bot-icon {
        color: #3b82f6;
      }

      .title-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .bot-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #f8fafc;
      }

      .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 10px;
        cursor: pointer;

        &.online {
          background: rgba(16, 185, 129, 0.15);
          color: #34d399;
          .dot {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #10b981;
          }
        }

        &.offline {
          background: rgba(245, 158, 11, 0.15);
          color: #fbbf24;
          .dot {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #f59e0b;
          }
        }
      }
    }

    .minimize-btn {
      background: none;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;

      &:hover {
        background: rgba(255, 255, 255, 0.06);
        color: #ffffff;
      }
    }
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;

    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
  }

  .message-bubble {
    display: flex;
    gap: 8px;
    max-width: 90%;

    &.assistant {
      align-self: flex-start;

      .avatar {
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
      }

      .content {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
      }
    }

    &.user {
      align-self: flex-end;
      flex-direction: row-reverse;

      .avatar {
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
      }

      .content {
        background: #2563eb;
        color: #ffffff;
      }
    }

    .avatar {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .content {
      padding: 8px 12px;
      border-radius: 12px;
      font-size: 0.82rem;
      line-height: 1.5;
      word-break: break-word;
      overflow-wrap: break-word;

      p {
        margin: 0;
        word-break: break-word;
        overflow-wrap: break-word;
      }

      .msg-footer {
        display: flex;
        gap: 6px;
        margin-top: 4px;
        font-size: 0.68rem;
        color: #94a3b8;
      }
    }

    &.loading .spin {
      animation: spin 1s linear infinite;
    }
  }

  .quick-prompts {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding: 6px 12px;
    background: rgba(0, 0, 0, 0.2);
    border-top: 1px solid rgba(255, 255, 255, 0.04);

    &::-webkit-scrollbar {
      display: none;
    }

    .prompt-chip {
      white-space: nowrap;
      padding: 3px 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      color: #94a3b8;
      font-size: 0.7rem;
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.3);
        color: #60a5fa;
      }
    }
  }

  .chat-input-area {
    display: flex;
    padding: 10px 12px;
    gap: 8px;
    background: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(255, 255, 255, 0.06);

    input {
      flex: 1;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 8px 12px;
      color: #f8fafc;
      font-size: 0.85rem;
      outline: none;

      &:focus,
      &:focus-visible {
        border-color: #3b82f6;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
      }

      &::placeholder {
        color: #94a3b8;
      }
    }

    .send-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    }
  }

  @keyframes popIn {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
`;
