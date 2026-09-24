"""Send outreach from the user's own Gmail (Gmail API, scope gmail.send only).

* The user connects once (OAuth code flow + PKCE, offline access). Only the refresh token
  is kept, encrypted with GMAIL_TOKEN_KEY (Fernet); access tokens live in memory for one send.
* gmail.send can only SEND - it cannot read, list or delete anything in the mailbox.
* Disconnecting revokes the token at Google and deletes it here."""
from __future__ import annotations

import base64
import hashlib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode

import httpx
import truststore
from cryptography.fernet import Fernet, InvalidToken

from backend.infrastructure.email.renderer import RenderedEmail
from backend.infrastructure.oauth.google import AUTH_URL, TOKEN_URL, USERINFO_URL, OAuthError, PkcePair

SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class GmailRevokedError(OAuthError):
    """The user withdrew access (or it expired): they must connect again."""


class TokenCipher:
    """Fernet encryption keyed from GMAIL_TOKEN_KEY. Any long random string works (e.g. the
    value Render generates): it is stretched to a Fernet key with SHA-256."""

    def __init__(self, secret: str):
        if len(secret) < 32:
            raise ValueError("GMAIL_TOKEN_KEY must be at least 32 characters")
        self._fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest()))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:  # key rotated / data tampered with
            raise GmailRevokedError("stored Gmail token cannot be decrypted") from exc


@dataclass(frozen=True)
class GmailGrant:
    email: str
    refresh_token: str
    scopes: str


class GmailClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, timeout: float = 20):
        self._client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._timeout = timeout

    def _http(self) -> httpx.Client:
        return httpx.Client(timeout=self._timeout, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))

    def authorization_url(self, state: str, pkce: PkcePair, login_hint: str) -> str:
        return AUTH_URL + "?" + urlencode({
            "client_id": self._client_id, "redirect_uri": self.redirect_uri, "response_type": "code",
            "scope": f"openid email {SEND_SCOPE}", "state": state,
            "code_challenge": pkce.challenge, "code_challenge_method": "S256",
            # offline + consent: Google returns a refresh token every time the user connects.
            "access_type": "offline", "prompt": "consent", "login_hint": login_hint,
        })

    def exchange(self, code: str, code_verifier: str) -> GmailGrant:
        try:
            with self._http() as http:
                token = http.post(TOKEN_URL, data={
                    "code": code, "client_id": self._client_id, "client_secret": self._client_secret,
                    "redirect_uri": self.redirect_uri, "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                })
                if token.status_code != 200:
                    raise OAuthError(f"token exchange failed ({token.status_code})")
                data = token.json()
                if SEND_SCOPE not in data.get("scope", "").split():
                    raise OAuthError("gmail.send permission was not granted")
                if not data.get("refresh_token"):
                    raise OAuthError("no refresh token returned")
                info = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {data['access_token']}"})
                if info.status_code != 200:
                    raise OAuthError(f"userinfo failed ({info.status_code})")
                email = info.json().get("email", "")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise OAuthError(str(exc)) from exc
        return GmailGrant(email=email, refresh_token=data["refresh_token"], scopes=data["scope"])

    def _access_token(self, http: httpx.Client, refresh_token: str) -> str:
        response = http.post(TOKEN_URL, data={
            "client_id": self._client_id, "client_secret": self._client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        })
        if response.status_code == 400 and response.json().get("error") == "invalid_grant":
            raise GmailRevokedError("Gmail access was revoked or expired")
        if response.status_code != 200:
            raise OAuthError(f"token refresh failed ({response.status_code})")
        return response.json()["access_token"]

    def send(self, refresh_token: str, *, sender_name: str, sender_email: str, recipient: str,
             email: RenderedEmail) -> str:
        """Send from the user's mailbox (it also lands in their Sent folder). Returns the Gmail id."""
        message = EmailMessage()
        message["From"] = formataddr((sender_name, sender_email))
        message["To"] = recipient
        message["Subject"] = email.subject
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        try:
            with self._http() as http:
                access = self._access_token(http, refresh_token)
                response = http.post(SEND_URL, json={"raw": raw}, headers={"Authorization": f"Bearer {access}"})
                if response.status_code == 401:  # 403 is also used for rate limits: not a revocation
                    raise GmailRevokedError("Gmail rejected the credentials (401)")
                if response.status_code != 200:
                    raise OAuthError(f"Gmail send failed ({response.status_code})")
                return response.json().get("id", "")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise OAuthError(str(exc)) from exc

    def revoke(self, refresh_token: str) -> None:
        """Best effort: the token is deleted locally whatever Google answers."""
        try:
            with self._http() as http:
                http.post(REVOKE_URL, data={"token": refresh_token})
        except httpx.HTTPError:
            pass
