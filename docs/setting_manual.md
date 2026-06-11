# 배포 세팅 매뉴얼 (실전 기록)

처음 배포를 진행하면서 실제로 겪은 문제와 해결 방법을 정리한 매뉴얼.
공식 런북(DEPLOY.md)과 함께 읽을 것.

---

## 전체 흐름 요약

```
1. AWS Lightsail 서버 생성
2. 서버에 Docker 설치
3. GitHub 레포 생성 + 코드 push
4. Cloudflare 도메인 + Tunnel 설정
5. GitHub Secrets 등록
6. GitHub self-hosted runner 설치
7. 첫 배포 트리거
```

---

## 1단계: AWS Lightsail 서버 생성

1. AWS 콘솔 → Lightsail → **Create instance**
2. Region: `ap-northeast-2` (서울)
3. Platform: Linux / Blueprint: **Ubuntu 22.04 LTS**
4. 플랜: **2GB RAM / 2 vCPU** ($12/월) 권장
5. Networking 탭 → 방화벽: **SSH(22)만** 열어둠 (HTTP/HTTPS 불필요)

---

## 2단계: 서버 기본 세팅

### SSH 접속 방법

> **주의**: 이 명령들은 반드시 서버에서 실행해야 한다.  
> 맥북 터미널에서 실행하면 안 됨.

Lightsail 콘솔 → 인스턴스 클릭 → **Connect** 버튼으로 브라우저 터미널 접속.  
접속 후 프롬프트가 `ubuntu@ip-xxx-xxx-xxx-xxx` 로 시작해야 정상.

### Docker 설치

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

- `$USER`는 현재 로그인된 계정(ubuntu)을 자동으로 가리킴. 별도 계정 불필요.
- `sudo usermod` 실행 시 비밀번호가 필요하면 맥북에서 실행하고 있는 것 — 서버로 다시 접속할 것.

---

## 3단계: GitHub 레포 + 코드 push

### PAT 토큰 발급 (GitHub 비밀번호 대신 사용)

GitHub는 비밀번호 인증을 지원하지 않음. Personal Access Token(PAT)을 발급해야 함.

1. GitHub → 프로필 → **Settings**
2. 왼쪽 맨 아래 **Developer settings**
3. **Personal access tokens → Tokens (classic)**
4. **Generate new token (classic)**
5. `repo` 항목 체크 → **Generate token**
6. `ghp_` 로 시작하는 토큰이 표시됨 → **즉시 복사** (다시 볼 수 없음)

> 토큰을 한 번 놓치면 삭제하고 다시 발급해야 한다.

### .env 파일 절대 커밋 금지

`.env` 파일에 API 키가 들어있어서 커밋하면 GitHub이 push를 차단함.  
이미 커밋된 경우 히스토리에서 제거해야 함:

```bash
pip install git-filter-repo
git filter-repo --path .env --invert-paths --force

# filter-repo 실행 후 remote 설정이 초기화됨 — 다시 추가
git remote add origin https://github.com/josj219/running_coach.git
git push -u origin main --force
```

### .gitignore 설정

```bash
cat > .gitignore << 'EOF'
.env
__pycache__/
*.pyc
*.pyo
.DS_Store
node_modules/
.next/
EOF

git add .gitignore
git commit -m "add .gitignore"
git push
```

### 코드 push 후 서버에서 pull

```bash
# 서버 터미널에서
cd running_coach
git pull
```

---

## 4단계: Cloudflare 도메인 + Tunnel

### 도메인 구매 순서 (가비아 + Cloudflare 연동)

가비아에서 도메인 구매 시 Cloudflare 네임서버를 먼저 받아야 함.  
순서를 바꾸면 진행이 안 됨.

**올바른 순서:**

1. **Cloudflare에서 먼저** → Add a domain → `gogojo.cloud` 입력 → Free 플랜 선택
2. DNS 레코드 화면은 그냥 넘어감 (Tunnel이 처리)
3. **네임서버 2개 확인** (예: `noel.ns.cloudflare.com`, `tricia.ns.cloudflare.com`)
4. **가비아에서** 도메인 구매 → 타사 네임서버 선택 → Cloudflare 네임서버 입력
5. Cloudflare로 돌아와 **"I updated my nameservers"** 클릭
6. 반영까지 수 분~수 시간 대기

### Cloudflare Zero Trust 설정

1. Cloudflare 대시보드 → **Zero Trust** → Free 플랜 선택
2. **Networks → Manage Tunnels → Create a tunnel**
3. Type: **Cloudflared**, 이름: `coach`
4. OS: **Debian**, Architecture: **64-bit** 선택

### cloudflared 서버 설치

서버 터미널에서:

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings

