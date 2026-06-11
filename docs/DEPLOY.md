# 배포 런북 — AWS Lightsail + Docker + Cloudflare Tunnel + GitHub self-hosted runner

개인 도그푸딩용 1대 서버 배포. 폰에 PWA로 설치해 매일 쓰는 것이 목표.

## 전체 그림

```
  git push (main)
        │
        ▼
  GitHub Actions  ──►  Lightsail VM 의 self-hosted runner
                              │  docker compose -f docker-compose.prod.yml up -d --build
                              ▼
                       ┌─────────────────────────────┐
                       │ db ─ api ─ web ─ cloudflared │   (인바운드 포트 0개)
                       └──────────────┬──────────────┘
                                      │ 바깥으로 연결
                                      ▼
                              Cloudflare (HTTPS + Access 로그인)
                                      ▼
                                   내 폰 / 브라우저
```

핵심: **인바운드 포트를 안 연다.** cloudflared가 Cloudflare로 *바깥으로* 연결을 맺어서, Lightsail 방화벽은 SSH(22)만 열면 된다. 접근 잠금은 Cloudflare Access(무료)가 담당.

---

## 사전 준비물
- AWS 계정, GitHub repo(이 코드), Anthropic API 키
- **도메인 1개** (싼 것 OK — Cloudflare에 연결). Cloudflare Tunnel의 고정 URL에 필요.

---

## 1. Lightsail 인스턴스 생성
1. Lightsail 콘솔 → **Create instance**
2. Region: Seoul(ap-northeast-2), Platform: **Linux**, Blueprint: **Ubuntu 22.04 LTS**
3. 플랜: **2GB RAM / 2 vCPU** ($12) 권장 (1GB도 되지만 빌드 시 빠듯)
4. 인스턴스 이름 지정 → Create
5. **Networking** 탭 → 방화벽은 **SSH(22)만** 열어둔다(HTTP/HTTPS 열 필요 없음 — 터널이 처리)
6. (선택) Static IP 연결 — SSH 접속 편의용

## 2. 서버 기본 세팅 (SSH 접속 후)
```bash
# Docker + compose 플러그인
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # 또는 재로그인

# 코드 클론
git clone https://github.com/<your>/performance-coach.git
cd performance-coach
```

## 3. Cloudflare에 도메인 연결 + Tunnel 생성
1. [Cloudflare](https://dash.cloudflare.com) 가입 → **Add a site**로 도메인 추가 → 안내대로 도메인 등록업체에서 **네임서버를 Cloudflare 것으로 변경**(반영 몇 분~수 시간)
2. **Zero Trust** 대시보드 → **Networks → Tunnels → Create a tunnel**
   - 타입: **Cloudflared**, 이름 예: `coach`
   - 생성되면 **토큰**이 나온다 → 복사(아래 GitHub Secret `TUNNEL_TOKEN`에 넣음)
   - **Public Hostname** 추가:
     - Subdomain: `coach` (원하는 것), Domain: 내 도메인
     - Service: **HTTP** → URL `web:80`
     - (Docker 네트워크 안에서 cloudflared가 web 컨테이너를 이름으로 찾는다)
3. **접근 잠금 (Access)**: Zero Trust → **Access → Applications → Add an application**
   - Self-hosted, 도메인 = 방금 만든 `coach.내도메인`
   - Policy: **Allow**, 조건 = Emails → 내 이메일만
   - 이제 그 URL은 내 이메일 OTP/구글 로그인 통과해야만 열린다

## 4. GitHub self-hosted runner 설치 (Lightsail에서)
1. GitHub repo → **Settings → Actions → Runners → New self-hosted runner** → Linux 선택
2. 화면에 나오는 `./config.sh ...` 명령을 **서버에서** 실행(repo 토큰 포함)
3. 서비스로 상시 구동:
```bash
sudo ./svc.sh install
sudo ./svc.sh start
```
4. runner가 docker를 쓰므로 docker 그룹에 포함됐는지 확인(2번에서 usermod 했음). 안 되면:
   `sudo usermod -aG docker actions-runner && sudo ./svc.sh stop && sudo ./svc.sh start`

## 5. GitHub Secrets 등록
repo → **Settings → Secrets and variables → Actions → New repository secret**
| 이름 | 값 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic 키 |
| `DB_PASSWORD` | 임의의 강한 문자열 |
| `TUNNEL_TOKEN` | 3번에서 복사한 터널 토큰 |
| `STRAVA_CLIENT_ID` / `STRAVA_CLIENT_SECRET` | (나중에 Strava 켤 때, 지금은 빈 값도 OK) |
| `WEB_BASE_URL` / `API_BASE_URL` | `https://coach.내도메인` (Strava 콜백용, 없으면 빈 값) |

## 6. 첫 배포
- `main`에 push하거나, repo **Actions → deploy → Run workflow**(수동) 실행
- runner가 `docker compose -f docker-compose.prod.yml up -d --build` 후 health check
- 성공하면 `https://coach.내도메인` 접속 → Cloudflare 로그인 → 앱 첫 화면(온보딩)

## 7. 폰에 PWA 설치
- 폰 브라우저로 그 URL 접속 → Cloudflare 로그인
- iOS Safari: 공유 → **홈 화면에 추가** / Android Chrome: **앱 설치**
- 이제 홈 아이콘으로 앱처럼 실행

## 8. 백업 cron 등록
```bash
crontab -e
# 매일 03:30 자동 백업(7일 보관)
30 3 * * * /home/ubuntu/performance-coach/ops/backup.sh >> /home/ubuntu/backup.log 2>&1
```

---

## 운영 메모
- **로그**: `docker compose -f docker-compose.prod.yml logs -f api`
- **수동 재배포**: 서버에서 `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- **DB 유지**: 배포해도 `pgdata` 볼륨은 보존된다(데이터 안 날아감)
- **복구**: `gunzip -c <백업>.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U coach -d coach`
- **Strava 켜기**: Strava 앱 등록 시 Authorization Callback Domain에 `coach.내도메인` 등록 → Secrets에 키 채우고 재배포
- **비용 감각**: Lightsail 2GB ≈ $12/월, 도메인 ≈ 연 1~2만원, Cloudflare/Anthropic은 사용량 기반
