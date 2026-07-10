# AI Usage Log

DRAFT — CANDIDATE MUST VERIFY AND PERSONALIZE

## Interaction 1
- What I asked: "Help me choose an algorithm for an in-memory rate limiter that supports bursty traffic and a meaningful Retry-After."
- What the AI suggested: A fixed-window counter with simple counters per organization and endpoint.
- What I kept: The overall need for a configurable, middleware-based limiter.
- What I changed or rejected: I rejected the fixed-window counter and switched to a sliding-window request log because the user asked for an alternate strategy and the rolling-window semantics were easier to explain and verify.
- Why: The new approach still gives a meaningful Retry-After and keeps the implementation small enough for the proof of concept.
- How I verified it: I exercised the middleware locally and confirmed that requests are rejected once the request history fills the configured window.

## Interaction 2
- What I asked: "Can you help me structure the middleware so rejected requests do not partially consume capacity?"
- What the AI suggested: A two-step check that might consume the organization bucket before checking the endpoint bucket.
- What I kept: The idea of a shared middleware layer.
- What I changed or rejected: I changed the implementation to perform a single all-or-nothing decision under one lock, refilling and checking both buckets before either is consumed.
- Why: This is the core correctness requirement from the prompt and prevents inconsistent state on a reject.
- How I verified it: I added tests that assert a blocked request leaves both buckets unchanged.

## Interaction 3
- What I asked: "Should I trust X-Org-ID as an authenticated organization identifier?"
- What the AI suggested: A simple header-based lookup was acceptable for the PoC.
- What I kept: The header-based organization mapping for the demo.
- What I changed or rejected: I documented clearly that this is a proof-of-concept identifier only and that production should derive organization identity from an authenticated principal or API key.
- Why: The prompt explicitly called out the security limitation and the need for honest documentation.
- How I verified it: I checked the middleware and README wording to ensure the documentation clearly states the limitation.

## Additional notes
- The repository intentionally avoids Redis, auth systems, and distributed infrastructure because the challenge asks for a compact local PoC.
- The candidate should personalize these entries to match the actual session interactions before submission.
