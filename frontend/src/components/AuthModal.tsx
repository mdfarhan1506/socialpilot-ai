'use client';

import React, { useState } from 'react';
import { api } from '../services/api';

interface AuthModalProps {
  isOpen: boolean;
  onSuccess: () => void;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function AuthModal({ isOpen, onSuccess, onToast }: AuthModalProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let data: { access_token: string };
      if (isRegister) {
        data = await api.register(email, password);
        onToast('Account created successfully!', 'success');
      } else {
        data = await api.login(email, password);
        onToast('Logged in successfully!', 'success');
      }
      localStorage.setItem('access_token', data.access_token);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
      onToast(err.message || 'Authentication failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            className="brand-logo"
            style={{ width: 48, height: 48, margin: '0 auto 1rem auto', fontSize: '1.4rem' }}
          >
            SP
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
            {isRegister ? 'Create your account' : 'Welcome to SocialPilot AI'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {isRegister
              ? 'Start generating and scheduling content across platforms'
              : 'Sign in to access your workspaces, studio, and analytics'}
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '0.75rem',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              color: '#f87171',
              fontSize: '0.85rem',
              marginBottom: '1rem',
            }}
          >
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.85rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account? ' : "Don't have an account yet? "}
          </span>
          <button
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent-primary)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
          >
            {isRegister ? 'Sign In' : 'Register'}
          </button>
        </div>
      </div>
    </div>
  );
}
