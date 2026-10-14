-- The API stopped writing sessions.ip in 0.12.0; nothing reads it.
ALTER TABLE sessions DROP COLUMN IF EXISTS ip;
