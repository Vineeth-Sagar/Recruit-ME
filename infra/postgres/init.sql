-- Runs once, as the postgres superuser, the first time the data directory is
-- initialised (mounted at /docker-entrypoint-initdb.d/). Migration 0001 also
-- issues `CREATE EXTENSION IF NOT EXISTS citext`, but on a managed Postgres the
-- application role usually cannot create extensions — an admin runs this first.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
