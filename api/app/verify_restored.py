"""Select the fixed disposable restore DB before importing any app database modules."""
import asyncio
import os
from sqlalchemy.engine import make_url

target = os.environ["VERIFY_DATABASE"]
if target != "coach_journey_verify":
    raise RuntimeError("Only the dedicated restore database is allowed")
url = make_url(os.environ["DATABASE_URL"]).set(database=target)
os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
from .verify_migration import verify  # noqa: E402

if __name__ == "__main__":
    asyncio.run(verify())
