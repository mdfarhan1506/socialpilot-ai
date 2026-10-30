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
}

export default function TopBar({
  workspaces,
  currentWorkspace,
  onSelectWorkspace,
  onOpenCreateWorkspace,
  config,
  onOpenNewPost,
}: TopBarProps) {
  return (
    <header className="top-bar">
      <div className="top-bar-left">
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
            className={`mode-badge ${config.mock_mode ? 'mock' : 'live'}`}
            title={
              config.mock_mode
                ? 'Mock Mode: Real external API calls to OpenAI and Meta are simulated. Safe for offline development.'
                : 'Live Mode: Connected to real OpenAI and Meta Instagram APIs.'
            }
          >
            <span>{config.mock_mode ? '🟡' : '🟢'}</span>
            <span>{config.mode_label}</span>
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
