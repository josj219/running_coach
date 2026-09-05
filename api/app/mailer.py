"""메일 발송 — 표준 smtplib(STARTTLS/SSL)를 스레드에서 실행한다.

SMTP_HOST가 비어 있으면 '콘솔 모드': 실제 발송 없이 서버 로그에 내용을 남기고 `outbox`에 쌓는다.
로컬 개발과 테스트가 메일 서버 없이 동작하도록 하기 위해서다(테스트는 outbox에서 코드를 읽는다).
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

log = logging.getLogger("coach.mailer")

# 콘솔 모드에서 보낸 메일 기록(최근 20통). 테스트/로컬 디버깅용.
outbox: list[dict] = []
_OUTBOX_MAX = 20


def is_configured() -> bool:
    return bool(get_settings().smtp_host)


def _send_sync(to: str, subject: str, body: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.smtp_from or s.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if s.smtp_port == 465:
        with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=20) as srv:
            if s.smtp_user:
                srv.login(s.smtp_user, s.smtp_password)
            srv.send_message(msg)
        return
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as srv:
        srv.ehlo()
        srv.starttls()
        if s.smtp_user:
            srv.login(s.smtp_user, s.smtp_password)
        srv.send_message(msg)


async def send_mail(to: str, subject: str, body: str) -> None:
    """메일 1통 발송. 미설정이면 로그+outbox에만 남긴다. 발송 실패는 예외로 올린다."""
    if not is_configured():
        log.warning("[mailer:console] to=%s subject=%s\n%s", to, subject, body)
        outbox.append({"to": to, "subject": subject, "body": body})
        del outbox[:-_OUTBOX_MAX]
        return
    await asyncio.to_thread(_send_sync, to, subject, body)
