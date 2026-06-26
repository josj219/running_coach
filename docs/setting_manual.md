# 배포 세팅 완전 이해 매뉴얼

이 매뉴얼은 단순히 "이렇게 해라"가 아니라 **왜 이걸 하는지**를 함께 설명한다.
처음 배포를 진행하면서 실제로 겪은 문제도 함께 기록했다.

---

## 전체 구조를 먼저 이해하자

배포를 한다는 것은 **맥북에 있는 코드를 인터넷에 연결된 서버에서 실행시키는 것**이다.

```
내 맥북 (코드 작성)
    │
    │ git push (코드 업로드)
    ▼
GitHub (코드 저장소)
    │
    │ 코드가 push되면 자동으로 서버에 배포 명령
    ▼
AWS Lightsail 서버 (실제로 앱이 돌아가는 곳)
    │
    │ Cloudflare Tunnel (외부에서 안전하게 접근)
    ▼
https://coach.gogojo.cloud (인터넷으로 접속 가능)
```

이 흐름을 만들기 위해 7단계를 진행했다.

---

## 1단계: AWS Lightsail 서버 생성

### 왜 서버가 필요한가?

맥북에서 앱을 실행하면 맥북이 꺼지면 앱도 꺼진다.
24시간 켜져 있는 별도 컴퓨터(서버)가 필요하다.
AWS Lightsail은 그 컴퓨터를 월 $12에 빌려주는 서비스다.

### 왜 Ubuntu인가?

Ubuntu는 서버용 Linux 운영체제다.
Windows나 macOS보다 서버 운영에 적합하고, Docker 등 도구가 잘 작동한다.

### 왜 방화벽에서 SSH(22)만 열었나?

서버에 외부에서 접근하는 경로를 최소화하는 보안 원칙이다.
HTTP(80), HTTPS(443) 포트를 열지 않는 이유는 Cloudflare Tunnel이 대신 처리하기 때문이다.
터널은 서버가 바깥으로 연결을 먼저 맺는 방식이라 인바운드 포트가 필요 없다.

### 실습
1. AWS 콘솔 → Lightsail → **Create instance**
2. Region: `ap-northeast-2` (서울)
3. Platform: Linux / Blueprint: **Ubuntu 22.04 LTS**
4. 플랜: **2GB RAM / 2 vCPU** ($12/월)
5. Networking 탭 → 방화벽: **SSH(22)만** 열어둠

---

## 2단계: 서버 기본 세팅 (Docker 설치)

### SSH란 무엇인가?

SSH(Secure Shell)는 원격 서버에 터미널로 접속하는 방법이다.
마치 서버 앞에 키보드가 있는 것처럼 명령을 입력할 수 있다.

Lightsail 콘솔의 **Connect** 버튼을 누르면 브라우저에서 바로 SSH 접속이 된다.
접속 후 프롬프트가 `ubuntu@ip-xxx-xxx-xxx-xxx` 로 시작하면 서버 안에 있는 것이다.

> **실수 주의**: 맥북 터미널에서 실행하면 안 된다. 반드시 서버 터미널에서 실행해야 한다.
> 프롬프트가 `chungwoohyuk@MacBookAir`이면 맥북이다.

### Docker란 무엇인가?

앱을 실행하려면 Python, Node.js, PostgreSQL 등 여러 프로그램이 필요하다.
이걸 서버에 일일이 설치하면 버전 충돌, 설정 문제 등이 생긴다.

Docker는 앱과 그 앱에 필요한 모든 것을 **컨테이너**라는 격리된 상자에 담아서 실행한다.
"내 맥북에서 됐는데 서버에서 안 됨" 문제를 없애준다.

이 프로젝트는 다음 4개 컨테이너로 구성된다:
- `db`: PostgreSQL 데이터베이스 (훈련 기록 저장)
- `api`: FastAPI 백엔드 (AI 코치 로직)
- `web`: nginx + React 프론트엔드 (화면)
- `cloudflared`: Cloudflare Tunnel 에이전트 (외부 접속 담당)

### 왜 `usermod -aG docker $USER`를 했나?

Docker 명령은 기본적으로 root(관리자)만 실행할 수 있다.
`usermod`는 현재 사용자(ubuntu)를 docker 그룹에 추가해서 `sudo` 없이도 docker를 쓸 수 있게 한다.
`$USER`는 현재 로그인된 사용자 이름을 자동으로 가져오는 변수다 (`ubuntu`).

