# Database Keepalives and Scheduler Reliability

## Facts

- **TCP Keepalives:** Set TCP keepalives (`idle=30`, `interval=10`, `count=5`) for psycopg connections to prevent cloud load balancers (Azure/Neon) from dropping idle connections.
- **Resilient Schedulers:** Scheduler services must implement resilient run loops with auto-reconnection logic to handle temporary DB outages gracefully.
- **Standard Cron:** Ensure `IntervalTrigger.to_cron()` generates standard 5-field cron expressions for hourly intervals to avoid misinterpretation as seconds-based schedules.

## Reason

Cloud database connections (like Azure PostgreSQL) often have strict idle timeouts (e.g., 4 minutes) that silently drop connections, leading to "server closed the connection unexpectedly" errors. Keepalives prevent this connectivity loss. Standard 5-field cron ensures consistent execution intervals across different cron parsers and avoids ambiguity.

## Citations

- `components/appkit-commons/src/appkit_commons/scheduler/pgqueuer.py`: Lines 46-53
- `components/appkit-commons/src/appkit_commons/scheduler/scheduler_types.py`: Lines 75-80
