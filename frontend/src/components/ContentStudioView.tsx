'use client';

import React, { useState, useEffect } from 'react';
import { Workspace, BrandProfile, ContentIdea, AppConfig, MetaStatus } from '../types';
import { api } from '../services/api';

interface ContentStudioViewProps {
  workspace: Workspace | null;
  brands: BrandProfile[];
  config: AppConfig | null;
  metaStatus: MetaStatus | null;
  onPostCreated: () => void;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
  initialCaption?: string;
  initialDate?: string;
}

export default function ContentStudioView({
  workspace,
  brands,
  config,
  metaStatus,
  onPostCreated,
  onToast,
  initialCaption = '',
  initialDate,
}: ContentStudioViewProps) {
  // Brand selection
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');
  
  // AI Generator inputs
  const [niche, setNiche] = useState('Tech & AI Innovations');
  const [audience, setAudience] = useState('Tech entrepreneurs & social marketers');
  const [tone, setTone] = useState('informative & inspiring');
  const [goal, setGoal] = useState('drive engagement');
  const [extraContext, setExtraContext] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedIdeas, setGeneratedIdeas] = useState<ContentIdea[]>([]);
  // null = no generation yet; set after first successful call
  const [generationSource, setGenerationSource] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // Post Editor state
  const [platform, setPlatform] = useState('instagram');
  const [caption, setCaption] = useState(initialCaption);
  const [imageUrl, setImageUrl] = useState(
    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1080&auto=format&fit=crop&q=80'
  );
  const [imageMeta, setImageMeta] = useState<{
    source?: string;
    isAi?: boolean;
    provider?: string;
    category?: string;
  }>({
    source: 'stock_library',
    isAi: false,
    provider: 'unsplash_curated',
    category: 'tech',
  });
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);

  // Schedule Modal
  const [showScheduleModal, setShowScheduleModal] = useState(Boolean(initialDate));
  const [scheduleTime, setScheduleTime] = useState(
    initialDate
      ? `${initialDate}T12:00`
      : new Date(Date.now() + 3600 * 1000 * 2).toISOString().slice(0, 16)
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  // When a brand profile is selected, auto-fill AI inputs
  useEffect(() => {
    if (selectedBrandId) {
      const b = brands.find((item) => item.id === selectedBrandId);
      if (b) {
        setNiche(b.niche);
        setAudience(b.target_audience);
        setTone(b.tone);
        if (b.content_preferences) setExtraContext(b.content_preferences);
      }
    }
  }, [selectedBrandId, brands]);

  // Handle AI generation
  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setIsGenerating(true);
    setAiError(null);
    try {
      const res = await api.generateContent({
        niche,
        target_audience: audience,
        tone,
        platform,
        goal,
        extra_context: extraContext || undefined,
      });
      setGeneratedIdeas(res.ideas);
      setGenerationSource(res.source);
      onToast(
        `Generated ${res.ideas.length} ideas via ${res.source === 'openai' ? 'OpenAI' : 'Mock AI'}!`,
        'success'
      );
    } catch (err: any) {
      const msg: string = err.message || 'Content generation failed';
      // Surface quota / billing errors clearly instead of showing mock content silently
      if (msg.includes('402') || msg.toLowerCase().includes('quota') || msg.toLowerCase().includes('credits') || msg.toLowerCase().includes('rate limit')) {
        const reason = 'OpenAI account has no credits. Add credits at platform.openai.com to generate real AI content.';
        setAiError(reason);
        onToast(reason, 'error');
      } else {
        setAiError(msg);
        onToast(msg, 'error');
      }
    } finally {
      setIsGenerating(false);
    }
  }

  // Apply idea to editor
  async function applyIdea(idea: ContentIdea) {
    setCaption(`${idea.title}\n\n${idea.caption}`);
    onToast('Idea loaded into caption editor', 'info');
    // Automatically retrieve/generate topic-specific image matching the idea
    await handleRegenerateImage(idea.title);
  }

  // Handle Regenerate Image
  async function handleRegenerateImage(customPrompt?: string) {
    const promptText = customPrompt || caption.slice(0, 100) || niche;
    setIsGeneratingImage(true);
    try {
      const res = await api.generateImage({
        prompt: promptText,
        niche: niche,
        topic: promptText,
        prefer_ai: !config?.mock_mode && config?.openai_configured,
      });
      setImageUrl(res.url);
      setImageMeta({
        source: res.source,
        isAi: Boolean(res.metadata?.is_ai_generated),
        provider: res.metadata?.provider || res.source,
        category: res.category,
      });
      if (res.metadata?.is_ai_generated) {
        onToast('🎨 Generated new AI visual for topic via DALL-E 3!', 'success');
      } else {
        onToast(`🖼️ Selected verified topic stock image (${res.category})`, 'info');
      }
    } catch (err: any) {
      onToast(err.message || 'Image generation failed', 'error');
    } finally {
      setIsGeneratingImage(false);
    }
  }

  // Quick Hashtag click
  function addHashtag(tag: string) {
    if (!caption.includes(tag)) {
      setCaption((prev) => (prev ? `${prev} ${tag}` : tag));
    }
  }

  // Handle Scheduling
  async function handleScheduleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspace) {
      onToast('Please select or create a workspace first', 'error');
      return;
    }
    if (!caption.trim()) {
      onToast('Caption cannot be empty', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      const post = await api.createSchedule({
        workspace_id: workspace.id,
        caption: caption.trim(),
        image_url: imageUrl.trim() || undefined,
        scheduled_time: new Date(scheduleTime).toISOString(),
      });
      onToast(
        `Post scheduled successfully for ${new Date(post.scheduled_time).toLocaleString()}!`,
        'success'
      );
      setShowScheduleModal(false);
      onPostCreated();
    } catch (err: any) {
      onToast(err.message || 'Failed to schedule post', 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  // Handle Instant Publish (Mock or Real)
  async function handleInstantPublish() {
    if (!caption.trim()) {
      onToast('Caption cannot be empty', 'error');
      return;
    }
    if (!(metaStatus?.account_linked || metaStatus?.connected)) {
      onToast(
        'No Instagram account linked. Please link your account in the Social Accounts tab first.',
        'error'
      );
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.publishPost({
        image_url: imageUrl || 'https://via.placeholder.com/600',
        caption: caption.trim(),
      });

      if (res.mock) {
        onToast(
          '🎉 [MOCK PUBLISHED] Simulated publish success! No real Instagram API call was made.',
          'info'
        );
      } else {
        onToast('🚀 Post published live to Instagram successfully!', 'success');
      }
      onPostCreated();
    } catch (err: any) {
      onToast(err.message || 'Publishing failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  const suggestedHashtags = [
    '#AIContent',
    '#SocialMediaMarketing',
    '#ContentCreator',
    '#BrandStrategy',
    '#DigitalMarketing',
    '#GrowthHacking',
    '#SocialPilotAI',
    '#Innovation',
  ];

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Content Studio</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Craft posts, generate AI captions, select hashtags, and schedule across platforms.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '2rem' }}>
        {/* Left Column: AI Generator & Editor */}
        <div>
          {/* AI Generation Form */}
          <div className="card" style={{ marginBottom: '2rem' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 className="card-title" style={{ margin: 0 }}>🤖 AI Idea Generator</h3>
                <span className={`mode-badge ${config?.mock_mode ? 'mock' : 'live'}`}>
                  {config?.mock_mode ? 'Mock AI' : 'OpenAI Live'}
                </span>
              </div>

              {brands.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Load Brand:</span>
                  <select
                    className="form-select"
                    style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem', width: 'auto' }}
                    value={selectedBrandId}
                    onChange={(e) => setSelectedBrandId(e.target.value)}
                  >
                    <option value="">-- Choose Brand --</option>
                    {brands.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.niche} ({b.tone})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <form onSubmit={handleGenerate}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Brand Niche / Topic</label>
                  <input
                    type="text"
                    className="form-input"
                    value={niche}
                    onChange={(e) => setNiche(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Target Audience</label>
                  <input
                    type="text"
                    className="form-input"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Tone of Voice</label>
                  <select
                    className="form-select"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                  >
                    <option value="friendly">Friendly & Relatable</option>
                    <option value="informative & inspiring">Informative & Inspiring</option>
                    <option value="professional & authoritative">Professional & Authoritative</option>
                    <option value="bold & disruptive">Bold & Disruptive</option>
                    <option value="playful & witty">Playful & Witty</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Primary Goal</label>
                  <select
                    className="form-select"
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                  >
                    <option value="drive engagement">Drive Engagement & Comments</option>
                    <option value="educate audience">Educate Audience</option>
                    <option value="promote product">Promote Product / Offer</option>
                    <option value="build community">Build Community Connection</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Extra Context / Key Points (Optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. mention the weekend sale or new feature drop"
                  value={extraContext}
                  onChange={(e) => setExtraContext(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={isGenerating}
              >
                {isGenerating ? 'Generating Ideas with AI...' : '✨ Generate Post Ideas'}
              </button>
            </form>

            {/* AI Error banner — shown when real AI is unavailable */}
            {aiError && (
              <div
                style={{
                  marginTop: '1rem',
                  padding: '0.85rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  fontSize: '0.82rem',
                  color: 'var(--danger)',
                }}
              >
                ⚠️ <strong>AI unavailable:</strong> {aiError}
              </div>
            )}

            {/* Generated Ideas Result */}
            {generatedIdeas.length > 0 && (
              <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                    AI Suggested Ideas
                    {generationSource && (
                      <span
                        style={{
                          marginLeft: '0.5rem',
                          fontSize: '0.72rem',
                          fontWeight: 500,
                          padding: '0.15rem 0.4rem',
                          borderRadius: '4px',
                          background: generationSource === 'openai' ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                          color: generationSource === 'openai' ? 'var(--success)' : '#d97706',
                        }}
                      >
                        {generationSource === 'openai' ? '✓ OpenAI' : '⚠ Mock AI'}
                      </span>
                    )}
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Click to apply</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {generatedIdeas.map((idea, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.85rem',
                        backgroundColor: 'var(--bg-main)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.3rem', color: 'var(--text-primary)' }}>
                        {idea.title}
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        {idea.caption}
                      </p>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => applyIdea(idea)}
                      >
                        ✍️ Use This Idea
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Caption & Post Editor */}
          <div className="card">
            <h3 className="card-title">📝 Post Editor</h3>
            <p className="card-subtitle">Finalize your post, attach media, and add hashtags.</p>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <label className="form-label" style={{ margin: 0 }}>Caption</label>
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: caption.length > 2200 ? 'var(--danger)' : 'var(--text-muted)',
                  }}
                >
                  {caption.length} / 2,200 chars
                </span>
              </div>
              <textarea
                className="form-textarea"
                rows={6}
                placeholder="Write an engaging caption or generate one above..."
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
              />
            </div>

            {/* Hashtag Suggestions */}
            <div className="form-group">
              <label className="form-label">Suggested Hashtags (click to add)</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {suggestedHashtags.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => addHashtag(tag)}
                    style={{
                      background: caption.includes(tag) ? 'var(--accent-primary)' : 'var(--bg-main)',
                      color: caption.includes(tag) ? '#fff' : 'var(--text-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-full)',
                      padding: '0.25rem 0.65rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label className="form-label" style={{ margin: 0 }}>Image Media</label>
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  disabled={isGeneratingImage}
                  onClick={() => handleRegenerateImage()}
                  style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
                >
                  {isGeneratingImage ? '🔄 Generating Visual...' : '🎨 Regenerate Image'}
                </button>
              </div>
              <input
                type="url"
                className="form-input"
                placeholder="https://..."
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <span>
                  Source: <strong>{imageMeta.isAi ? 'OpenAI DALL-E 3 (AI)' : 'Verified Topic Stock'}</strong>
                </span>
                <span>Category: {imageMeta.category || 'General'}</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={() => setShowScheduleModal(true)}
              >
                📅 Schedule Post
              </button>

              <button
                className="btn btn-success"
                style={{ flex: 1 }}
                disabled={isSubmitting}
                onClick={handleInstantPublish}
                title="Publish directly using stored token"
              >
                {isSubmitting ? 'Publishing...' : '🚀 Publish Now'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Realistic Post Preview */}
        <div>
          <div style={{ position: 'sticky', top: '80px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>
              📱 Live Instagram Preview
            </h3>

            <div className="ig-mockup">
              <div className="ig-header">
                <div className="ig-avatar">SP</div>
                <div className="ig-user-info">
                  <div className="ig-username">socialpilot_official</div>
                  <div style={{ fontSize: '0.7rem', color: '#8e8e8e' }}>Original Post</div>
                </div>
                <div style={{ color: '#8e8e8e', cursor: 'pointer' }}>•••</div>
              </div>

              <div className="ig-image-area">
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt="Post preview"
                    className="ig-image"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                ) : (
                  <span style={{ color: '#666', fontSize: '0.85rem' }}>No image URL provided</span>
                )}
              </div>

              <div className="ig-actions">
                <span>❤️</span>
                <span>💬</span>
                <span>✈️</span>
                <span style={{ marginLeft: 'auto' }}>🔖</span>
              </div>

              <div className="ig-caption-area">
                <p>
                  <span className="ig-caption-author">socialpilot_official</span>
                  {caption || (
                    <span style={{ color: '#8e8e8e' }}>
                      Your post caption and hashtags will appear here in real-time...
                    </span>
                  )}
                </p>
                <div style={{ fontSize: '0.7rem', color: '#8e8e8e', marginTop: '0.5rem' }}>
                  Just now • SocialPilot AI
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: '1.5rem',
                padding: '1rem',
                backgroundColor: 'rgba(99, 102, 241, 0.08)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
              }}
            >
              ℹ️ <strong>Publishing Mode Note</strong>: In Mock Mode, publishing tests the complete token decryption, database scheduling, and duplicate guard without making real Meta Graph calls.
            </div>
          </div>
        </div>
      </div>

      {/* Schedule Post Modal */}
      {showScheduleModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">📅 Schedule Post</h3>
              <button className="close-btn" onClick={() => setShowScheduleModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleScheduleSubmit}>
              <div className="form-group">
                <label className="form-label">Publishing Date & Time</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  required
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Must be scheduled in the future.
                </span>
              </div>

              <div className="form-group">
                <label className="form-label">Caption Preview</label>
                <div
                  style={{
                    padding: '0.75rem',
                    backgroundColor: 'var(--bg-main)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.85rem',
                    maxHeight: '120px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {caption || 'No caption entered'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setShowScheduleModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Scheduling...' : 'Confirm Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
