'use client';

import React from 'react';
import { User } from '../types';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  currentUser: User | null;
  onLogout: () => void;
}

export default function Sidebar({
  currentTab,
  onTabChange,
  currentUser,
  onLogout,
}: SidebarProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'studio', label: 'Content Studio', icon: '✨' },
    { id: 'calendar', label: 'Content Calendar', icon: '📅' },
    { id: 'brands', label: 'Brand Profiles', icon: '🎨' },
    { id: 'accounts', label: 'Social Accounts', icon: '🔗' },
    { id: 'comments', label: 'Community & Comments', icon: '💬' },
    { id: 'analytics', label: 'Analytics', icon: '📈' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-logo">SP</div>
        <div className="brand-title">SocialPilot AI</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        {currentUser ? (
          <div className="user-profile-badge">
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Signed in as</span>
              <span className="user-email-text" title={currentUser.email}>
                {currentUser.email}
              </span>
            </div>
            <button
              className="btn btn-sm btn-secondary"
              onClick={onLogout}
              title="Sign Out"
              style={{ padding: '0.2rem 0.5rem' }}
            >
              🚪
            </button>
          </div>
        ) : (
          <button className="btn btn-primary" style={{ width: '100%' }}>
            Sign In
          </button>
        )}
      </div>
    </aside>
  );
}
