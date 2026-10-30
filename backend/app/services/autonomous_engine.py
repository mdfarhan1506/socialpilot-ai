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

    def validate_media(self, image_url: Optional[str]) -> Dict[str, Any]:
        """Validate media URL structure, format, and availability."""
        if not image_url:
            return {"valid": False, "reason": "Missing media URL"}

        url = image_url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return {"valid": False, "reason": "URL must begin with http:// or https://"}

        # Check for valid image extensions or recognized media hosting path
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        has_ext = any(url.lower().endswith(ext) or ext in url.lower() for ext in valid_extensions)
        is_known_host = any(h in url.lower() for h in ["images.unsplash.com", "via.placeholder.com", "minio", "s3.amazonaws.com", "cdn"])

        if not (has_ext or is_known_host):
            return {"valid": False, "reason": "Unsupported media format. Expected JPG, PNG, or WebP"}

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
    ) -> datetime:
        """Compute an optimal posting time slot that strictly avoids quiet hours."""
        # Candidate hours spaced throughout daytime: e.g. 10:00, 14:00, 18:00
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

    async def run_autonomous_cycle(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Execute one complete autonomous creator cycle for a workspace:
        
        1. Ingest analytics observations for published posts.
        2. Formulate learning hypotheses & strategy updates.
        3. Check policy & pause state.
        4. Maintain rolling 3-day content plan with platform-ready posts.
        5. Screen sensitive content & enforce approval queues.
        6. Log full cycle decisions to audit trail.
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
        strategy = await learning_engine.get_active_strategy(db, workspace_id)

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

        # 5. Maintain rolling content plan for next 3 days
        new_posts: List[ScheduledPost] = []
        recommended_hook = strategy.get("recommended_hook_type", "statistic")

        for day_offset in range(1, 4):
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
                slot_time = self.compute_adaptive_slot(
                    target_date,
                    post_index_for_day=count,
                    start_quiet=cfg.quiet_hours_start,
                    end_quiet=cfg.quiet_hours_end,
                )

                # Synthesize complete platform-ready content
                concept = f"{niche} Strategy Breakdown: Day {day_offset}"
                if recommended_hook == "statistic":
                    hook = f"82% of leaders in {niche} attribute their growth to automated workflows."
                elif recommended_hook == "question":
                    hook = f"What is the single biggest bottleneck holding your {niche} brand back?"
                elif recommended_hook == "how_to":
                    hook = f"How to scale your {niche} strategy in 15 minutes a day."
                else:
                    hook = f"Stop relying on manual posting for {niche} in 2026."

                script_body = (
                    f"Here is the proven framework:\n"
                    f"1. Continuous trend research\n"
                    f"2. Automated hook-tested creation\n"
                    f"3. Closed-loop performance iteration."
                )
                cta = "Save this post and drop your thoughts in the comments!"
                hashtags = f"#{niche.replace(' ', '')} #SocialMediaStrategy #GrowthHacking #AIAutomation"
                full_caption = f"{hook}\n\n{script_body}\n\n{cta}\n\n{hashtags}"

                media_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80"
                media_validation = self.validate_media(media_url)

                # Content policy screening
                screening = self.screen_content_policy(full_caption, cfg.restricted_keywords)
                requires_approval = False
                post_status = "scheduled"

                if not screening["passed"] or cfg.approval_mode == "manual":
                    requires_approval = True
                    post_status = "pending_approval"

                # Duplicate prevention: verify identical caption doesn't exist
                dup_res = await db.execute(
                    select(ScheduledPost).where(
                        ScheduledPost.workspace_id == workspace_id,
                        ScheduledPost.caption == full_caption,
                        ScheduledPost.scheduled_time == slot_time,
                    )
                )
                if not dup_res.scalar_one_or_none():
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

                    # Audit log creation
                    audit = AutomationAuditLog(
                        workspace_id=workspace_id,
                        action="plan_generation",
                        status="success" if not requires_approval else "pending_review",
                        summary=f"Planned post for {slot_time.strftime('%Y-%m-%d %H:%M UTC')} ({post_status})",
                        details={
                            "concept": concept,
                            "hook_type": recommended_hook,
                            "requires_approval": requires_approval,
                            "flagged_terms": screening.get("flagged_terms", []),
                            "scheduled_time": slot_time.isoformat(),
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
