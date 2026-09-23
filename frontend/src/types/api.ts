// Mirrors backend/application/dto.py. The backend is the source of truth.

export type JobStatus = "active" | "not_seen_recently" | "archived";
export type RunStatus = "success" | "partial" | "failed";
export type ScrapeStatus =
  | "success"
  | "timeout"
  | "network_error"
  | "parse_error"
  | "zero_results"
  | "config_error";
export type ChangeType = "new" | "content_updated" | "new_source" | "source_url_updated";
export type JobSort = "relevance" | "newest" | "updated" | "score";
export type RoleType = "software" | "qa" | "embedded" | "hardware" | "other";
export type ExperienceLevel = "junior" | "experienced";

export interface Evaluation {
  junior_score: number;
  is_eligible: boolean;
  matched_rules: string[];
  rejection_reasons: string[];
  scrape_run_id: string;
  created_at: string;
  is_junior: boolean;
  location_matched: boolean;
  role_type: RoleType;
  is_government_tender: boolean;
  rank_score: number;
}

export interface JobListItem {
  id: number;
  title: string;
  client_company: string | null;
  location: string | null;
  status: JobStatus;
  junior_score: number | null;
  is_eligible: boolean | null;
  is_junior: boolean | null;
  role_type: RoleType | null;
  is_government_tender: boolean;
  known_recruiters: string[];
  source_count: number;
  recruitment_companies: string[];
  last_seen_at: string | null;
  updated_at: string;
  first_seen_at: string;
}

export interface JobList {
  items: JobListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobDetail {
  id: number;
  title: string;
  description: string;
  requirements: string;
  client_company: string | null;
  employment_type: string | null;
  location: string | null;
  region: string | null;
  status: JobStatus;
  published_at: string | null;
  first_seen_at: string;
  updated_at: string;
  last_seen_at: string | null;
  evaluation: Evaluation | null;
}

export interface JobSource {
  id: number;
  recruitment_company: string;
  source_job_id: string | null;
  source_url: string;
  external_title: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: JobStatus;
}

export interface JobChange {
  id: number;
  job_id: number;
  job_title: string;
  change_type: ChangeType;
  recruitment_company: string;
  scrape_run_id: string;
  created_at: string;
}

export interface ScrapeRun {
  id: string;
  scheduled_date: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  status: RunStatus;
  sites_total: number;
  sites_succeeded: number;
  sites_failed: number;
  raw_jobs_found: number;
  normalized_jobs: number;
  canonical_jobs_touched: number;
  eligible_jobs: number;
  success_ratio: number | null;
}

export interface ScraperRun {
  id: number;
  site: string;
  status: ScrapeStatus;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  jobs_fetched: number;
  jobs_parsed: number;
  jobs_invalid: number;
  warning: string | null;
  error: string | null;
}

export interface RunDetail extends ScrapeRun {
  scrapers: ScraperRun[];
}

export interface SourceHealth {
  name: string;
  type: string;
  enabled: boolean;
  note: string | null;
  last_status: ScrapeStatus | null;
  last_run_at: string | null;
  last_successful_at: string | null;
  jobs_fetched: number | null;
  last_error: string | null;
  active_job_sources: number;
}

export interface Stats {
  active_jobs: number;
  new_jobs: number;
  updated_jobs: number;
  eligible_jobs: number;
  latest_run: ScrapeRun | null;
  failed_sources: string[];
}

export interface JobFilterValues {
  q: string;
  location: string;
  eligible: "" | "true" | "false";
  status: "" | JobStatus;
  source: string;
  role_type: RoleType | "all";
  government: "" | "true";
  sort: JobSort;
  page: number;
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
  experience_level: ExperienceLevel;
  alerts_enabled: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface RecruiterInput {
  name: string;
  email: string;
  company: string;
}

export interface Recruiter extends RecruiterInput {
  id: number;
  created_at: string;
}

export interface OutreachResult {
  recruiter_id: number;
  recruiter_name: string;
  status: "sent" | "failed" | "skipped" | "not_sent";
  detail: string | null;
}

export interface NamedCount {
  name: string;
  count: number;
}

export interface DailyCount {
  day: string;
  logins: number;
  failed_logins: number;
  page_views: number;
}

export interface AdminStats {
  users_total: number;
  users_active_7d: number;
  logins_7d: number;
  failed_logins_7d: number;
  page_views_7d: number;
  alerts_sent_7d: number;
  outreach_sent_7d: number;
  jobs_active: number;
  jobs_eligible: number;
  government_tenders_active: number;
  daily: DailyCount[];
  top_pages: NamedCount[];
  jobs_by_source: NamedCount[];
  jobs_by_role: NamedCount[];
  recent_runs: ScrapeRun[];
}
