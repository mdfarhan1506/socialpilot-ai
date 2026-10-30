'use client';

import React, { useState } from 'react';
import { BrandProfile, Workspace } from '../types';
import { api } from '../services/api';

interface BrandProfilesViewProps {
  workspace: Workspace | null;
  brands: BrandProfile[];
  onRefresh: () => void;
  onSelectBrandForStudio: (brand: BrandProfile) => void;
  onToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export default function BrandProfilesView({
  workspace,
  brands,
  onRefresh,
  onSelectBrandForStudio,
  onToast,
}: BrandProfilesViewProps) {
  const [showModal, setShowModal] = useState(false);
  const [editingBrand, setEditingBrand] = useState<BrandProfile | null>(null);

  // Form fields
  const [niche, setNiche] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [tone, setTone] = useState('inspiring');
  const [brandVoice, setBrandVoice] = useState('');
  const [contentPreferences, setContentPreferences] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function openCreateModal() {
    setEditingBrand(null);
    setNiche('');
    setTargetAudience('');
    setTone('inspiring');
    setBrandVoice('');
    setContentPreferences('');
    setShowModal(true);
  }

  function openEditModal(brand: BrandProfile) {
    setEditingBrand(brand);
    setNiche(brand.niche);
    setTargetAudience(brand.target_audience);
    setTone(brand.tone);
    setBrandVoice(brand.brand_voice || '');
    setContentPreferences(brand.content_preferences || '');
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspace) {
      onToast('Please select a workspace first', 'error');
      return;
    }

    setSubmitting(true);
    try {
      if (editingBrand) {
        await api.updateBrand(editingBrand.id, {
          niche,
          target_audience: targetAudience,
          tone,
          brand_voice: brandVoice || undefined,
          content_preferences: contentPreferences || undefined,
        });
        onToast('Brand profile updated successfully!', 'success');
      } else {
        await api.createBrand({
          workspace_id: workspace.id,
          niche,
          target_audience: targetAudience,
          tone,
          brand_voice: brandVoice || undefined,
          content_preferences: contentPreferences || undefined,
        });
        onToast('New brand profile created!', 'success');
      }
      setShowModal(false);
      onRefresh();
    } catch (err: any) {
      onToast(err.message || 'Operation failed', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Are you sure you want to delete this brand profile?')) return;
    try {
      await api.deleteBrand(id);
      onToast('Brand profile deleted', 'info');
      onRefresh();
    } catch (err: any) {
      onToast(err.message || 'Failed to delete brand', 'error');
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800 }}>Brand Profiles</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Define custom brand identities, tone of voice, audience personas, and content themes.
          </p>
        </div>

        <button className="btn btn-primary" onClick={openCreateModal}>
          + Create Brand Profile
        </button>
      </div>

      {brands.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🎨</div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            No brand profiles yet
          </h3>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 450, margin: '0 auto 1.5rem auto' }}>
            Create brand profiles to guide AI generation in producing tailored captions that match your exact voice and target demographic.
          </p>
          <button className="btn btn-primary" onClick={openCreateModal}>
            Create First Brand Profile
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
          {brands.map((brand) => (
            <div key={brand.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {brand.niche}
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600 }}>
                    Tone: {brand.tone}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => openEditModal(brand)}
                    title="Edit Brand"
                  >
                    ✏️
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(brand.id)}
                    title="Delete Brand"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem' }}>
                <div style={{ padding: '0.65rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Target Audience:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{brand.target_audience}</span>
                </div>

                {brand.brand_voice && (
                  <div style={{ padding: '0.65rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Brand Voice:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{brand.brand_voice}</span>
                  </div>
                )}

                {brand.content_preferences && (
                  <div style={{ padding: '0.65rem', backgroundColor: 'var(--bg-main)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Content Guidelines:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{brand.content_preferences}</span>
                  </div>
                )}
              </div>

              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                <button
                  className="btn btn-sm btn-primary"
                  style={{ width: '100%' }}
                  onClick={() => onSelectBrandForStudio(brand)}
                >
                  ✨ Use in Content Studio &rarr;
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">
                {editingBrand ? 'Edit Brand Profile' : 'New Brand Profile'}
              </h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Niche / Industry</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. AI SaaS, Sustainable Fashion, Fitness Coaching"
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Target Audience</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Startup founders, Gen-Z fitness enthusiasts"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Tone of Voice</label>
                <select
                  className="form-select"
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                >
                  <option value="inspiring">Inspiring & Uplifting</option>
                  <option value="authoritative">Authoritative & Thought Leader</option>
                  <option value="friendly">Friendly & Approachable</option>
                  <option value="humorous">Humorous & Witty</option>
                  <option value="urgent">Urgent & High-Energy</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Brand Voice Description (Optional)</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="e.g. Speak with confidence, short punchy sentences, avoid corporate jargon."
                  value={brandVoice}
                  onChange={(e) => setBrandVoice(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Content Preferences / Topics (Optional)</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="e.g. Always include a call to action asking a question in comments."
                  value={contentPreferences}
                  onChange={(e) => setContentPreferences(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={submitting}
                >
                  {submitting ? 'Saving...' : editingBrand ? 'Save Changes' : 'Create Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
