'use client';

import React from 'react';
import { AnalyticsData, Workspace, AppConfig } from '../types';

interface AnalyticsViewProps {
  workspace: Workspace | null;
  analytics: AnalyticsData | null;
  config: AppConfig | null;
}

export default function AnalyticsView({
  workspace,
  analytics,
  config,
}: AnalyticsViewProps) {
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Performance & Analytics</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Publishing metrics and audience reach for <strong>{workspace?.name}</strong>
        </p>
      </div>

      {/* Honest Mock Notice */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <span>📊</span>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fbbf24' }}>
            [MOCK DATA NOTICE] Real Database Counts + Simulated Reach
          </h3>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          {analytics?.note ||
            'Analytics display real counts of your scheduled posts and comments from the database. Real reach, impression, and follower analytics require Meta Graph API Insights with pages_read_engagement permissions.'}
        </p>
      </div>

      {/* Primary KPI Grid */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-info">
            <div className="stat-label">Active Schedules</div>
            <div className="stat-value">{analytics?.scheduled_posts ?? 0}</div>
            <div className="stat-hint">Verified DB count</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">💬</div>
          <div className="stat-info">
            <div className="stat-label">Total Comments</div>
            <div className="stat-value">{analytics?.total_comments ?? 0}</div>
            <div className="stat-hint">Verified DB count</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">👁️</div>
          <div className="stat-info">
            <div className="stat-label">Estimated Reach</div>
            <div className="stat-value" style={{ fontSize: '1.4rem' }}>
              {analytics?.estimated_reach || '[MOCK] 0'}
            </div>
            <div className="stat-hint">
              <span className="mode-badge mock" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                Mock
              </span>{' '}
              Simulated reach
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🔥</div>
          <div className="stat-info">
            <div className="stat-label">Avg Engagement Rate</div>
            <div className="stat-value">4.8%</div>
            <div className="stat-hint">
              <span className="mode-badge mock" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                Mock
              </span>{' '}
              Industry benchmark
            </div>
          </div>
        </div>
      </div>

      {/* Visual Analytics Sections */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Content Publishing Consistency */}
        <div className="card">
          <h3 className="card-title">📈 Publishing Velocity</h3>
          <p className="card-subtitle">Posts scheduled vs queue capacity</p>

          <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                <span>Scheduled Posts in Queue</span>
                <strong>{analytics?.scheduled_posts ?? 0} / 20 weekly target</strong>
              </div>
              <div
                style={{
                  height: 10,
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(100, ((analytics?.scheduled_posts ?? 0) / 20) * 100)}%`,
                    height: '100%',
                    backgroundColor: 'var(--accent-primary)',
                    borderRadius: 'var(--radius-full)',
                  }}
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                <span>Community Engagement Responses</span>
                <strong>{analytics?.total_comments ?? 0} comments</strong>
              </div>
              <div
                style={{
                  height: 10,
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(100, ((analytics?.total_comments ?? 0) / 10) * 100)}%`,
                    height: '100%',
                    backgroundColor: 'var(--success)',
                    borderRadius: 'var(--radius-full)',
                  }}
                />
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: '1.5rem',
              padding: '0.85rem',
              backgroundColor: 'var(--bg-main)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
            }}
          >
            💡 <strong>Pro Tip</strong>: Schedule at least 3-5 posts per week across peak hours (9:00 AM, 1:00 PM, 7:00 PM) to maximize algorithm reach.
          </div>
        </div>

        {/* Live Meta Graph Integration Roadmap */}
        <div className="card">
          <h3 className="card-title">🔌 Live Meta Insights Integration</h3>
          <p className="card-subtitle">Connecting real metrics from Instagram</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.1rem' }}>✅</span>
              <div>
                <strong>Local Queue Analytics</strong>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  Real-time database aggregation for posts, schedules, and comments.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.1rem' }}>🔒</span>
              <div>
                <strong>Meta Graph API Insights</strong>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  Requires verified Facebook App with <code>pages_read_engagement</code> and <code>instagram_basic</code>.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.1rem' }}>📈</span>
              <div>
                <strong>Reels & Story Impressions</strong>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  Tracks reach, retention, and viewer drop-off directly from Instagram CDN.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
