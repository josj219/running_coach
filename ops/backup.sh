#!/usr/bin/env bash
# Postgres 일일 백업 — 날짜별 dump, 7일 보관.
# cron 등록(매일 03:30):
#   crontab -e
#   30 3 * * * /home/ubuntu/performance-coach/ops/backup.sh >> /home/ubuntu/backup.log 2>&1
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/coach-backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
COMPOSE="docker compose -f $PROJECT_DIR/docker-compose.prod.yml"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M)"
OUT="$BACKUP_DIR/coach-$STAMP.sql.gz"

# db 컨테이너 안에서 덤프 → gzip
$COMPOSE exec -T db pg_dump -U coach coach | gzip > "$OUT"
echo "$(date '+%F %T') backup → $OUT ($(du -h "$OUT" | cut -f1))"

# 오래된 백업 정리
find "$BACKUP_DIR" -name 'coach-*.sql.gz' -mtime "+$KEEP_DAYS" -delete

# 복구(참고): gunzip -c coach-YYYYMMDD-HHMM.sql.gz | \
#   docker compose -f docker-compose.prod.yml exec -T db psql -U coach -d coach
