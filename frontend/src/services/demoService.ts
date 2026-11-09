import {
  DEMO_USER,
  DEMO_WORKSPACE,
  DEMO_BRAND_PROFILE,
  DEMO_META_STATUS,
  DEMO_ANALYTICS,
  DEMO_SCHEDULED_POSTS,
  DEMO_COMMENTS,
  DEMO_AUTONOMOUS_CONFIG,
  DEMO_STRATEGY_INSIGHTS,
  DEMO_AUDIT_LOGS,
  DEMO_AUTONOMOUS_PLAN,
  DEMO_CONTENT_IDEAS,
  DEMO_STOCK_IMAGES,
} from './demoData';
import {
  User,
  Workspace,
  BrandProfile,
  ScheduledPost,
  CommentItem,
  AnalyticsData,
  MetaStatus,
  ContentIdea,
  AutonomousConfig,
  StrategyInsight,
  AutomationAuditLog,
  AutonomousPlanPost,
} from '../types';

let isDemoSessionActive = false;

// In-memory demo state for interactive simulation
let demoSchedules: ScheduledPost[] = [...DEMO_SCHEDULED_POSTS];
let demoBrands: BrandProfile[] = [{ ...DEMO_BRAND_PROFILE }];
let demoComments: CommentItem[] = [...DEMO_COMMENTS];
let demoAutonomousConfig: AutonomousConfig = { ...DEMO_AUTONOMOUS_CONFIG };
let demoAuditLogs: AutomationAuditLog[] = [...DEMO_AUDIT_LOGS];
let demoPlan: AutonomousPlanPost[] = [...DEMO_AUTONOMOUS_PLAN];

export function isDemoMode(): boolean {
  if (typeof window === 'undefined') return false;
  return isDemoSessionActive || sessionStorage.getItem('socialpilot_demo_mode') === 'true';
}

export function setDemoMode(active: boolean): void {
  isDemoSessionActive = active;
  if (typeof window !== 'undefined') {
    if (active) {
      sessionStorage.setItem('socialpilot_demo_mode', 'true');
    } else {
      sessionStorage.removeItem('socialpilot_demo_mode');
      // Reset in-memory demo changes
      demoSchedules = [...DEMO_SCHEDULED_POSTS];
      demoBrands = [{ ...DEMO_BRAND_PROFILE }];
      demoComments = [...DEMO_COMMENTS];
      demoAutonomousConfig = { ...DEMO_AUTONOMOUS_CONFIG };
      demoAuditLogs = [...DEMO_AUDIT_LOGS];
      demoPlan = [...DEMO_AUTONOMOUS_PLAN];
    }
  }
}

