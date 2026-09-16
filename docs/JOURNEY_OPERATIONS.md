# 사용자 여정 배포 및 데이터 복구

`main` 배포는 SQLite/PostgreSQL 16 회귀·마이그레이션 복구 테스트, PWA 빌드, Expo API 계약, Chrome 여정을 먼저 통과해야 한다. 이후 self-hosted runner가 `ops/deploy.sh`를 실행한다.

1. 실행 중 API/web 이미지에 복구 태그를 붙이고 새 이미지를 빌드한다.
2. cloudflared/web/API를 중지해 쓰기를 잠시 막는다. DB 볼륨은 유지한다.
3. `$HOME/coach-backups/deploy-<UTC시각>/coach.dump`에 PostgreSQL custom-format 백업과 SHA-256을 저장한다. checkout 밖이므로 git clean에도 보존된다. 배포 백업은 일일 백업 정리에서 제외한다.
4. 전용 임시 DB `coach_journey_verify`에 복원한다. `app.verify_restored`는 마이그레이션을 두 번 실행하고 모든 기존 행·컬럼, 리뷰·계획 연결, FK를 대조한다. 확인 후 임시 DB를 삭제한다.
5. 실제 DB에서도 `app.verify_migration`으로 같은 대조를 수행한다. 허용된 변경은 새 수행 기준에 따른 세션 상태 재분류뿐이다. 원래 상태·사유는 `journey_events`에 보존한다.
6. API/web을 시작하고 nginx 경유 `app.production_smoke`로 로그인, PB-only, 같은 날 복수 저장, ID 수정, 부분 수행, 목표 버전, 양 공급자 중복, 성장 비교를 확인한다. 임시 계정과 기록은 finally에서 제거한다. 실사용자 기록·로그인은 변경하지 않는다. AI/실제 Garmin·Strava 통신은 호출하지 않는다.
7. 성공 후 cloudflared를 재생성해 외부 접속을 연다. `/api/health`의 `revision`은 배포 커밋이다.

실패하면 외부 쓰기를 다시 열지 않고 백업 위치를 로그에 남긴다. 백업을 덮어쓰거나 DB 볼륨을 삭제하지 않는다.

## 유지보수 중 실패 복구

**외부 접속을 재개하기 전이고 백업 이후 사용자 쓰기가 없는 경우** 아래 절차를 사용한다. 이미 외부 접속을 열었다면 새 쓰기를 별도로 백업하고 병합 또는 전진 수정한다. 예전 백업을 덮어써 새 기록을 잃지 않도록 한다.

```bash
restore_dir="$HOME/coach-backups/deploy-YYYYMMDDTHHMMSSZ"
docker compose -f docker-compose.prod.yml stop cloudflared web api
sha256sum -c "$restore_dir/coach.dump.sha256"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U coach -Fc coach > "$restore_dir/before-recovery.dump"
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U coach --exit-on-error --clean --if-exists --no-owner -d coach < "$restore_dir/coach.dump"
```

`images.txt`의 API/web 태그를 Compose override의 `services.api.image`와 `services.web.image`로 지정해 `up -d --no-build api web`을 실행한다. 내부 health·로그인·기록 조회 후 cloudflared를 다시 시작한다. 복구 이미지 태그는 삭제하지 않는다.

새 테이블은 additive라 백업에 없던 빈 테이블이 남을 수 있다. **하루 복수 기록이 생긴 뒤 구버전 코드로만 돌아가면 날짜 단위 조회가 실패할 수 있으므로 신규 쓰기가 있는 운영은 전진 수정이 우선이다.**

방식의 기준: [SQLite 테이블 재구성 절차](https://www.sqlite.org/lang_altertable.html#making_other_kinds_of_table_schema_changes), [PostgreSQL 16 pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html). 이 검증은 기록 보존을 확인하며 추정 모델 정확도를 검증하지 않는다.
