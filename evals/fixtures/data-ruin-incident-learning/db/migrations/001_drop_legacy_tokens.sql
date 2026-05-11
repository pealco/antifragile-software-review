ALTER TABLE users DROP COLUMN legacy_token;
UPDATE users SET migrated = true;
