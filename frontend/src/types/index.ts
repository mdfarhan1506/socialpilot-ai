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
  scheduled_time: string;
  status: 'scheduled' | 'published' | 'cancelled' | 'failed';
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
}

export interface AppConfig {
  mock_mode: boolean;
  openai_configured: boolean;
  meta_configured: boolean;
  mode_label: string;
}

export interface MetaStatus {
  mock_mode: boolean;
  meta_configured: boolean;
  account_linked: boolean;
  ig_user_id?: string | null;
  redirect_uri?: string;
}

export interface ContentIdea {
  title: string;
  caption: string;
  hashtags?: string[];
}
