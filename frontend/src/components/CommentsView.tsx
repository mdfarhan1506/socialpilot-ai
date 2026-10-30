'use client';

import React, { useState, useEffect } from 'react';
import { CommentItem, Workspace, ScheduledPost } from '../types';
import { api } from '../services/api';

interface CommentsViewProps {
  workspace: Workspace | null;
  schedules: ScheduledPost[];
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function CommentsView({
  workspace,
  schedules,
  onToast,
}: CommentsViewProps) {
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [author, setAuthor] = useState('');
  const [text, setText] = useState('');
  const [selectedPostId, setSelectedPostId] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (workspace) {
      loadComments();
    }
  }, [workspace, selectedPostId]);

  async function loadComments() {
    if (!workspace) return;
    setLoading(true);
    try {
      const data = await api.listComments(workspace.id, selectedPostId || undefined);
      setComments(data);
    } catch (err: any) {
      onToast(err.message || 'Failed to load comments', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateComment(e: React.FormEvent) {
    e.preventDefault();
    if (!workspace) return;
    if (!text.trim()) return;

    setSubmitting(true);
    try {
      await api.createComment({
        workspace_id: workspace.id,
        post_id: selectedPostId || undefined,
        author: author.trim() || undefined,
        text: text.trim(),
      });
      onToast('Comment added to workspace feed!', 'success');
      setText('');
      loadComments();
    } catch (err: any) {
      onToast(err.message || 'Failed to add comment', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Community & Comments</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Monitor comments across your published and scheduled posts.
        </p>
      </div>

      {/* Honest Mock Notice */}
      <div
        className="card"
        style={{
          marginBottom: '2rem',
          backgroundColor: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <span>💬</span>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
            [MOCK COMMUNITY FEED] Local Database Storage
          </h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Comments are stored securely in your workspace database. When Meta Instagram API credentials with the <code>pages_read_engagement</code> permission are linked, live incoming comments will synchronize automatically.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '2rem' }}>
        {/* Comments Feed */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 className="card-title" style={{ margin: 0 }}>Workspace Comments ({comments.length})</h3>

            {schedules.length > 0 && (
              <select
                className="form-select"
                style={{ width: 'auto', padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
                value={selectedPostId}
                onChange={(e) => setSelectedPostId(e.target.value)}
              >
                <option value="">All Posts</option>
                {schedules.map((p) => (
                  <option key={p.id} value={p.id}>
                    Post: {p.caption.slice(0, 25)}...
                  </option>
                ))}
              </select>
            )}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Loading comments...
            </div>
          ) : comments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💬</div>
              <p>No comments in this workspace yet.</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Use the form on the right to simulate an audience response or test moderation.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {comments.map((c) => (
                <div
                  key={c.id}
                  style={{
                    padding: '1rem',
                    backgroundColor: 'var(--bg-main)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: '50%',
                          backgroundColor: 'var(--accent-primary)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: '#fff',
                        }}
                      >
                        {(c.author || 'U')[0].toUpperCase()}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                        {c.author || 'Anonymous User'}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', paddingLeft: '2.25rem' }}>
                    {c.text}
                  </p>

                  {c.post_id && (
                    <div style={{ paddingLeft: '2.25rem', marginTop: '0.5rem' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Linked to Post ID: <code>{c.post_id.slice(0, 8)}...</code>
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add / Simulate Comment Form */}
        <div className="card">
          <h3 className="card-title">✍️ Simulate Audience Comment</h3>
          <p className="card-subtitle">
            Post a test comment to test reply notifications and engagement analytics.
          </p>

          <form onSubmit={handleCreateComment}>
            <div className="form-group">
              <label className="form-label">Author Name / Handle</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. @sarah_designs, TechFan99"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Target Post (Optional)</label>
              <select
                className="form-select"
                value={selectedPostId}
                onChange={(e) => setSelectedPostId(e.target.value)}
              >
                <option value="">General Workspace Feed</option>
                {schedules.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.caption.slice(0, 30)}...
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Comment Message</label>
              <textarea
                className="form-textarea"
                rows={4}
                required
                placeholder="e.g. Loved this insight! How do you handle scheduling across timezones?"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Post Test Comment'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
