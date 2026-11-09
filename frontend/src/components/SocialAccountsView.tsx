'use client';

import React, { useState } from 'react';
import { MetaStatus, AppConfig } from '../types';
import { api } from '../services/api';

interface SocialAccountsViewProps {
  metaStatus: MetaStatus | null;
  config: AppConfig | null;
  onRefreshStatus: () => void;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function SocialAccountsView({
  metaStatus,
  config,
  onRefreshStatus,
  onToast,
}: SocialAccountsViewProps) {
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  async function handleDisconnect() {
    const confirmed = window.confirm(
      'Are you sure you want to disconnect your Instagram account? This will remove the stored access token, but your scheduled posts, workspaces, and analytics data will be preserved.'
    );
    if (!confirmed) return;

    setDisconnecting(true);
    try {
      await api.disconnectMeta();
      onToast('✅ Instagram account disconnected successfully.', 'success');
      onRefreshStatus();
    } catch (err: any) {
      onToast(err.message || 'Failed to disconnect Instagram account', 'error');
    } finally {
      setDisconnecting(false);
    }
  }

  async function handleMockConnect() {
    setConnecting(true);
    try {
      const res = await api.connectMockMeta('mock_oauth_code_verified');
      onToast(
        `✅ Connected Mock Instagram account (${res.ig_user_id || 'MOCK_IG_USER_ID'})! Encrypted token stored.`,
        'success'
      );
      onRefreshStatus();
    } catch (err: any) {
      onToast(err.message || 'Connection failed', 'error');
    } finally {
      setConnecting(false);
    }
  }

  async function handleLiveConnect() {
    try {
      const res = await api.getOAuthStart();
      if (res.mock_mode) {
        onToast('Mock Mode is active. Using simulated mock connection instead.', 'info');
        handleMockConnect();
      } else if (res.oauth_url) {
        window.location.href = res.oauth_url;
      }
    } catch (err: any) {
      onToast(err.message || 'Failed to start OAuth', 'error');
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Social Accounts</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Connect and manage social media accounts for automatic publishing.
        </p>
      </div>

      {/* Mode Information Card */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          backgroundColor: config?.mock_mode ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 185, 129, 0.08)',
          border: `1px solid ${config?.mock_mode ? 'rgba(245, 158, 11, 0.25)' : 'rgba(16, 185, 129, 0.25)'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>{config?.mock_mode ? '🟡' : '🟢'}</span>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
            {config?.mock_mode ? 'Mock Mode Enabled' : 'Live Integration Active'}
          </h3>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          {config?.mock_mode
            ? 'In Mock Mode, OAuth callbacks, encrypted token storage, and Instagram publishing simulate Meta Graph API v19.0. No live credentials or Facebook Developer App required to test the end-to-end workflow.'
            : 'Meta Graph API v19.0 configured with live credentials. Publishing creates real Instagram media containers and posts directly to your linked business account.'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        {/* Instagram Account Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 'var(--radius-md)',
                  background: 'linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.4rem',
                }}
              >
                📸
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Instagram Business</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Feed & Reels Publishing</span>
              </div>
            </div>

            <span
              className={`status-chip ${(metaStatus?.account_linked || metaStatus?.connected) ? 'status-published' : 'status-failed'}`}
            >
              {(metaStatus?.account_linked || metaStatus?.connected) ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <div
            style={{
              padding: '1rem',
              backgroundColor: 'var(--bg-main)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              marginBottom: '1.25rem',
              fontSize: '0.85rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Status:</span>
              <strong style={{ color: (metaStatus?.account_linked || metaStatus?.connected) ? 'var(--success)' : 'var(--warning)' }}>
                {(metaStatus?.account_linked || metaStatus?.connected) ? 'Linked & Active' : 'Not Connected'}
              </strong>
            </div>

            {(metaStatus?.account_linked || metaStatus?.connected) && (
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>IG User ID:</span>
                <code>{metaStatus.ig_user_id || 'Connected'}</code>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Security:</span>
              <span>Encrypted at rest (Fernet)</span>
            </div>
          </div>

          {(metaStatus?.account_linked || metaStatus?.connected) ? (
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={handleMockConnect}
                disabled={connecting || disconnecting}
              >
                {connecting ? 'Refreshing...' : '🔄 Re-link Account'}
              </button>
              <button
                className="btn btn-danger"
                style={{
                  flex: 1,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  color: '#ef4444',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  cursor: disconnecting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  padding: '0.6rem 1rem',
                  borderRadius: 'var(--radius-md, 8px)',
                  transition: 'all 0.2s ease',
                }}
                onClick={handleDisconnect}
                disabled={connecting || disconnecting}
              >
                {disconnecting ? 'Disconnecting...' : 'Disconnect Instagram'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {config?.mock_instagram ? (
                <button
                  className="btn btn-primary"
                  onClick={handleMockConnect}
                  disabled={connecting}
                >
                  {connecting ? 'Connecting...' : '🔗 Connect Mock Instagram Account'}
                </button>
              ) : (
                <button className="btn btn-primary" onClick={handleLiveConnect}>
                  🔗 Connect with Facebook Login
                </button>
              )}
            </div>
          )}
        </div>

        {/* LinkedIn Placeholder */}
        <div className="card" style={{ opacity: 0.75 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: '#0a66c2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.4rem',
                }}
              >
                💼
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>LinkedIn</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Pages & Profiles</span>
              </div>
            </div>
            <span className="status-chip status-cancelled">Roadmap</span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Multi-account company pages and personal creator updates coming soon.
          </p>

          <button className="btn btn-secondary" disabled style={{ width: '100%' }}>
            Coming Soon
          </button>
        </div>

        {/* Twitter / X Placeholder */}
        <div className="card" style={{ opacity: 0.75 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: '#000',
                  border: '1px solid #333',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.4rem',
                }}
              >
                𝕏
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Twitter / X</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Threads & Posts</span>
              </div>
            </div>
            <span className="status-chip status-cancelled">Roadmap</span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Schedule threads, tweet scheduling, and reply management.
          </p>

          <button className="btn btn-secondary" disabled style={{ width: '100%' }}>
            Coming Soon
          </button>
        </div>
      </div>

      {/* Meta App Requirements / Guide */}
      <div className="card" style={{ marginTop: '2rem' }}>
        <h3 className="card-title">⚙️ Switching to Live Meta Instagram API</h3>
        <p className="card-subtitle">
          To transition from Mock Mode to live publishing on production Instagram:
        </p>

        <ol style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.8 }}>
          <li>
            Create a Facebook App at <code style={{ color: 'var(--accent-primary)' }}>developers.facebook.com</code> with the <strong>Instagram Graph API</strong> product.
          </li>
          <li>
            Add environment variables to your <code style={{ color: 'var(--text-primary)' }}>.env</code>:
            <pre
              style={{
                backgroundColor: 'var(--bg-main)',
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                marginTop: '0.5rem',
                color: '#e2e8f0',
              }}
            >
              META_APP_ID=your_facebook_app_id{'\n'}
              META_APP_SECRET=your_facebook_app_secret{'\n'}
              META_OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback
            </pre>
          </li>
          <li>
            Add the redirect URI in the Facebook App dashboard under <strong>Valid OAuth Redirect URIs</strong>.
          </li>
          <li>
            Ensure your Instagram account is an <strong>Instagram Business or Creator</strong> account linked to a Facebook Page you manage.
          </li>
        </ol>
      </div>
    </div>
  );
}
