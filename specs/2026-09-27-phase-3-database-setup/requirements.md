# Phase 3 Feature Specification — Database Setup

## Context

Phase 3 follows the completed configuration phase and establishes reproducible PostgreSQL metadata persistence infrastructure. It is guided by the [mission](../mission.md), [roadmap](../roadmap.md), and [tech stack](../tech-stack.md). The system is a modular monolith: SQLAlchemy and Alembic belong at the infrastructure boundary, while domain behavior must not depend on ORM types.

## Scope

The implementation must provide:

1. PostgreSQL engine and connection lifecycle management using the Phase 2 settings contract.
2. A SQLAlchemy declarative base and session factory.
3. Safe session commit, rollback, and close behavior.
4. Alembic configuration and initial migration wiring.
5. Repeatable database integration tests and local migration documentation.

## Confirmed decisions

* Use SQLAlchemy’s async engine and session with the existing `psycopg` dependency; no second PostgreSQL driver is introduced.
* Do not connect to PostgreSQL while importing modules or constructing the FastAPI application.
* Include the confirmed Phase 4/5 document, artifact, and processing-job tables in the initial Alembic migration.
* Keep database URLs and credentials in environment variables and never embed them in Alembic files.
* Use the PostgreSQL service from Docker Compose for integration tests.
* Add async database pool settings to the Phase 2 configuration contract if the implementation needs operational tuning.

## Constraints and non-goals

* Do not implement repositories, document/artifact/job models, domain transitions, upload behavior, or RabbitMQ publishing here.
* Do not store binary document contents in PostgreSQL.
* Do not make `/health` require PostgreSQL.
* Do not add a microservice or a second persistence abstraction without a demonstrated boundary need.

## Future compatibility

Phase 4 domain types must remain importable without SQLAlchemy. Phase 5 repositories may build on this session boundary, but transaction orchestration must remain explicit and testable. Later migrations must be versioned and safe to apply in deployment order.
