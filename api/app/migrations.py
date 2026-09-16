"""Transactional, idempotent SQLite/PostgreSQL migration. Run only after a backup.

SQLite keeps the original name until copy succeeds. The rebuild copies every column,
retains IDs, indexes and references. No dates, reviews or session links are discarded.
PostgreSQL removes only the obsolete unique constraints and adds scoped indexes.
"""
import re
from sqlalchemy import inspect

VERSION = "20260913_journey_1"


def _remove_unique(conn, table, columns):
    inspector = inspect(conn)
    obsolete = [c for c in inspector.get_unique_constraints(table) if c["column_names"] == columns]
    if not obsolete:
        return
    if conn.dialect.name == "postgresql":
        quote = conn.dialect.identifier_preparer.quote
        for c in obsolete:
            conn.exec_driver_sql(f"ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(c['name'])}")
        return
    original = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).scalar_one()
    indexes = list(conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type IN ('index', 'trigger') AND tbl_name=? AND sql IS NOT NULL", (table,)).scalars())
    names = [c["name"] for c in inspector.get_columns(table)]
    quoted = ", ".join('"' + n + '"' for n in names)
    pattern = r",?\s*(?:CONSTRAINT\s+\w+\s+)?UNIQUE\s*\(\s*" + r"\s*,\s*".join(columns) + r"\s*\)"
    revised, count = re.subn(pattern, "", original, flags=re.I)
    if count != 1:
        raise RuntimeError(f"Cannot safely remove obsolete unique constraint from {table}")
    revised = re.sub(r"CREATE TABLE\s+[\"`\[]?" + table + r"[\"`\]]?", f'CREATE TABLE "{table}_journey"', revised, count=1, flags=re.I)
    conn.exec_driver_sql(revised)
    conn.exec_driver_sql(f'INSERT INTO "{table}_journey" ({quoted}) SELECT {quoted} FROM "{table}"')
    before = conn.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar_one()
    copied = conn.exec_driver_sql(f'SELECT count(*) FROM "{table}_journey"').scalar_one()
    if before != copied:
        raise RuntimeError("Migration row count mismatch")
    conn.exec_driver_sql(f'DROP TABLE "{table}"')
    conn.exec_driver_sql(f'ALTER TABLE "{table}_journey" RENAME TO "{table}"')
    for sql in indexes:
        conn.exec_driver_sql(sql)


def migrate_journey(conn):
    conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR PRIMARY KEY)")
    applied = conn.exec_driver_sql("SELECT version FROM schema_migrations").scalars().all()
    if VERSION in applied:
        return
    _remove_unique(conn, "workout_logs", ["user_id", "log_date"])
    _remove_unique(conn, "external_activities", ["provider", "external_id"])
    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_log_request ON workout_logs(user_id, client_request_id)")
    # Existing duplicate source IDs are preserved; imports resolve legacy matches explicitly.
    duplicates = conn.exec_driver_sql("SELECT count(*) FROM (SELECT user_id, source, external_id FROM workout_logs WHERE external_id IS NOT NULL GROUP BY user_id, source, external_id HAVING count(*) > 1) d").scalar_one()
    if not duplicates:
        conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_log_external ON workout_logs(user_id, source, external_id)")
    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_activity_owner ON external_activities(user_id, provider, external_id)")
    conn.exec_driver_sql("UPDATE workout_logs SET updated_at = created_at WHERE updated_at IS NULL")
    if conn.dialect.name == "sqlite" and conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Migration foreign key validation failed")
    # Reclassify legacy status using observed quantities; preserve original status in an event.
    from sqlalchemy.orm import Session
    from .db import JourneyEvent, PlanSession, WeeklyPlan, WorkoutLog
    from .services.records import fulfillment_status
    with Session(bind=conn) as db:
        for session, owner in db.query(PlanSession, WeeklyPlan.user_id).join(WeeklyPlan).all():
            logs = db.query(WorkoutLog).filter(WorkoutLog.session_id == session.id).all()
            if not logs:
                continue
            before = session.status
            fulfillment_status(session, logs)
            if before != session.status:
                db.add(JourneyEvent(user_id=owner, event_type="fulfillment_migrated", entity_id=session.id,
                    reason="참여와 계획 이행을 분리하는 기준 적용", before={"status": before}, after={"status": session.status}))
        db.flush()
    conn.exec_driver_sql(f"INSERT INTO schema_migrations(version) VALUES ('{VERSION}')")
