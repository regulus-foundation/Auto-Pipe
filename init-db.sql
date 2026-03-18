-- Auto-Pipe database (same PostgreSQL instance as Langfuse)
-- This runs on first container creation only (docker-entrypoint-initdb.d)

CREATE DATABASE autopipe;
GRANT ALL PRIVILEGES ON DATABASE autopipe TO langfuse;
