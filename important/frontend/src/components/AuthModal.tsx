import React, { useState } from 'react';
import styled from 'styled-components';
import { X, Lock, Mail, User, ArrowRight } from 'lucide-react';
import { api, setStoredToken } from '../api/client';
import type { UserProfile } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

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
      } else {
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

  return (
    <StyledAuthBackdrop onClick={onClose}>
      <div className="form-card" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button className="close-btn" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>

        {/* Tab Switcher */}
        <div className="tab-switcher">
          <button
            type="button"
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(null); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(null); }}
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

          <button type="submit" className="submit-btn" disabled={loading}>
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
