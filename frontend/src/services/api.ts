import {
  User,
  Workspace,
  BrandProfile,
  ScheduledPost,
  CommentItem,
  AnalyticsData,
  AppConfig,
  MetaStatus,
  ContentIdea,
  AutonomousConfig,
  StrategyInsight,
  AutomationAuditLog,
  AutonomousPlanPost,
  GeneratedImageResult,
  TrendOpportunityItem,
} from '../types';

function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  // In browser on non-localhost, warn if defaulting to localhost
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return 'http://localhost:8000';
}

export const API_BASE = getApiBase();

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err: any) {
    if (typeof window !== 'undefined') {
      const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
      if (isProduction && API_BASE.includes('localhost')) {
        throw new Error(
          `Unable to connect to backend: NEXT_PUBLIC_API_URL is configured as "${API_BASE}". In production, please set NEXT_PUBLIC_API_URL in your Vercel project environment variables to your deployed backend URL.`
        );
      }
    }
    throw new Error(
      `Unable to connect to API server at ${API_BASE}. Please verify the backend is running and CORS allows this domain.`
    );
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status}`;
    try {
      const err = await res.json();
      errorMsg = err.detail || JSON.stringify(err);
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }
  if (res.status === 204) {
    return {} as T;
  }
  return res.json();
}

export const api = {
  // Config
  async getConfig(): Promise<AppConfig> {
    const res = await apiFetch(`${API_BASE}/config`);
    return handleResponse<AppConfig>(res);
  },

  // Auth
  async getMe(): Promise<User> {
    const res = await apiFetch(`${API_BASE}/auth/me`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<User>(res);
  },

  async register(email: string, password: string): Promise<{ access_token: string }> {
    const res = await apiFetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return handleResponse<{ access_token: string }>(res);
  },

  async login(email: string, password: string): Promise<{ access_token: string }> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const res = await apiFetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
    return handleResponse<{ access_token: string }>(res);
  },

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    const res = await apiFetch(`${API_BASE}/workspace/`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Workspace[]>(res);
  },

  async createWorkspace(name: string): Promise<Workspace> {
    const res = await apiFetch(`${API_BASE}/workspace/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ name }),
    });
    return handleResponse<Workspace>(res);
  },

  // Brands
  async listBrands(workspaceId: string): Promise<BrandProfile[]> {
    const res = await apiFetch(`${API_BASE}/brand/?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<BrandProfile[]>(res);
  },

  async createBrand(data: {
    workspace_id: string;
    niche: string;
    target_audience: string;
    tone: string;
    brand_voice?: string;
    content_preferences?: string;
  }): Promise<BrandProfile> {
    const res = await apiFetch(`${API_BASE}/brand/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<BrandProfile>(res);
  },

  async updateBrand(
    brandId: string,
    data: {
      niche?: string;
      target_audience?: string;
      tone?: string;
      brand_voice?: string;
      content_preferences?: string;
    }
  ): Promise<BrandProfile> {
    const res = await apiFetch(`${API_BASE}/brand/${brandId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<BrandProfile>(res);
  },

  async deleteBrand(brandId: string): Promise<void> {
    const res = await apiFetch(`${API_BASE}/brand/${brandId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<void>(res);
  },

  // Content Generation
  async generateContent(data: {
    niche: string;
    target_audience: string;
    tone?: string;
    platform?: string;
    goal?: string;
    extra_context?: string;
  }): Promise<{ ideas: ContentIdea[]; source: string; mock_mode: boolean; ai_error?: string | null }> {
    const res = await apiFetch(`${API_BASE}/content/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<{ ideas: ContentIdea[]; source: string; mock_mode: boolean; ai_error?: string | null }>(res);
  },

  async generateImage(data: {
    prompt: string;
    niche?: string;
    topic?: string;
    prefer_ai?: boolean;
  }): Promise<GeneratedImageResult> {
    const res = await apiFetch(`${API_BASE}/content/generate-image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<GeneratedImageResult>(res);
  },

  // Scheduling
  async listSchedules(workspaceId: string): Promise<ScheduledPost[]> {
    const res = await apiFetch(`${API_BASE}/schedule/?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<ScheduledPost[]>(res);
  },

  async createSchedule(data: {
    workspace_id: string;
    caption: string;
    image_url?: string;
    scheduled_time: string;
  }): Promise<ScheduledPost> {
    const res = await apiFetch(`${API_BASE}/schedule/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<ScheduledPost>(res);
  },

  async cancelSchedule(scheduleId: string): Promise<void> {
    const res = await apiFetch(`${API_BASE}/schedule/${scheduleId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<void>(res);
  },

  // Meta Instagram
  async getMetaStatus(): Promise<MetaStatus> {
    const res = await apiFetch(`${API_BASE}/meta/status`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<MetaStatus>(res);
  },

  async getOAuthStart(): Promise<{ mock_mode: boolean; oauth_url: string; note?: string }> {
    const res = await apiFetch(`${API_BASE}/meta/oauth/start`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ mock_mode: boolean; oauth_url: string; note?: string }>(res);
  },

  async connectMockMeta(code: string = 'mock_oauth_code_verified'): Promise<any> {
    const res = await apiFetch(`${API_BASE}/meta/oauth/callback?code=${code}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<any>(res);
  },

  async disconnectMeta(): Promise<{ detail: string }> {
    const res = await apiFetch(`${API_BASE}/meta/disconnect`, {
      method: 'DELETE',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ detail: string }>(res);
  },

  async publishPost(data: { image_url: string; caption: string }): Promise<any> {
    const res = await apiFetch(`${API_BASE}/meta/publish`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<any>(res);
  },

  // Comments
  async listComments(workspaceId: string, postId?: string): Promise<CommentItem[]> {
    let url = `${API_BASE}/comments/?workspace_id=${workspaceId}`;
    if (postId) url += `&post_id=${postId}`;
    const res = await apiFetch(url, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<CommentItem[]>(res);
  },

  async createComment(data: {
    workspace_id: string;
    post_id?: string;
    author?: string;
    text: string;
  }): Promise<CommentItem> {
    const res = await apiFetch(`${API_BASE}/comments/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<CommentItem>(res);
  },

  // Analytics
  async getAnalytics(workspaceId: string): Promise<AnalyticsData> {
    const res = await apiFetch(`${API_BASE}/analytics/?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AnalyticsData>(res);
  },

  // Autonomous Creator
  async getAutonomousConfig(workspaceId: string): Promise<AutonomousConfig> {
    const res = await apiFetch(`${API_BASE}/autonomous/config?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AutonomousConfig>(res);
  },

  async updateAutonomousConfig(
    data: Partial<AutonomousConfig> & { workspace_id: string }
  ): Promise<{ status: string; is_active: boolean }> {
    const res = await apiFetch(`${API_BASE}/autonomous/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<{ status: string; is_active: boolean }>(res);
  },

  async pauseAutonomous(workspaceId: string): Promise<{ status: string; is_active: boolean }> {
    const res = await apiFetch(`${API_BASE}/autonomous/pause?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ status: string; is_active: boolean }>(res);
  },

  async resumeAutonomous(workspaceId: string): Promise<{ status: string; is_active: boolean }> {
    const res = await apiFetch(`${API_BASE}/autonomous/resume?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ status: string; is_active: boolean }>(res);
  },

  async runAutonomousCycle(workspaceId: string): Promise<any> {
    const res = await apiFetch(`${API_BASE}/autonomous/run-cycle?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<any>(res);
  },

  async getAutonomousInsights(workspaceId: string): Promise<StrategyInsight[]> {
    const res = await apiFetch(`${API_BASE}/autonomous/insights?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<StrategyInsight[]>(res);
  },

  async getAutonomousAuditLogs(workspaceId: string): Promise<AutomationAuditLog[]> {
    const res = await apiFetch(`${API_BASE}/autonomous/audit-logs?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AutomationAuditLog[]>(res);
  },

  async getAutonomousPlan(workspaceId: string): Promise<AutonomousPlanPost[]> {
    const res = await apiFetch(`${API_BASE}/autonomous/plan?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AutonomousPlanPost[]>(res);
  },

  async approvePost(postId: string): Promise<{ status: string; post_id: string }> {
    const res = await apiFetch(`${API_BASE}/autonomous/posts/${postId}/approve`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ status: string; post_id: string }>(res);
  },
};
