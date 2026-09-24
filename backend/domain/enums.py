from enum import Enum


class JobStatus(Enum):
    ACTIVE = "active"
    NOT_SEEN_RECENTLY = "not_seen_recently"
    ARCHIVED = "archived"


class JobSourceStatus(Enum):
    ACTIVE = "active"
    NOT_SEEN_RECENTLY = "not_seen_recently"
    ARCHIVED = "archived"


class RunStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ScrapeStatus(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    ZERO_RESULTS = "zero_results"
    CONFIG_ERROR = "config_error"


class JobChange(Enum):
    NEW = "new"
    CONTENT_UPDATED = "content_updated"
    NEW_SOURCE = "new_source"
    SOURCE_URL_UPDATED = "source_url_updated"


class ExperienceLevel(Enum):
    JUNIOR = "junior"
    EXPERIENCED = "experienced"


class OutreachStatus(Enum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class UserRole(Enum):
    USER = "user"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class SubscriptionStatus(Enum):
    INACTIVE = "inactive"
    TRIAL = "trial"
    ACTIVE = "active"


class PointAction(Enum):
    JOB_POSTED = "job_posted"
    JOB_REMOVED = "job_removed"          # reverses the JOB_POSTED award
    SUBSCRIPTION = "subscription"        # points redeemed for a subscription
    FEATURED_JOB = "featured_job"        # points redeemed to pin a posting


class PaymentMethod(Enum):
    FREE = "free"      # allowed only while the configured price is 0
    POINTS = "points"
