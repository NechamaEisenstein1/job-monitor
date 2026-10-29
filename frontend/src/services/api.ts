import { errorLabel, he } from "../i18n/he";
import type {
  AdminStats, AuthConfig, BillingPrices, ContactCategory, ContactMessagePage, ExperienceLevel, ForumCategory, ForumThread, ForumThreadPage, MyContactMessagePage, JobApplication, Region, JobChange, JobDetail, JobFilterValues, JobList, JobSource,
  GmailStatus, JobSubmission, ManualJob, ManualJobInput, ReviewResult, VerificationResult, OutreachLogEntry, OutreachResult, PublishResult, Recruiter, RecruiterInput, RegisterInput, RunDetail,
  ScrapeRun, SourceHealth, Stats, SubscriptionState, User, UserRole, Wallet,
} from "../types/api";
import type { Article, ArticleInput, ArticleSummary, EditableArticle } from "../types/articles";

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
const del = <T = void>(path: string) => request<T>("DELETE", path);

/** Empty optional fields go out as null (the server parses the date; "" is not one). */
const postingBody = (j: ManualJobInput) =>
  ({ ...j, source_recruiter: j.source_recruiter || null, source_published_on: j.source_published_on || null });

export const PAGE_SIZE = 25;
/** Personal area matches: a shorter page. */
export const MATCHES_PAGE_SIZE = 10;

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
  regions: () => get<Region[]>("/regions"),
  updateProfile: (p: { display_name: string; experience_level: ExperienceLevel; alerts_enabled: boolean;
    preferred_regions: string[] }) =>
    put<User>("/me/profile", p),
  recruiters: () => get<Recruiter[]>("/me/recruiters"),
  addRecruiter: (r: RecruiterInput) => post<Recruiter>("/me/recruiters", r),
  updateRecruiter: (id: number, r: RecruiterInput) => put<Recruiter>(`/me/recruiters/${id}`, r),
  deleteRecruiter: (id: number) => del(`/me/recruiters/${id}`),
  matches: (page: number, government?: boolean) =>
    get<JobList>("/me/matches", { page, page_size: MATCHES_PAGE_SIZE, government }),
  outreachStatus: (jobId: number) => get<OutreachResult[]>(`/me/jobs/${jobId}/outreach`),
  sendOutreach: (jobId: number) => post<OutreachResult[]>(`/me/jobs/${jobId}/outreach`),
  outreachLog: () => get<OutreachLogEntry[]>("/me/outreach"),
  gmailStatus: () => get<GmailStatus>("/gmail/status"),
  gmailDisconnect: () => post<void>("/gmail/disconnect"),

  // jobs the user applied to
  applications: () => get<JobApplication[]>("/me/applications"),
  markApplied: (jobId: number) => put<void>(`/me/applications/${jobId}`, {}),
  unmarkApplied: (jobId: number) => del(`/me/applications/${jobId}`),
  removeApplication: (entryId: number) => del(`/me/applications/entry/${entryId}`),

  // "the details are correct" votes
  myVerifications: () => get<number[]>("/me/verifications"),
  verifyJob: (jobId: number, verified: boolean) =>
    (verified ? put<VerificationResult>(`/jobs/${jobId}/verification`, {}) : del<VerificationResult>(`/jobs/${jobId}/verification`)),

  // contact the site admin
  contactAdmin: (m: { category: ContactCategory; subject: string; body: string }) => post<{ id: number }>("/me/contact", m),
  myMessages: (page: number) => get<MyContactMessagePage>("/me/contact", { page, page_size: MATCHES_PAGE_SIZE }),

  // forum
  forumCategories: () => get<ForumCategory[]>("/forum/categories"),
  forumThreads: (f: { category?: string; q?: string; page: number; page_size?: number }) =>
    get<ForumThreadPage>("/forum/threads", { page_size: PAGE_SIZE, ...f }),
  forumThread: (id: number, page: number, countView: boolean) =>
    get<ForumThread>(`/forum/threads/${id}`, { page, count_view: countView ? undefined : false }),
  forumCreateThread: (t: { category: string; title: string; body: string }) => post<{ id: number }>("/forum/threads", t),
  forumUpdateThread: (id: number, t: { title?: string; category?: string; is_pinned?: boolean; is_locked?: boolean }) =>
    put<void>(`/forum/threads/${id}`, t),
  forumReply: (threadId: number, body: string) =>
    post<{ id: number; page: number }>(`/forum/threads/${threadId}/posts`, { body }),
  forumEditPost: (id: number, body: string) => put<void>(`/forum/posts/${id}`, { body }),
  forumDeletePost: (id: number) => del<{ thread_deleted: boolean }>(`/forum/posts/${id}`),
  forumThank: (id: number, thanked: boolean) =>
    (thanked ? put<{ thanks_count: number }>(`/forum/posts/${id}/thanks`, {}) : del<{ thanks_count: number }>(`/forum/posts/${id}/thanks`)),

  // guide articles: anyone reads; the admin also opens drafts
  articles: () => get<ArticleSummary[]>("/articles"),
  article: (slug: string) => get<Article>(`/articles/${encodeURIComponent(slug)}`),

  // admin
  adminArticles: () => get<ArticleSummary[]>("/admin/articles"),
  adminArticle: (id: number) => get<EditableArticle>(`/admin/articles/${id}`),
  adminCreateArticle: (article: ArticleInput) => post<{ id: number }>("/admin/articles", article),
  adminUpdateArticle: (id: number, article: ArticleInput) => put<void>(`/admin/articles/${id}`, article),
  adminDeleteArticle: (id: number) => del(`/admin/articles/${id}`),
  adminStats: () => get<AdminStats>("/admin/stats"),
  adminMessages: (openOnly: boolean, page: number) =>
    get<ContactMessagePage>("/admin/messages", { open_only: openOnly, page, page_size: PAGE_SIZE }),
  adminSetMessageHandled: (id: number, handled: boolean) => put<void>(`/admin/messages/${id}`, { handled }),
  adminReplyToMessage: (id: number, reply: string) => put<void>(`/admin/messages/${id}/reply`, { reply }),
  adminUsers: () => get<User[]>("/admin/users"),
  adminCreateUser: (u: { email: string; display_name: string; password: string; is_admin: boolean;
    experience_level: ExperienceLevel }) => post<User>("/admin/users", u),
  adminUpdateUser: (id: number, u: { is_active?: boolean; is_admin?: boolean; role?: UserRole; new_password?: string }) =>
    put<User>(`/admin/users/${id}`, u),

  // recruiter postings
  myPostings: (all = false) => get<ManualJob[]>("/recruiter/jobs", { all: all || undefined }),
  publishJob: (j: ManualJobInput) => post<PublishResult>("/recruiter/jobs", postingBody(j)),
  removeJob: (id: number) => del<{ points_reversed: number }>(`/recruiter/jobs/${id}`),
  featureJob: (id: number) => post<ManualJob>(`/recruiter/jobs/${id}/feature`),
  submitJob: (j: ManualJobInput) => post<JobSubmission>("/job-submissions", postingBody(j)),
  mySubmissions: () => get<JobSubmission[]>("/job-submissions/mine"),
  adminSubmissions: () => get<JobSubmission[]>("/admin/job-submissions"),
  adminApproveSubmission: (id: number) => post<ReviewResult>(`/admin/job-submissions/${id}/approve`),
  adminRejectSubmission: (id: number, note: string) => post<ReviewResult>(`/admin/job-submissions/${id}/reject`, { note }),

  // points & subscription
  billingPrices: () => get<BillingPrices>("/billing/prices"),
  wallet: () => get<Wallet>("/billing/wallet"),
  subscription: () => get<SubscriptionState>("/billing/subscription"),
  startTrial: () => post<SubscriptionState>("/billing/subscription/trial"),
  checkout: (method: "free" | "points") => post<SubscriptionState>("/billing/subscription/checkout", { method }),
};
