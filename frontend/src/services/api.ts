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
} from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
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
    const res = await fetch(`${API_BASE}/config`);
    return handleResponse<AppConfig>(res);
  },

  // Auth
  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<User>(res);
  },

  async register(email: string, password: string): Promise<{ access_token: string }> {
    const res = await fetch(`${API_BASE}/auth/register`, {
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
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
    return handleResponse<{ access_token: string }>(res);
  },

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    const res = await fetch(`${API_BASE}/workspace/`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Workspace[]>(res);
  },

  async createWorkspace(name: string): Promise<Workspace> {
    const res = await fetch(`${API_BASE}/workspace/`, {
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
    const res = await fetch(`${API_BASE}/brand/?workspace_id=${workspaceId}`, {
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
    const res = await fetch(`${API_BASE}/brand/`, {
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
    const res = await fetch(`${API_BASE}/brand/${brandId}`, {
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
    const res = await fetch(`${API_BASE}/brand/${brandId}`, {
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
  }): Promise<{ ideas: ContentIdea[]; source: string; mock_mode: boolean }> {
    const res = await fetch(`${API_BASE}/content/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(data),
    });
    return handleResponse<{ ideas: ContentIdea[]; source: string; mock_mode: boolean }>(res);
  },

  // Scheduling
  async listSchedules(workspaceId: string): Promise<ScheduledPost[]> {
    const res = await fetch(`${API_BASE}/schedule/?workspace_id=${workspaceId}`, {
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
    const res = await fetch(`${API_BASE}/schedule/`, {
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
    const res = await fetch(`${API_BASE}/schedule/${scheduleId}`, {
      method: 'DELETE',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<void>(res);
  },

  // Meta Instagram
  async getMetaStatus(): Promise<MetaStatus> {
    const res = await fetch(`${API_BASE}/meta/status`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<MetaStatus>(res);
  },

  async getOAuthStart(): Promise<{ mock_mode: boolean; oauth_url: string; note?: string }> {
    const res = await fetch(`${API_BASE}/meta/oauth/start`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ mock_mode: boolean; oauth_url: string; note?: string }>(res);
  },

  async connectMockMeta(code: string = 'mock_oauth_code_verified'): Promise<any> {
    const res = await fetch(`${API_BASE}/meta/oauth/callback?code=${code}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<any>(res);
  },

  async publishPost(data: { image_url: string; caption: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/meta/publish`, {
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
    const res = await fetch(url, {
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
    const res = await fetch(`${API_BASE}/comments/`, {
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
    const res = await fetch(`${API_BASE}/analytics/?workspace_id=${workspaceId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AnalyticsData>(res);
  },
};
