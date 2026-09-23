"""Google sign-in: OAuth 2.0 authorization-code flow with PKCE.

Only two server-to-server calls are made (token exchange, then OpenID userinfo) over TLS
to Google, so no ID-token signature handling is needed here."""
from __future__ import annotations

import base64
import hashlib
import secrets
import ssl
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import truststore

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class OAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    name: str


@dataclass(frozen=True)
class PkcePair:
    verifier: str
    challenge: str

    @classmethod
    def new(cls) -> "PkcePair":
        verifier = secrets.token_urlsafe(48)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return cls(verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii"))


class GoogleOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, timeout: float = 15):
        self._client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._timeout = timeout

    def authorization_url(self, state: str, pkce: PkcePair) -> str:
        return AUTH_URL + "?" + urlencode({
            "client_id": self._client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": pkce.challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        })

    def fetch_profile(self, code: str, code_verifier: str) -> GoogleProfile:
        try:
            with httpx.Client(timeout=self._timeout, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as http:
                token = http.post(TOKEN_URL, data={
                    "code": code, "client_id": self._client_id, "client_secret": self._client_secret,
                    "redirect_uri": self.redirect_uri, "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                })
                if token.status_code != 200:
                    raise OAuthError(f"token exchange failed ({token.status_code})")
                info = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {token.json()['access_token']}"})
                if info.status_code != 200:
                    raise OAuthError(f"userinfo failed ({info.status_code})")
                data = info.json()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise OAuthError(str(exc)) from exc
        if not data.get("sub") or not data.get("email"):
            raise OAuthError("profile without sub/email")
        return GoogleProfile(sub=str(data["sub"]), email=data["email"].lower(),
                             email_verified=bool(data.get("email_verified")),
                             name=data.get("name") or data["email"].split("@")[0])
