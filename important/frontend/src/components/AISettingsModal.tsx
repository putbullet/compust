import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Bot,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Cpu,
  RefreshCw,
  ExternalLink,
  Save,
  Check,
} from 'lucide-react';
import { api } from '../api/client';
import type { AIStatus, AIProvider } from '../api/client';

interface AISettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsSaved?: () => void;
}

export const AISettingsModal: React.FC<AISettingsModalProps> = ({
  isOpen,
  onClose,
  onSettingsSaved,
}) => {
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const fetchAIInfo = async () => {
    try {
      setLoading(true);
      const [statusRes, provList] = await Promise.all([
        api.getAIStatus(),
        api.getAIProviders(),
      ]);
      setAIStatus(statusRes);
      setProviders(provList);
      if (statusRes.selected_model) {
        setSelectedModel(statusRes.selected_model);
      } else if (statusRes.models.length > 0) {
        setSelectedModel(statusRes.models[0].name);
      }
    } catch (err) {
      console.error('Failed to load AI runtime status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchAIInfo();
      setSavedSuccess(false);
    }
  }, [isOpen]);

  const handleSaveModel = async () => {
    if (!selectedModel) return;
    try {
      setSaving(true);
      const updated = await api.setAISettings(selectedModel);
      setAIStatus(updated);
      setSavedSuccess(true);
      if (onSettingsSaved) onSettingsSaved();
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save AI model settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <ModalOverlay onClick={onClose}>
      <ModalCard onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="title-area">
            <Bot size={22} className="header-icon" />
            <h3>Local AI & Provider Configuration</h3>
          </div>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        {loading ? (
          <LoadingArea>
            <RefreshCw size={24} className="spin" />
            <span>Detecting local AI runtime...</span>
          </LoadingArea>
        ) : (
          <div className="modal-body">
            {/* Section 1: AI Providers */}
            <div className="config-section">
              <div className="section-title">AI Providers</div>
              <div className="providers-grid">
                {providers.map((p) => {
                  const isOllama = p.id === 'ollama';
                  const isConnected = isOllama && aiStatus?.status === 'connected';

                  return (
                    <div
                      key={p.id}
                      className={`provider-card ${p.enabled ? 'enabled' : 'disabled'}`}
                    >
                      <div className="provider-top">
                        <div className="provider-name-row">
                          <Cpu size={16} />
                          <span className="provider-title">{p.name}</span>
                        </div>
                        <span
                          className={`provider-badge ${
                            isConnected
                              ? 'connected'
                              : isOllama
                              ? 'offline'
                              : 'coming-soon'
                          }`}
                        >
                          {isConnected
                            ? 'Connected'
                            : isOllama
                            ? 'Not Running'
                            : 'Coming soon'}
                        </span>
                      </div>
                      <div className="provider-desc">
                        {isOllama ? (
                          <span>
                            {isConnected
                              ? `Reachable at ${aiStatus?.url} (${aiStatus?.models.length} installed models)`
                              : `Configured at ${aiStatus?.url || 'http://127.0.0.1:11434'}`}
                          </span>
                        ) : (
                          <span>Cloud LLM provider (Disabled in local-first deployment)</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Section 2: Model Discovery & Selection */}
            <div className="config-section">
              <div className="section-title">Ollama Installed Models</div>
              {aiStatus?.status === 'connected' ? (
                aiStatus.models.length > 0 ? (
                  <div className="model-select-box">
                    <label>Active Model (Discovered dynamically)</label>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                    >
                      {aiStatus.models.map((m) => (
                        <option key={m.name} value={m.name}>
                          {m.name} {m.parameter_size ? `(${m.parameter_size})` : ''}
                        </option>
                      ))}
                    </select>

                    <div className="model-details">
                      {aiStatus.selected_model && (
                        <div className="status-row">
                          {aiStatus.selected_model_available ? (
                            <CheckCircle2 size={15} className="ok-icon" />
                          ) : (
                            <AlertCircle size={15} className="warn-icon" />
                          )}
                          <span>
                            Current model: <strong>{aiStatus.selected_model}</strong>{' '}
                            {aiStatus.selected_model_available
                              ? '(Verified available)'
                              : '(Not found in local Ollama)'}
                          </span>
                        </div>
                      )}
                    </div>

                    <button
                      className="save-btn"
                      onClick={handleSaveModel}
                      disabled={saving || !selectedModel}
                    >
                      {saving ? (
                        <>
                          <RefreshCw size={14} className="spin" />
                          <span>Saving...</span>
                        </>
                      ) : savedSuccess ? (
                        <>
                          <Check size={14} />
                          <span>Saved!</span>
                        </>
                      ) : (
                        <>
                          <Save size={14} />
                          <span>Save Active Model</span>
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <EmptyModelNotice>
                    <AlertCircle size={20} className="notice-icon" />
                    <div>
                      <strong>No local Ollama models were found.</strong>
                      <p>
                        Ollama is running, but no models have been pulled yet. Run in your terminal:
                      </p>
                      <code>ollama pull qwen3.5:0.8b</code>
                      <a
                        href="https://ollama.com/library"
                        target="_blank"
                        rel="noreferrer"
                        className="doc-link"
                      >
                        <span>Browse Ollama Model Library</span>
                        <ExternalLink size={12} />
                      </a>
                    </div>
                  </EmptyModelNotice>
                )
              ) : (
                <OfflineNotice>
                  <XCircle size={20} className="notice-icon" />
                  <div>
                    <strong>Ollama is not running.</strong>
                    <p>
                      COMPUST operates normally without AI. To enable local chat and resume
                      assistance, ensure Ollama is started on <code>http://127.0.0.1:11434</code>.
                    </p>
                    <button className="retry-btn" onClick={fetchAIInfo}>
                      <RefreshCw size={13} />
                      <span>Check again</span>
                    </button>
                  </div>
                </OfflineNotice>
              )}
            </div>
          </div>
        )}

        <div className="modal-actions">
          <button className="cancel-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </ModalCard>
    </ModalOverlay>
  );
};

const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
`;

const ModalCard = styled.div`
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  width: 100%;
  max-width: 580px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .title-area {
      display: flex;
      align-items: center;
      gap: 10px;

      .header-icon {
        color: #3b82f6;
      }

      h3 {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
      }
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 1.5rem;
      color: #64748b;
      cursor: pointer;

      &:hover {
        color: #ffffff;
      }
    }
  }

  .config-section {
    margin-bottom: 20px;
  }

  .section-title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    margin-bottom: 10px;
  }

  .providers-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .provider-card {
    padding: 12px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);

    &.disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .provider-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .provider-name-row {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #f1f5f9;
      font-weight: 600;
      font-size: 0.85rem;
    }

    .provider-desc {
      font-size: 0.72rem;
      color: #94a3b8;
      line-height: 1.3;
    }

    .provider-badge {
      font-size: 0.68rem;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 8px;

      &.connected {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }

      &.offline {
        background: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.3);
      }

      &.coming-soon {
        background: rgba(100, 116, 139, 0.15);
        color: #94a3b8;
      }
    }
  }

  .model-select-box {
    background: rgba(0, 0, 0, 0.25);
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 8px;
    }

    select {
      width: 100%;
      padding: 10px 12px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 10px;
      color: #f8fafc;
      font-size: 0.85rem;
      outline: none;
      margin-bottom: 12px;

      &:focus {
        border-color: #3b82f6;
      }
    }

    .model-details {
      margin-bottom: 14px;
    }

    .status-row {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      color: #cbd5e1;

      .ok-icon {
        color: #34d399;
      }

      .warn-icon {
        color: #f59e0b;
      }
    }

    .save-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;

    .cancel-btn {
      padding: 8px 16px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;
      border-radius: 8px;
      font-size: 0.82rem;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #ffffff;
      }
    }
  }
`;

const LoadingArea = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: #94a3b8;
  font-size: 0.85rem;

  .spin {
    animation: spin 1.2s linear infinite;
  }
`;

const EmptyModelNotice = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 12px;
  color: #fde68a;
  font-size: 0.82rem;

  .notice-icon {
    color: #f59e0b;
    flex-shrink: 0;
  }

  p {
    margin: 4px 0 6px;
    color: #fde68a;
  }

  code {
    display: block;
    padding: 6px 10px;
    background: rgba(0, 0, 0, 0.4);
    border-radius: 6px;
    font-family: monospace;
    font-size: 0.8rem;
    color: #93c5fd;
    margin-bottom: 8px;
  }

  .doc-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #60a5fa;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
`;

const OfflineNotice = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: rgba(244, 63, 94, 0.08);
  border: 1px solid rgba(244, 63, 94, 0.25);
  border-radius: 12px;
  color: #fda4af;
  font-size: 0.82rem;

  .notice-icon {
    color: #f43f5e;
    flex-shrink: 0;
  }

  p {
    margin: 4px 0 10px;
    color: #cbd5e1;
  }

  code {
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 6px;
    border-radius: 4px;
    color: #93c5fd;
  }

  .retry-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #ffffff;
    border-radius: 6px;
    font-size: 0.75rem;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.15);
    }
  }
`;
