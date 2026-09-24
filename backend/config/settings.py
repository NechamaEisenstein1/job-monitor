"""Configuration loading: YAML files for business rules, environment variables for secrets."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Minimal .env loader. Real environment variables always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(2) or ""), value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return _expand_env(yaml.safe_load(fh) or {})


# ---------------------------------------------------------------- typed config

@dataclass(frozen=True)
class RunStatusConfig:
    success_ratio: float
    partial_ratio: float


@dataclass(frozen=True)
class LocationsConfig:
    primary: list[str]
    secondary: list[str]
    # Some sources publish no location field; then look for the city in the posting text.
    search_text_when_missing: bool = False


@dataclass(frozen=True)
class JuniorKeywords:
    strong_positive: list[str]
    medium_positive: list[str]
    strong_negative: list[str]


@dataclass(frozen=True)
class JuniorScoring:
    base: float
    strong_positive: float
    medium_positive: float
    strong_negative: float


@dataclass(frozen=True)
class ExperienceConfig:
    # Junior = at most this many years required ("no experience" counts as 0).
    # A posting that requires more is never junior, whatever its keywords say.
    junior_max_years: float = 2


@dataclass(frozen=True)
class Thresholds:
    junior_score: float
    match_title_fuzzy: float


@dataclass(frozen=True)
class RetentionConfig:
    # Skip pruning a site when one run would remove more than this share of its postings.
    max_prune_ratio: float = 0.5


@dataclass(frozen=True)
class EmailConfig:
    recipient: str
    subject: str
    notification_type: str
    claim_timeout_minutes: int = 30


@dataclass(frozen=True)
class ScraperConfig:
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    rate_limit_per_site: float
    max_concurrent_workers: int


@dataclass(frozen=True)
class RolesConfig:
    types: dict[str, list[str]]
    eligible_types: list[str]
    fallback_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GovernmentConfig:
    keywords: list[str]


@dataclass(frozen=True)
class RankingConfig:
    junior_bonus: float
    role_priority: list[str]
    role_step: float


@dataclass(frozen=True)
class ScheduleConfig:
    timezone: str = "Asia/Jerusalem"


@dataclass(frozen=True)
class UsersConfig:
    alert_subject: str = "משרות שמתאימות לך - {date}"
    outreach_daily_limit: int = 30
    session_days: int = 14
    admin_emails: str = ""

    @property
    def admin_email_set(self) -> frozenset[str]:
        return frozenset(e.strip().lower() for e in self.admin_emails.split(",") if e.strip())


@dataclass(frozen=True)
class BillingConfig:
    """Points economy and subscription pricing. Values may come from ${ENV} in the YAML,
    so they are coerced here. The price is 0 until a real payment provider is wired in."""
    points_per_manual_job: int = 10
    # Anti-farming: postings beyond this per day are published but earn no points.
    max_awarded_posts_per_day: int = 10
    subscription_price_ils: float = 0.0
    subscription_price_points: int = 100
    subscription_days: int = 30
    trial_days: int = 14
    featured_job_points: int = 50
    featured_job_days: int = 7

    def __post_init__(self) -> None:
        for f in fields(self):
            cast = float if f.name.endswith("_ils") else int
            object.__setattr__(self, f.name, cast(getattr(self, f.name) or 0))
        if self.subscription_price_ils < 0 or self.subscription_price_points < 0:
            raise ValueError("billing prices must not be negative")


@dataclass(frozen=True)
class MatchingConfig:
    run_status: RunStatusConfig
    locations: LocationsConfig
    junior_keywords: JuniorKeywords
    junior_scoring: JuniorScoring
    experience: ExperienceConfig
    thresholds: Thresholds
    retention: RetentionConfig
    email: EmailConfig
    scraper: ScraperConfig
    roles: RolesConfig
    government: GovernmentConfig
    ranking: RankingConfig
    schedule: ScheduleConfig
    users: UsersConfig
    billing: BillingConfig = BillingConfig()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MatchingConfig":
        return cls(
            run_status=RunStatusConfig(**raw["run_status"]),
            locations=LocationsConfig(**raw["locations"]),
            junior_keywords=JuniorKeywords(**raw["keywords"]["junior"]),
            junior_scoring=JuniorScoring(**raw["junior_scoring"]),
            experience=ExperienceConfig(**raw.get("experience", {})),
            thresholds=Thresholds(**raw["thresholds"]),
            retention=RetentionConfig(**raw.get("retention", {})),
            email=EmailConfig(**raw["email"]),
            scraper=ScraperConfig(**raw["scraper"]),
            roles=RolesConfig(**raw["roles"]),
            government=GovernmentConfig(**raw["government"]),
            ranking=RankingConfig(**raw["ranking"]),
            schedule=ScheduleConfig(**raw.get("schedule", {})),
            users=UsersConfig(**raw.get("users", {})),
            billing=BillingConfig(**raw.get("billing", {})),
        )


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str
    sender: str
    use_tls: bool


def normalize_database_url(url: str) -> str:
    """Hosting providers hand out postgres:// or postgresql:// URLs, which SQLAlchemy maps to
    the psycopg2 driver. This project ships psycopg 3, so name that driver explicitly."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    config_dir: Path
    email_outbox_dir: Path
    smtp: SmtpSettings | None
    log_level: str
    # Used for links in emails, e.g. https://jobs.example.com
    public_base_url: str = "http://localhost:8000"
    # True in production (HTTPS): the session cookie is then sent over HTTPS only.
    cookie_secure: bool = False
    # Anyone may create an account (set ALLOW_SIGNUP=false for invite-only).
    allow_signup: bool = True
    # Google sign-in is enabled when both are set (Google Cloud console -> OAuth client).
    google_client_id: str = ""
    google_client_secret: str = ""
    # Google Search Console "HTML tag" verification code (the content="..." value only).
    google_site_verification: str = ""
    # Public contact address shown on the privacy page (data/deletion requests).
    contact_email: str = ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        smtp_host = os.environ.get("SMTP_HOST", "")
        smtp = None
        if smtp_host:
            smtp = SmtpSettings(
                host=smtp_host,
                port=int(os.environ.get("SMTP_PORT", "587")),
                user=os.environ.get("SMTP_USER", ""),
                password=os.environ.get("SMTP_PASSWORD", ""),
                sender=os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
                use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
            )
        public_base_url = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        return cls(
            database_url=normalize_database_url(
                os.environ.get("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'job_monitor.db'}")),
            config_dir=Path(os.environ.get("CONFIG_DIR", PROJECT_ROOT / "config")),
            email_outbox_dir=Path(os.environ.get("EMAIL_OUTBOX_DIR", PROJECT_ROOT / "outbox")),
            smtp=smtp,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            public_base_url=public_base_url,
            # Secure cookies whenever the site is served over HTTPS, unless explicitly overridden.
            cookie_secure=os.environ.get("COOKIE_SECURE", str(public_base_url.startswith("https://"))).lower() == "true",
            allow_signup=os.environ.get("ALLOW_SIGNUP", "true").lower() == "true",
            google_client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
            google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            google_site_verification=os.environ.get("GOOGLE_SITE_VERIFICATION", ""),
            contact_email=os.environ.get("CONTACT_EMAIL", ""),
        )


def load_matching_config(config_dir: Path) -> MatchingConfig:
    load_dotenv()
    return MatchingConfig.from_dict(_read_yaml(config_dir / "matching.yaml"))


def load_sources_config(config_dir: Path) -> list[SourceConfig]:
    load_dotenv()
    raw = _read_yaml(config_dir / "sources.yaml")
    sources = []
    for item in raw.get("sources") or []:
        item = dict(item)
        sources.append(SourceConfig(name=item.pop("name"), type=item.pop("type"), options=item))
    return sources
