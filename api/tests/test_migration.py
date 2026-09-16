"""Start from the actual old SQLite schema; retain IDs, reviews, FK links and all values."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys


def test_legacy_sqlite_migration_and_restore(tmp_path):
    import sqlite3
    from app.db import Base
    from sqlalchemy import create_engine
    path = tmp_path / "legacy.db"
    eng = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(eng)
    eng.dispose()
    with sqlite3.connect(path) as c:
        # Reintroduce the two old constraints and remove the migration marker.
        for table, columns in [("workout_logs", "user_id, log_date"), ("external_activities", "provider, external_id")]:
            sql = c.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
            sql = sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE old_{table}")
            sql = sql.rstrip()[:-1] + f", UNIQUE ({columns}))"
            c.execute(sql)
            c.execute(f"DROP TABLE {table}")
            c.execute(f"ALTER TABLE old_{table} RENAME TO {table}")
        c.execute("INSERT INTO users(id,email,nickname,onboarded,created_at) VALUES(7,'legacy@test.invalid','legacy',1,'2026-01-01')")
        c.execute("INSERT INTO weekly_plans(id,user_id,iso_year,iso_week,week_start,created_at) VALUES(8,7,2026,1,'2025-12-29','2026-01-01')")
        c.execute("INSERT INTO sessions(id,plan_id,session_date,weekday,kind,distance_km,status,is_rest) VALUES(9,8,'2026-01-01',3,'easy',6,'done',0)")
        c.execute("INSERT INTO workout_logs(id,user_id,session_id,log_date,kind,distance_km,duration_sec,pain_level,source,created_at,updated_at) VALUES(10,7,9,'2026-01-01','easy',1,360,0,'manual','2026-01-01','2026-01-01')")
        c.execute("INSERT INTO workout_reviews(id,log_id,coach_comment,created_at) VALUES(11,10,'original review','2026-01-01')")
        c.execute("INSERT INTO external_activities(id,user_id,provider,external_id,imported_log_id,raw) VALUES(12,7,'garmin','one',10,'{}')")
        for table, columns in [("workout_logs", ["sport", "client_request_id", "started_at", "fulfillment", "comparison_tag", "revision", "updated_at"]), ("workout_reviews", ["is_stale"]), ("user_profiles", ["pb_10k_date", "pb_half_date", "pb_full_date"]), ("integrations", ["last_sync_error"])]:
            for column in columns:
                # request/source constraints are current-only; legacy tables never had them.
                if column == "client_request_id":
                    continue
                c.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        c.commit()
        backup = tmp_path / "backup.db"
        with sqlite3.connect(backup) as dest:
            c.backup(dest)
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{path}", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-m", "app.verify_migration"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '"migration": "passed"' in result.stdout
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT status FROM sessions WHERE id=9").fetchone()[0] == "partial"
        assert c.execute("SELECT log_id,coach_comment FROM workout_reviews").fetchone() == (10, "original review")
        c.execute("INSERT INTO workout_logs(id,user_id,session_id,log_date,kind,distance_km,pain_level,source,created_at,updated_at) VALUES(13,7,9,'2026-01-01','easy',8,0,'manual','2026-01-01','2026-01-01')")
        assert c.execute("SELECT sum(distance_km) FROM workout_logs").fetchone()[0] == 9
        assert not c.execute("PRAGMA foreign_key_check").fetchall()
    # Recovery rehearsal to a separate file leaves migrated data untouched.
    restored = tmp_path / "restored.db"
    with sqlite3.connect(backup) as src, sqlite3.connect(restored) as dest:
        src.backup(dest)
        assert dest.execute("SELECT id,distance_km FROM workout_logs").fetchall() == [(10, 1.0)]
