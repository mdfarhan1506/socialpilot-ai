'use client';

import { useEffect, useState } from 'react';

interface Config {
  mock_mode: boolean;
  openai_configured: boolean;
  meta_configured: boolean;
  mode_label: string;
}

export default function Home() {
  const [config, setConfig] = useState<Config | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/config`)
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => setConfig(null));
  }, [apiUrl]);

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
      {/* Mode banner */}
      {config && (
        <div
          style={{
            padding: '0.75rem 1rem',
            marginBottom: '1.5rem',
            borderRadius: 8,
            background: config.mock_mode ? '#fef3c7' : '#d1fae5',
            border: `1px solid ${config.mock_mode ? '#f59e0b' : '#10b981'}`,
            color: config.mock_mode ? '#92400e' : '#065f46',
            fontWeight: 600,
          }}
        >
          {config.mode_label} &nbsp;|&nbsp; OpenAI:{' '}
          {config.openai_configured ? '✅ configured' : '⚠️ not configured'} &nbsp;|&nbsp; Meta:{' '}
          {config.meta_configured ? '✅ configured' : '⚠️ not configured'}
        </div>
      )}

      <h1>SocialPilot AI</h1>
      <p>AI-powered social media management platform.</p>

      <section style={{ marginTop: '2rem' }}>
        <h2>Features</h2>
        <ul>
          <li>🔐 JWT Authentication</li>
          <li>🏢 Multi-workspace management</li>
          <li>🎨 Brand profiles</li>
          <li>🤖 AI content generation {config?.mock_mode ? '(Mock Mode)' : '(OpenAI Live)'}</li>
          <li>📅 Post scheduling with duplicate detection</li>
          <li>📸 Instagram publishing {config?.mock_mode ? '(Mock Mode)' : '(Meta Live)'}</li>
          <li>💬 Comment management</li>
          <li>📊 Analytics dashboard</li>
        </ul>
      </section>

      <section style={{ marginTop: '2rem' }}>
        <h2>API</h2>
        <p>
          Backend API Docs:{' '}
          <a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">
            {apiUrl}/docs
          </a>
        </p>
      </section>
    </main>
  );
}
