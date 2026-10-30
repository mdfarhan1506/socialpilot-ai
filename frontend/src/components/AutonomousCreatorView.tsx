'use client';

import React, { useState, useEffect } from 'react';
import {
  Workspace,
  AutonomousConfig,
  StrategyInsight,
  AutomationAuditLog,
  AutonomousPlanPost,
  AppConfig,
  MetaStatus,
} from '../types';
import { api } from '../services/api';

interface AutonomousCreatorViewProps {
  workspace: Workspace | null;
  config: AppConfig | null;
  metaStatus: MetaStatus | null;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function AutonomousCreatorView({
  workspace,
  config,
  metaStatus,
  onToast,
}: AutonomousCreatorViewProps) {
  const [autoConfig, setAutoConfig] = useState<AutonomousConfig | null>(null);
  const [insights, setInsights] = useState<StrategyInsight[]>([]);
  const [planPosts, setPlanPosts] = useState<AutonomousPlanPost[]>([]);
  const [auditLogs, setAuditLogs] = useState<AutomationAuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [runningLoop, setRunningLoop] = useState(false);

  // Settings modal
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [minPosts, setMinPosts] = useState(1);
  const [maxPosts, setMaxPosts] = useState(3);
  const [quietStart, setQuietStart] = useState(22);
  const [quietEnd, setQuietEnd] = useState(7);
  const [keywordsInput, setKeywordsInput] = useState('');
  const [approvalMode, setApprovalMode] = useState('manual_for_sensitive');
  const [savingSettings, setSavingSettings] = useState(false);

  // Filter tabs for plan
  const [planTab, setPlanTab] = useState<'all' | 'pending_approval'>('all');

  useEffect(() => {
    if (workspace) {
      loadAllData();
    }
  }, [workspace]);

  async function loadAllData() {
    if (!workspace) return;
    setLoading(true);
    try {
      const [c, ins, pl, logs] = await Promise.all([
        api.getAutonomousConfig(workspace.id).catch(() => null),
        api.getAutonomousInsights(workspace.id).catch(() => []),
        api.getAutonomousPlan(workspace.id).catch(() => []),
        api.getAutonomousAuditLogs(workspace.id).catch(() => []),
      ]);
      if (c) {
        setAutoConfig(c);
        setMinPosts(c.min_posts_per_day);
        setMaxPosts(c.max_posts_per_day);
        setQuietStart(c.quiet_hours_start);
        setQuietEnd(c.quiet_hours_end);
        setKeywordsInput((c.restricted_keywords || []).join(', '));
        setApprovalMode(c.approval_mode);
      }
      setInsights(ins);
      setPlanPosts(pl);
      setAuditLogs(logs);
    } catch (err: any) {
      onToast(err.message || 'Failed to load autonomous creator data', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function togglePauseResume() {
    if (!workspace || !autoConfig) return;
    try {
      if (autoConfig.is_active) {
        await api.pauseAutonomous(workspace.id);
        onToast('Autonomous Creator Paused', 'info');
      } else {
        await api.resumeAutonomous(workspace.id);
        onToast('Autonomous Creator Resumed', 'success');
      }
      loadAllData();
    } catch (err: any) {
      onToast(err.message || 'Failed to update automation state', 'error');
    }
  }

  async function handleTriggerCycle() {
    if (!workspace) return;
    setRunningLoop(true);
    try {
      const res = await api.runAutonomousCycle(workspace.id);
      onToast(
        `Autonomous cycle executed! ${res.new_posts_planned || 0} posts planned, ${res.observations_ingested || 0} observations ingested.`,
        'success'
      );
      loadAllData();
    } catch (err: any) {
      onToast(err.message || 'Failed to trigger autonomous loop', 'error');
    } finally {
      setRunningLoop(false);
    }
  }

  async function handleApprovePost(postId: string) {
    try {
      await api.approvePost(postId);
      onToast('Post approved and added to publishing queue!', 'success');
      loadAllData();
    } catch (err: any) {
      onToast(err.message || 'Approval failed', 'error');
    }
  }

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    if (!workspace) return;
    setSavingSettings(true);
    try {
      const keywords = keywordsInput
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);

      await api.updateAutonomousConfig({
        workspace_id: workspace.id,
        min_posts_per_day: minPosts,
        max_posts_per_day: maxPosts,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        restricted_keywords: keywords,
        approval_mode: approvalMode,
      });
      onToast('Autonomous policies updated!', 'success');
      setShowSettingsModal(false);
      loadAllData();
    } catch (err: any) {
      onToast(err.message || 'Failed to save settings', 'error');
    } finally {
      setSavingSettings(false);
    }
  }

  const pendingApprovals = planPosts.filter((p) => p.requires_approval || p.status === 'pending_approval');
  const displayedPosts = planTab === 'pending_approval' ? pendingApprovals : planPosts;

  return (
    <div>
      {/* Top Banner / Controls */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderLeft: `4px solid ${autoConfig?.is_active ? 'var(--accent-primary)' : 'var(--warning)'}`,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.4rem' }}>🤖</span>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Autonomous Creator Manager</h1>
            <span
              className={`status-chip ${autoConfig?.is_active ? 'status-published' : 'status-cancelled'}`}
            >
              {autoConfig?.is_active ? '● Running Continuously' : '⏸️ Automation Paused'}
            </span>
            <span className={`mode-badge ${config?.mock_mode ? 'mock' : 'live'}`}>
              {config?.mock_mode ? 'Simulated Execution [MOCK]' : 'Live Execution [META/OPENAI]'}
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.35rem' }}>
            Persistent orchestration: trend ingestion, rolling 3-7 day planning, hook synthesis, policy screening, and feedback iteration.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className={`btn ${autoConfig?.is_active ? 'btn-danger' : 'btn-success'}`}
            onClick={togglePauseResume}
          >
            {autoConfig?.is_active ? '⏸️ Pause Automation' : '▶️ Resume Automation'}
          </button>

          <button
            className="btn btn-primary"
            onClick={handleTriggerCycle}
            disabled={runningLoop || !autoConfig?.is_active}
          >
            {runningLoop ? 'Orchestrating...' : '⚡ Trigger Loop Now'}
          </button>

          <button className="btn btn-secondary" onClick={() => setShowSettingsModal(true)}>
            ⚙️ Policies
          </button>
        </div>
      </div>

      {/* Grid: Current Strategy & Policy Rules */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.1fr 0.9fr',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        {/* Strategy & Learning Insights */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🧠</span>
              <h3 className="card-title" style={{ margin: 0 }}>Active Strategy & Learned Hypotheses</h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Data Provenance: {config?.mock_mode ? 'Simulated' : 'Verified Live'}
            </span>
          </div>

          {insights.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <p>No strategy hypotheses generated yet.</p>
              <button
                className="btn btn-sm btn-primary"
                style={{ marginTop: '0.75rem' }}
                onClick={handleTriggerCycle}
                disabled={runningLoop}
              >
                Synthesize First Strategy Cycle
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {insights.slice(0, 3).map((ins) => (
                <div
                  key={ins.id}
                  style={{
                    padding: '0.85rem',
                    backgroundColor: 'var(--bg-main)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-primary)' }}>
                      {ins.topic}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Confidence: {Math.round(ins.confidence_score * 100)}%
                    </span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                    💡 <em>&quot;{ins.hypothesis}&quot;</em>
                  </p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    🎯 <strong>Action:</strong> {ins.recommendation}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Policy Guardrails & Restrictions */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🛡️</span>
              <h3 className="card-title" style={{ margin: 0 }}>Policy Guardrails & Limits</h3>
            </div>
            <button className="btn btn-sm btn-secondary" onClick={() => setShowSettingsModal(true)}>
              Edit Rules
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border-color)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Adaptive Frequency</span>
              <strong>{autoConfig?.min_posts_per_day || 1} to {autoConfig?.max_posts_per_day || 3} posts/day</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border-color)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Quiet Hours (Zero Publishing)</span>
              <strong>{autoConfig?.quiet_hours_start || 22}:00 to {autoConfig?.quiet_hours_end || 7}:00 UTC</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border-color)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Approval Mode</span>
              <strong style={{ textTransform: 'capitalize' }}>
                {autoConfig?.approval_mode.replace('_', ' ') || 'Manual For Sensitive'}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0' }}>
              <span style={{ color: 'var(--text-muted)' }}>Prohibited Word Filter</span>
              <span>
                {(autoConfig?.restricted_keywords || []).length} keywords configured
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Rolling Content Plan & Approval Queue */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 className="card-title" style={{ margin: 0 }}>
              📅 Autonomous Rolling Content Plan (Next 3-7 Days)
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
              Synthesized platform-ready content: Hook, Script, Caption, CTA, and Validated Media.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className={`btn btn-sm ${planTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setPlanTab('all')}
            >
              All Planned ({planPosts.length})
            </button>
            <button
              className={`btn btn-sm ${planTab === 'pending_approval' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setPlanTab('pending_approval')}
            >
              Needs Approval ({pendingApprovals.length})
            </button>
          </div>
        </div>

        {displayedPosts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📭</div>
            <p>No planned posts matching filter.</p>
            <button
              className="btn btn-sm btn-primary"
              style={{ marginTop: '0.75rem' }}
              onClick={handleTriggerCycle}
              disabled={runningLoop}
            >
              ⚡ Run Autonomous Generation
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
            {displayedPosts.map((post) => (
              <div
                key={post.id}
                style={{
                  padding: '1.25rem',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${post.requires_approval ? 'var(--warning)' : 'var(--border-color)'}`,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span
                    className={`status-chip ${
                      post.requires_approval ? 'status-failed' : 'status-scheduled'
                    }`}
                  >
                    {post.requires_approval ? '⚠️ Needs Approval' : 'Scheduled'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    🕒 {new Date(post.scheduled_time).toLocaleString()}
                  </span>
                </div>

                {post.concept && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600, marginBottom: '0.4rem' }}>
                    Concept: {post.concept}
                  </div>
                )}

                {post.hook && (
                  <div style={{ padding: '0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                    <strong>🪝 Hook:</strong> {post.hook}
                  </div>
                )}

                <p
                  style={{
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                    marginBottom: '0.75rem',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {post.caption}
                </p>

                {post.call_to_action && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                    <strong>CTA:</strong> {post.call_to_action}
                  </div>
                )}

                <div style={{ marginTop: 'auto', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {post.image_url ? '🖼️ Media Validated' : '📝 Text Asset'}
                  </span>

                  {post.requires_approval && (
                    <button
                      className="btn btn-sm btn-success"
                      onClick={() => handleApprovePost(post.id)}
                    >
                      ✅ Approve Post
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Automation Activity & Audit Trail */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>📜</span>
            <h3 className="card-title" style={{ margin: 0 }}>Automation Activity & Audit Trail</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Last {auditLogs.length} autonomous events
          </span>
        </div>

        {auditLogs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
            No audit log entries recorded yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
            {auditLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span
                    className={`status-chip ${
                      log.status === 'success' ? 'status-published' : log.status === 'blocked' ? 'status-failed' : 'status-scheduled'
                    }`}
                  >
                    {log.action}
                  </span>
                  <span>{log.summary}</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">⚙️ Autonomous Policy Settings</h3>
              <button className="close-btn" onClick={() => setShowSettingsModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveSettings}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Min Posts / Day</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    className="form-input"
                    value={minPosts}
                    onChange={(e) => setMinPosts(parseInt(e.target.value) || 1)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Max Posts / Day</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    className="form-input"
                    value={maxPosts}
                    onChange={(e) => setMaxPosts(parseInt(e.target.value) || 3)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Quiet Hours Start (UTC)</label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="form-input"
                    value={quietStart}
                    onChange={(e) => setQuietStart(parseInt(e.target.value) || 0)}
                  />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>e.g. 22 for 10:00 PM</span>
                </div>

                <div className="form-group">
                  <label className="form-label">Quiet Hours End (UTC)</label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="form-input"
                    value={quietEnd}
                    onChange={(e) => setQuietEnd(parseInt(e.target.value) || 0)}
                  />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>e.g. 7 for 7:00 AM</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Approval Policy</label>
                <select
                  className="form-select"
                  value={approvalMode}
                  onChange={(e) => setApprovalMode(e.target.value)}
                >
                  <option value="manual_for_sensitive">Manual Approval for Sensitive/Flagged Content</option>
                  <option value="auto">Fully Autonomous (Auto-Publish All Safe Content)</option>
                  <option value="manual">Require Manual Approval for Every Post</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Prohibited Keywords (comma separated)</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="e.g. controversial, guaranteed returns, secret trick, unverified"
                  value={keywordsInput}
                  onChange={(e) => setKeywordsInput(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setShowSettingsModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={savingSettings}
                >
                  {savingSettings ? 'Saving...' : 'Save Policies'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
