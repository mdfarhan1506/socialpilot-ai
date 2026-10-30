'use client';

import React, { useState } from 'react';
import { ScheduledPost, Workspace } from '../types';

interface CalendarViewProps {
  workspace: Workspace | null;
  schedules: ScheduledPost[];
  onOpenScheduleForDate: (dateStr: string) => void;
  onCancelPost: (postId: string) => void;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function CalendarView({
  workspace,
  schedules,
  onOpenScheduleForDate,
  onCancelPost,
  onToast,
}: CalendarViewProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedPost, setSelectedPost] = useState<ScheduledPost | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Navigation
  function prevMonth() {
    setCurrentDate(new Date(year, month - 1, 1));
  }

  function nextMonth() {
    setCurrentDate(new Date(year, month + 1, 1));
  }

  function goToday() {
    setCurrentDate(new Date());
  }

  // Days calculations
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const firstDayIndex = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  // Map posts to YYYY-MM-DD
  const postsByDate: Record<string, ScheduledPost[]> = {};
  schedules.forEach((post) => {
    try {
      const d = new Date(post.scheduled_time);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
        d.getDate()
      ).padStart(2, '0')}`;
      if (!postsByDate[key]) postsByDate[key] = [];
      postsByDate[key].push(post);
    } catch {
      // ignore
    }
  });

  // Calendar cells
  const cells: { day: number; isCurrentMonth: boolean; dateKey: string }[] = [];

  // Previous month trailing days
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    const d = daysInPrevMonth - i;
    const prevM = month === 0 ? 12 : month;
    const prevY = month === 0 ? year - 1 : year;
    const dateKey = `${prevY}-${String(prevM).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({ day: d, isCurrentMonth: false, dateKey });
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({ day: d, isCurrentMonth: true, dateKey });
  }

  // Next month leading days (to complete 35 or 42 cells)
  const remainingCells = 42 - cells.length;
  for (let d = 1; d <= remainingCells; d++) {
    const nextM = month === 11 ? 1 : month + 2;
    const nextY = month === 11 ? year + 1 : year;
    const dateKey = `${nextY}-${String(nextM).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({ day: d, isCurrentMonth: false, dateKey });
  }

  const todayStr = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(
    2,
    '0'
  )}-${String(new Date().getDate()).padStart(2, '0')}`;

  return (
    <div>
      {/* Calendar Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>
            {monthNames[month]} {year}
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Content publishing schedule for <strong>{workspace?.name}</strong>
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={goToday}>
            Today
          </button>
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            <button className="btn btn-secondary btn-sm" onClick={prevMonth}>
              ◀
            </button>
            <button className="btn btn-secondary btn-sm" onClick={nextMonth}>
              ▶
            </button>
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onOpenScheduleForDate(todayStr)}
          >
            + New Post
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="calendar-grid">
        {daysOfWeek.map((day) => (
          <div key={day} className="calendar-header-day">
            {day}
          </div>
        ))}

        {cells.map((cell, idx) => {
          const isToday = cell.dateKey === todayStr;
          const dayPosts = postsByDate[cell.dateKey] || [];

          return (
            <div
              key={idx}
              className={`calendar-cell ${!cell.isCurrentMonth ? 'other-month' : ''} ${
                isToday ? 'today' : ''
              }`}
            >
              <div className="calendar-day-num">
                <span style={{ color: isToday ? 'var(--accent-primary)' : 'inherit' }}>
                  {cell.day}
                </span>
                {cell.isCurrentMonth && (
                  <button
                    onClick={() => onOpenScheduleForDate(cell.dateKey)}
                    title="Schedule post for this day"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                    }}
                  >
                    +
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', overflowY: 'auto' }}>
                {dayPosts.map((post) => (
                  <div
                    key={post.id}
                    className="calendar-post-badge"
                    onClick={() => setSelectedPost(post)}
                    title={post.caption}
                  >
                    <span style={{ fontWeight: 600 }}>
                      {new Date(post.scheduled_time).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>{' '}
                    • {post.caption.slice(0, 20)}...
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Post Details Modal */}
      {selectedPost && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Post Details</h3>
              <button className="close-btn" onClick={() => setSelectedPost(null)}>
                ✕
              </button>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span className={`status-chip status-${selectedPost.status}`}>
                  {selectedPost.status}
                </span>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Scheduled: {new Date(selectedPost.scheduled_time).toLocaleString()}
                </span>
              </div>

              {selectedPost.image_url && (
                <div
                  style={{
                    width: '100%',
                    height: '200px',
                    borderRadius: 'var(--radius-md)',
                    overflow: 'hidden',
                    marginBottom: '1rem',
                    backgroundColor: '#000',
                  }}
                >
                  <img
                    src={selectedPost.image_url}
                    alt="Scheduled post"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>
              )}

              <div
                style={{
                  padding: '1rem',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.9rem',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '200px',
                  overflowY: 'auto',
                }}
              >
                {selectedPost.caption}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginTop: '1.5rem' }}>
              {selectedPost.status === 'scheduled' ? (
                <button
                  className="btn btn-danger"
                  style={{ flex: 1 }}
                  onClick={() => {
                    onCancelPost(selectedPost.id);
                    setSelectedPost(null);
                  }}
                >
                  Cancel Scheduled Post
                </button>
              ) : (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'center' }}>
                  Post is {selectedPost.status} (no cancellation available)
                </span>
              )}
              <button
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={() => setSelectedPost(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
