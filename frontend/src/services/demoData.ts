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
  GeneratedImageResult,
} from '../types';

export const DEMO_USER: User = {
  id: 'demo-user-urban-threads',
  email: 'demo@urbanthreads.fashion',
};

export const DEMO_WORKSPACE: Workspace = {
  id: 'demo-workspace-urban-threads',
  name: 'Urban Threads Studio',
  owner_id: DEMO_USER.id,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
};

export const DEMO_BRAND_PROFILE: BrandProfile = {
  id: 'demo-brand-urban-threads',
  workspace_id: DEMO_WORKSPACE.id,
  user_id: DEMO_USER.id,
  niche: 'Fashion & Lifestyle',
  target_audience: 'Modern Gen-Z & Millennial Urban Fashion Enthusiasts',
  tone: 'Chic, authentic, trend-forward, and inspiring',
  brand_voice: 'Bold minimalism, streetwear aesthetic, sustainable fashion advocacy',
  content_preferences: 'High-contrast editorial photos, fit breakdowns, styling reels, capsule wardrobe guides',
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
};

export const DEMO_META_STATUS: MetaStatus = {
  connected: true,
  account_linked: true,
  ig_user_id: 'urbanthreads_demo',
  mock_mode: true,
  meta_configured: true,
};

export const DEMO_ANALYTICS: AnalyticsData = {
  workspace_id: DEMO_WORKSPACE.id,
  mock_mode: true,
  scheduled_posts: 3,
  total_comments: 89,
  estimated_reach: '84.2K',
  note: '[DEMO] Realistic simulated audience metrics for Urban Threads.',
  instagram_connected: true,
  instagram_live_data: {
    success: true,
    mock: true,
    ig_user_id: 'urbanthreads_demo',
    username: 'urbanthreads_official',
    followers_count: 42800,
    media_count: 142,
    reach: 84200,
    profile_accessible: true,
    insights_accessible: true,
    granted_permissions: [
      'instagram_basic',
      'instagram_content_publish',
      'instagram_manage_insights',
      'instagram_manage_comments',
    ],
  },
};

export const DEMO_SCHEDULED_POSTS: ScheduledPost[] = [
  {
    id: 'demo-post-1',
    concept: 'Autumn Streetwear Capsule Essentials',
    hook: 'The only 5 jackets you actually need in your rotation this season 🧥',
    script_or_body: 'Minimalist layering done right. Which silhouette is your go-to?',
    call_to_action: 'Save this guide for your next wardrobe refresh!',
    caption: '[DEMO] The only 5 jackets you actually need in your rotation this season 🧥\n\nMinimalist layering done right: oversized bomber, tailored trench, shearling aviator, structured wool blazer, and water-repellent tech shell.\n\nSave this guide for your next wardrobe refresh! #UrbanThreads #CapsuleWardrobe #StreetwearStyle #AutumnFits',
    image_url: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80',
    scheduled_time: new Date(Date.now() + 86400000).toISOString(),
    status: 'scheduled',
    requires_approval: false,
    created_at: '2026-11-08T10:00:00Z',
  },
  {
    id: 'demo-post-2',
    concept: 'Sustainable Denim Fit Breakdown',
    hook: 'Vintage wash vs raw selvedge: How to choose your signature denim 👖',
    script_or_body: '100% recycled cotton, zero microplastics. Here is how we break in our signature denim.',
    call_to_action: 'Drop a 🔥 in the comments if you want the lookbook link!',
    caption: '[DEMO] Vintage wash vs raw selvedge: How to choose your signature denim 👖\n\nCrafted from 100% circular organic cotton with zero wastewater. Every crease tells your story.\n\nDrop a 🔥 in the comments if you want the lookbook link! #SustainableFashion #DenimStyle #UrbanOutfitters',
    image_url: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80',
    scheduled_time: new Date(Date.now() + 172800000).toISOString(),
    status: 'scheduled',
    requires_approval: false,
    created_at: '2026-11-08T12:00:00Z',
  },
  {
    id: 'demo-post-3',
    concept: 'Monochrome Monochrome Aesthetic',
    hook: 'Why all-black monochrome outfits will forever dominate Parisian fashion 🖤',
    script_or_body: 'Texture over color: wool, silk, matte leather. The secret to elevated monochrome fits.',
    call_to_action: 'Share this with your best dressed friend.',
    caption: '[DEMO] Why all-black monochrome outfits will forever dominate Parisian fashion 🖤\n\nWhen you master subtle textural contrast, you never need loud patterns again.\n\nShare this with your best dressed friend! #AllBlackEverything #EditorialFashion #MonochromeFit',
    image_url: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80',
    scheduled_time: new Date(Date.now() - 86400000).toISOString(),
    status: 'published',
    requires_approval: false,
    created_at: '2026-11-07T14:00:00Z',
  },
];

