"""앱 설정 — 환경변수 기반 (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB. 로컬 단독 실행 시 sqlite 폴백, compose에서는 postgres URL 주입.
    database_url: str = "sqlite+aiosqlite:///./coach.db"

    # AI
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    coach_mock: str = ""  # "1"이면 실 API 미호출(테스트/CI)

    # 인증 (이메일+비밀번호 → JWT). 운영에서는 JWT_SECRET을 반드시 환경변수로 주입.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_days: int = 30

    # Strava OAuth (https://www.strava.com/settings/api 에서 발급)
    strava_client_id: str = ""
    strava_client_secret: str = ""
    # OAuth 콜백 후 사용자를 돌려보낼 프론트 주소
    web_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"

    tz: str = "Asia/Seoul"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
