from app.config import RateLimitConfig
from app.limiter import InMemoryRateLimiter


def test_idle_bucket_cleanup_removes_inactive_entries():
    config = RateLimitConfig(
        plans={
            "standard": {"organization": {"requests": 2, "window_seconds": 60, "burst": 1}},
        },
        endpoint_limits={
            "read": {"requests": 2, "window_seconds": 60, "burst": 1},
        },
        organizations={"org-standard": {"plan": "standard"}},
        routes=[],
        cleanup={"idle_ttl_seconds": 0, "cleanup_interval_seconds": 0},
        default_plan="standard",
        exempt_paths=[],
    )
    limiter = InMemoryRateLimiter(config=config, now_func=lambda: 0.0)
    limiter.check_request("org-standard", "standard", "read")

    limiter.cleanup(now=10.0)

    assert limiter.active_bucket_count() == 0


def test_active_buckets_are_not_removed():
    config = RateLimitConfig(
        plans={
            "standard": {"organization": {"requests": 2, "window_seconds": 60, "burst": 1}},
        },
        endpoint_limits={
            "read": {"requests": 2, "window_seconds": 60, "burst": 1},
        },
        organizations={"org-standard": {"plan": "standard"}},
        routes=[],
        cleanup={"idle_ttl_seconds": 100, "cleanup_interval_seconds": 0},
        default_plan="standard",
        exempt_paths=[],
    )
    limiter = InMemoryRateLimiter(config=config, now_func=lambda: 0.0)
    limiter.check_request("org-standard", "standard", "read")

    limiter.cleanup(now=10.0)

    assert limiter.active_bucket_count() == 2
