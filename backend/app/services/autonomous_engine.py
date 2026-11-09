"""Autonomous Creator Orchestration Engine.

Coordinates persistent research, rolling content planning, platform-ready generation,
media validation, policy enforcement, adaptive scheduling, and closed-loop learning.
"""
from __future__ import annotations

import re
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.autonomous import AutonomousConfig, AutomationAuditLog, StrategyInsight
from ..models.brand import BrandProfile
from ..models.content import ScheduledPost, PublishedPost
from ..models.meta_token import MetaToken
from ..services.learning_engine import learning_engine
from ..services.provider_factory import get_ai_provider
from ..services.image_service import generate_topic_image
from ..services.content_uniqueness import (
    is_duplicate_or_near_duplicate,
    get_recent_posts_in_window,
    pick_distinct_format_and_angle,
)
from ..services.trend_research import conduct_workspace_research
from ..services.adaptive_scheduler import get_best_hour_for_day
from ..services.publish_validator import validate_post_for_publishing
from ..settings import settings

log = logging.getLogger(__name__)


class AutonomousEngine:
    """Persistent Autonomous Social Media Creator Manager."""

    async def get_or_create_config(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> AutonomousConfig:
        """Fetch or initialize default autonomous configuration for a workspace."""
        res = await db.execute(
            select(AutonomousConfig).where(AutonomousConfig.workspace_id == workspace_id)
        )
        cfg = res.scalar_one_or_none()
        if not cfg:
            cfg = AutonomousConfig(
                workspace_id=workspace_id,
                is_active=True,
                approval_mode="manual_for_sensitive",
                min_posts_per_day=1,
                max_posts_per_day=3,
                quiet_hours_start=22,
                quiet_hours_end=7,
                restricted_keywords=["controversial", "guaranteed returns", "unverified"],
                target_topics=["Industry Trends", "Productivity Tips", "Product Showcase"],
            )
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
        return cfg

    def validate_media(
        self,
        image_url: Optional[str],
        caption: Optional[str] = None,
        aspect_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validate media URL structure, format, aspect ratio, and Instagram publishing specs.
        
        Instagram specs:
        - Must be public HTTPS URL.
        - Supported formats: JPG, JPEG, PNG, WebP (GIF is not supported for feed posts).
        - Aspect ratio must be between 4:5 (0.80) and 1.91:1 (1.91).
        - Caption must not exceed 2,200 characters.
        - Hashtags must not exceed 30.
        """
        if not image_url:
            return {"valid": False, "reason": "Missing media URL"}

        url = image_url.strip()
        if not url.startswith("https://"):
            return {
                "valid": False,
                "reason": "URL must begin with https:// (Instagram requires secure public HTTPS URLs)",
            }

        # Check for valid image extensions or recognized media hosting path
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        url_lower = url.lower()
        if ".gif" in url_lower:
            return {"valid": False, "reason": "GIF format is not supported for Instagram feed posts. Use JPG or PNG."}

        has_ext = any(url_lower.endswith(ext) or (ext + "?") in url_lower for ext in valid_extensions)
        is_known_host = any(h in url_lower for h in ["images.unsplash.com", "via.placeholder.com", "minio", "s3.amazonaws.com", "cdn"])

        if not (has_ext or is_known_host):
            return {"valid": False, "reason": "Unsupported media format. Expected JPG, JPEG, PNG, or WebP"}

        # Aspect ratio check if provided
        if aspect_ratio is not None:
            if aspect_ratio < 0.79 or aspect_ratio > 1.92:
                return {
                    "valid": False,
                    "reason": f"Invalid aspect ratio ({aspect_ratio:.2f}). Instagram requires between 4:5 (0.80) and 1.91:1 (1.91).",
                }

        # Caption constraints check
        if caption:
            if len(caption) > 2200:
                return {"valid": False, "reason": "Caption exceeds Instagram limit of 2,200 characters"}
            hashtag_count = len(re.findall(r"#\w+", caption))
            if hashtag_count > 30:
                return {"valid": False, "reason": f"Hashtag count ({hashtag_count}) exceeds Instagram limit of 30"}

        return {"valid": True, "url": url, "format": "image"}

    def is_in_quiet_hours(self, dt: datetime, start_hour: int, end_hour: int) -> bool:
        """Check if target datetime falls within quiet hours (UTC)."""
        h = dt.hour
        if start_hour > end_hour:
            # e.g., 22:00 to 07:00
            return h >= start_hour or h < end_hour
        else:
            return start_hour <= h < end_hour

    def compute_adaptive_slot(
        self,
        target_date: datetime,
        post_index_for_day: int,
        start_quiet: int,
        end_quiet: int,
        strategy_hour: int = 14,
        scheduling_basis: str = "hypothesis",
    ) -> datetime:
        """Compute an optimal posting time slot that strictly avoids quiet hours.

        Args:
            strategy_hour: Primary UTC hour to use (may be evidence-based or hypothesis).
            scheduling_basis: 'live_data_verified' | 'hypothesis' — recorded in audit log.
        """
        # Candidate hours spaced throughout daytime: lead with evidence-based hour
        candidate_hours = [strategy_hour, 10, 18, 12, 16]
        hour = candidate_hours[post_index_for_day % len(candidate_hours)]

        slot = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)

        # If falls in quiet hours, shift into safe morning window
        if self.is_in_quiet_hours(slot, start_quiet, end_quiet):
            safe_hour = (end_quiet + 1) % 24
            slot = slot.replace(hour=safe_hour)

        return slot

    def screen_content_policy(
        self, text: str, restricted_keywords: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Screen content against prohibited words and sensitive policy rules."""
        if not restricted_keywords:
            return {"passed": True, "flagged_terms": []}

        lower = text.lower()
        flagged = [term for term in restricted_keywords if term.lower() in lower]

        return {
            "passed": len(flagged) == 0,
            "flagged_terms": flagged,
            "requires_approval": len(flagged) > 0,
        }

    async def generate_platform_content(
        self,
        niche: str,
        audience: str,
        tone: str,
        target_topic: str,
        recommended_hook: str,
        day_offset: int,
        format_info: Optional[Dict[str, str]] = None,
        attempt: int = 1,
    ) -> Dict[str, Any]:
        """Generate platform-ready post content using OpenAI when available, or a grounded fallback template.
        
        CRITICAL RULES:
        1. Never invent fake statistics or unverified percentage claims.
        2. Ground insights in established principles, actionable frameworks, or observational questions.
        3. Clearly identify whether the content was AI-generated or produced by a fallback template.
        4. Support varied formats (educational_tips, question, checklist, contrarian_insight, promotional_offer).
        """
        is_ai_generated = False
        source = "fallback_template" if not settings.USE_MOCK else "mock_simulation"
        fmt_name = format_info.get("format", "single_image") if format_info else "single_image"
        fmt_angle = format_info.get("angle", "Actionable perspective") if format_info else "Actionable perspective"

        if not settings.USE_MOCK and settings.OPENAI_API_KEY:
            try:
                ai_provider = get_ai_provider()
                prompt = (
                    f"You are an expert social media creator and strategist for Instagram.\n"
                    f"Create an authentic, high-value, niche-specific Instagram post for a brand in the '{niche}' niche.\n"
                    f"Target audience: {audience}.\n"
                    f"Brand voice and tone: {tone}.\n"
                    f"Primary topic: {target_topic}.\n"
                    f"Content format: {fmt_name} (Angle: {fmt_angle}).\n"
                    f"Hook format to utilize: {recommended_hook} (attempt variation: {attempt}).\n\n"
                    f"CRITICAL COMPLIANCE RULES:\n"
                    f"1. Do NOT invent statistics, fake percentages, or present unverified survey numbers as facts.\n"
                    f"2. Ground insights in proven principles, actionable steps, or thought-provoking questions.\n"
                    f"3. Keep the body concise and formatted with line breaks for Instagram readability.\n"
                    f"4. Include a clear call-to-action (CTA) encouraging comments, saves, or shares.\n"
                    f"5. Include 4-7 relevant hashtags (under 30 total).\n"
                    f"6. Total caption must be under 2,200 characters.\n\n"
                    f"Return ONLY a JSON object with exactly these keys:\n"
                    f"{{\n"
                    f'  "concept": "A 3-6 word theme for this post",\n'
                    f'  "hook": "The compelling opening line",\n'
                    f'  "script_or_body": "The core educational or inspirational body text",\n'
                    f'  "call_to_action": "The closing CTA",\n'
                    f'  "hashtags": "#Tag1 #Tag2 #Tag3",\n'
                    f'  "caption": "The complete combined caption ready to publish"\n'
                    f"}}"
                )
                ai_res = await ai_provider.generate(prompt)
                parsed: Optional[Dict[str, Any]] = None
                if isinstance(ai_res, dict):
                    if "ideas" in ai_res and isinstance(ai_res["ideas"], list) and ai_res["ideas"]:
                        first = ai_res["ideas"][0]
                        if isinstance(first, dict):
                            parsed = first
                    elif "caption" in ai_res:
                        parsed = ai_res

                if parsed and parsed.get("caption"):
                    concept = parsed.get("concept") or parsed.get("title") or f"{niche} {target_topic}: Day {day_offset}"
                    hook = parsed.get("hook") or parsed.get("caption", "").split("\n")[0]
                    script_body = parsed.get("script_or_body") or parsed.get("description") or parsed.get("caption")
                    cta = parsed.get("call_to_action") or "Save this post and drop your perspective below!"
                    hashtags = parsed.get("hashtags") or f"#{niche.replace(' ', '')} #Strategy #Growth"
                    caption = parsed.get("caption")
                    if not caption:
                        caption = f"{hook}\n\n{script_body}\n\n{cta}\n\n{hashtags}"

                    return {
                        "concept": concept,
                        "hook": hook,
                        "script_or_body": script_body,
                        "call_to_action": cta,
                        "hashtags": hashtags,
                        "caption": caption,
                        "is_ai_generated": True,
                        "source": "openai",
                        "format": fmt_name,
                    }
            except Exception as e:
                log.warning("AI content generation failed, falling back to grounded template: %s", e)

        # Grounded Fallback Template (NO fake statistics, distinct per day, format, and attempt!)
        concept = f"{target_topic} ({fmt_angle}): Day {day_offset}"
        if fmt_name == "question" or recommended_hook == "question":
            hook = f"What is the single biggest operational bottleneck holding your {niche} brand back regarding {target_topic}?"
            script_body = (
                f"Most leaders focus on symptoms rather than root causes.\n\n"
                f"When addressing {target_topic.lower()}:\n"
                f"- Are expectations aligned with team bandwidth?\n"
                f"- Is your tooling supporting or obstructing workflow?\n"
                f"- What metric are you prioritizing this quarter?"
            )
            cta = "Drop your answer in the comments and let us discuss!"
        elif fmt_name == "checklist" or recommended_hook == "checklist":
            hook = f"The 4-point {target_topic} checklist for high-performing {niche} teams:"
            script_body = (
                f"Before scaling operations, verify:\n"
                f"[ ] Documented repeatable SOPs\n"
                f"[ ] Real-time performance visibility\n"
                f"[ ] Clear delegation lines\n"
                f"[ ] Automated data collection"
            )
            cta = "Bookmark this checklist for your next planning session!"
        elif fmt_name == "contrarian_insight" or recommended_hook == "contrarian":
            hook = f"Why relying on disconnected manual routines is slowing your {target_topic} momentum:"
            script_body = (
                f"Working harder is not an operating strategy.\n\n"
                f"Top operators in {niche} build leverage by automating repetitive workflows "
                f"and investing deep focus into creative direction and customer relationships."
            )
            cta = "Save this reminder and share it with someone who needs it today."
        elif fmt_name == "promotional_offer" or recommended_hook == "promotional":
            hook = f"Ready to streamline your {target_topic} in {niche}?"
            script_body = (
                f"Stop losing hours every week to fragmented tasks.\n\n"
                f"Our structured workflows allow teams to focus on revenue-generating strategy "
                f"while automation handles the repetitive heavy lifting."
            )
            cta = "Click the link in bio to explore how to get started today."
        else:
            # educational_tips / framework
            hook = f"The 3 core pillars behind high-performing {target_topic} in {niche}:"
            script_body = (
                f"Here is the proven execution model:\n"
                f"1. Continuous research and feedback detection\n"
                f"2. Consistent value-driven distribution\n"
                f"3. Objective performance analysis and rapid iteration."
            )
            cta = "Save this framework for your team and follow for more actionable insights!"

        # Ensure variation between attempts if retry is triggered
        if attempt > 1:
            hook = f"[Variation {attempt}] {hook}"

        clean_tag = re.sub(r'[^a-zA-Z0-9]', '', niche)
        topic_tag = re.sub(r'[^a-zA-Z0-9]', '', target_topic)
        hashtags = f"#{clean_tag} #{topic_tag} #Operations #Strategy #Growth"
        full_caption = f"{hook}\n\n{script_body}\n\n{cta}\n\n{hashtags}"

        return {
            "concept": concept,
            "hook": hook,
            "script_or_body": script_body,
            "call_to_action": cta,
            "hashtags": hashtags,
            "caption": full_caption,
            "is_ai_generated": is_ai_generated,
            "source": source,
            "format": fmt_name,
        }

    async def run_autonomous_cycle(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Execute one complete autonomous creator cycle for a workspace:
        
        1. Ingest analytics observations for published posts (idempotent – skips already-observed posts).
        2. Formulate learning hypotheses & strategy updates.
        3. Check policy & pause state.
        4. Maintain rolling 3-day content plan with platform-ready posts.
        5. Screen sensitive content & enforce approval queues.
        6. Log full cycle decisions to audit trail.

        Safe to retry: the duplicate-observation guard and existing-post check
        ensure reruns produce no duplicate schedules or observations.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cfg = await self.get_or_create_config(db, workspace_id)

        # 1. Ingest analytics and update learning strategy
        observations = await learning_engine.ingest_post_observations(
            db, workspace_id, is_mock=settings.USE_MOCK
        )
        insights = await learning_engine.update_strategy_insights(
            db, workspace_id, is_mock=settings.USE_MOCK
        )
        # Use live strategy only when not in mock mode; mock strategy is informational only
        strategy = await learning_engine.get_active_strategy(
            db, workspace_id, require_live=not settings.USE_MOCK
        )

        # 2. Check if workspace automation is paused
        if not cfg.is_active:
            audit = AutomationAuditLog(
                workspace_id=workspace_id,
                action="policy_pause",
                status="blocked",
                summary="Autonomous creator cycle paused by workspace policy",
                details={"is_active": False},
                created_at=now,
            )
            db.add(audit)
            await db.commit()
            return {
                "status": "paused",
                "observations_ingested": len(observations),
                "strategy_insights": len(insights),
                "new_posts_planned": 0,
            }

        # 3. Check Meta token validity (if live mode)
        if not settings.USE_MOCK:
            token_res = await db.execute(
                select(MetaToken).where(MetaToken.user_id == cfg.id)  # or owner
            )
            token = token_res.scalar_one_or_none()
            if token and token.expires_at and token.expires_at < now:
                log.warning("Workspace %s has an expired Meta token – pausing autonomous scheduling", workspace_id)
                cfg.is_active = False
                audit = AutomationAuditLog(
                    workspace_id=workspace_id,
                    action="policy_pause",
                    status="blocked",
                    summary="Paused autonomous creator due to expired platform credentials",
                    details={"error": "Expired Meta token"},
                    created_at=now,
                )
                db.add(audit)
                await db.commit()
                return {"status": "paused_expired_token"}

        # 4. Check active brand profiles
        brand_res = await db.execute(
            select(BrandProfile).where(BrandProfile.workspace_id == workspace_id)
        )
        brands = brand_res.scalars().all()
        active_brand = brands[0] if brands else None

        niche = active_brand.niche if active_brand else "Tech & AI Innovations"
        audience = active_brand.target_audience if active_brand else "Marketers & Founders"
        tone = active_brand.tone if active_brand else "informative & inspiring"

        # 5. Conduct real trend research for niche
        research_res = await conduct_workspace_research(db, workspace_id, niche)
        trend_topics = [t["title"] for t in research_res.get("trends", [])]
        available_topics = trend_topics or cfg.target_topics or [
            "Industry Trends",
            "Practical Tips",
            "Operating Frameworks",
            "Common Mistakes",
            "Case Studies",
            "Tool Recommendations",
            "Strategic Predictions",
        ]

        # 6. Maintain rolling content plan across rolling 7 days (checking existing history for duplicates)
        new_posts: List[ScheduledPost] = []
        recommended_hook = strategy.get("recommended_hook_type", "statistic")

        # Load recent 7-day post window to prevent duplicates or topic repeats
        recent_posts = await get_recent_posts_in_window(db, workspace_id, days=7, reference_time=now)
        existing_captions = [p["caption"] for p in recent_posts if p.get("caption")]

        for day_offset in range(1, 8):
            target_date = now + timedelta(days=day_offset)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

            # Check existing posts on this day
            existing_count_res = await db.execute(
                select(func.count())
                .select_from(ScheduledPost)
                .where(
                    ScheduledPost.workspace_id == workspace_id,
                    ScheduledPost.scheduled_time >= start_of_day,
                    ScheduledPost.scheduled_time <= end_of_day,
                    ScheduledPost.status.in_(["scheduled", "pending_approval", "published"]),
                )
            )
            count = existing_count_res.scalar() or 0

            # If below minimum, plan up to min_posts_per_day
            while count < cfg.min_posts_per_day:
                # Phase 7: use evidence-based hour when sufficient live data exists
                hour_rec = await get_best_hour_for_day(db, workspace_id, post_index=count)
                slot_time = self.compute_adaptive_slot(
                    target_date,
                    post_index_for_day=count,
                    start_quiet=cfg.quiet_hours_start,
                    end_quiet=cfg.quiet_hours_end,
                    strategy_hour=hour_rec["hour_utc"],
                    scheduling_basis=hour_rec["data_basis"],
                )

                # Pick distinct topic from verified trends or defaults
                target_topic = available_topics[(day_offset + count) % len(available_topics)]
                format_info = pick_distinct_format_and_angle(day_offset, count)

                # Uniqueness Retry Loop: Attempt up to 3 times to generate a distinct caption
                max_retries = 3
                unique_content_payload: Optional[Dict[str, Any]] = None

                for attempt in range(1, max_retries + 1):
                    content_payload = await self.generate_platform_content(
                        niche=niche,
                        audience=audience,
                        tone=tone,
                        target_topic=target_topic,
                        recommended_hook=format_info["hook_style"],
                        day_offset=day_offset,
                        format_info=format_info,
                        attempt=attempt,
                    )
                    candidate_caption = content_payload["caption"]
                    is_dup, matched_text, sim = is_duplicate_or_near_duplicate(
                        candidate_caption, existing_captions, threshold=0.75
                    )
                    if not is_dup:
                        unique_content_payload = content_payload
                        break
                    log.warning(
                        "Duplicate/near-duplicate detected on day %d (attempt %d, similarity=%.2f): %s",
                        day_offset,
                        attempt,
                        sim,
                        matched_text,
                    )

                if not unique_content_payload:
                    log.error(
                        "Uniqueness retry exhausted for workspace %s on day %d. Skipping duplicate.",
                        workspace_id,
                        day_offset,
                    )
                    audit = AutomationAuditLog(
                        workspace_id=workspace_id,
                        action="plan_generation_skipped",
                        status="exhausted_retries",
                        summary=f"Skipped scheduling duplicate for {slot_time.strftime('%Y-%m-%d %H:%M UTC')} after {max_retries} attempts",
                        details={"topic": target_topic, "day_offset": day_offset},
                        created_at=now,
                    )
                    db.add(audit)
                    count += 1
                    continue

                concept = unique_content_payload["concept"]
                hook = unique_content_payload["hook"]
                script_body = unique_content_payload["script_or_body"]
                cta = unique_content_payload["call_to_action"]
                hashtags = unique_content_payload["hashtags"]
                full_caption = unique_content_payload["caption"]
                is_ai_generated = unique_content_payload["is_ai_generated"]
                content_source = unique_content_payload["source"]

                # Topic-specific image generation / retrieval
                image_res = await generate_topic_image(
                    prompt=f"{concept}: {hook}",
                    niche=niche,
                    topic=target_topic,
                    prefer_ai=False,
                )
                media_url = image_res["url"]
                
                # Phase 8: Pre-publish validation check
                pre_pub_validation = await validate_post_for_publishing(
                    caption=full_caption,
                    image_url=media_url,
                    is_mock=settings.USE_MOCK,
                    check_reachability=False,
                )
                media_validation = self.validate_media(media_url, caption=full_caption)

                # Content policy screening
                screening = self.screen_content_policy(full_caption, cfg.restricted_keywords)
                requires_approval = False
                post_status = "scheduled"

                if not screening["passed"] or cfg.approval_mode == "manual" or not pre_pub_validation.passed:
                    requires_approval = True
                    post_status = "pending_approval"

                post = ScheduledPost(
                    workspace_id=workspace_id,
                    concept=concept,
                    hook=hook,
                    script_or_body=script_body,
                    call_to_action=cta,
                    caption=full_caption,
                    image_url=media_url if media_validation["valid"] else None,
                    scheduled_time=slot_time,
                    status=post_status,
                    requires_approval=requires_approval,
                )
                db.add(post)
                new_posts.append(post)
                existing_captions.append(full_caption)

                # Audit log creation with content provenance & scheduling basis
                audit = AutomationAuditLog(
                    workspace_id=workspace_id,
                    action="plan_generation",
                    status="success" if not requires_approval else "pending_review",
                    summary=f"Planned post for {slot_time.strftime('%Y-%m-%d %H:%M UTC')} ({post_status}, source={content_source}, format={format_info['format']}, basis={hour_rec['data_basis']})",
                    details={
                        "concept": concept,
                        "hook_type": format_info["hook_style"],
                        "format": format_info["format"],
                        "requires_approval": requires_approval,
                        "flagged_terms": screening.get("flagged_terms", []),
                        "scheduled_time": slot_time.isoformat(),
                        "scheduling_basis": hour_rec["data_basis"],
                        "is_ai_generated": is_ai_generated,
                        "source": content_source,
                        "media_valid": media_validation["valid"],
                        "pre_publish_valid": pre_pub_validation.passed,
                        "validation_failures": pre_pub_validation.failures,
                    },
                    created_at=now,
                )
                db.add(audit)

                count += 1

        await db.commit()

        # Audit overall cycle
        final_audit = AutomationAuditLog(
            workspace_id=workspace_id,
            action="autonomous_cycle",
            status="success",
            summary=f"Completed autonomous creator loop: {len(new_posts)} posts planned, {len(observations)} observations ingested",
            details={
                "new_posts_count": len(new_posts),
                "observations_count": len(observations),
                "strategy_hook": recommended_hook,
            },
            created_at=now,
        )
        db.add(final_audit)
        await db.commit()

        return {
            "status": "success",
            "observations_ingested": len(observations),
            "strategy_insights": len(insights),
            "new_posts_planned": len(new_posts),
            "active_strategy": strategy,
        }


autonomous_engine = AutonomousEngine()
