# Configuration reference

Settings use unprefixed, case-insensitive environment variables and may be loaded from
a local `.env`. Copy `.env.example` for local names; it contains no credentials.

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development`, `test`, or `production` |
| `LOG_LEVEL` | `INFO` | `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG` |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind address and port |
| `MAX_UPLOAD_SIZE_BYTES` | `26214400` | 25 MiB default |
| `ALLOWED_EXTENSIONS` | `.pdf,.jpg,.jpeg,.png,.docx,.xlsx` | Comma-separated |
| `ALLOWED_MIME_TYPES` | PDF, JPEG, PNG, DOCX, XLSX MIME types | Comma-separated |
| `DATABASE_URL` | unset | Application PostgreSQL URL; required in production. For PyCharm with Compose services, use `postgresql://app:app@localhost:5432/app`. |
| `DATABASE_URL_DOCKER` | Compose service default | Compose-only override; defaults to the `postgres` service hostname. |
| `DATABASE_ECHO` | `false` | SQLAlchemy logging |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | `5` / `10` | Async pool sizing |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `30` | Pool acquisition timeout |
| `RABBITMQ_URL` | unset | Application RabbitMQ URL; required in production. For PyCharm with Compose services, use `amqp://guest:guest@localhost:5672/`. |
| `RABBITMQ_URL_DOCKER` | Compose service default | Compose-only override; defaults to the `rabbitmq` service hostname. |
| `RABBITMQ_EXCHANGE` / `RABBITMQ_QUEUE` | `document-ingestion` / `document-processing` | Durable topology names |
| `RABBITMQ_ROUTING_KEY` | `document.process` | Processing route |
| `RABBITMQ_RETRY_COUNT` | `3` | Fixed at exactly three |
| `RABBITMQ_RETRY_BASE_DELAY_SECONDS` / `RABBITMQ_RETRY_MAX_DELAY_SECONDS` | `1` / `60` | Exponential retry bounds |
| `RABBITMQ_RETRY_JITTER` | `false` | Reserved policy toggle |
| `RABBITMQ_DLQ_EXCHANGE` / `RABBITMQ_DLQ_QUEUE` | `document-ingestion-dlx` / `document-processing-dlq` | Dead-letter topology |
| `RABBITMQ_PREFETCH_COUNT` | `10` | Consumer QoS |
| `RABBITMQ_PUBLISH_TIMEOUT_SECONDS` | `10` | Publish operation timeout setting |
| `FIREBASE_PROJECT_ID` | unset | Required in production |
| `FIREBASE_CREDENTIALS_PATH` | unset | Service credential path; never commit it. Local PyCharm can use `google-service-account-key.json`. |
| `FIREBASE_CREDENTIALS_PATH_DOCKER` | Compose mount default | Compose-only override; defaults to `/run/secrets/firebase-service-account.json`. |
| `FIREBASE_STORAGE_BUCKET` | unset | Required in production |
| `JWT_SIGNING_KEY` | unset | Application access-token signing secret; required in production |
| `AUTH_ISSUER` / `AUTH_AUDIENCE` | platform defaults | JWT validation values |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `900` | Short-lived application access token lifetime |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `2592000` | Refresh-session lifetime |
| `STORAGE_BACKEND` | `filesystem` | `filesystem` locally, `firebase` in production |
| `STORAGE_ROOT` | `.data/artifacts` | Local artifact root |

Production validation requires database, RabbitMQ, Firebase project/credentials/bucket,
and `STORAGE_BACKEND=firebase`. URLs and credentials must be injected by the runtime
secret manager or deployment environment. Do not put tokens, service-account JSON,
document bytes, or production connection strings in `.env`, images, logs, or tests.

For focused tests use `_env_file=None`, in-memory storage, and static token verification.
For integration tests use isolated local PostgreSQL/RabbitMQ resources and safe local
credentials; Firebase production credentials are not required.
