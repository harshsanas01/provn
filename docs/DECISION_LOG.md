# Decision Log

## Decision: Use a sliding-window request log rather than a fixed window
- Reason: Sliding windows provide a rolling-rate check that is easy to explain, deterministic, and straightforward to implement in memory.
- Rejected alternative: A token bucket was rejected for this iteration because the prompt asked for a different strategy and the sliding-window approach is easier to reason about for a compact proof of concept.
- Consequence: The limiter is slightly more memory-intensive than a pure token-bucket approach but remains simple and correct for local use.

## Decision: Enforce two limits in one atomic decision
- Reason: Organization-wide fairness and endpoint-category fairness both matter.
- Rejected alternative: Checking only one bucket or consuming one before the other was rejected.
- Consequence: A rejected request does not partially consume capacity.

## Decision: Use monotonic time for refill calculations
- Reason: Monotonic time is stable for elapsed durations and avoids clock jumps.
- Rejected alternative: Wall-clock time was rejected for bucket refill math.
- Consequence: The limiter behaves consistently during clock changes.

## Decision: Use lazy cleanup for buckets
- Reason: The in-memory map must not grow forever without adding a background scheduler.
- Rejected alternative: A high-frequency background thread or aggressive cleanup policy was rejected.
- Consequence: Cleanup is simple and bounded but not perfect.

## Decision: Keep the solution config-driven rather than route-by-route
- Reason: The challenge explicitly requested middleware/config-based classification without modifying every route.
- Rejected alternative: Per-route decorators or code changes per endpoint were rejected.
- Consequence: New routes can be classified by configuration.

## Decision: Keep the implementation in-process only
- Reason: The challenge prohibits Redis or distributed infrastructure for this PoC.
- Rejected alternative: A distributed store was rejected for now.
- Consequence: The design is simple and local, but not production-safe across replicas.
