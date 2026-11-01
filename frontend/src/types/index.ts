export interface User {
  id: string;
  email: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface BrandProfile {
  id: string;
  workspace_id: string;
  user_id: string;
  niche: string;
  target_audience: string;
  tone: string;
  brand_voice?: string | null;
  content_preferences?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduledPost {
  id: string;
  caption: string;
  image_url?: string | null;
  concept?: string | null;
  hook?: string | null;
  script_or_body?: string | null;
  call_to_action?: string | null;
  requires_approval?: boolean;
  approved_at?: string | null;
  scheduled_time: string;
  status: 'scheduled' | 'published' | 'cancelled' | 'failed' | 'pending_approval';
  created_at: string;
}

export interface CommentItem {
  id: string;
  workspace_id: string;
  post_id?: string | null;
  author?: string | null;
  text: string;
  created_at: string;
}

export interface AnalyticsData {
  workspace_id: string;
  mock_mode: boolean;
  scheduled_posts: number;
  total_comments: number;
  estimated_reach: string;
  note: string;
  instagram_connected?: boolean;
  instagram_live_data?: {
    success: boolean;
    mock: boolean;
    ig_user_id?: string;
    username?: string;
    followers_count?: number;
    media_count?: number;
    reach?: number;
    profile_accessible?: boolean;
    insights_accessible?: boolean;
    granted_permissions?: string[];
    missing_permissions?: string[];
    error_note?: string | null;
  } | null;
}

export interface AppConfig {
  mock_mode: boolean;
  openai_configured: boolean;
  meta_configured: boolean;
  mode_label: string;
}

export interface MetaStatus {
  mock_mode: boolean;
  meta_configured?: boolean;
  connected?: boolean;
  account_linked?: boolean;
  ig_user_id?: string | null;
  redirect_uri?: string;
}

export interface ContentIdea {
  title: string;
  caption: string;
  hashtags?: string[];
}

export interface AutonomousConfig {
  id: string;
  workspace_id: string;
  is_active: boolean;
  approval_mode: string;
  min_posts_per_day: number;
  max_posts_per_day: number;
  quiet_hours_start: number;
  quiet_hours_end: number;
  restricted_keywords: string[];
  target_topics: string[];
}

export interface StrategyInsight {
  id: string;
  topic: string;
  hook_type?: string | null;
  format_type?: string | null;
  best_time_slot?: string | null;
  performance_score: number;
  hypothesis: string;
  recommendation: string;
  confidence_score: number;
  is_mock: boolean;
  created_at?: string | null;
}

export interface AutomationAuditLog {
  id: string;
  action: string;
  status: string;
  summary: string;
  details?: any;
  created_at: string;
}

export interface AutonomousPlanPost {
  id: string;
  concept?: string | null;
  hook?: string | null;
  script_or_body?: string | null;
  call_to_action?: string | null;
  caption: string;
  image_url?: string | null;
  scheduled_time: string;
  status: string;
  requires_approval: boolean;
  approved_at?: string | null;
}
