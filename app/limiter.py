from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Callable

from app.config import RateLimitConfig
from app.models import LimiterStats, RateLimitDecision, RateLimitRule, SlidingWindowState


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig, now_func: Callable[[], float] | None = None) -> None:
        self.config = config
        self.now_func = now_func or time.monotonic
        self._lock = threading.Lock()
        self._buckets: dict[str, SlidingWindowState] = {}
        self._stats = LimiterStats()
        self._last_cleanup = self.now_func()

    def check_request(self, organization_id: str, plan: str, endpoint_category: str) -> RateLimitDecision:
        now = self.now_func()
        with self._lock:
            self._maybe_cleanup(now)

            org_bucket_key = f"org:{organization_id}"
            endpoint_bucket_key = f"org:{organization_id}:category:{endpoint_category}"

            org_bucket = self._get_or_create_bucket(org_bucket_key, self._plan_rule(plan), now)
            endpoint_bucket = self._get_or_create_bucket(endpoint_bucket_key, self._endpoint_rule(endpoint_category), now)

            self._prune_bucket(org_bucket, now)
            self._prune_bucket(endpoint_bucket, now)

            org_remaining = max(0, org_bucket.limit - len(org_bucket.timestamps))
            endpoint_remaining = max(0, endpoint_bucket.limit - len(endpoint_bucket.timestamps))

            if len(org_bucket.timestamps) >= org_bucket.limit:
                self._stats.rejected_requests += 1
                self._stats.organization_rejections += 1
                return RateLimitDecision(
                    allowed=False,
                    violated_limit_type="organization",
                    retry_after_seconds=self._retry_after_seconds(org_bucket, now),
                    organization_limit=org_bucket.limit,
                    organization_remaining=org_remaining,
                    endpoint_limit=endpoint_bucket.limit,
                    endpoint_remaining=endpoint_remaining,
                    endpoint_category=endpoint_category,
                    message="Organization rate limit exceeded.",
                )

            if len(endpoint_bucket.timestamps) >= endpoint_bucket.limit:
                self._stats.rejected_requests += 1
                self._stats.endpoint_rejections += 1
                return RateLimitDecision(
                    allowed=False,
                    violated_limit_type="endpoint",
                    retry_after_seconds=self._retry_after_seconds(endpoint_bucket, now),
                    organization_limit=org_bucket.limit,
                    organization_remaining=org_remaining,
                    endpoint_limit=endpoint_bucket.limit,
                    endpoint_remaining=endpoint_remaining,
                    endpoint_category=endpoint_category,
                    message="Write endpoint rate limit exceeded." if endpoint_category == "write" else "Endpoint rate limit exceeded.",
                )

            org_bucket.timestamps.append(now)
            endpoint_bucket.timestamps.append(now)
            org_bucket.last_accessed = now
            endpoint_bucket.last_accessed = now
            self._stats.allowed_requests += 1
            return RateLimitDecision(
                allowed=True,
                organization_limit=org_bucket.limit,
                organization_remaining=max(0, org_bucket.limit - len(org_bucket.timestamps)),
                endpoint_limit=endpoint_bucket.limit,
                endpoint_remaining=max(0, endpoint_bucket.limit - len(endpoint_bucket.timestamps)),
                endpoint_category=endpoint_category,
            )

    def cleanup(self, now: float | None = None) -> int:
        now = now if now is not None else self.now_func()
        with self._lock:
            self._maybe_cleanup(now, force=True)
            return len(self._buckets)

    def active_bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    def stats(self) -> dict[str, object]:
        with self._lock:
            self._stats.active_bucket_count = len(self._buckets)
            return self._stats.to_dict()

    def _plan_rule(self, plan: str) -> RateLimitRule:
        plan_config = self.config.plans.get(plan) or self.config.plans[self.config.default_plan]
        rule = plan_config["organization"]
        return RateLimitRule(requests=rule["requests"], window_seconds=rule["window_seconds"], burst=rule["burst"])

    def _endpoint_rule(self, endpoint_category: str) -> RateLimitRule:
        rule = self.config.endpoint_limits.get(endpoint_category)
        if rule is None:
            rule = self.config.endpoint_limits.get("read", {"requests": 120, "window_seconds": 60, "burst": 30})
        return RateLimitRule(requests=rule["requests"], window_seconds=rule["window_seconds"], burst=rule["burst"])

    def _get_or_create_bucket(self, key: str, rule: RateLimitRule, now: float) -> SlidingWindowState:
        bucket = self._buckets.get(key)
        if bucket is None:
            effective_limit = max(1, rule.requests + rule.burst)
            bucket = SlidingWindowState(
                timestamps=deque(),
                limit=effective_limit,
                window_seconds=rule.window_seconds,
                last_accessed=now,
            )
            self._buckets[key] = bucket
        return bucket

    def _prune_bucket(self, bucket: SlidingWindowState, now: float) -> None:
        cutoff = now - bucket.window_seconds
        while bucket.timestamps and bucket.timestamps[0] <= cutoff:
            bucket.timestamps.popleft()
        bucket.last_accessed = now

    def _maybe_cleanup(self, now: float, force: bool = False) -> None:
        interval = self.config.cleanup["cleanup_interval_seconds"]
        if not force and interval > 0 and (now - self._last_cleanup) < interval:
            return
        ttl = self.config.cleanup["idle_ttl_seconds"]
        if ttl < 0:
            return
        removable = [key for key, bucket in self._buckets.items() if (now - bucket.last_accessed) > ttl]
        for key in removable:
            del self._buckets[key]
        self._last_cleanup = now
        self._stats.last_cleanup_time = now
        self._stats.last_cleanup_bucket_count = len(self._buckets)

    def _retry_after_seconds(self, bucket: SlidingWindowState, now: float) -> int:
        if not bucket.timestamps:
            return 1
        oldest = bucket.timestamps[0]
        wait_seconds = math.ceil((oldest + bucket.window_seconds) - now)
        return max(1, wait_seconds)
