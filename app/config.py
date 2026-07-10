from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class RateLimitRuleModel(BaseModel):
    requests: int = Field(gt=0)
    window_seconds: int = Field(gt=0)
    burst: int = Field(ge=0)


class PlanModel(BaseModel):
    organization: RateLimitRuleModel


class OrganizationModel(BaseModel):
    plan: str


class RouteRuleModel(BaseModel):
    path_prefix: str
    category: str


class CleanupModel(BaseModel):
    idle_ttl_seconds: int = Field(ge=0)
    cleanup_interval_seconds: int = Field(ge=0)


class RateLimitConfigModel(BaseModel):
    plans: dict[str, PlanModel]
    organizations: dict[str, OrganizationModel]
    endpoint_limits: dict[str, RateLimitRuleModel]
    routes: list[RouteRuleModel]
    cleanup: CleanupModel
    default_plan: str
    exempt_paths: list[str]

    @field_validator("plans")
    @classmethod
    def validate_plans(cls, value: dict[str, PlanModel]) -> dict[str, PlanModel]:
        if not value:
            raise ValueError("At least one plan must be configured")
        return value

    @field_validator("endpoint_limits")
    @classmethod
    def validate_endpoint_limits(cls, value: dict[str, RateLimitRuleModel]) -> dict[str, RateLimitRuleModel]:
        if not value:
            raise ValueError("At least one endpoint category must be configured")
        return value


class RateLimitConfig:
    def __init__(self, **kwargs: Any) -> None:
        self.plans = kwargs["plans"]
        self.organizations = kwargs["organizations"]
        self.endpoint_limits = kwargs["endpoint_limits"]
        self.routes = kwargs["routes"]
        self.cleanup = kwargs["cleanup"]
        self.default_plan = kwargs["default_plan"]
        self.exempt_paths = kwargs["exempt_paths"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans": self.plans,
            "organizations": self.organizations,
            "endpoint_limits": self.endpoint_limits,
            "routes": self.routes,
            "cleanup": self.cleanup,
            "default_plan": self.default_plan,
            "exempt_paths": self.exempt_paths,
        }


def load_config(data: dict[str, Any] | None = None) -> RateLimitConfig:
    if data is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "rate_limits.yaml"
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    try:
        parsed = RateLimitConfigModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid configuration: {exc}") from exc

    if parsed.default_plan not in parsed.plans:
        raise ValueError("default_plan must reference an existing plan")

    result = {
        "plans": {name: {"organization": {"requests": plan.organization.requests, "window_seconds": plan.organization.window_seconds, "burst": plan.organization.burst}} for name, plan in parsed.plans.items()},
        "organizations": {name: {"plan": org.plan} for name, org in parsed.organizations.items()},
        "endpoint_limits": {name: {"requests": rule.requests, "window_seconds": rule.window_seconds, "burst": rule.burst} for name, rule in parsed.endpoint_limits.items()},
        "routes": [{"path_prefix": route.path_prefix, "category": route.category} for route in parsed.routes],
        "cleanup": {"idle_ttl_seconds": parsed.cleanup.idle_ttl_seconds, "cleanup_interval_seconds": parsed.cleanup.cleanup_interval_seconds},
        "default_plan": parsed.default_plan,
        "exempt_paths": parsed.exempt_paths,
    }
    return RateLimitConfig(**result)
