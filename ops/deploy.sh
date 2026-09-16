#!/usr/bin/env bash
# Build, backup, restore rehearsal, validated migration, application smoke and expose.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -f docker-compose.prod.yml)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${BACKUP_DIR:-$HOME/coach-backups}/deploy-$stamp"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
umask 077
maintenance=0
verify_db="coach_journey_verify"
on_failure() {
  code=$?
  if [ "$maintenance" = 1 ]; then
    echo "Deployment stopped during maintenance. Backup: $backup_dir/coach.dump"
    echo "Services remain closed to preserve recovery consistency. See docs/DEPLOY.md recovery steps."
    "${compose[@]}" stop api web cloudflared || true
  fi
  exit "$code"
}
trap on_failure ERR

# Preserve exact running images before rebuilding tags.
for service in api web; do
  container_id="$("${compose[@]}" ps -q "$service")"
  if [ -n "$container_id" ]; then
    image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
    docker image tag "$image_id" "coach-$service:rollback-$stamp"
    echo "$service=coach-$service:rollback-$stamp" >> "$backup_dir/images.txt"
  fi
done
"${compose[@]}" build api web
"${compose[@]}" up -d db

# No user writes between the final backup and verification/exposure.
maintenance=1
"${compose[@]}" stop cloudflared web api
"${compose[@]}" exec -T db pg_dump -U coach -Fc coach > "$backup_dir/coach.dump"
test -s "$backup_dir/coach.dump"
sha256sum "$backup_dir/coach.dump" > "$backup_dir/coach.dump.sha256"
"${compose[@]}" exec -T db dropdb -U coach --if-exists "$verify_db"
"${compose[@]}" exec -T db createdb -U coach "$verify_db"
"${compose[@]}" exec -T db pg_restore -U coach --exit-on-error --no-owner -d "$verify_db" < "$backup_dir/coach.dump"

# DATABASE_URL is derived inside the container so credentials never enter CLI/logs.
"${compose[@]}" run --rm --no-deps -e VERIFY_DATABASE="$verify_db" api \
  python -m app.verify_restored | tee "$backup_dir/restore-verification.json"
"${compose[@]}" exec -T db dropdb -U coach "$verify_db"

# Verify all existing records again during the real migration.
"${compose[@]}" run --rm --no-deps api python -m app.verify_migration \
  | tee "$backup_dir/production-migration.json"
"${compose[@]}" up -d --no-build api web
for i in $(seq 1 30); do
  if "${compose[@]}" exec -T api curl -fsS http://localhost:8000/api/health; then
    break
  fi
  if [ "$i" = 30 ]; then exit 1; fi
  sleep 2
done
"${compose[@]}" exec -T api python -m app.production_smoke | tee "$backup_dir/production-smoke.json"
"${compose[@]}" up -d --force-recreate cloudflared
maintenance=0
echo "Deployment and production smoke passed. Recovery material: $backup_dir"
