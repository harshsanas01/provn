import threading
from concurrent.futures import ThreadPoolExecutor

from app.config import RateLimitConfig
from app.limiter import InMemoryRateLimiter


def make_limiter(now_func, config=None):
    if config is None:
        config = RateLimitConfig(
            plans={
                "standard": {"organization": {"requests": 2, "window_seconds": 60, "burst": 1}},
                "premium": {"organization": {"requests": 10, "window_seconds": 60, "burst": 2}},
            },
            endpoint_limits={
                "read": {"requests": 3, "window_seconds": 60, "burst": 1},
                "write": {"requests": 1, "window_seconds": 60, "burst": 0},
                "expensive": {"requests": 1, "window_seconds": 60, "burst": 0},
            },
            organizations={"org-standard": {"plan": "standard"}},
            routes=[],
            cleanup={"idle_ttl_seconds": 900, "cleanup_interval_seconds": 60},
            default_plan="standard",
            exempt_paths=[],
        )
    return InMemoryRateLimiter(config=config, now_func=now_func)


def test_standard_organization_can_make_requests_within_limit():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    first = limiter.check_request("org-standard", "standard", "read")
    second = limiter.check_request("org-standard", "standard", "read")
    third = limiter.check_request("org-standard", "standard", "read")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is True


def test_organization_limit_returns_429():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    decisions = [limiter.check_request("org-standard", "standard", "read") for _ in range(5)]

    assert decisions[0].allowed is True
    assert decisions[1].allowed is True
    assert decisions[2].allowed is True
    assert decisions[3].allowed is False
    assert decisions[3].violated_limit_type == "organization"


def test_write_endpoint_limit_is_stricter_than_read_endpoint_limit():
    current_time = 0.0
    limiter = InMemoryRateLimiter(
        config=RateLimitConfig(
            plans={
                "standard": {"organization": {"requests": 10, "window_seconds": 60, "burst": 2}},
            },
            endpoint_limits={
                "read": {"requests": 3, "window_seconds": 60, "burst": 1},
                "write": {"requests": 1, "window_seconds": 60, "burst": 0},
            },
            organizations={"org-standard": {"plan": "standard"}},
            routes=[],
            cleanup={"idle_ttl_seconds": 900, "cleanup_interval_seconds": 60},
            default_plan="standard",
            exempt_paths=[],
        ),
        now_func=lambda: current_time,
    )

    read_decisions = [limiter.check_request("org-standard", "standard", "read") for _ in range(4)]
    write_decisions = [limiter.check_request("org-standard", "standard", "write") for _ in range(2)]

    assert read_decisions[-1].allowed is True
    assert write_decisions[-1].allowed is False
    assert write_decisions[-1].violated_limit_type == "endpoint"


def test_endpoint_limit_can_be_hit_while_organization_capacity_remains():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    decisions = [limiter.check_request("org-standard", "standard", "write") for _ in range(2)]

    assert decisions[0].allowed is True
    assert decisions[1].allowed is False
    assert decisions[1].violated_limit_type == "endpoint"


def test_organization_limit_can_be_hit_across_multiple_endpoint_categories():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    decisions = [limiter.check_request("org-standard", "standard", category) for category in ["read", "read", "write"]]

    assert decisions[0].allowed is True
    assert decisions[1].allowed is True
    assert decisions[2].allowed is True


def test_successful_request_consumes_both_relevant_buckets():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    limiter.check_request("org-standard", "standard", "write")

    org_bucket = limiter._buckets["org:org-standard"]
    endpoint_bucket = limiter._buckets["org:org-standard:category:write"]

    assert len(org_bucket.timestamps) == 1
    assert len(endpoint_bucket.timestamps) == 1


def test_rejected_request_does_not_partially_consume_capacity():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    limiter.check_request("org-standard", "standard", "write")
    limiter.check_request("org-standard", "standard", "write")

    org_bucket = limiter._buckets["org:org-standard"]
    endpoint_bucket = limiter._buckets["org:org-standard:category:write"]

    assert len(org_bucket.timestamps) == 1
    assert len(endpoint_bucket.timestamps) == 1


def test_retry_after_is_present_and_positive_integer():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    limiter.check_request("org-standard", "standard", "write")
    decision = limiter.check_request("org-standard", "standard", "write")

    assert decision.retry_after_seconds is not None
    assert decision.retry_after_seconds >= 1


def test_window_rolls_off_after_time_advances():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    first = limiter.check_request("org-standard", "standard", "read")
    current_time = 61.0
    second = limiter.check_request("org-standard", "standard", "read")

    assert first.allowed is True
    assert second.allowed is True


def test_burst_behavior_matches_documented_semantics():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    for _ in range(4):
        limiter.check_request("org-standard", "standard", "read")

    org_bucket = limiter._buckets["org:org-standard"]

    assert org_bucket.limit == 3
    assert len(org_bucket.timestamps) == 3


def test_concurrent_checks_do_not_allow_obvious_over_limit_leakage():
    current_time = 0.0
    limiter = make_limiter(lambda: current_time)

    results = []

    def worker():
        results.append(limiter.check_request("org-standard", "standard", "write"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: worker(), range(4)))

    assert sum(1 for item in results if item.allowed) <= 1
