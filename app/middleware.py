from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import RateLimitConfig
from app.limiter import InMemoryRateLimiter
from app.models import ErrorResponse


class RateLimitMiddleware:
    def __init__(self, app: FastAPI, limiter: InMemoryRateLimiter, config: RateLimitConfig) -> None:
        self.app = app
        self.limiter = limiter
        self.config = config
        self._exempt_paths = set(config.exempt_paths)
        self._route_rules = config.routes
        self._route_rules.sort(key=lambda route: len(route["path_prefix"]), reverse=True)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        if self._is_exempt(path):
            await self.app(scope, receive, send)
            return

        organization_id = request.headers.get("X-Org-ID")
        if not organization_id:
            response = JSONResponse(
                status_code=400,
                content={
                    "error": "missing_organization_id",
                    "message": "The X-Org-ID header is required for protected routes.",
                },
            )
            await response(scope, receive, send)
            return

        plan = self._plan_for_organization(organization_id)
        endpoint_category = self._classify_endpoint(path, request.method)
        decision = self.limiter.check_request(organization_id, plan, endpoint_category)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                header_map = {key.decode("latin-1"): value.decode("latin-1") for key, value in headers}
                header_map.update(self._build_header_map(decision, organization_id, endpoint_category))
                message["headers"] = [
                    (key.encode("latin-1"), value.encode("latin-1"))
                    for key, value in header_map.items()
                ]
            await send(message)

        if not decision.allowed:
            response = self._build_rate_limit_response(request, organization_id, endpoint_category, decision)
            await response(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send_wrapper)

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self._exempt_paths)

    def _plan_for_organization(self, organization_id: str) -> str:
        config = self.config.organizations.get(organization_id)
        return config["plan"] if config else self.config.default_plan

    def _classify_endpoint(self, path: str, method: str) -> str:
        for route in self._route_rules:
            if path.startswith(route["path_prefix"]):
                return route["category"]
        if method in {"GET", "HEAD", "OPTIONS"}:
            return "read"
        return "write"

    def _build_rate_limit_response(self, request: Request, organization_id: str, endpoint_category: str, decision) -> JSONResponse:
        payload = {
            "error": "rate_limit_exceeded",
            "message": decision.message or "Rate limit exceeded.",
            "limit_type": decision.violated_limit_type,
            "endpoint_category": endpoint_category,
            "organization_id": organization_id,
            "limit": decision.organization_limit if decision.violated_limit_type == "organization" else decision.endpoint_limit,
            "window_seconds": 60,
            "retry_after_seconds": decision.retry_after_seconds,
        }
        response = JSONResponse(status_code=429, content=payload)
        response.headers.update(self._build_header_map(decision, organization_id, endpoint_category))
        response.headers["Retry-After"] = str(decision.retry_after_seconds or 1)
        return response

    def _build_header_map(self, decision, organization_id: str, endpoint_category: str) -> dict[str, str]:
        return {
            "X-RateLimit-Org-Limit": str(decision.organization_limit or 0),
            "X-RateLimit-Org-Remaining": str(decision.organization_remaining or 0),
            "X-RateLimit-Endpoint-Limit": str(decision.endpoint_limit or 0),
            "X-RateLimit-Endpoint-Remaining": str(decision.endpoint_remaining or 0),
            "X-RateLimit-Policy": f"org:{decision.violated_limit_type or 'none'}",
        }
