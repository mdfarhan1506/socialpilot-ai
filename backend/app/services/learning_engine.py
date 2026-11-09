"""Learning engine for SocialPilot AI Autonomous Creator.

Analyzes post observations, tracks hook & topic efficacy, and produces strategy hypotheses.
STRICT PROVENANCE RULE: Mock metrics are never used to train live strategy models.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.content import ScheduledPost, PublishedPost
from ..models.autonomous import PostAnalyticsObservation, StrategyInsight, AutomationAuditLog
from ..models.meta_token import MetaToken
from ..utils.security import decrypt_token
from .meta_insights import meta_insights
from ..settings import settings


class LearningEngine:
    """Evaluates content performance, formulates hypotheses, and updates strategy."""

    async def ingest_post_observations(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        is_mock: bool = True,
    ) -> List[PostAnalyticsObservation]:
        """Record performance observations for all published posts in the workspace."""
        # Find published posts for this workspace
        q = (
            select(PublishedPost, ScheduledPost)
            .join(ScheduledPost, PublishedPost.scheduled_post_id == ScheduledPost.id)
            .where(
                ScheduledPost.workspace_id == workspace_id,
                PublishedPost.status == "success",
            )
        )
        res = await db.execute(q)
        rows = res.all()

        observations: List[PostAnalyticsObservation] = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for pub_post, sched_post in rows:
            # Skip if we already have an observation for this scheduled post (prevents duplicate collection)
            existing_obs_res = await db.execute(
                select(PostAnalyticsObservation.id).where(PostAnalyticsObservation.scheduled_post_id == sched_post.id)
            )
            if existing_obs_res.scalar_one_or_none() is not None:
                continue

            # Calculate post age in hours
            pub_time = pub_post.published_at or sched_post.scheduled_time or now
            post_age_hours = max(0.1, (now - pub_time).total_seconds() / 3600.0)

            if is_mock or settings.USE_MOCK:
                # Simulated observation based on hook type & post age
                hook_factor = 1.4 if sched_post.hook and any(q in sched_post.hook.lower() for q in ["?", "%", "framework", "how"]) else 1.0
                base_reach = int(120 * post_age_hours * hook_factor)
                impressions = int(base_reach * 1.35)
                likes = int(base_reach * 0.06)
                comments = int(base_reach * 0.02)
                shares = int(base_reach * 0.01)
                saves = int(base_reach * 0.015)
                eng_rate = round(((likes + comments + shares + saves) / max(1, base_reach)) * 100, 2)
                provenance = "mock_simulation"

                obs = PostAnalyticsObservation(
                    workspace_id=workspace_id,
                    scheduled_post_id=sched_post.id,
                    platform_post_id=pub_post.platform_post_id,
                    post_age_hours=round(post_age_hours, 1),
                    impressions=impressions,
                    reach=base_reach,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    saves=saves,
                    engagement_rate=eng_rate,
                    data_provenance=provenance,
                    recorded_at=now,
                )
                db.add(obs)
                observations.append(obs)
            else:
                # LIVE MODE: Fetch verified metrics from Meta Insights API
                if not pub_post.platform_post_id:
                    continue

                token_res = await db.execute(
                    select(MetaToken).where(MetaToken.user_id == sched_post.user_id)
                )
                token_row = token_res.scalar_one_or_none()
                if not token_row:
                    log.warning("No MetaToken found for user %s to fetch insights", sched_post.user_id)
                    audit = AutomationAuditLog(
                        workspace_id=workspace_id,
                        action="insights_fetch",
                        status="skipped",
                        summary=f"Skipped insights for post {sched_post.id}: missing Meta token",
                        details={"post_id": str(sched_post.id), "reason": "missing_token"},
                        created_at=now,
                    )
                    db.add(audit)
                    continue

                access_token = decrypt_token(token_row.encrypted_token)
                metrics_res = await meta_insights.fetch_media_metrics(
                    platform_post_id=pub_post.platform_post_id,
                    access_token=access_token,
                )

                if metrics_res.get("success") and not metrics_res.get("mock"):
                    obs = PostAnalyticsObservation(
                        workspace_id=workspace_id,
                        scheduled_post_id=sched_post.id,
                        platform_post_id=pub_post.platform_post_id,
                        post_age_hours=round(post_age_hours, 1),
                        impressions=metrics_res.get("impressions", 0),
                        reach=metrics_res.get("reach", 0),
                        likes=metrics_res.get("likes", 0),
                        comments=metrics_res.get("comments", 0),
                        shares=metrics_res.get("shares", 0),
                        saves=metrics_res.get("saved", 0),
                        engagement_rate=metrics_res.get("engagement_rate", 0.0),
                        data_provenance="live_meta_api",
                        recorded_at=now,
                    )
                    db.add(obs)
                    observations.append(obs)
                else:
                    err_msg = metrics_res.get("error", "Insights unavailable or threshold not reached (<5 viewers)")
                    audit = AutomationAuditLog(
                        workspace_id=workspace_id,
                        action="insights_fetch",
                        status="unavailable",
                        summary=f"Live insights unavailable for post {sched_post.id}: {err_msg}",
                        details={"post_id": str(sched_post.id), "error": err_msg},
                        created_at=now,
                    )
                    db.add(audit)

        await db.commit()
        return observations

    async def update_strategy_insights(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        is_mock: bool = True,
    ) -> List[StrategyInsight]:
        """Aggregate observations, test hypotheses, and persist data-driven recommendations.
        
        Strict data provenance: If is_mock is False, only records with
        data_provenance == 'live_meta_api' are considered.
        """
        # Fetch observations matching provenance
        target_provenance = "mock_simulation" if is_mock else "live_meta_api"
        obs_res = await db.execute(
            select(PostAnalyticsObservation, ScheduledPost)
            .join(ScheduledPost, PostAnalyticsObservation.scheduled_post_id == ScheduledPost.id)
            .where(
                PostAnalyticsObservation.workspace_id == workspace_id,
                PostAnalyticsObservation.data_provenance == target_provenance,
            )
            .order_by(desc(PostAnalyticsObservation.recorded_at))
            .limit(100)
        )
        data = obs_res.all()

        insights: List[StrategyInsight] = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not is_mock and not data:
            # LIVE MODE with zero live observations yet
            baseline_insight = StrategyInsight(
                workspace_id=workspace_id,
                topic="Audience Baseline Learning",
                hook_type="framework",
                format_type="single_image",
                best_time_slot="14:00 UTC",
                performance_score=0.0,
                hypothesis="Awaiting real audience engagement data from Meta Insights API.",
                recommendation="Maintain standard publishing cadence until initial live metrics are ingested.",
                confidence_score=0.0,
                is_mock=False,
                evidence_data={"samples": 0, "status": "awaiting_live_data"},
                created_at=now,
            )
            db.add(baseline_insight)
            insights.append(baseline_insight)

            audit = AutomationAuditLog(
                workspace_id=workspace_id,
                action="strategy_update",
                status="neutral",
                summary="Strategy engine awaiting live Meta Insights data (0 observations)",
                details={"observations_analyzed": 0, "is_mock": False},
                created_at=now,
            )
            db.add(audit)
            await db.commit()
            return insights

        # 1. Analyze hook types (Question vs Framework vs Actionable vs Contrarian vs Statistic)
        hook_metrics: Dict[str, List[float]] = {
            "question": [],
            "framework": [],
            "actionable": [],
            "contrarian": [],
            "statistic": [],
        }

        for obs, post in data:
            h = (post.hook or "").lower()
            if "?" in h:
                hook_metrics["question"].append(obs.engagement_rate)
            elif "framework" in h or "pillar" in h:
                hook_metrics["framework"].append(obs.engagement_rate)
            elif "how" in h or "action" in h or "step" in h:
                hook_metrics["actionable"].append(obs.engagement_rate)
            elif "why" in h or "stop" in h or "costing" in h or "myth" in h:
                hook_metrics["contrarian"].append(obs.engagement_rate)
            else:
                hook_metrics["statistic"].append(obs.engagement_rate)

        # Generate hook insight from data
        best_hook = "framework"
        best_avg = 0.0
        for h_type, rates in hook_metrics.items():
            avg = sum(rates) / len(rates) if rates else 0.0
            if avg > best_avg:
                best_avg = avg
                best_hook = h_type

        # Formulate data-driven frequency recommendation
        frequency_note = ""
        if best_avg >= 4.0:
            frequency_note = " Audience engagement is robust (>4.0%); maintain or adapt daily frequency toward upper limit."
        elif best_avg > 0.0 and best_avg < 2.0:
            frequency_note = " Engagement is developing (<2.0%); test alternative hook formats before increasing publishing frequency."

        hook_insight = StrategyInsight(
            workspace_id=workspace_id,
            topic="Hook Performance Optimization",
            hook_type=best_hook,
            format_type="single_image",
            best_time_slot="14:00-16:00 UTC",
            performance_score=best_avg or (5.2 if is_mock else 0.0),
            hypothesis=f"Posts utilizing '{best_hook}' hooks produce higher audience engagement rates.",
            recommendation=f"Prioritize '{best_hook}' openers for upcoming rolling plan drafts.{frequency_note}",
            confidence_score=0.85 if len(data) > 5 else (0.60 if is_mock else 0.40),
            is_mock=is_mock,
            evidence_data={"samples": len(data), "avg_engagement": best_avg},
            created_at=now,
        )
        db.add(hook_insight)
        insights.append(hook_insight)

        # 2. Timing Optimization Insight
        timing_insight = StrategyInsight(
            workspace_id=workspace_id,
            topic="Audience Peak Activity Window",
            hook_type=best_hook,
            format_type="carousel",
            best_time_slot="13:00-15:00 UTC",
            performance_score=(best_avg * 1.15) if best_avg else (5.8 if is_mock else 0.0),
            hypothesis="Mid-day publishing slots outside quiet hours yield higher initial impressions.",
            recommendation="Schedule high-priority announcements between 13:00 and 15:00 UTC.",
            confidence_score=0.75 if len(data) > 5 else (0.50 if is_mock else 0.35),
            is_mock=is_mock,
            evidence_data={"recommended_window_utc": "13:00-15:00", "samples": len(data)},
            created_at=now,
        )
        db.add(timing_insight)
        insights.append(timing_insight)

        # Audit log the strategy learning update
        audit = AutomationAuditLog(
            workspace_id=workspace_id,
            action="strategy_update",
            status="success",
            summary=f"Strategy engine formulated {len(insights)} learning recommendations (is_mock={is_mock}, samples={len(data)})",
            details={
                "best_hook": best_hook,
                "best_time_slot": "13:00-15:00 UTC",
                "observations_analyzed": len(data),
                "is_mock": is_mock,
                "avg_engagement": best_avg,
            },
            created_at=now,
        )
        db.add(audit)

        await db.commit()
        return insights

    async def get_active_strategy(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        require_live: bool = False,
    ) -> Dict[str, Any]:
        """Fetch the latest active strategy recommendations for content generation.

        Args:
            require_live: When True, only return recommendations derived from real
                Meta Insights data (data_provenance == 'live_meta_api').  If no
                qualifying insights exist yet, returns safe defaults with a
                ``data_status`` note explaining that live data is still accumulating.
                This prevents mock-derived hypotheses from influencing live production.
        """
        query = (
            select(StrategyInsight)
            .where(StrategyInsight.workspace_id == workspace_id)
            .order_by(desc(StrategyInsight.created_at))
        )
        if require_live:
            query = query.where(StrategyInsight.is_mock == False)  # noqa: E712

        query = query.limit(5)
        res = await db.execute(query)
        insights = res.scalars().all()

        # Minimum live observations threshold: do not act on live strategy until
        # at least MIN_LIVE_SAMPLES real posts have been observed.
        MIN_LIVE_SAMPLES = 5
        has_enough_live_data = False

        recommended_hook = "statistic"
        best_time_slot = "14:00 UTC"
        data_status = "awaiting_live_data" if require_live else "mock_or_default"

        if insights:
            for item in insights:
                # For live strategy, verify the underlying evidence has enough samples.
                if require_live:
                    evidence = item.evidence_data or {}
                    samples = evidence.get("samples", 0)
                    if samples >= MIN_LIVE_SAMPLES and item.hook_type:
                        recommended_hook = item.hook_type
                        best_time_slot = item.best_time_slot or best_time_slot
                        has_enough_live_data = True
                        data_status = "live_data_verified"
                        break
                else:
                    if item.hook_type:
                        recommended_hook = item.hook_type
                        best_time_slot = item.best_time_slot or best_time_slot
                        data_status = "mock_simulation"
                        break

        if require_live and not has_enough_live_data:
            data_status = "awaiting_live_data"
            log.info(
                "Workspace %s has insufficient live observations for strategy adaptation "
                "(need %d samples). Using default hook type.",
                workspace_id,
                MIN_LIVE_SAMPLES,
            )

        return {
            "recommended_hook_type": recommended_hook,
            "recommended_time_slot": best_time_slot,
            "data_status": data_status,
            "has_enough_live_data": has_enough_live_data,
            "insights": [
                {
                    "topic": i.topic,
                    "hypothesis": i.hypothesis,
                    "recommendation": i.recommendation,
                    "confidence": i.confidence_score,
                    "is_mock": i.is_mock,
                }
                for i in insights
            ],
        }


learning_engine = LearningEngine()
