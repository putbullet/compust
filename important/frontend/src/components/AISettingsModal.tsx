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
  Eye,
  EyeOff,
  ShieldCheck,
  Cloud,
  Key,
  Trash2,
  Zap,
  AlertTriangle,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import { api } from '../api/client';
import type { AIStatus, AIProvider } from '../api/client';

interface AISettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsSaved?: () => void;
}

const GEMINI_MODELS = [
  { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash', desc: 'Recommended Default · Fast & highly capable' },
  { id: 'gemini-flash-latest', name: 'Gemini Flash Latest', desc: 'Balanced reasoning & multimodal support' },
  { id: 'gemini-flash-lite-latest', name: 'Gemini Flash Lite Latest', desc: 'Ultra-low latency & high throughput' },
  { id: 'gemini-pro-latest', name: 'Gemini Pro Latest', desc: 'Maximum capability & complex generation' },
];

export const AISettingsModal: React.FC<AISettingsModalProps> = ({
  isOpen,
  onClose,
  onSettingsSaved,
}) => {
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeProvider, setActiveProvider] = useState<'ollama' | 'gemini'>('ollama');

  // Gemini 4-step wizard state: 1: Consent, 2: Key & Model, 3: Test, 4: Apply
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1);

  // Ollama state
  const [selectedOllamaModel, setSelectedOllamaModel] = useState<string>('qwen3.5:0.8b');

  // Gemini state
  const [selectedGeminiModel, setSelectedGeminiModel] = useState<string>('gemini-3.8-flash');
  const [geminiKeyInput, setGeminiKeyInput] = useState<string>('');
  const [showGeminiKey, setShowGeminiKey] = useState<boolean>(false);
  const [savingKey, setSavingKey] = useState<boolean>(false);
  const [keySavedMessage, setKeySavedMessage] = useState<string | null>(null);
  const [fallbackPolicy, setFallbackPolicy] = useState<string>('deterministic');

  // Consent & testing
  const [testingConnection, setTestingConnection] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    provider: string;
    model?: string;
    message: string;
    latency_ms?: number;
  } | null>(null);

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

      const prov = (statusRes.active_provider as 'ollama' | 'gemini') || 'ollama';
      setActiveProvider(prov);

      if (prov === 'ollama') {
        if (statusRes.selected_model) {
          setSelectedOllamaModel(statusRes.selected_model);
        } else if (statusRes.models && statusRes.models.length > 0) {
          setSelectedOllamaModel(statusRes.models[0].name);
        }
      } else {
        if (statusRes.selected_model) {
          setSelectedGeminiModel(statusRes.selected_model);
        }
      }

      if (statusRes.consent_granted) {
        if (statusRes.gemini_key_configured) {
          setWizardStep(4);
        } else {
          setWizardStep(2);
        }
      } else {
        setWizardStep(1);
      }

      if (statusRes.fallback_policy) {
        setFallbackPolicy(statusRes.fallback_policy);
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
      setTestResult(null);
      setKeySavedMessage(null);
      setGeminiKeyInput('');
    }
  }, [isOpen]);

  const handleSelectProvider = (provId: 'ollama' | 'gemini') => {
    setActiveProvider(provId);
    setTestResult(null);
    if (provId === 'gemini') {
      if (!aiStatus?.consent_granted) {
        setWizardStep(1);
      } else if (!aiStatus?.gemini_key_configured) {
        setWizardStep(2);
      }
    }
  };

  const handleGrantConsent = async () => {
    try {
      setSaving(true);
      await api.setAISettings({
        consent_granted: true,
      });
      if (aiStatus) {
        setAIStatus({ ...aiStatus, consent_granted: true });
      }
      setWizardStep(2);
    } catch (err) {
      console.error('Failed to record Gemini consent:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!geminiKeyInput.trim()) return;
    try {
      setSavingKey(true);
      const res = await api.saveGeminiKey(geminiKeyInput.trim());
      setKeySavedMessage(`API key encrypted and saved locally (${res.masked}).`);
      setGeminiKeyInput('');
      await fetchAIInfo();
      setTimeout(() => setKeySavedMessage(null), 4000);
    } catch (err) {
      console.error('Failed to save Gemini API key:', err);
      setKeySavedMessage('Failed to save API key. Please check your credentials.');
    } finally {
      setSavingKey(false);
    }
  };

  const handleRemoveGeminiKey = async () => {
    try {
      setSavingKey(true);
      await api.removeGeminiKey();
      setKeySavedMessage('API key removed from secure storage.');
      await fetchAIInfo();
      setTimeout(() => setKeySavedMessage(null), 4000);
    } catch (err) {
      console.error('Failed to remove Gemini API key:', err);
    } finally {
      setSavingKey(false);
    }
  };

  const handleTestConnection = async (targetProvider?: 'gemini' | 'ollama') => {
    const prov = targetProvider || activeProvider;
    try {
      setTestingConnection(true);
      setTestResult(null);
      const modelToTest = prov === 'gemini' ? selectedGeminiModel : selectedOllamaModel;
      const res = await api.testAIConnection(prov, modelToTest, geminiKeyInput.trim() || undefined);
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        provider: prov,
        message: err.message || 'Connection test failed unexpectedly.',
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveAllSettings = async () => {
    try {
      setSaving(true);
      const model = activeProvider === 'gemini' ? selectedGeminiModel : selectedOllamaModel;
      const updated = await api.setAISettings({
        active_provider: activeProvider,
        selected_model: model,
        fallback_policy: fallbackPolicy,
        consent_granted: activeProvider === 'gemini' ? true : undefined,
      });
      setAIStatus(updated);
      setSavedSuccess(true);
      window.dispatchEvent(new CustomEvent('compust-ai-provider-changed'));
      if (onSettingsSaved) onSettingsSaved();
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save AI settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const isOllamaConnected = aiStatus?.provider === 'ollama' && aiStatus?.status === 'connected';
  const isGeminiReady = Boolean(aiStatus?.gemini_key_configured || geminiKeyInput.trim());

  return (
    <ModalOverlay onClick={onClose}>
      <ModalCard onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="title-area">
            <Bot size={22} className="header-icon" />
            <div>
              <h3>AI Provider & Runtime Settings</h3>
              <p className="modal-subtitle">Configure local offline AI or cloud Google Gemini intelligence</p>
            </div>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {loading ? (
          <LoadingArea>
            <RefreshCw size={24} className="spin" />
            <span>Detecting AI providers and runtimes...</span>
          </LoadingArea>
        ) : (
          <div className="modal-body">
            {/* Provider Selector Cards */}
            <div className="config-section">
              <div className="section-title">Select Active AI Provider</div>
              <div className="providers-grid">
                {/* Ollama Card */}
                <ProviderCard
                  $selected={activeProvider === 'ollama'}
                  onClick={() => handleSelectProvider('ollama')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="provider-top">
                    <div className="provider-name-row">
                      <Cpu size={18} className="icon-ollama" />
                      <span className="provider-title">Ollama</span>
                    </div>
                    <span
                      className={`provider-badge ${isOllamaConnected ? 'connected' : 'offline'}`}
                    >
                      {isOllamaConnected ? 'Connected' : 'Offline'}
                    </span>
                  </div>
                  <div className="provider-desc">
                    Local & 100% offline. Zero data leaves your computer. Runs on your CPU/GPU.
                  </div>
                  <div className="provider-meta">
                    {isOllamaConnected
                      ? `${aiStatus?.models?.length || 0} local models available`
                      : 'Not running on 127.0.0.1:11434'}
                  </div>
                </ProviderCard>

                {/* Gemini Card */}
                <ProviderCard
                  $selected={activeProvider === 'gemini'}
                  onClick={() => handleSelectProvider('gemini')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="provider-top">
                    <div className="provider-name-row">
                      <Cloud size={18} className="icon-gemini" />
                      <span className="provider-title">Google Gemini</span>
                    </div>
                    <span
                      className={`provider-badge ${
                        aiStatus?.gemini_key_configured
                          ? 'connected'
                          : 'configured'
                      }`}
                    >
                      {aiStatus?.gemini_key_configured
                        ? `Configured (${aiStatus.gemini_key_masked})`
                        : 'Requires Key'}
                    </span>
                  </div>
                  <div className="provider-desc">
                    Cloud intelligence. High reasoning speed & precision. Free quota available.
                  </div>
                  <div className="provider-meta">
                    PII automatically scrubbed locally before request.
                  </div>
                </ProviderCard>
              </div>
            </div>

            {/* Provider Configuration */}
            {activeProvider === 'ollama' ? (
              <div className="config-section">
                <div className="section-title">Ollama Local Settings</div>
                {isOllamaConnected ? (
                  aiStatus?.models && aiStatus.models.length > 0 ? (
                    <div className="config-box">
                      <label>Installed Local Model</label>
                      <select
                        value={selectedOllamaModel}
                        onChange={(e) => setSelectedOllamaModel(e.target.value)}
                      >
                        {aiStatus.models.map((m) => (
                          <option key={m.name} value={m.name}>
                            {m.name} {m.parameter_size ? `(${m.parameter_size})` : ''}
                          </option>
                        ))}
                      </select>

                      <div className="model-details">
                        <div className="status-row">
                          <CheckCircle2 size={15} className="ok-icon" />
                          <span>
                            Active model: <strong>{selectedOllamaModel}</strong> (Verified available locally)
                          </span>
                        </div>
                      </div>

                      <div className="field-group" style={{ marginTop: 14 }}>
                        <label>Fallback Failure Policy</label>
                        <select
                          value={fallbackPolicy}
                          onChange={(e) => setFallbackPolicy(e.target.value)}
                        >
                          <option value="deterministic">
                            Deterministic Fallback (Offline rules, recommended)
                          </option>
                          <option value="error">
                            Fail with plain-language error message
                          </option>
                        </select>
                      </div>

                      {/* Test Connection Button */}
                      <div className="test-area" style={{ marginTop: 14 }}>
                        <button
                          type="button"
                          className="test-btn"
                          onClick={() => handleTestConnection('ollama')}
                          disabled={testingConnection}
                        >
                          {testingConnection ? (
                            <>
                              <RefreshCw size={14} className="spin" />
                              <span>Testing Ollama connection...</span>
                            </>
                          ) : (
                            <>
                              <Zap size={14} />
                              <span>Test Ollama Local Connection</span>
                            </>
                          )}
                        </button>
                      </div>
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
                        Compust operates normally with deterministic fallbacks without AI. To enable local AI
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
            ) : (
              /* Google Gemini 4-Step Stepped Setup Flow */
              <div className="config-section">
                <div className="section-title">Google Gemini Provider Setup Flow</div>
                
                {/* Stepper Navigation Bar */}
                <StepperBar>
                  <StepItem
                    $active={wizardStep === 1}
                    $completed={wizardStep > 1 || Boolean(aiStatus?.consent_granted)}
                    onClick={() => setWizardStep(1)}
                  >
                    <span className="step-num">1</span>
                    <span className="step-name">Consent & Privacy</span>
                  </StepItem>
                  <StepConnector $completed={wizardStep > 1 || Boolean(aiStatus?.consent_granted)} />

                  <StepItem
                    $active={wizardStep === 2}
                    $completed={wizardStep > 2 || Boolean(aiStatus?.gemini_key_configured)}
                    onClick={() => setWizardStep(2)}
                  >
                    <span className="step-num">2</span>
                    <span className="step-name">Key & Model</span>
                  </StepItem>
                  <StepConnector $completed={wizardStep > 2 || Boolean(aiStatus?.gemini_key_configured)} />

                  <StepItem
                    $active={wizardStep === 3}
                    $completed={wizardStep > 3 || Boolean(testResult?.success)}
                    onClick={() => setWizardStep(3)}
                  >
                    <span className="step-num">3</span>
                    <span className="step-name">Test Latency</span>
                  </StepItem>
                  <StepConnector $completed={wizardStep > 3} />

                  <StepItem
                    $active={wizardStep === 4}
                    $completed={wizardStep === 4 && savedSuccess}
                    onClick={() => setWizardStep(4)}
                  >
                    <span className="step-num">4</span>
                    <span className="step-name">Save & Apply</span>
                  </StepItem>
                </StepperBar>

                {/* Step 1: Consent & Privacy */}
                {wizardStep === 1 && (
                  <StepContainer>
                    <div className="step-header">
                      <ShieldCheck size={22} className="step-icon accent-blue" />
                      <div>
                        <h4>Step 1: Explicit Consent & Privacy Architecture</h4>
                        <p>Compust is local-first. Cloud AI requires your explicit permission.</p>
                      </div>
                    </div>

                    <div className="step-body">
                      <div className="privacy-card">
                        <div className="privacy-point">
                          <CheckCircle2 size={16} className="pt-icon" />
                          <div>
                            <strong>Local PII Stripping:</strong> Your personal identity data (real name, personal email, phone numbers, home address, social links) is purged client-side on your PC before any payload leaves your machine.
                          </div>
                        </div>

                        <div className="privacy-point">
                          <CheckCircle2 size={16} className="pt-icon" />
                          <div>
                            <strong>Direct Encrypted HTTPS:</strong> Requests are dispatched exclusively to Google Gemini official API endpoints over TLS 1.3 encryption. No intermediary proxies or telemetry tracking.
                          </div>
                        </div>

                        <div className="privacy-point">
                          <CheckCircle2 size={16} className="pt-icon" />
                          <div>
                            <strong>Local DPAPI Key Encryption:</strong> Your Gemini API key is encrypted using Windows Data Protection API (DPAPI) and never transmitted or logged.
                          </div>
                        </div>

                        <div className="privacy-point">
                          <CheckCircle2 size={16} className="pt-icon" />
                          <div>
                            <strong>Instant One-Click Reversion:</strong> You can switch back to offline Ollama or deterministic rule engines at any time with no lock-in.
                          </div>
                        </div>
                      </div>

                      <div className="step-actions">
                        <button
                          type="button"
                          className="primary-step-btn"
                          onClick={handleGrantConsent}
                          disabled={saving}
                        >
                          <Check size={16} />
                          <span>I Understand & Accept (Proceed to Key Setup)</span>
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </StepContainer>
                )}

                {/* Step 2: Key & Model */}
                {wizardStep === 2 && (
                  <StepContainer>
                    <div className="step-header">
                      <Key size={22} className="step-icon accent-cyan" />
                      <div>
                        <h4>Step 2: API Key & Model Configuration</h4>
                        <p>Provide your Google AI Studio API key and choose your preferred Gemini model.</p>
                      </div>
                    </div>

                    <div className="step-body">
                      <div className="field-group">
                        <label>
                          Gemini API Key
                          <span className="tag-safe">Encrypted locally with Windows DPAPI</span>
                        </label>
                        <div className="key-input-row">
                          <div className="input-wrap">
                            <Key size={15} className="input-icon" />
                            <input
                              type={showGeminiKey ? 'text' : 'password'}
                              placeholder={
                                aiStatus?.gemini_key_configured
                                  ? `Active Key: ${aiStatus.gemini_key_masked} (enter new key to replace)`
                                  : 'Enter Gemini API key (AIza...)'
                              }
                              value={geminiKeyInput}
                              onChange={(e) => setGeminiKeyInput(e.target.value)}
                            />
                            <button
                              type="button"
                              className="eye-btn"
                              onClick={() => setShowGeminiKey(!showGeminiKey)}
                              title={showGeminiKey ? 'Hide key' : 'Show key'}
                            >
                              {showGeminiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                            </button>
                          </div>

                          <button
                            type="button"
                            className="save-key-btn"
                            onClick={handleSaveGeminiKey}
                            disabled={savingKey || !geminiKeyInput.trim()}
                          >
                            {savingKey ? <RefreshCw size={13} className="spin" /> : <Save size={13} />}
                            <span>Save Key</span>
                          </button>

                          {aiStatus?.gemini_key_configured && (
                            <button
                              type="button"
                              className="remove-key-btn"
                              onClick={handleRemoveGeminiKey}
                              disabled={savingKey}
                              title="Remove stored key"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>

                        {keySavedMessage && <div className="key-msg">{keySavedMessage}</div>}

                        <div className="helper-text">
                          Keys are write-only from the user interface and encrypted on disk via Windows DPAPI. Get a free key at{' '}
                          <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
                            Google AI Studio <ExternalLink size={11} />
                          </a>
                        </div>
                      </div>

                      {/* Cloud Model Selector */}
                      <div className="field-group" style={{ marginTop: 14 }}>
                        <label>Cloud Model</label>
                        <select
                          value={selectedGeminiModel}
                          onChange={(e) => setSelectedGeminiModel(e.target.value)}
                        >
                          {GEMINI_MODELS.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name} — {m.desc}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="step-actions dual-actions">
                        <button
                          type="button"
                          className="secondary-step-btn"
                          onClick={() => setWizardStep(1)}
                        >
                          <ChevronLeft size={16} />
                          <span>Back: Privacy</span>
                        </button>
                        <button
                          type="button"
                          className="primary-step-btn"
                          onClick={() => setWizardStep(3)}
                          disabled={!isGeminiReady}
                        >
                          <span>Next: Test Connection</span>
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </StepContainer>
                )}

                {/* Step 3: Test Connection with Latency Display */}
                {wizardStep === 3 && (
                  <StepContainer>
                    <div className="step-header">
                      <Zap size={22} className="step-icon accent-amber" />
                      <div>
                        <h4>Step 3: Live Verification & Latency Test</h4>
                        <p>Verify live API credentials, model availability, and measured round-trip response latency.</p>
                      </div>
                    </div>

                    <div className="step-body">
                      <div className="test-box">
                        <div className="test-box-meta">
                          <div>
                            <strong>Target Model:</strong> <code>{selectedGeminiModel}</code>
                          </div>
                          <div>
                            <strong>Credentials:</strong>{' '}
                            {aiStatus?.gemini_key_configured ? (
                              <span className="badge-ok">Configured ({aiStatus.gemini_key_masked})</span>
                            ) : geminiKeyInput.trim() ? (
                              <span className="badge-pending">Provided in input</span>
                            ) : (
                              <span className="badge-missing">Missing Key</span>
                            )}
                          </div>
                        </div>

                        <button
                          type="button"
                          className="run-test-btn"
                          onClick={() => handleTestConnection('gemini')}
                          disabled={testingConnection || !isGeminiReady}
                        >
                          {testingConnection ? (
                            <>
                              <RefreshCw size={15} className="spin" />
                              <span>Testing Gemini connection & measuring latency...</span>
                            </>
                          ) : (
                            <>
                              <Zap size={15} />
                              <span>Execute Live Connection Test</span>
                            </>
                          )}
                        </button>

                        {testResult && (
                          <TestResultCard $success={testResult.success} style={{ marginTop: 14 }}>
                            {testResult.success ? (
                              <CheckCircle2 size={18} className="icon-success" />
                            ) : (
                              <AlertTriangle size={18} className="icon-error" />
                            )}
                            <div className="test-text">
                              <strong>{testResult.message}</strong>
                              {testResult.latency_ms !== undefined && (
                                <span className="latency-badge">
                                  Round-trip Latency: <strong>{testResult.latency_ms} ms</strong>
                                </span>
                              )}
                            </div>
                          </TestResultCard>
                        )}
                      </div>

                      <div className="step-actions dual-actions">
                        <button
                          type="button"
                          className="secondary-step-btn"
                          onClick={() => setWizardStep(2)}
                        >
                          <ChevronLeft size={16} />
                          <span>Back: Key & Model</span>
                        </button>
                        <button
                          type="button"
                          className="primary-step-btn"
                          onClick={() => setWizardStep(4)}
                        >
                          <span>Next: Review & Apply</span>
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </StepContainer>
                )}

                {/* Step 4: Save & Apply Globally */}
                {wizardStep === 4 && (
                  <StepContainer>
                    <div className="step-header">
                      <CheckCircle2 size={22} className="step-icon accent-green" />
                      <div>
                        <h4>Step 4: Save & Apply Globally</h4>
                        <p>Applies immediately across all COMPUST features without requiring an application restart.</p>
                      </div>
                    </div>

                    <div className="step-body">
                      <div className="summary-card">
                        <div className="summary-row">
                          <span className="label">Active Provider</span>
                          <span className="value strong">Google Gemini (Cloud)</span>
                        </div>
                        <div className="summary-row">
                          <span className="label">Selected Model</span>
                          <span className="value code">{selectedGeminiModel}</span>
                        </div>
                        <div className="summary-row">
                          <span className="label">Key Encryption</span>
                          <span className="value safe">Windows DPAPI Protected</span>
                        </div>
                        <div className="summary-row">
                          <span className="label">Privacy Guard</span>
                          <span className="value safe">Active (Client-side PII Purge)</span>
                        </div>

                        <div className="field-group" style={{ marginTop: 14 }}>
                          <label>Fallback Failure Policy</label>
                          <select
                            value={fallbackPolicy}
                            onChange={(e) => setFallbackPolicy(e.target.value)}
                          >
                            <option value="deterministic">
                              Deterministic Fallback (Offline rules, recommended)
                            </option>
                            <option value="ollama">
                              Try local Ollama (if running)
                            </option>
                            <option value="error">
                              Fail with plain-language error message
                            </option>
                          </select>
                          <span className="helper-note">
                            Ensures zero disruption if offline or quota limits are encountered.
                          </span>
                        </div>
                      </div>

                      {savedSuccess && (
                        <SuccessBanner>
                          <CheckCircle2 size={16} />
                          <span>
                            Applied globally! All features (Cover Letter, Resume Tailoring, Interview Prep, Career Assistant) now use Google Gemini immediately without restart.
                          </span>
                        </SuccessBanner>
                      )}

                      <div className="step-actions dual-actions">
                        <button
                          type="button"
                          className="secondary-step-btn"
                          onClick={() => setWizardStep(3)}
                        >
                          <ChevronLeft size={16} />
                          <span>Back: Latency Test</span>
                        </button>
                        <button
                          type="button"
                          className="primary-step-btn save-global-btn"
                          onClick={handleSaveAllSettings}
                          disabled={saving || !isGeminiReady}
                        >
                          {saving ? (
                            <>
                              <RefreshCw size={15} className="spin" />
                              <span>Applying settings...</span>
                            </>
                          ) : (
                            <>
                              <Save size={15} />
                              <span>Apply Globally (No Restart Required)</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </StepContainer>
                )}
              </div>
            )}

            {/* Test result card if tested in Ollama mode */}
            {activeProvider === 'ollama' && testResult && (
              <TestResultCard $success={testResult.success} style={{ marginTop: 14 }}>
                {testResult.success ? (
                  <CheckCircle2 size={16} className="icon-success" />
                ) : (
                  <AlertTriangle size={16} className="icon-error" />
                )}
                <div className="test-text">
                  <strong>{testResult.message}</strong>
                  {testResult.latency_ms !== undefined && (
                    <span>Latency: {testResult.latency_ms}ms</span>
                  )}
                </div>
              </TestResultCard>
            )}
          </div>
        )}

        <div className="modal-actions">
          <button className="cancel-btn" onClick={onClose}>
            Close
          </button>
          {activeProvider === 'ollama' && (
            <button
              className="save-all-btn"
              onClick={handleSaveAllSettings}
              disabled={saving}
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
                  <span>Apply Ollama Settings</span>
                </>
              )}
            </button>
          )}
        </div>
      </ModalCard>
    </ModalOverlay>
  );
};

/* Styled Components */

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
  max-width: 660px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;

    .title-area {
      display: flex;
      align-items: flex-start;
      gap: 12px;

      .header-icon {
        color: #3b82f6;
        margin-top: 2px;
      }

      h3 {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
      }

      .modal-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin: 2px 0 0;
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
    gap: 12px;
  }

  .config-box {
    background: rgba(0, 0, 0, 0.25);
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    .field-group {
      margin-bottom: 14px;
      &:last-child {
        margin-bottom: 0;
      }
    }

    label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.8rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 8px;

      .tag-safe {
        font-size: 0.7rem;
        color: #10b981;
        font-weight: 500;
      }
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

      &:focus {
        border-color: #3b82f6;
      }
    }

    .helper-text {
      font-size: 0.72rem;
      color: #94a3b8;
      margin-top: 6px;

      a {
        color: #60a5fa;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 3px;

        &:hover {
          text-decoration: underline;
        }
      }
    }

    .helper-note {
      display: block;
      font-size: 0.72rem;
      color: #f59e0b;
      margin-top: 6px;
    }

    .model-details {
      margin-top: 10px;
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
    }
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;

    .cancel-btn {
      padding: 9px 16px;
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

    .save-all-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 18px;
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
`;

const ProviderCard = styled.div<{ $selected: boolean }>`
  padding: 14px;
  border-radius: 12px;
  background: ${(props) =>
    props.$selected ? 'rgba(37, 99, 235, 0.12)' : 'rgba(255, 255, 255, 0.03)'};
  border: 1px solid
    ${(props) =>
      props.$selected ? '#3b82f6' : 'rgba(255, 255, 255, 0.08)'};
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: ${(props) =>
      props.$selected ? '#3b82f6' : 'rgba(255, 255, 255, 0.18)'};
    background: ${(props) =>
      props.$selected ? 'rgba(37, 99, 235, 0.16)' : 'rgba(255, 255, 255, 0.06)'};
  }

  .provider-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .provider-name-row {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #f1f5f9;
    font-weight: 700;
    font-size: 0.9rem;

    .icon-ollama {
      color: #a855f7;
    }

    .icon-gemini {
      color: #38bdf8;
    }
  }

  .provider-badge {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 8px;

    &.connected {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    &.configured {
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }

    &.offline {
      background: rgba(244, 63, 94, 0.15);
      color: #f43f5e;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }
  }

  .provider-desc {
    font-size: 0.74rem;
    color: #94a3b8;
    line-height: 1.4;
    margin-bottom: 6px;
  }

  .provider-meta {
    font-size: 0.68rem;
    color: #64748b;
  }
`;

const StepperBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
`;

const StepItem = styled.div<{ $active: boolean; $completed: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  opacity: ${(props) => (props.$active || props.$completed ? 1 : 0.45)};
  transition: opacity 0.2s;

  .step-num {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
    background: ${(props) =>
      props.$active
        ? '#38bdf8'
        : props.$completed
        ? '#10b981'
        : 'rgba(255, 255, 255, 0.1)'};
    color: ${(props) => (props.$active || props.$completed ? '#0f172a' : '#cbd5e1')};
  }

  .step-name {
    font-size: 0.75rem;
    font-weight: ${(props) => (props.$active ? '700' : '500')};
    color: ${(props) => (props.$active ? '#f8fafc' : '#94a3b8')};

    @media (max-width: 600px) {
      display: none;
    }
  }
`;

const StepConnector = styled.div<{ $completed: boolean }>`
  flex: 1;
  height: 2px;
  margin: 0 8px;
  background: ${(props) =>
    props.$completed ? 'rgba(16, 185, 129, 0.5)' : 'rgba(255, 255, 255, 0.08)'};
`;

const StepContainer = styled.div`
  background: rgba(0, 0, 0, 0.25);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 18px;

  .step-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;

    .step-icon {
      flex-shrink: 0;
      margin-top: 2px;

      &.accent-blue { color: #38bdf8; }
      &.accent-cyan { color: #06b6d4; }
      &.accent-amber { color: #f59e0b; }
      &.accent-green { color: #10b981; }
    }

    h4 {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 700;
      color: #f8fafc;
    }

    p {
      margin: 3px 0 0;
      font-size: 0.78rem;
      color: #94a3b8;
    }
  }

  .privacy-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 10px;
    padding: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    .privacy-point {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      font-size: 0.78rem;
      line-height: 1.45;
      color: #cbd5e1;

      .pt-icon {
        color: #38bdf8;
        flex-shrink: 0;
        margin-top: 2px;
      }

      strong {
        color: #f1f5f9;
      }
    }
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 6px;

    label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.8rem;
      font-weight: 600;
      color: #cbd5e1;

      .tag-safe {
        font-size: 0.7rem;
        color: #10b981;
        font-weight: 500;
      }
    }

    select {
      width: 100%;
      padding: 9px 12px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      color: #f8fafc;
      font-size: 0.82rem;
      outline: none;

      &:focus {
        border-color: #38bdf8;
      }
    }

    .helper-text {
      font-size: 0.72rem;
      color: #94a3b8;

      a {
        color: #38bdf8;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 3px;

        &:hover {
          text-decoration: underline;
        }
      }
    }

    .helper-note {
      font-size: 0.72rem;
      color: #94a3b8;
    }
  }

  .key-input-row {
    display: flex;
    gap: 8px;
    align-items: center;

    .input-wrap {
      position: relative;
      flex: 1;

      .input-icon {
        position: absolute;
        left: 10px;
        top: 50%;
        transform: translateY(-50%);
        color: #64748b;
      }

      input {
        width: 100%;
        padding: 9px 36px 9px 32px;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        color: #f8fafc;
        font-size: 0.82rem;
        outline: none;

        &:focus {
          border-color: #38bdf8;
        }
      }

      .eye-btn {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        padding: 4px;

        &:hover {
          color: #ffffff;
        }
      }
    }

    .save-key-btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 9px 14px;
      background: #0284c7;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;

      &:hover:not(:disabled) {
        background: #0369a1;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }

    .remove-key-btn {
      padding: 9px 10px;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #f87171;
      border-radius: 8px;
      cursor: pointer;

      &:hover {
        background: rgba(239, 68, 68, 0.25);
      }
    }
  }

  .key-msg {
    margin-top: 6px;
    font-size: 0.75rem;
    color: #34d399;
    font-weight: 500;
  }

  .test-box {
    background: rgba(15, 23, 42, 0.6);
    border-radius: 10px;
    padding: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    .test-box-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      color: #cbd5e1;
      margin-bottom: 12px;

      code {
        background: rgba(0, 0, 0, 0.3);
        padding: 2px 6px;
        border-radius: 4px;
        color: #38bdf8;
      }

      .badge-ok {
        color: #34d399;
        font-weight: 600;
      }
      .badge-pending {
        color: #fbbf24;
      }
      .badge-missing {
        color: #f87171;
      }
    }

    .run-test-btn {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 16px;
      background: #0284c7;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;

      &:hover:not(:disabled) {
        background: #0369a1;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }

  .summary-card {
    background: rgba(15, 23, 42, 0.6);
    border-radius: 10px;
    padding: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);

    .summary-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.82rem;

      &:last-of-type {
        border-bottom: none;
      }

      .label {
        color: #94a3b8;
      }

      .value {
        color: #f1f5f9;

        &.strong { font-weight: 700; color: #38bdf8; }
        &.code { font-family: monospace; color: #7dd3fc; }
        &.safe { color: #34d399; font-weight: 600; }
      }
    }
  }

  .step-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 16px;

    &.dual-actions {
      justify-content: space-between;
    }

    .primary-step-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 16px;
      background: #0284c7;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;

      &:hover:not(:disabled) {
        background: #0369a1;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      &.save-global-btn {
        background: #10b981;
        &:hover:not(:disabled) {
          background: #059669;
        }
      }
    }

    .secondary-step-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 14px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      border-radius: 8px;
      font-size: 0.82rem;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
      }
    }
  }
`;

const SuccessBanner = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 10px 14px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  color: #34d399;
  font-size: 0.8rem;
  font-weight: 500;
  line-height: 1.4;
`;

const TestResultCard = styled.div<{ $success: boolean }>`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  background: ${(props) =>
    props.$success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'};
  border: 1px solid
    ${(props) =>
      props.$success ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'};
  font-size: 0.78rem;

  .icon-success {
    color: #34d399;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .icon-error {
    color: #f87171;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .test-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
    color: #e2e8f0;

    .latency-badge {
      display: inline-block;
      font-size: 0.72rem;
      color: #38bdf8;
      strong {
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
