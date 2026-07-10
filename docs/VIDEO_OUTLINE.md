# Video Walkthrough Outline

## 0:00–1:00 — Problem and approach
- Explain that one client consumed disproportionate capacity and caused latency for others.
- Describe the middleware-based approach.
- Emphasize the two simultaneous limits: organization and endpoint category.
- Mention config-driven classification and token-bucket semantics.

## 1:00–4:30 — Code walkthrough
- Show the YAML configuration.
- Explain the token-bucket state and limit rule structure.
- Walk through the limiter decision logic and the atomic check-and-consume behavior.
- Show the middleware and how it runs before route handlers.
- Point out the route classification rules and sample endpoints.
- Show the tests and the live 429 demo.

## 4:30–6:30 — Failure modes
- Explain that restart resets quota.
- Explain that multiple replicas each maintain independent state.
- Explain that clients can multiply effective quota across replicas.
- Mention memory growth and cleanup behavior.
- Mention the Redis migration path and why it is needed.

## 6:30–8:00 — Mandatory AI redirection question
- Name the exact moment where the AI suggestion did not meet the bar.
- State what the AI suggested.
- State why it did not meet the bar.
- State what changed.
- State how the correction was verified.
- Connect the decision to production behavior.

CANDIDATE MUST RETELL THIS IN THEIR OWN WORDS AND VERIFY IT MATCHES THE ACTUAL SESSION

## 8:00–9:00 — More time
- Mention Redis-backed atomic Lua scripts.
- Mention auth-derived organization identity.
- Mention live configuration reload and metrics.
- Mention chaos testing and route-cardinality safeguards.
