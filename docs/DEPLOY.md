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
| `JWT_SECRET` | 로그인 토큰 서명 키. 32자 이상 임의 문자열 (`openssl rand -hex 32`) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | 비밀번호 재설정 인증 메일용. 아래 "비밀번호 재설정 메일 설정" 참고. 비워두면 재설정 기능이 메일을 못 보낸다 |

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

## 계정 관리 — 생성 · 비밀번호 재설정 · 복구

앱에는 셀프 회원가입이 없다. 계정은 서버에서 만들고, 비밀번호는 앱의 이메일 인증으로 사용자가 직접 재설정한다.

### 계정 만들기 (최초 1회)
서버 터미널에서:
```bash
cd ~/performance-coach
docker compose -f docker-compose.prod.yml exec -T api \
  python -m app.create_user <이메일> <비밀번호> <닉네임>
```
로그인 이메일 = 여기서 넣은 이메일. 소문자로 저장되며 로그인 시 대소문자를 구분하지 않는다.

### 비밀번호 재설정 메일 설정 (Gmail 기준)
1. Google 계정 → 보안 → **2단계 인증** 켜기 (앱 비밀번호 발급 조건)
2. https://myaccount.google.com/apppasswords → 앱 이름 `coach` → 생성 → 16자리 비밀번호 복사
3. GitHub Secrets에 등록:

| 이름 | 값 |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | 내 Gmail 주소 |
| `SMTP_PASSWORD` | 위에서 만든 16자리 앱 비밀번호 (공백 제거) |
| `SMTP_FROM` | 내 Gmail 주소 (비워도 `SMTP_USER` 사용) |

4. 재배포(Actions → deploy → Run workflow). 이후 로그인 화면의 **"비밀번호를 잊으셨나요?"** → 이메일 입력 → 메일로 온 6자리 코드 + 새 비밀번호 입력 → 바로 로그인된다.

동작 규칙: 코드는 10분 유효, 1회용, 5회 틀리면 폐기(다시 받아야 함), 재발송은 60초에 1번. 존재하지 않는 이메일에도 같은 응답을 줘 계정 유무를 노출하지 않는다.
Gmail 외 SMTP(SES, Resend 등)도 host/port/user/password만 바꾸면 된다. 465 포트를 주면 SSL, 그 외는 STARTTLS로 붙는다.

### 메일이 안 될 때 수동 복구
이메일을 잊었거나 SMTP가 아직 없으면 서버에서 직접 처리한다.
```bash
# 1) 등록된 계정 확인
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U coach -d coach -c "select id, email, nickname from users;"
# 2) 비밀번호만 바꾸기 (닉네임·기록은 그대로)
docker compose -f docker-compose.prod.yml exec -T api \
  python -m app.create_user <이메일> <새비밀번호>
```
SMTP 미설정 상태에서 앱의 재설정을 시도하면 메일은 안 가고 api 로그(`logs -f api`)에 `[mailer:console]`로 코드가 찍힌다 — 급할 때 로그에서 코드를 읽어 앱에 입력해도 된다.

---

## 운영 메모
- **로그**: `docker compose -f docker-compose.prod.yml logs -f api`
- **수동 재배포**: 서버에서 `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- **DB 유지**: 배포해도 `pgdata` 볼륨은 보존된다(데이터 안 날아감)
- **복구**: `gunzip -c <백업>.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U coach -d coach`
- **Strava 켜기**: Strava 앱 등록 시 Authorization Callback Domain에 `coach.내도메인` 등록 → Secrets에 키 채우고 재배포
- **비용 감각**: Lightsail 2GB ≈ $12/월, 도메인 ≈ 연 1~2만원, Cloudflare/Anthropic은 사용량 기반
