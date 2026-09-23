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
