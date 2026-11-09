'use client';

import React, { useState, useEffect } from 'react';
import {
  User,
  Workspace,
  BrandProfile,
  ScheduledPost,
  AnalyticsData,
  AppConfig,
  MetaStatus,
} from '../types';
import { api } from '../services/api';
import { isDemoMode, setDemoMode } from '../services/demoService';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/TopBar';
import AuthModal from '../components/AuthModal';
import DashboardView from '../components/DashboardView';
import ContentStudioView from '../components/ContentStudioView';
import CalendarView from '../components/CalendarView';
import BrandProfilesView from '../components/BrandProfilesView';
import SocialAccountsView from '../components/SocialAccountsView';
import CommentsView from '../components/CommentsView';
import AnalyticsView from '../components/AnalyticsView';
import AutonomousCreatorView from '../components/AutonomousCreatorView';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

export default function Home() {
  // Navigation
  const [currentTab, setCurrentTab] = useState<string>('dashboard');

  // Global App States
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [config, setConfig] = useState<AppConfig | null>(null);

  // Workspaces
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [createWorkspaceModalOpen, setCreateWorkspaceModalOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');

  // Workspace Data
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [schedules, setSchedules] = useState<ScheduledPost[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [metaStatus, setMetaStatus] = useState<MetaStatus | null>(null);

  // Studio Pre-fill parameters
  const [studioInitialCaption, setStudioInitialCaption] = useState('');
  const [studioInitialDate, setStudioInitialDate] = useState<string | undefined>(undefined);

  // Toasts
  const [toasts, setToasts] = useState<Toast[]>([]);

  function addToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }

  // Initial load: config and check saved session
  useEffect(() => {
    api.getConfig().then(setConfig).catch(() => setConfig(null));

    if (isDemoMode()) {
      setIsDemo(true);
      setAuthModalOpen(false);
      api
        .getMe()
        .then((user) => {
          setCurrentUser(user);
          loadWorkspaces();
        })
        .catch(() => null);
      return;
    }

    const token = localStorage.getItem('access_token');
    if (token) {
      api
        .getMe()
        .then((user) => {
          setCurrentUser(user);
          loadWorkspaces();
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          setCurrentUser(null);
          setAuthModalOpen(true);
        });
    } else {
      setAuthModalOpen(true);
    }

    // Handle OAuth redirect query parameters (connected or error)
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const oauthError = urlParams.get('oauth_error');
      const connected = urlParams.get('connected');

      if (oauthError) {
        addToast(`Instagram connection failed: ${decodeURIComponent(oauthError)}`, 'error');
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (connected === 'instagram') {
        addToast('🎉 Instagram account successfully connected!', 'success');
        api.getMetaStatus().then(setMetaStatus).catch(() => null);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }, []);

  // Load workspaces
  async function loadWorkspaces() {
    try {
      const list = await api.listWorkspaces();
      setWorkspaces(list);
      if (list.length > 0) {
        // preserve current selection or select first
        setCurrentWorkspace((prev) => (prev ? list.find((w) => w.id === prev.id) || list[0] : list[0]));
      } else {
        // Auto prompt to create workspace if empty
        setCreateWorkspaceModalOpen(true);
      }
    } catch (err: any) {
      addToast(err.message || 'Failed to fetch workspaces', 'error');
    }
  }

  // Load workspace-scoped data
  useEffect(() => {
    if (currentWorkspace && currentUser) {
      loadWorkspaceData(currentWorkspace.id);
    }
  }, [currentWorkspace, currentUser]);

  async function loadWorkspaceData(workspaceId: string) {
    try {
      const [brandList, schedList, analData, mStatus] = await Promise.all([
        api.listBrands(workspaceId).catch(() => []),
        api.listSchedules(workspaceId).catch(() => []),
        api.getAnalytics(workspaceId).catch(() => null),
        api.getMetaStatus().catch(() => null),
      ]);
      setBrands(brandList);
      setSchedules(schedList);
      setAnalytics(analData);
      setMetaStatus(mStatus);
    } catch {
      // ignore
    }
  }

  // Auth success handler
  function handleAuthSuccess() {
    setAuthModalOpen(false);
    api
      .getMe()
      .then((user) => {
        setCurrentUser(user);
        loadWorkspaces();
      })
      .catch((err) => addToast(err.message, 'error'));
  }

  // Sign out
  function handleLogout() {
    setDemoMode(false);
    setIsDemo(false);
    localStorage.removeItem('access_token');
    setCurrentUser(null);
    setCurrentWorkspace(null);
    setWorkspaces([]);
    setBrands([]);
    setSchedules([]);
    setAnalytics(null);
    setAuthModalOpen(true);
    addToast('Logged out', 'info');
  }

  // Enter Demo Mode handler
  function handleEnterDemo() {
    setDemoMode(true);
    setIsDemo(true);
    setAuthModalOpen(false);
    addToast('Entered Demo Mode with sample brand "Urban Threads". Simulated session active.', 'info');
    api
      .getMe()
      .then((user) => {
        setCurrentUser(user);
        loadWorkspaces();
      })
      .catch((err) => addToast(err.message, 'error'));
  }

  // Create Workspace
  async function handleCreateWorkspaceSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    try {
      const created = await api.createWorkspace(newWorkspaceName.trim());
      addToast(`Workspace "${created.name}" created!`, 'success');
      setNewWorkspaceName('');
      setCreateWorkspaceModalOpen(false);
      await loadWorkspaces();
      setCurrentWorkspace(created);
    } catch (err: any) {
      addToast(err.message || 'Failed to create workspace', 'error');
    }
  }

  // Cancel Scheduled Post
  async function handleCancelPost(postId: string) {
    if (!confirm('Are you sure you want to cancel this scheduled post?')) return;
    try {
      await api.cancelSchedule(postId);
      addToast('Post schedule cancelled', 'info');
      if (currentWorkspace) loadWorkspaceData(currentWorkspace.id);
    } catch (err: any) {
      addToast(err.message || 'Failed to cancel schedule', 'error');
    }
  }

  // Quick navigation helpers
  function openStudioForDate(dateStr: string) {
    setStudioInitialDate(dateStr);
    setCurrentTab('studio');
  }

  function handleSelectBrandForStudio(brand: BrandProfile) {
    setCurrentTab('studio');
    addToast(`Selected brand "${brand.niche}" for Content Studio`, 'info');
  }

  return (
    <div className="app-container">
      {/* Toast Alert System */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span>
              {t.type === 'success' ? '✅' : t.type === 'error' ? '⚠️' : 'ℹ️'}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onSuccess={handleAuthSuccess}
        onEnterDemo={handleEnterDemo}
        onToast={addToast}
      />

      {/* Create Workspace Modal */}
      {createWorkspaceModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Create Workspace</h3>
              {workspaces.length > 0 && (
                <button
                  className="close-btn"
                  onClick={() => setCreateWorkspaceModalOpen(false)}
                >
                  ✕
                </button>
              )}
            </div>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.25rem' }}>
              Workspaces isolate your brand profiles, post schedules, and analytics for each client or project.
            </p>

            <form onSubmit={handleCreateWorkspaceSubmit}>
              <div className="form-group">
                <label className="form-label">Workspace Name</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Acme Marketing, Personal Brand, Startup Growth"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                {workspaces.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ flex: 1 }}
                    onClick={() => setCreateWorkspaceModalOpen(false)}
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  Create Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => {
          setCurrentTab(tab);
          setMobileMenuOpen(false);
        }}
        currentUser={currentUser}
        onLogout={handleLogout}
        isOpenMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        {/* Persistent Demo Mode Banner */}
        {isDemo && (
          <div className="demo-banner">
            <div className="demo-banner-content">
              <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>⚠️</span>
              <span>
                <strong>DEMO MODE — You are viewing simulated data.</strong> Real publishing, live Meta API calls, and external credits are completely disabled.
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="demo-exit-btn"
            >
              Exit Demo
            </button>
          </div>
        )}

        <TopBar
          workspaces={workspaces}
          currentWorkspace={currentWorkspace}
          onSelectWorkspace={setCurrentWorkspace}
          onOpenCreateWorkspace={() => setCreateWorkspaceModalOpen(true)}
          config={config}
          metaStatus={metaStatus}
          onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
          onOpenNewPost={() => {
            setStudioInitialCaption('');
            setStudioInitialDate(undefined);
            setCurrentTab('studio');
          }}
        />

        <main className="content-body">
          {currentTab === 'dashboard' && (
            <DashboardView
              workspace={currentWorkspace}
              brands={brands}
              schedules={schedules}
              analytics={analytics}
              metaStatus={metaStatus}
              config={config}
              onNavigate={setCurrentTab}
              onCancelPost={handleCancelPost}
            />
          )}

          {currentTab === 'autonomous' && (
            <AutonomousCreatorView
              workspace={currentWorkspace}
              config={config}
              metaStatus={metaStatus}
              onToast={addToast}
            />
          )}

          {currentTab === 'studio' && (
            <ContentStudioView
              workspace={currentWorkspace}
              brands={brands}
              config={config}
              metaStatus={metaStatus}
              initialCaption={studioInitialCaption}
              initialDate={studioInitialDate}
              onPostCreated={() => {
                if (currentWorkspace) loadWorkspaceData(currentWorkspace.id);
                setCurrentTab('calendar');
              }}
              onToast={addToast}
            />
          )}

          {currentTab === 'calendar' && (
            <CalendarView
              workspace={currentWorkspace}
              schedules={schedules}
              onOpenScheduleForDate={openStudioForDate}
              onCancelPost={handleCancelPost}
              onToast={addToast}
            />
          )}

          {currentTab === 'brands' && (
            <BrandProfilesView
              workspace={currentWorkspace}
              brands={brands}
              onRefresh={() => {
                if (currentWorkspace) loadWorkspaceData(currentWorkspace.id);
              }}
              onSelectBrandForStudio={handleSelectBrandForStudio}
              onToast={addToast}
            />
          )}

          {currentTab === 'accounts' && (
            <SocialAccountsView
              metaStatus={metaStatus}
              config={config}
              onRefreshStatus={() => {
                if (currentWorkspace) loadWorkspaceData(currentWorkspace.id);
              }}
              onToast={addToast}
            />
          )}

          {currentTab === 'comments' && (
            <CommentsView
              workspace={currentWorkspace}
              schedules={schedules}
              onToast={addToast}
            />
          )}

          {currentTab === 'analytics' && (
            <AnalyticsView
              workspace={currentWorkspace}
              analytics={analytics}
              config={config}
            />
          )}
        </main>
      </div>
    </div>
  );
}
