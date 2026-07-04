-- Enforce append-only audit log semantics at the DB layer.
-- Any UPDATE/DELETE attempt on audit_logs is rejected.

CREATE TRIGGER
IF NOT EXISTS trg_audit_logs_no_update
BEFORE
UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs is append-only');
END;

CREATE TRIGGER
IF NOT EXISTS trg_audit_logs_no_delete
BEFORE
DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs is append-only');
END;
