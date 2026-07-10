import pytest

from app.config import load_config


def test_invalid_configuration_fails_clearly():
    with pytest.raises(ValueError):
        load_config({
            "plans": {},
            "organizations": {},
            "endpoint_limits": {},
            "routes": [],
            "cleanup": {"idle_ttl_seconds": 900, "cleanup_interval_seconds": 60},
            "default_plan": "standard",
            "exempt_paths": [],
        })
