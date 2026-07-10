from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RateLimitRule:
    requests: int
    window_seconds: int
    burst: int


@dataclass(slots=True)
class PlanConfig:
    organization: RateLimitRule


@dataclass(slots=True)
class OrganizationConfig:
    plan: str


@dataclass(slots=True)
class EndpointCategory:
    name: str


@dataclass(slots=True)
class RouteRule:
    path_prefix: str
    category: str


@dataclass(slots=True)
class CleanupConfig:
    idle_ttl_seconds: int
    cleanup_interval_seconds: int


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    violated_limit_type: str | None = None
    retry_after_seconds: int | None = None
    organization_limit: int | None = None
    organization_remaining: int | None = None
    endpoint_limit: int | None = None
    endpoint_remaining: int | None = None
    endpoint_category: str | None = None
    message: str | None = None


@dataclass(slots=True)
class SlidingWindowState:
    timestamps: deque[float]
    limit: int
    window_seconds: int
    last_accessed: float


@dataclass(slots=True)
class ErrorResponse:
    error: str
    message: str
    limit_type: str | None = None
    endpoint_category: str | None = None
    organization_id: str | None = None
    limit: int | None = None
    window_seconds: int | None = None
    retry_after_seconds: int | None = None


@dataclass(slots=True)
class LimiterStats:
    active_bucket_count: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    organization_rejections: int = 0
    endpoint_rejections: int = 0
    last_cleanup_time: float | None = None
    last_cleanup_bucket_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_bucket_count": self.active_bucket_count,
            "allowed_requests": self.allowed_requests,
            "rejected_requests": self.rejected_requests,
            "organization_rejections": self.organization_rejections,
            "endpoint_rejections": self.endpoint_rejections,
            "last_cleanup_time": self.last_cleanup_time,
            "last_cleanup_bucket_count": self.last_cleanup_bucket_count,
        }
