'use client';

import React from 'react';
import { Workspace, AppConfig } from '../types';

interface TopBarProps {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  onSelectWorkspace: (workspace: Workspace) => void;
  onOpenCreateWorkspace: () => void;
  config: AppConfig | null;
  onOpenNewPost: () => void;
  metaStatus?: { connected?: boolean; is_expired?: boolean } | null;
  onToggleMobileMenu?: () => void;
}

export default function TopBar({
  workspaces,
  currentWorkspace,
  onSelectWorkspace,
  onOpenCreateWorkspace,
  config,
  onOpenNewPost,
  metaStatus,
  onToggleMobileMenu,
}: TopBarProps) {
  // LIVE MODE = openai_configured AND meta token valid AND NOT mock_mode
  const metaTokenValid = Boolean(metaStatus?.connected && !metaStatus?.is_expired);
  const isFullyLive = !config?.mock_mode && config?.openai_configured && metaTokenValid;
  const setupIssues: string[] = [];
  if (config && !config.mock_mode) {
    if (!config.openai_configured) setupIssues.push('AI key missing');
    if (!metaTokenValid) setupIssues.push('Instagram not connected');
  }
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        {onToggleMobileMenu && (
          <button
            className="hamburger-btn"
            onClick={onToggleMobileMenu}
            aria-label="Toggle Navigation Menu"
          >
            ☰
          </button>
        )}
        <div className="workspace-select-wrapper">
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Workspace:</span>
          {workspaces.length > 0 ? (
            <select
              className="form-select"
              style={{ width: 'auto', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
              value={currentWorkspace?.id || ''}
              onChange={(e) => {
                const found = workspaces.find((w) => w.id === e.target.value);
                if (found) onSelectWorkspace(found);
              }}
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name}
                </option>
              ))}
            </select>
          ) : (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              No workspaces yet
            </span>
          )}
          <button
            className="btn btn-sm btn-secondary"
            onClick={onOpenCreateWorkspace}
            title="Create Workspace"
          >
            + New
          </button>
        </div>
      </div>

      <div className="top-bar-right">
        {config && (
          <div
            className={`mode-badge ${config.mock_mode ? 'mock' : (isFullyLive ? 'live' : 'mock')}`}
            title={
              config.mock_mode
                ? 'Mock Mode: Real API calls are simulated.'
                : isFullyLive
                  ? 'Live Mode: Connected to real OpenAI and Meta Instagram APIs.'
                  : `Setup Incomplete: ${setupIssues.join(', ')}`
            }
          >
            <span>{config.mock_mode ? '🟡' : (isFullyLive ? '🟢' : '🟠')}</span>
            <span>
              {config.mock_mode
                ? config.mode_label
                : isFullyLive
                  ? 'Live Mode'
                  : `Setup Incomplete`}
            </span>
          </div>
        )}

        <button className="btn btn-primary" onClick={onOpenNewPost}>
          <span>✍️</span>
          <span>Create Post</span>
        </button>
      </div>
    </header>
  );
}
