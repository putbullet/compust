import React, { useState } from 'react';
import styled from 'styled-components';
import { X, Lock, Mail, User, ArrowRight, KeyRound } from 'lucide-react';
import { api, setStoredToken } from '../api/client';
import type { UserProfile } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
}

type ModalMode = 'login' | 'register' | 'forgot_password';

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [mode, setMode] = useState<ModalMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  // Reset password state
  const [resetEmail, setResetEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const switchMode = (nextMode: ModalMode) => {
    setMode(nextMode);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const res = await api.login(email, password);
        setStoredToken(res.access_token);
        onSuccess(res.user);
        onClose();
      } else if (mode === 'register') {
        const res = await api.register({
          email,
          password,
          first_name: firstName,
          last_name: lastName,
        });
        setStoredToken(res.access_token);
        onSuccess(res.user);
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await api.resetPassword(resetEmail, newPassword);
      setStoredToken(res.access_token);
      onSuccess(res.user);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Password reset failed. Please check your email address.');
    } finally {
      setLoading(false);
    }
  };

  // ── Forgot Password View ──────────────────────────────────────────────────
  if (mode === 'forgot_password') {
    return (
      <StyledAuthBackdrop onClick={onClose}>
        <div className="form-card" onClick={(e) => e.stopPropagation()}>
          <button className="close-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>

          <div className="auth-brand-badge">
            <img src="/logo-transparent.png" alt="Compust Logo" className="auth-logo" />
            <span className="auth-brand-name">Compust</span>
          </div>

          <div className="reset-icon-wrap">
            <KeyRound size={28} className="reset-icon" />
          </div>

          <h3 className="auth-title">Reset Password</h3>
          <p className="auth-subtitle">
            Enter your account email and choose a new password. No email required — reset happens instantly.
          </p>

          {error && <div className="error-banner">{error}</div>}

          <form className="auth-form" onSubmit={handleResetSubmit}>
            <div className="input-group">
              <label htmlFor="reset-email">Account Email</label>
              <div className="input-field">
                <Mail size={16} className="icon" />
                <input
                  id="reset-email"
                  type="email"
                  required
                  placeholder="your@email.com"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="reset-new-password">New Password</label>
              <div className="input-field">
                <Lock size={16} className="icon" />
                <input
                  id="reset-new-password"
                  type="password"
                  required
                  minLength={6}
                  placeholder="At least 6 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="reset-confirm-password">Confirm New Password</label>
              <div className="input-field">
                <Lock size={16} className="icon" />
                <input
                  id="reset-confirm-password"
                  type="password"
                  required
                  placeholder="Repeat new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              id="reset-password-submit-btn"
              className="submit-btn"
              disabled={loading}
            >
              <span>{loading ? 'Resetting...' : 'Reset & Sign In'}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          <button
            type="button"
            className="back-to-login-btn"
            onClick={() => switchMode('login')}
          >
            ← Back to Sign In
          </button>
        </div>
      </StyledAuthBackdrop>
    );
  }

  // ── Login / Register View ─────────────────────────────────────────────────
  return (
    <StyledAuthBackdrop onClick={onClose}>
      <div className="form-card" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button className="close-btn" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>

        {/* Brand Header */}
        <div className="auth-brand-badge">
          <img src="/logo-transparent.png" alt="Compust Logo" className="auth-logo" />
          <span className="auth-brand-name">Compust</span>
        </div>

        {/* Tab Switcher */}
        <div className="tab-switcher">
          <button
            type="button"
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => switchMode('login')}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => switchMode('register')}
          >
            Create Account
          </button>
        </div>

        <h3 className="auth-title">
          {mode === 'login' ? 'Welcome Back to Compust' : 'Unlock Personalized Matches'}
        </h3>
        <p className="auth-subtitle">
          {mode === 'login'
            ? 'Sign in to access your saved opportunities and match scores.'
            : 'Register to calculate match percentages against your career preferences.'}
        </p>

        {error && <div className="error-banner">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="names-row">
              <div className="input-group">
                <label htmlFor="auth-first-name">First Name</label>
                <div className="input-field">
                  <User size={16} className="icon" />
                  <input
                    id="auth-first-name"
                    type="text"
                    required
                    placeholder="Hamza"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                  />
                </div>
              </div>
              <div className="input-group">
                <label htmlFor="auth-last-name">Last Name</label>
                <div className="input-field">
                  <User size={16} className="icon" />
                  <input
                    id="auth-last-name"
                    type="text"
                    placeholder="Alaoui"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          <div className="input-group">
            <label htmlFor="auth-email">Email Address</label>
            <div className="input-field">
              <Mail size={16} className="icon" />
              <input
                id="auth-email"
                type="email"
                required
                placeholder="developer@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="auth-password">Password</label>
            <div className="input-field">
              <Lock size={16} className="icon" />
              <input
                id="auth-password"
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {mode === 'login' && (
            <button
              type="button"
              id="forgot-password-btn"
              className="forgot-password-btn"
              onClick={() => switchMode('forgot_password')}
            >
              Forgot password?
            </button>
          )}

          <button
            type="submit"
            id="auth-submit-btn"
            className="submit-btn"
            disabled={loading}
          >
            <span>{loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Get Started')}</span>
            <ArrowRight size={16} />
          </button>
        </form>
      </div>
    </StyledAuthBackdrop>
  );
};