curl -fsSL https://pkg.cloudflare.com/cloudflare-public-v2.gpg | sudo tee /usr/share/keyrings/cloudflare-public-v2.gpg >/dev/null

echo 'deb [signed-by=/usr/share/keyrings/cloudflare-public-v2.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt-get update && sudo apt-get install cloudflared
```

설치 후 토큰으로 서비스 등록:

```bash
sudo cloudflared service install eyJ여기에토큰전체붙여넣기
```

성공 메시지: `Linux service for cloudflared installed successfully`

### Tunnel Route 설정

Cloudflare 터널 설정 화면에서:

- Subdomain: `coach`
- Domain: `gogojo.cloud`
- Path: 비워둠
- Service Type: `HTTP`
- Service URL: `web:80`

> `web:80`은 Docker 컨테이너 이름. cloudflared가 Docker 네트워크 안에서 직접 찾음.

터널 목록에서 **HEALTHY** 상태가 되면 성공.

---

## 5단계: GitHub Secrets 등록

레포 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic 콘솔에서 발급 |
| `DB_PASSWORD` | 임의의 강한 문자열 (예: `coach2026!`) |
| `TUNNEL_TOKEN` | Cloudflare 터널 생성 시 받은 `eyJ...` 토큰 |
| `STRAVA_CLIENT_ID` | 나중에 (지금은 빈 값) |
| `STRAVA_CLIENT_SECRET` | 나중에 (지금은 빈 값) |
| `WEB_BASE_URL` | 나중에 (지금은 빈 값) |
| `API_BASE_URL` | 나중에 (지금은 빈 값) |

---

## 6단계: GitHub self-hosted runner

레포 → **Settings → Actions → Runners → New self-hosted runner** → Linux 선택

### 설치 (화면에 나오는 명령 그대로 서버에서 실행)

```bash
# 폴더 생성 및 이동
mkdir actions-runner && cd actions-runner

# runner 다운로드 (화면의 명령 그대로)
curl -o actions-runner-linux-x64-x.x.x.tar.gz -L https://...
tar xzf ./actions-runner-linux-x64-x.x.x.tar.gz

# GitHub 연결 (화면의 명령 그대로 — 토큰 포함)
./config.sh --url https://github.com/josj219/running_coach --token AP...
```

config.sh 실행 중 나오는 질문은 전부 **Enter**(기본값).

### 서비스 등록 (필수)

`./run.sh`만 실행하면 터미널 끄면 멈춤. 반드시 서비스로 등록해야 함.

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

GitHub 레포 → Settings → Runners에서 **Idle** 상태가 되면 성공.

---

## 7단계: 첫 배포 트리거

```bash
# 맥북에서
cd /Users/sungjae/study/AI/performance-coach
git commit --allow-empty -m "trigger first deploy"
git push
```

GitHub 레포 → **Actions** 탭에서 deploy 워크플로우 진행 상황 확인.

또는 Actions → deploy → **Run workflow**(수동 실행)으로도 가능.

---

## 자주 겪은 문제 모음

| 문제 | 원인 | 해결 |
|---|---|---|
| `sudo usermod` 비밀번호 요구 | 맥북에서 실행 | 서버 터미널에서 실행 |
| `password authentication not supported` | GitHub 비밀번호 사용 | PAT 토큰 사용 |
| `repository not found` | 레포 이름 오타 | `running_coach` (언더스코어) |
| push 차단 (secret detected) | `.env`가 커밋에 포함 | git filter-repo로 히스토리 제거 |
| `origin does not appear to be a git repository` | filter-repo가 remote 초기화 | git remote add 다시 실행 |
| cloudflared 토큰 입력창 없음 | OS가 Mac으로 설정됨 | Debian으로 변경 후 명령 복사 |
| runner 재시작 후 멈춤 | ./run.sh로 임시 실행 | svc.sh install/start로 서비스 등록 |

---

## 완료 체크리스트

- [ ] Lightsail 인스턴스: Ubuntu 22.04, 2GB RAM
- [ ] Docker 설치 완료, ubuntu 사용자 docker 그룹 추가
- [ ] GitHub 레포에 코드 push 완료
- [ ] .env .gitignore에 등록됨
- [ ] Cloudflare 도메인 `gogojo.cloud` 연결
- [ ] Cloudflare Tunnel `coach` 상태: HEALTHY
- [ ] GitHub Secrets 3개 등록 (ANTHROPIC_API_KEY, DB_PASSWORD, TUNNEL_TOKEN)
- [ ] GitHub runner 상태: Idle
- [ ] 첫 배포 Actions에서 성공
- [ ] `https://coach.gogojo.cloud` 접속 확인