```bash
curl -fsSL https://get.docker.com | sudo sh   # Docker 설치
sudo usermod -aG docker $USER                  # ubuntu 계정을 docker 그룹에 추가
newgrp docker                                  # 그룹 변경 즉시 적용
```

---

## 3단계: GitHub 레포 + 코드 push

### 왜 GitHub가 필요한가?

GitHub는 코드를 저장하는 인터넷 창고다.
맥북 코드를 GitHub에 올리면, 서버가 GitHub에서 코드를 가져올 수 있다.
또한 코드가 GitHub에 올라가면 자동으로 배포가 시작되게 설정할 수 있다(GitHub Actions).

### PAT 토큰이란? 왜 비밀번호를 못 쓰나?

GitHub는 2021년부터 git 명령에서 비밀번호 인증을 막았다.
보안 때문에 **Personal Access Token(PAT)** 이라는 별도 키를 발급해서 사용해야 한다.

PAT는 GitHub 아이디/비밀번호 대신 쓰는 긴 문자열(`ghp_`로 시작)이다.
발급 시 딱 한 번만 보여주기 때문에 즉시 복사해야 한다.

**발급 방법:**
1. GitHub → 프로필 → Settings
2. 왼쪽 맨 아래 → Developer settings
3. Personal access tokens → Tokens (classic)
4. Generate new token (classic)
5. `repo` 항목 체크 → Generate token
6. `ghp_...` 토큰 즉시 복사

### .env 파일이란? 왜 GitHub에 올리면 안 되나?

`.env` 파일은 API 키, 데이터베이스 비밀번호 등 **비밀 정보**를 모아둔 파일이다.
이걸 GitHub에 올리면 전 세계 누구나 볼 수 있어서 API 키가 탈취될 수 있다.
실제로 이번 세팅 중 GitHub이 `.env`를 감지하고 push를 자동으로 차단했다.

**.gitignore란?**
git이 추적하지 말아야 할 파일 목록을 적어두는 파일이다.
`.env`를 여기에 추가하면 `git add .`을 해도 자동으로 제외된다.

```
.env            ← API 키 등 비밀 정보
__pycache__/    ← Python 컴파일 임시 파일
node_modules/   ← npm 패키지 (용량 크고 재설치 가능)
api/.venv/      ← Python 가상환경 (재설치 가능)
```

### node_modules와 .venv는 왜 git에 넣으면 안 되나?

`node_modules`는 npm 패키지들이 설치된 폴더다. 수천 개 파일에 수십 MB다.
`api/.venv`는 Python 라이브러리들이 설치된 가상환경이다.

이것들은 **`package.json`이나 `requirements.txt`만 있으면 언제든 재설치 가능**하다.
코드가 아닌 설치 결과물이므로 git에 포함하지 않는다.
포함하면 push 속도가 매우 느려지고 GitHub이 HTTP 400으로 차단한다.

### git 히스토리에서 파일 완전 삭제 (filter-repo)

이미 커밋된 파일은 `.gitignore`에 추가해도 히스토리에 남아있다.
`git filter-repo`는 히스토리를 재작성해서 특정 파일을 모든 커밋에서 제거한다.

```bash
pip install git-filter-repo
git filter-repo --path .env --invert-paths --force
# 실행 후 remote 설정이 초기화되므로 다시 추가
git remote add origin https://github.com/josj219/running_coach.git
git push -u origin main --force
```

> **주의**: filter-repo 실행 후 git remote가 초기화된다. 반드시 remote를 다시 추가해야 한다.

---

## 4단계: Cloudflare 도메인 + Tunnel

### 도메인이란?

`coach.gogojo.cloud` 같은 주소를 도메인이라고 한다.
없으면 IP 주소(`172.26.9.36`)로만 접속해야 하는데, HTTPS가 안 되고 PWA 설치가 불가능하다.
가비아에서 `gogojo.cloud` 도메인을 구매했다.

### 네임서버(Nameserver)란?

도메인을 입력했을 때 어떤 서버로 연결할지 알려주는 DNS 서버다.
가비아에서 도메인을 사면 기본적으로 가비아 네임서버를 쓴다.
Cloudflare 네임서버로 바꾸면 DNS 관리를 Cloudflare에서 하게 된다.

**왜 Cloudflare 네임서버로 바꾸나?**
Cloudflare Tunnel, Access(로그인), DDoS 방어 등을 쓰려면 Cloudflare가 DNS를 관리해야 한다.

