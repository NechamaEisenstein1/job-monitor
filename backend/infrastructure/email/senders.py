from __future__ import annotations

import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from backend.config.settings import SmtpSettings
from backend.infrastructure.email.renderer import RenderedEmail


class EmailSender(Protocol):
    def send(self, recipient: str, email: RenderedEmail) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: SmtpSettings, timeout_seconds: float = 30):
        self._cfg = settings
        self._timeout = timeout_seconds

    def send(self, recipient: str, email: RenderedEmail) -> None:
        msg = EmailMessage()
        msg["Subject"] = email.subject
        msg["From"] = self._cfg.sender
        msg["To"] = recipient
        if email.reply_to:
            msg["Reply-To"] = email.reply_to
        msg.set_content(email.text)
        msg.add_alternative(email.html, subtype="html")
        with smtplib.SMTP(self._cfg.host, self._cfg.port, timeout=self._timeout) as smtp:
            if self._cfg.use_tls:
                smtp.starttls()
            if self._cfg.user:
                smtp.login(self._cfg.user, self._cfg.password)
            smtp.send_message(msg)


class FileEmailSender:
    """Local development: writes the email to an outbox folder instead of sending."""

    def __init__(self, outbox_dir: Path):
        self._dir = outbox_dir

    def send(self, recipient: str, email: RenderedEmail) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", recipient)
        path = self._dir / f"{datetime.now():%Y%m%d-%H%M%S}-{safe}.html"
        path.write_text(email.html, encoding="utf-8")