const StyledAuthBackdrop = styled.div`
  position: fixed;
  inset: 0;
  z-index: 250;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;

  .form-card {
    position: relative;
    width: 100%;
    max-width: 420px;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
    animation: fadeIn 0.25s ease;
  }

  .close-btn {
    position: absolute;
    top: 18px;
    right: 18px;
    color: #64748b;
    padding: 6px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }
  }

  .auth-brand-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-bottom: 20px;
  }

  .auth-logo {
    width: 36px;
    height: 36px;
    object-fit: contain;
    filter: drop-shadow(0 0 10px rgba(0, 240, 255, 0.4));
  }

  .auth-brand-name {
    font-family: var(--font-heading);
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
  }

  .reset-icon-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 14px;

    .reset-icon {
      color: #38bdf8;
      filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
    }
  }

  .tab-switcher {
    display: flex;
    background: rgba(255, 255, 255, 0.05);
    padding: 4px;
    border-radius: 12px;
    margin-bottom: 22px;
  }

  .tab {
    flex: 1;
    padding: 8px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #94a3b8;
    transition: all 0.2s;

    &.active {
      background: #2563eb;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
    }
  }

  .auth-title {
    font-size: 1.25rem;
    color: #ffffff;
    margin-bottom: 6px;
  }

  .auth-subtitle {
    font-size: 0.82rem;
    color: #94a3b8;
    margin-bottom: 18px;
    line-height: 1.5;
  }

  .error-banner {
    padding: 10px 14px;
    background: rgba(244, 63, 94, 0.15);
    border: 1px solid rgba(244, 63, 94, 0.3);
    border-radius: 10px;
    color: #f87171;
    font-size: 0.82rem;
    margin-bottom: 16px;
  }

  .auth-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .names-row {
    display: flex;
    gap: 12px;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;

    label {
      font-size: 0.78rem;
      font-weight: 500;
      color: #cbd5e1;
    }
  }

  .input-field {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 10px 14px;
    transition: all 0.2s;

    &:focus-within {
      border-color: #3b82f6;
      box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
    }

    .icon {
      color: #64748b;
    }

    input {
      width: 100%;
      background: transparent;
      border: none;
      outline: none;
      color: #f8fafc;
      font-size: 0.9rem;

      &::placeholder {
        color: #94a3b8;
      }
    }
  }

  .forgot-password-btn {
    align-self: flex-end;
    margin-top: -6px;
    font-size: 0.78rem;
    font-weight: 500;
    color: #60a5fa;
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 0;
    transition: color 0.18s;

    &:hover {
      color: #93c5fd;
      text-decoration: underline;
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
      border-radius: 4px;
    }
  }

  .back-to-login-btn {
    margin-top: 18px;
    width: 100%;
    font-size: 0.82rem;
    font-weight: 500;
    color: #94a3b8;
    background: none;
    border: none;
    cursor: pointer;
    text-align: center;
    transition: color 0.18s;

    &:hover {
      color: #cbd5e1;
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
      border-radius: 4px;
    }
  }

  .submit-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 12px;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.95rem;
    font-weight: 600;
    border-radius: 10px;
    margin-top: 8px;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #1d4ed8;
      box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
      transform: translateY(-1px);
    }

    &:focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  .tab:focus-visible,
  .close-btn:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: 2px;
  }

  @media (max-width: 480px) {
    padding: 12px;

    .form-card {
      padding: 24px 18px;
    }

    .names-row {
      flex-direction: column;
      gap: 12px;
    }
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
  }
`;