export const DEMO_COMMENTS: CommentItem[] = [
  {
    id: 'demo-comment-1',
    workspace_id: DEMO_WORKSPACE.id,
    post_id: 'demo-post-3',
    author: 'clara_styled',
    text: 'That wool coat silhouette is absolute perfection! Is it available in size S?',
    created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
  },
  {
    id: 'demo-comment-2',
    workspace_id: DEMO_WORKSPACE.id,
    post_id: 'demo-post-3',
    author: 'marcus_kicks',
    text: 'Need that styling guide breakdown ASAP. Amazing photography 🔥',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  },
  {
    id: 'demo-comment-3',
    workspace_id: DEMO_WORKSPACE.id,
    post_id: 'demo-post-2',
    author: 'eco_aesthetic',
    text: 'Love the commitment to 100% circular denim! Huge win for sustainability 🙌',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

export const DEMO_AUTONOMOUS_CONFIG: AutonomousConfig = {
  id: 'demo-auto-cfg',
  workspace_id: DEMO_WORKSPACE.id,
  is_active: true,
  approval_mode: 'manual_for_sensitive',
  min_posts_per_day: 1,
  max_posts_per_day: 3,
  quiet_hours_start: 22,
  quiet_hours_end: 7,
  restricted_keywords: ['fast fashion', 'unethical', 'knockoff'],
  target_topics: ['Sustainable Streetwear', 'Capsule Wardrobe Styling', 'Editorial Fit Guides'],
};

export const DEMO_STRATEGY_INSIGHTS: StrategyInsight[] = [
  {
    id: 'demo-insight-1',
    topic: 'Capsule Wardrobe Styling',
    hook_type: 'question',
    format_type: 'carousel',
    best_time_slot: '18:00 UTC (Peak commute engagement)',
    performance_score: 9.2,
    hypothesis: 'Curated 5-item wardrobe carousel posts drive 3.2x higher saves than single product shots.',
    recommendation: 'Increase carousel breakdown cadence to 2x per week with clear cover slide titles.',
    confidence_score: 0.94,
    is_mock: true,
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 'demo-insight-2',
    topic: 'Sustainable Fabric Origins',
    hook_type: 'bold_statement',
    format_type: 'single_image',
    best_time_slot: '13:00 UTC',
    performance_score: 7.8,
    hypothesis: 'Behind-the-scenes sustainability claims generate 65% more comments from conscious buyers.',
    recommendation: 'Feature raw fabric textures and certification badges in opening visual frames.',
    confidence_score: 0.88,
    is_mock: true,
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

export const DEMO_AUDIT_LOGS: AutomationAuditLog[] = [
  {
    id: 'demo-audit-1',
    action: 'autonomous_cycle',
    status: 'success',
    summary: '[DEMO] Scheduled 2 curated editorial posts for the upcoming 48 hours based on peak engagement windows.',
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'demo-audit-2',
    action: 'policy_screening',
    status: 'success',
    summary: '[DEMO] Verified zero restricted keywords in scheduled captions; aesthetic standards passed.',
    created_at: new Date(Date.now() - 7100000).toISOString(),
  },
  {
    id: 'demo-audit-3',
    action: 'trend_research',
    status: 'success',
    summary: '[DEMO] Discovered 4 trending seasonal fashion topics: Oversized Outerwear, Recycled Denim, Earth Tones.',
    created_at: new Date(Date.now() - 14400000).toISOString(),
  },
];

export const DEMO_AUTONOMOUS_PLAN: AutonomousPlanPost[] = [
  {
    id: 'demo-plan-1',
    concept: 'Earth Tone Streetwear Layering',
    hook: 'Why olive, sand, and espresso brown are the new universal neutrals 🍂',
    script_or_body: 'Minimalist tones crafted for effortless daily rotation.',
    call_to_action: 'Save this color palette for your next outfit!',
    caption: '[DEMO] Why olive, sand, and espresso brown are the new universal neutrals 🍂\n\nEarth tones create effortless versatility without sacrificing personal expression.\n\n#UrbanThreads #ColorPalette #Streetwear',
    image_url: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80',
    scheduled_time: new Date(Date.now() + 86400000).toISOString(),
    status: 'scheduled',
    requires_approval: false,
  },
  {
    id: 'demo-plan-2',
    concept: 'Sustainable Denim Fit Breakdown',
    hook: 'Vintage wash vs raw selvedge: How to choose your signature denim 👖',
    script_or_body: '100% recycled cotton, zero microplastics.',
    call_to_action: 'Drop your favorite denim brand below!',
    caption: '[DEMO] Vintage wash vs raw selvedge: How to choose your signature denim 👖\n\nCrafted from 100% circular organic cotton with zero wastewater.\n\n#SustainableDenim #UrbanThreads',
    image_url: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80',
    scheduled_time: new Date(Date.now() + 172800000).toISOString(),
    status: 'scheduled',
    requires_approval: false,
  },
];

export const DEMO_CONTENT_IDEAS: ContentIdea[] = [
  {
    title: '[DEMO] 5 Essential Outerwear Pieces for Minimalist Streetwear',
    caption: '[DEMO] Building your seasonal rotation starts with purposeful outerwear. Focus on structural weight, matte hardware, and versatile tailoring that transitions seamlessly from day to night. #CapsuleWardrobe #StreetwearInspo #UrbanThreads',
    hashtags: ['#CapsuleWardrobe', '#StreetwearInspo', '#UrbanThreads'],
  },
  {
    title: '[DEMO] The 60-30-10 Color Rule in Modern Casual Outfits',
    caption: '[DEMO] 60% dominant neutral, 30% complementary tone, 10% striking accent. Here is how we apply color theory to everyday elevated streetwear without looking overstyled. #ColorTheory #StylingTips #FashionFrameworks',
    hashtags: ['#ColorTheory', '#StylingTips', '#FashionFrameworks'],
  },
  {
    title: '[DEMO] Circular Denim: From Reclaimed Fiber to Everyday Uniform',
    caption: '[DEMO] Sustainable style is never about buying more — it is about keeping exceptional materials in perpetual motion. See the making of our zero-water wash collection. #CircularFashion #SustainableStyle #DenimLovers',
    hashtags: ['#CircularFashion', '#SustainableStyle', '#DenimLovers'],
  },
];

export const DEMO_STOCK_IMAGES = [
  'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=1200&q=80',
];