export const demoApi = {
  async getMe(): Promise<User> {
    return DEMO_USER;
  },

  async listWorkspaces(): Promise<Workspace[]> {
    return [DEMO_WORKSPACE];
  },

  async createWorkspace(name: string): Promise<Workspace> {
    return {
      id: `demo-workspace-${Date.now()}`,
      name: `${name} (Demo)`,
      owner_id: DEMO_USER.id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  },

  async listBrands(workspaceId: string): Promise<BrandProfile[]> {
    return demoBrands;
  },

  async createBrand(data: Partial<BrandProfile> & { workspace_id: string }): Promise<BrandProfile> {
    const created: BrandProfile = {
      id: `demo-brand-${Date.now()}`,
      workspace_id: data.workspace_id,
      user_id: DEMO_USER.id,
      niche: data.niche || 'Fashion & Lifestyle',
      target_audience: data.target_audience || 'Demo Target Audience',
      tone: data.tone || 'Chic and editorial',
      brand_voice: data.brand_voice,
      content_preferences: data.content_preferences,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    demoBrands = [created, ...demoBrands];
    return created;
  },

  async updateBrand(brandId: string, data: Partial<BrandProfile>): Promise<BrandProfile> {
    const idx = demoBrands.findIndex((b) => b.id === brandId);
    if (idx !== -1) {
      demoBrands[idx] = { ...demoBrands[idx], ...data };
      return demoBrands[idx];
    }
    return { ...DEMO_BRAND_PROFILE, ...data };
  },

  async deleteBrand(brandId: string): Promise<{ status: string }> {
    demoBrands = demoBrands.filter((b) => b.id !== brandId);
    return { status: 'deleted' };
  },

  async listSchedules(workspaceId: string): Promise<ScheduledPost[]> {
    return demoSchedules;
  },

  async createSchedule(data: {
    workspace_id: string;
    caption: string;
    scheduled_time: string;
    image_url?: string;
  }): Promise<ScheduledPost> {
    const created: ScheduledPost = {
      id: `demo-post-${Date.now()}`,
      caption: `[DEMO] ${data.caption.replace(/^\[DEMO\]\s*/, '')}`,
      image_url: data.image_url || DEMO_STOCK_IMAGES[0],
      scheduled_time: data.scheduled_time,
      status: 'scheduled',
      requires_approval: false,
      created_at: new Date().toISOString(),
    };
    demoSchedules = [created, ...demoSchedules];
    return created;
  },

  async cancelSchedule(postId: string): Promise<{ status: string }> {
    demoSchedules = demoSchedules.map((p) =>
      p.id === postId ? { ...p, status: 'cancelled' } : p
    );
    return { status: 'cancelled' };
  },

  async publishPost(postId: string): Promise<{ success: boolean; message: string }> {
    demoSchedules = demoSchedules.map((p) =>
      p.id === postId ? { ...p, status: 'published' } : p
    );
    return {
      success: true,
      message: '[DEMO] Simulated post successfully marked as published in demo session. No live Instagram call was made.',
    };
  },

  async generateContent(data: {
    niche: string;
    target_audience: string;
    tone?: string;
    platform?: string;
    goal?: string;
    extra_context?: string;
  }): Promise<{ ideas: ContentIdea[]; source: string; mock_mode: boolean; ai_error?: string | null }> {
    const sampleIdeas: ContentIdea[] = [
      {
        title: `[DEMO] ${data.niche || 'Fashion'} Trend Breakdown: 3 Rules to Elevate Your Aesthetic`,
        caption: `[DEMO] When building out your ${data.niche || 'fashion'} voice for ${data.target_audience || 'creatives'}, focus on intentional details. Which rule resonates most with you? #${(data.niche || 'Fashion').replace(/\s+/g, '')} #DemoInspo #CuratedStyle`,
        hashtags: [`#${(data.niche || 'Fashion').replace(/\s+/g, '')}`, '#DemoInspo', '#CuratedStyle'],
      },
      {
        title: `[DEMO] The Behind-The-Scenes Process: Sourcing Quality Materials`,
        caption: `[DEMO] Real craftsmanship is born from patience and curated quality. Here is our step-by-step breakdown for ${data.target_audience || 'design enthusiasts'}. Save this for inspiration! #StyleGuide #DemoCraft`,
        hashtags: ['#StyleGuide', '#DemoCraft', '#BehindTheScenes'],
      },
      {
        title: `[DEMO] The 5-Minute Styling Blueprint for Every Occasion`,
        caption: `[DEMO] Effortless elegance requires zero guesswork. Pair structured silhouettes with relaxed textures. Tap the link in bio to explore the full demo lookbook. #ElevatedCasual #UrbanThreads`,
        hashtags: ['#ElevatedCasual', '#UrbanThreads', '#Lookbook'],
      },
    ];

    return {
      ideas: sampleIdeas,
      source: 'demo_simulation',
      mock_mode: true,
      ai_error: null,
    };
  },

  async generateImage(data: {
    prompt: string;
    niche?: string;
    topic?: string;
    prefer_ai?: boolean;
  }): Promise<{
    url: string;
    source: string;
    category: string;
    metadata: Record<string, any>;
    mock_mode: boolean;
    fallback_reason?: string;
  }> {
    const idx = Math.abs((data.prompt || data.topic || 'demo').length) % DEMO_STOCK_IMAGES.length;
    return {
      url: DEMO_STOCK_IMAGES[idx],
      source: 'stock_fallback',
      category: 'demo_fashion',
      metadata: {
        is_ai_generated: false,
        provider: 'demo_curated_library',
        demo_note: 'Demo visual from curated royalty-free sample library',
      },
      mock_mode: true,
      fallback_reason: 'Demo Mode: simulated visual from curated sample library',
    };
  },

  async listComments(workspaceId: string): Promise<CommentItem[]> {
    return demoComments;
  },

  async createComment(data: {
    workspace_id: string;
    post_id?: string;
    author: string;
    text: string;
  }): Promise<CommentItem> {
    const created: CommentItem = {
      id: `demo-comment-${Date.now()}`,
      workspace_id: data.workspace_id,
      post_id: data.post_id,
      author: data.author,
      text: data.text,
      created_at: new Date().toISOString(),
    };
    demoComments = [created, ...demoComments];
    return created;
  },

  async getAnalytics(workspaceId: string): Promise<AnalyticsData> {
    return DEMO_ANALYTICS;
  },

  async getMetaStatus(): Promise<MetaStatus> {
    return DEMO_META_STATUS;
  },

  async getAutonomousConfig(workspaceId: string): Promise<AutonomousConfig> {
    return demoAutonomousConfig;
  },

  async updateAutonomousConfig(
    data: Partial<AutonomousConfig> & { workspace_id: string }
  ): Promise<{ status: string; is_active: boolean }> {
    demoAutonomousConfig = { ...demoAutonomousConfig, ...data };
    return { status: 'updated', is_active: demoAutonomousConfig.is_active };
  },

  async pauseAutonomous(workspaceId: string): Promise<{ status: string; is_active: boolean }> {
    demoAutonomousConfig.is_active = false;
    return { status: 'paused', is_active: false };
  },

  async resumeAutonomous(workspaceId: string): Promise<{ status: string; is_active: boolean }> {
    demoAutonomousConfig.is_active = true;
    return { status: 'resumed', is_active: true };
  },

  async runAutonomousCycle(workspaceId: string): Promise<any> {
    const newLog: AutomationAuditLog = {
      id: `demo-audit-${Date.now()}`,
      action: 'autonomous_cycle',
      status: 'success',
      summary: `[DEMO] Simulated autonomous cycle executed: 2 posts planned, 1 observation analyzed for Urban Threads.`,
      created_at: new Date().toISOString(),
    };
    demoAuditLogs = [newLog, ...demoAuditLogs];

    return {
      status: 'success',
      observations_ingested: 1,
      strategy_insights: demoAuditLogs.length,
      new_posts_planned: 2,
      active_strategy: {
        recommended_hook_type: 'question',
        best_format: 'carousel',
        scheduling_basis: 'demo_simulated_metrics',
      },
    };
  },

  async getAutonomousInsights(workspaceId: string): Promise<StrategyInsight[]> {
    return DEMO_STRATEGY_INSIGHTS;
  },

  async getAutonomousAuditLogs(workspaceId: string): Promise<AutomationAuditLog[]> {
    return demoAuditLogs;
  },

  async getAutonomousPlan(workspaceId: string): Promise<AutonomousPlanPost[]> {
    return demoPlan;
  },

  async approvePost(postId: string): Promise<{ status: string; post_id: string }> {
    demoPlan = demoPlan.map((p) =>
      p.id === postId ? { ...p, status: 'scheduled', requires_approval: false } : p
    );
    return { status: 'approved', post_id: postId };
  },
};
