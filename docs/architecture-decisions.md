# Architecture decisions

## Recovery is operator-triggered (phases 14–15)

The first recovery release provides dry-run reconciliation and bounded operator-
triggered retry. It does not schedule a periodic reconciler or perform automatic
destructive cleanup. This keeps ownership, retention, and escalation explicit.

## Integration services use isolated Compose resources

PostgreSQL and RabbitMQ are declared under the `integration` Compose profile.
Focused tests use in-memory storage and static authentication; integration tests
may start isolated local services and never require production credentials.
