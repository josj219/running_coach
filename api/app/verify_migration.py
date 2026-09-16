"""Verify a restored database without printing personal data or secrets.

python -m app.verify_migration runs migration twice, compares every legacy column,
checks all FK references and the relaxed uniqueness. Intended for a disposable restore.
"""
import asyncio
import hashlib
import json
from sqlalchemy import inspect, text
from .db import engine, init_db


def collect(conn, schemas=None):
    inspector = inspect(conn)
    schemas = schemas or {table: [c["name"] for c in inspector.get_columns(table)]
                          for table in inspector.get_table_names() if table != "schema_migrations"}
    quote = conn.dialect.identifier_preparer.quote
    result = {}
    for table, columns in schemas.items():
        rows = conn.exec_driver_sql(f'SELECT {", ".join(quote(c) for c in columns)} FROM {quote(table)}').mappings().all()
        result[table] = sorted([dict(r) for r in rows], key=lambda r: str(r.get("id", r.get("user_id", r))))
    return schemas, result


async def verify():
    async with engine.connect() as conn:
        schemas, before = await conn.run_sync(collect)
    await init_db()
    await init_db()  # idempotency is required on every app restart
    async with engine.connect() as conn:
        _, after = await conn.run_sync(lambda c: collect(c, schemas))
        for old, new in zip(before.get("sessions", []), after.get("sessions", [])):
            if old.get("status") != new.get("status"):
                reason = await conn.execute(text("SELECT id FROM journey_events WHERE event_type='fulfillment_migrated' AND entity_id=:id"), {"id": old["id"]})
                assert reason.first(), "Status changed without preserved explanation"
                new["status"] = old["status"]
        if "journey_events" in before:
            existing_ids = {e["id"] for e in before["journey_events"]}
            additions = [e for e in after["journey_events"] if e["id"] not in existing_ids]
            assert all(e["event_type"] == "fulfillment_migrated" for e in additions)
            after["journey_events"] = [e for e in after["journey_events"] if e["id"] in existing_ids]
        assert before == after, "Legacy values/rows or references changed unexpectedly"
        for table in ("workout_logs", "external_activities"):
            uniques = await conn.run_sync(lambda c: inspect(c).get_unique_constraints(table))
            assert all(c["column_names"] != (["user_id", "log_date"] if table == "workout_logs" else ["provider", "external_id"]) for c in uniques)
        if engine.dialect.name == "sqlite":
            assert not (await conn.exec_driver_sql("PRAGMA foreign_key_check")).fetchall()
        else:
            assert not (await conn.exec_driver_sql("SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated")).fetchall()
        digest = hashlib.sha256(json.dumps(before, default=str, sort_keys=True).encode()).hexdigest()
        print(json.dumps({"migration": "passed", "idempotent": True, "legacy_rows": {k: len(v) for k, v in before.items()}, "preserved_data_sha256": digest}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