**순서가 중요한 이유:**
가비아에서 도메인 구매 시 네임서버 입력이 필요하다.
그러려면 Cloudflare 네임서버 주소를 먼저 알아야 한다.
그래서 Cloudflare에서 먼저 도메인을 추가해서 네임서버를 확인한 다음, 가비아에서 입력했다.

```
Cloudflare에서 gogojo.cloud 추가
    → 네임서버 확인: noel.ns.cloudflare.com / tricia.ns.cloudflare.com
    → 가비아에서 도메인 구매 + 위 네임서버 입력
    → Cloudflare에서 "I updated my nameservers" 클릭
    → DNS 전파 대기 (수 시간)
```

### Cloudflare Tunnel이란?

일반적으로 외부에서 서버에 접속하려면 서버가 HTTP/HTTPS 포트를 열어야 한다.
그런데 포트를 열면 보안 위험이 생긴다(해킹 시도, DDoS 등).

Cloudflare Tunnel은 반대로 작동한다:
- 서버 안에서 `cloudflared`라는 프로그램이 Cloudflare 서버로 먼저 연결을 맺는다
- 외부 요청이 오면 이 연결을 통해 안으로 전달된다
- 서버는 포트를 열 필요가 없다

```
사용자 브라우저
    → Cloudflare 서버 (HTTPS 처리)
        → 터널 (서버가 먼저 맺은 연결)
            → 서버 안의 web 컨테이너
```

이번 세팅에서:
- `coach.gogojo.cloud`로 오는 요청을 Docker 안의 `web:80` 컨테이너로 전달하도록 설정했다
- `web:80`은 nginx가 돌고 있는 컨테이너 이름과 포트다

### cloudflared 설치 과정 이해

```bash
# 1. Cloudflare의 공개키 등록 (소프트웨어 진위 확인용)
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-public-v2.gpg | sudo tee /usr/share/keyrings/cloudflare-public-v2.gpg >/dev/null

# 2. Cloudflare 소프트웨어 저장소 추가
echo 'deb [signed-by=...] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# 3. cloudflared 설치
sudo apt-get update && sudo apt-get install cloudflared

# 4. 토큰으로 이 서버를 Cloudflare 터널에 연결
sudo cloudflared service install eyJ...토큰...
```

토큰은 "이 서버가 coach 터널에 속한다"는 인증 키다.
Cloudflare 대시보드에서 터널 생성 시 발급된다.

---

## 5단계: GitHub Secrets

### 왜 Secrets를 쓰나?

배포할 때 서버에 `.env` 파일을 만들어야 한다 (API 키, DB 비밀번호 등).
그런데 `.env`는 GitHub에 올리면 안 된다.

GitHub Secrets는 GitHub에 비밀 정보를 암호화해서 저장하는 기능이다.
배포 시 GitHub Actions가 Secrets를 꺼내서 서버에 `.env` 파일을 만들어준다.
이렇게 하면 코드에 비밀 정보를 넣지 않아도 된다.

### 등록한 항목

| 이름 | 의미 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude AI를 쓰기 위한 API 키. 없으면 AI 코치 기능 작동 안 함 |
| `DB_PASSWORD` | PostgreSQL 데이터베이스 비밀번호. 임의 문자열 OK |
| `TUNNEL_TOKEN` | cloudflared가 Cloudflare 터널에 연결하는 인증 키 |

---

## 6단계: GitHub self-hosted runner

### GitHub Actions란?

코드를 push하면 자동으로 정해진 작업을 실행해주는 CI/CD 시스템이다.
이 프로젝트의 `.github/workflows/deploy.yml`에 배포 절차가 적혀있다.

```yaml
# push가 발생하면:
# 1. 코드를 서버로 가져오고
# 2. .env 파일을 Secrets로 생성하고
# 3. Docker 컨테이너를 빌드하고 실행
# 4. 헬스체크로 정상 실행 확인
```

### runner란?

GitHub Actions 작업을 실제로 실행하는 프로그램이다.
GitHub가 제공하는 기본 runner를 쓸 수도 있지만, 그러면 서버에 SSH 키 설정 등이 필요하다.

**self-hosted runner**는 우리 서버에 직접 runner를 설치하는 방식이다.
서버 안에 runner가 있으니 SSH 없이 바로 docker compose 명령을 실행할 수 있다.

