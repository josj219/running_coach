"""코치 AI 제공자 라우팅 — DeepSeek(OpenAI 호환) / Anthropic. 실제 API 미호출(가짜 클라이언트)."""
import pytest
from app.config import Settings
from app.services import coach


def _settings(**over):
    base = dict(coach_mock="", deepseek_api_key="ds-key", anthropic_api_key="",
                coach_provider="", deepseek_model="deepseek-v4-pro")
    base.update(over)
    return Settings(_env_file=None, **base)


class _Msg:
    def __init__(self, content): self.content = content
class _Choice:
    def __init__(self, content): self.message = _Msg(content)
class _Resp:
    def __init__(self, content): self.choices = [_Choice(content)]


class _FakeDeepSeek:
    """openai.AsyncOpenAI 흉내 — 호출 인자를 기록하고 정해진 텍스트를 돌려준다."""
    def __init__(self, text, fail=None):
        self.text, self.fail, self.calls = text, fail, []
        self.chat = self
        self.completions = self
    async def create(self, **kw):
        self.calls.append(kw)
        if self.fail: raise self.fail
        if kw.get("stream"):
            async def gen():
                for tok in ["분석", " 중", "…"]:
                    class D: content = tok
                    class C: delta = D()
                    class Ch: choices = [C()]
                    yield Ch()
            return gen()
        return _Resp(self.text)


def test_provider_auto_selects_deepseek_when_key_present(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings())
    assert coach.provider() == "deepseek"
    assert coach.model_name() == "deepseek-v4-pro"


def test_provider_falls_back_to_anthropic_without_deepseek_key(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(deepseek_api_key="", anthropic_api_key="a"))
    assert coach.provider() == "anthropic"
    assert coach.model_name() == "claude-sonnet-4-6"


def test_provider_explicit_override_and_unknown(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(coach_provider="anthropic", anthropic_api_key="a"))
    assert coach.provider() == "anthropic"
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(coach_provider="gemini"))
    with pytest.raises(coach.CoachError):
        coach.provider()


async def test_generate_uses_deepseek_chat_completions_and_parses_json(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings())
    fake = _FakeDeepSeek('설명입니다.\n```json\n{"warmup": "걷기", "adjusted": false}\n```')
    monkeypatch.setattr(coach, "_deepseek_client", lambda: fake)
    data = await coach.generate("daily", "SYSTEM", "USER")
    assert data == {"warmup": "걷기", "adjusted": False}
    kw = fake.calls[0]
    assert kw["model"] == "deepseek-v4-pro"
    assert kw["extra_body"] == {"thinking": {"type": "disabled"}}  # 기본: 추론 비활성(응답 지연·토큰 소진 방지)
    assert kw["max_tokens"] == 4096
    assert kw["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert kw["messages"][1] == {"role": "user", "content": "USER"}


async def test_image_requests_always_go_to_anthropic(monkeypatch):
    """DeepSeek은 이미지를 받아도 내용을 지어낸다(검증됨) → 스크린샷 추출은 Anthropic으로만."""
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(anthropic_api_key="a"))
    ds = _FakeDeepSeek('{"found": true}')
    monkeypatch.setattr(coach, "_deepseek_client", lambda: ds)
    called = {}
    async def fake_anthropic(system_prompt, user_message, image_b64, image_media_type):
        called["image"] = (image_b64, image_media_type)
        return '{"found": true, "distance_km": 5.0}'
    monkeypatch.setattr(coach, "_anthropic_generate", fake_anthropic)
    data = await coach.generate("extract", "SYS", "읽어줘", image_b64="QUJD", image_media_type="image/png")
    assert data["distance_km"] == 5.0
    assert called["image"] == ("QUJD", "image/png")
    assert ds.calls == []


async def test_image_without_anthropic_key_is_clear_error_not_hallucination(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(anthropic_api_key=""))
    ds = _FakeDeepSeek('{"found": true, "distance_km": 42.195}')
    monkeypatch.setattr(coach, "_deepseek_client", lambda: ds)
    with pytest.raises(coach.CoachError) as ei:
        await coach.generate("extract", "SYS", "읽어줘", image_b64="QUJD")
    assert "ANTHROPIC_API_KEY" in str(ei.value)
    assert ds.calls == []


async def test_text_failure_without_fallback_becomes_coach_error(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(anthropic_api_key="a"))
    monkeypatch.setattr(coach, "_deepseek_client", lambda: _FakeDeepSeek("", fail=RuntimeError("boom")))
    with pytest.raises(coach.CoachError) as ei:
        await coach.generate("daily", "SYS", "USER")   # 텍스트 요청은 Anthropic으로 우회하지 않는다
    assert "deepseek" in str(ei.value)


async def test_missing_deepseek_key_is_clear_error(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(coach_provider="deepseek", deepseek_api_key=""))
    with pytest.raises(coach.CoachError) as ei:
        await coach.generate("daily", "SYS", "USER")
    assert "DEEPSEEK_API_KEY" in str(ei.value)


async def test_stream_text_uses_deepseek_delta_content(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings())
    fake = _FakeDeepSeek("")
    monkeypatch.setattr(coach, "_deepseek_client", lambda: fake)
    out = [t async for t in coach.stream_text("SYS", "USER")]
    assert "".join(out) == "분석 중…"
    assert fake.calls[0]["stream"] is True


async def test_health_exposes_provider_and_model(client, monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings())
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["coach_provider"] == "deepseek"
    assert r.json()["coach_model"] == "deepseek-v4-pro"


async def test_thinking_mode_opt_in_raises_token_budget(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: _settings(deepseek_thinking=True))
    fake = _FakeDeepSeek('{"ok": true}')
    monkeypatch.setattr(coach, "_deepseek_client", lambda: fake)
    await coach.generate("daily", "SYS", "USER")
    assert fake.calls[0]["extra_body"] == {"thinking": {"type": "enabled"}}
    assert fake.calls[0]["max_tokens"] == 8192
