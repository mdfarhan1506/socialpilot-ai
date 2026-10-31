'use client';

import React from 'react';
import {
  Workspace,
  BrandProfile,
  ScheduledPost,
  AnalyticsData,
  MetaStatus,
  AppConfig,
} from '../types';

interface DashboardViewProps {
  workspace: Workspace | null;
  brands: BrandProfile[];
  schedules: ScheduledPost[];
  analytics: AnalyticsData | null;
  metaStatus: MetaStatus | null;
  config: AppConfig | null;
  onNavigate: (tab: string) => void;
  onCancelPost: (id: string) => void;
}

export default function DashboardView({
  workspace,
  brands,
  schedules,
  analytics,
  metaStatus,
  config,
  onNavigate,
  onCancelPost,
}: DashboardViewProps) {
  const activeSchedules = schedules.filter((s) => s.status === 'scheduled');
  const pastPosts = schedules.filter((s) => s.status === 'published' || s.status === 'cancelled');

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Workspace Dashboard</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Overview for <strong>{workspace?.name || 'Workspace'}</strong> • AI content generation & social management
        </p>
      </div>

      {/* Account Connection Status Alert */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderLeft: `4px solid ${(metaStatus?.account_linked || metaStatus?.connected) ? 'var(--success)' : 'var(--warning)'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ fontSize: '2rem' }}>📸</div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Instagram Connection</h3>
              <span
                className={`status-chip ${(metaStatus?.account_linked || metaStatus?.connected) ? 'status-published' : 'status-failed'}`}
              >
                {(metaStatus?.account_linked || metaStatus?.connected) ? 'Connected' : 'Not Connected'}
              </span>
              {metaStatus?.mock_mode && (
                <span className="mode-badge mock" style={{ fontSize: '0.7rem' }}>
                  Mock Mode Active
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {(metaStatus?.account_linked || metaStatus?.connected)
                ? `Linked IG User ID: ${metaStatus.ig_user_id || 'Connected'} • Ready for scheduled & instant publishing`
                : 'Connect your Instagram account to enable automated post publishing and feed management.'}
            </p>
          </div>
        </div>

        <button
          className={`btn ${(metaStatus?.account_linked || metaStatus?.connected) ? 'btn-secondary' : 'btn-primary'}`}
          onClick={() => onNavigate('accounts')}
        >
          {(metaStatus?.account_linked || metaStatus?.connected) ? 'Manage Account' : 'Connect Instagram'}
        </button>
      </div>

      {/* Overview Stat Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-info">
            <div className="stat-label">Scheduled Posts</div>
            <div className="stat-value">{activeSchedules.length}</div>
            <div className="stat-hint">In queue for publishing</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎨</div>
          <div className="stat-info">
            <div className="stat-label">Brand Profiles</div>
            <div className="stat-value">{brands.length}</div>
            <div className="stat-hint">Target voices configured</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-info">
            <div className="stat-label">Community Comments</div>
            <div className="stat-value">{analytics?.total_comments ?? 0}</div>
            <div className="stat-hint">Audience responses</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🚀</div>
          <div className="stat-info">
            <div className="stat-label">Estimated Reach</div>
            <div className="stat-value" style={{ fontSize: '1.3rem' }}>
              {analytics?.estimated_reach || '[MOCK] 0'}
            </div>
            <div className="stat-hint">
              {config?.mock_mode ? 'Mock simulated reach' : 'Meta Graph Analytics'}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Launch Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        <div className="card" style={{ border: '1px solid var(--accent-primary)', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.08))' }}>
          <h3 className="card-title">🤖 Autonomous Creator</h3>
          <p className="card-subtitle">
            Persistent orchestration: rolling plans, hook synthesis, policy screening, and adaptive publishing.
          </p>
          <button className="btn btn-primary" onClick={() => onNavigate('autonomous')}>
            Manage Autonomous Creator &rarr;
          </button>
        </div>

        <div className="card">
          <h3 className="card-title">✨ Content Studio</h3>
          <p className="card-subtitle">
            Generate viral captions, select hashtags, and draft multi-platform posts using AI prompts.
          </p>
          <button className="btn btn-secondary" onClick={() => onNavigate('studio')}>
            Open Content Studio &rarr;
          </button>
        </div>

        <div className="card">
          <h3 className="card-title">📅 Content Calendar</h3>
          <p className="card-subtitle">
            View upcoming schedule on a monthly calendar, reschedule posts, or fill empty publishing slots.
          </p>
          <button className="btn btn-secondary" onClick={() => onNavigate('calendar')}>
            View Publishing Calendar &rarr;
          </button>
        </div>
      </div>

      {/* Two Column Section: Upcoming Scheduled & Recent History */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Upcoming Scheduled Posts */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="card-title" style={{ margin: 0 }}>Upcoming Scheduled Posts</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {activeSchedules.length} queued
            </span>
          </div>

          {activeSchedules.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
              <p>No posts scheduled yet.</p>
              <button
                className="btn btn-sm btn-primary"
                style={{ marginTop: '0.75rem' }}
                onClick={() => onNavigate('studio')}
              >
                Draft New Post
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {activeSchedules.map((post) => (
                <div
                  key={post.id}
                  style={{
                    padding: '0.85rem',
                    backgroundColor: 'var(--bg-main)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span className="status-chip status-scheduled">Scheduled</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      🕒 {new Date(post.scheduled_time).toLocaleString()}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: 'var(--text-primary)',
                      marginBottom: '0.5rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {post.caption}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {post.image_url ? '🖼️ Has Image' : '📝 Text Only'}
                    </span>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => onCancelPost(post.id)}
                    >
                      Cancel Post
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity / Published Posts */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="card-title" style={{ margin: 0 }}>Recent Publishing History</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {pastPosts.length} posts
            </span>
          </div>

          {pastPosts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🕰️</div>
              <p>No past publishing activity yet.</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Posts that reach their scheduled time or get cancelled appear here.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {pastPosts.slice(0, 5).map((post) => (
                <div
                  key={post.id}
                  style={{
                    padding: '0.85rem',
                    backgroundColor: 'var(--bg-main)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span
                      className={`status-chip ${
                        post.status === 'published' ? 'status-published' : 'status-cancelled'
                      }`}
                    >
                      {post.status}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(post.scheduled_time).toLocaleDateString()}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: '0.85rem',
                      color: 'var(--text-secondary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {post.caption}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
