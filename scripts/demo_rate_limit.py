import os
import json
import sys
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-Org-ID": "org-standard"}


def call(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], dict[str, str]]:
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("ALL_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("all_proxy", None)
    with httpx.Client(timeout=5.0, trust_env=False) as client:
        response = client.request(method=method, url=f"{BASE_URL}{path}", headers=HEADERS, json=payload)
        return response.status_code, response.json(), dict(response.headers)


def main() -> None:
    print("Sending read request...")
    status, body, headers = call("/api/items")
    print(status, body, {key: headers[key] for key in headers if key.startswith("X-RateLimit") or key == "Retry-After"})

    print("Sending write requests until the stricter endpoint category limit is hit...")
    for index in range(35):
        status, body, headers = call("/api/items", method="POST", payload={"name": f"demo{index}"})
        print(index, status, body, {key: headers[key] for key in headers if key.startswith("X-RateLimit") or key == "Retry-After"})
        if status == 429:
            break


if __name__ == "__main__":
    main()