```
GitHub Actions (코드 push 감지)
    → self-hosted runner (우리 서버 안에 설치됨)
        → docker compose -f docker-compose.prod.yml up -d --build
            → 컨테이너 빌드 및 실행
```

### 왜 svc.sh로 서비스 등록했나?

`./run.sh`로 실행하면 터미널을 닫으면 runner도 멈춘다.
`sudo ./svc.sh install && sudo ./svc.sh start`를 하면 **systemd 서비스**로 등록된다.
서버가 재시작되어도 자동으로 runner가 켜진다.

---

## 7단계: 배포 과정 이해

코드를 push하면 다음이 자동으로 일어난다:

```
1. git push → GitHub에 코드 업로드
2. GitHub Actions 트리거 → deploy.yml 실행 시작
3. runner가 코드 체크아웃 (서버로 코드 가져옴)
4. Secrets로 .env 파일 생성
5. docker compose -f docker-compose.prod.yml up -d --build
   - db 컨테이너: PostgreSQL 시작
   - api 컨테이너: FastAPI 앱 빌드 + 시작
   - web 컨테이너: React 빌드 + nginx 시작
   - cloudflared 컨테이너: Tunnel 연결
6. 헬스체크: api가 정상 응답하는지 확인
7. 성공 시 초록 체크 / 실패 시 빨간 X
```

---

## 실제로 겪은 문제들과 이유

### 문제 1: `sudo usermod`가 맥북에서 비밀번호 요구
**원인**: 맥북 터미널에서 실행함. 프롬프트가 `ubuntu@`로 시작하지 않으면 서버가 아님.
**해결**: Lightsail 콘솔에서 Connect 버튼으로 서버 터미널 접속 후 실행.

### 문제 2: GitHub 비밀번호로 push 안 됨
**원인**: GitHub은 2021년부터 git 명령에서 비밀번호 인증을 막음.
**해결**: Personal Access Token(PAT) 발급 후 비밀번호 대신 입력.

### 문제 3: .env가 커밋에 포함되어 push 차단
**원인**: `.gitignore` 설정 전에 이미 `.env`가 커밋 히스토리에 들어가 있었음.
**해결**: `git filter-repo`로 히스토리에서 완전 삭제 후 강제 push.

### 문제 4: push 후 filter-repo로 remote 초기화
**원인**: filter-repo는 히스토리를 재작성하면서 remote 설정도 초기화함.
**해결**: `git remote add origin ...` 으로 remote 재등록.

### 문제 5: node_modules, .venv 때문에 46MB push → HTTP 400
**원인**: 수천 개의 패키지 파일이 git에 포함됨. GitHub은 대용량 push를 막음.
**해결**: `git rm --cached`로 추적 해제 후 `.gitignore`에 추가. orphan 브랜치로 히스토리 초기화.

### 문제 6: API 컨테이너 Restarting (헬스체크 실패)
**원인**: DB 초기화 코드에서 User를 추가한 직후 flush 없이 AppSettings를 추가하자
PostgreSQL이 FK(외래키) 제약을 위반으로 판단함.
**해결**: `await db.flush()` 추가로 User INSERT를 먼저 확정시킨 후 AppSettings 삽입.

### 문제 7: 배포 성공인데 502 Bad Gateway
**원인**: 도메인 네임서버 변경이 아직 전파 안 됨. DNS 변경은 전 세계 서버에 반영되는 데 시간이 걸림.
**해결**: 1~6시간 대기. 서버 내부에서는 `docker exec`로 web 컨테이너가 정상임을 확인.

---

## 완료 체크리스트

- [ ] Lightsail 인스턴스: Ubuntu 22.04, 2GB RAM
- [ ] Docker 설치 완료, ubuntu 사용자 docker 그룹 추가
- [ ] GitHub 레포에 코드 push 완료 (node_modules, .venv, .env 제외)
- [ ] .gitignore 설정됨
- [ ] Cloudflare 도메인 `gogojo.cloud` 연결
- [ ] 가비아 네임서버 → Cloudflare 네임서버로 변경
- [ ] Cloudflare Tunnel `coach` 상태: HEALTHY
- [ ] GitHub Secrets 3개 등록 (ANTHROPIC_API_KEY, DB_PASSWORD, TUNNEL_TOKEN)
- [ ] GitHub runner 상태: Idle
- [ ] 첫 배포 Actions에서 성공 (초록 체크)
- [ ] `https://coach.gogojo.cloud` 접속 확인
