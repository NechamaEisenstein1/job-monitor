import { errorLabel, he } from "../i18n/he";
import type {
  AdminStats, AuthConfig, ExperienceLevel, JobChange, JobDetail, JobFilterValues, JobList, JobSource,
  OutreachResult, Recruiter, RecruiterInput, RegisterInput, RunDetail, ScrapeRun, SourceHealth, Stats, User,
} from "../types/api";

export class ApiError extends Error {
  constructor(public status: number, public code: string | undefined, message: string) {
    super(message);
  }
}

/** Called on any 401 so the app can drop back to the login screen. */
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

type Params = Record<string, string | number | boolean | undefined>;

async function request<T>(method: string, path: string, options: { params?: Params; body?: unknown } = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-Requested-With"] = "fetch"; // required by the server's CSRF check
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`/api${path}${query.size ? `?${query}` : ""}`, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
  if (!response.ok) {
    const detail = await response.json().then((d) => (typeof d?.detail === "string" ? d.detail : undefined)).catch(() => undefined);
    const message = detail ? errorLabel(detail)
      : response.status === 404 ? he.common.notFound : he.common.requestFailed(response.status);
    throw new ApiError(response.status, detail, message);
  }
  return (response.status === 204 ? undefined : response.json()) as Promise<T>;
}

const get = <T>(path: string, params?: Params) => request<T>("GET", path, { params });
const post = <T>(path: string, body?: unknown) => request<T>("POST", path, { body });
const put = <T>(path: string, body: unknown) => request<T>("PUT", path, { body });
const del = (path: string) => request<void>("DELETE", path);

export const PAGE_SIZE = 25;

export const api = {
  // auth
  me: () => get<User>("/auth/me"),
  authConfig: () => get<AuthConfig>("/auth/config"),
  register: (r: RegisterInput) => post<User>("/auth/register", r),
  resendVerification: () => post<void>("/auth/verify/resend"),
  login: (email: string, password: string) => post<User>("/auth/login", { email, password }),
  logout: () => post<void>("/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    post<void>("/auth/password", { current_password, new_password }),
  pageView: (path: string) => post<void>("/analytics/page-view", { path }),

  // monitoring
  stats: () => get<Stats>("/stats"),
  activity: (limit = 15) => get<JobChange[]>("/activity", { limit }),
  jobs: (f: JobFilterValues) =>
    get<JobList>("/jobs", { ...f, role_type: f.role_type === "all" ? undefined : f.role_type, page_size: PAGE_SIZE }),
  job: (id: number) => get<JobDetail>(`/jobs/${id}`),
  jobSources: (id: number) => get<JobSource[]>(`/jobs/${id}/sources`),
  jobHistory: (id: number) => get<JobChange[]>(`/jobs/${id}/history`),
  runs: () => get<ScrapeRun[]>("/runs"),
  run: (id: string) => get<RunDetail>(`/runs/${id}`),
  sources: () => get<SourceHealth[]>("/sources"),

  // personal area
  updateProfile: (p: { display_name: string; experience_level: ExperienceLevel; alerts_enabled: boolean }) =>
    put<User>("/me/profile", p),
  recruiters: () => get<Recruiter[]>("/me/recruiters"),
  addRecruiter: (r: RecruiterInput) => post<Recruiter>("/me/recruiters", r),
  updateRecruiter: (id: number, r: RecruiterInput) => put<Recruiter>(`/me/recruiters/${id}`, r),
  deleteRecruiter: (id: number) => del(`/me/recruiters/${id}`),
  matches: (page: number, government?: boolean) =>
    get<JobList>("/me/matches", { page, page_size: PAGE_SIZE, government }),
  outreachStatus: (jobId: number) => get<OutreachResult[]>(`/me/jobs/${jobId}/outreach`),
  sendOutreach: (jobId: number) => post<OutreachResult[]>(`/me/jobs/${jobId}/outreach`),

  // admin
  adminStats: () => get<AdminStats>("/admin/stats"),
  adminUsers: () => get<User[]>("/admin/users"),
  adminCreateUser: (u: { email: string; display_name: string; password: string; is_admin: boolean;
    experience_level: ExperienceLevel }) => post<User>("/admin/users", u),
  adminUpdateUser: (id: number, u: { is_active?: boolean; is_admin?: boolean; new_password?: string }) =>
    put<User>(`/admin/users/${id}`, u),
};
