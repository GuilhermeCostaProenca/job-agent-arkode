export type Job = {
  id: string;
  company: string;
  title: string;
  score: number;
  recommendation: string;
  status: string;
  source: string;
  url: string;
  anchors_json?: string;
  score_breakdown_json?: string;
  description?: string;
  location?: string;
};

export type Run = { id: string; started_at: string; status: string; jobs_collected: number };
export type RunStartInput = { sources: string[]; limit: number; rss_feed: string; manual_urls: string[] };
export type RunStartResult = { run_id: string; status: string; jobs_collected: number };
export type Artifact = { id: string; kind: string; path: string };
export type FeedItem = { id: string; source: string; url: string; text: string; is_hiring: boolean; confidence: number };
export type Application = {
  id: string;
  job_id: string;
  status: string;
  connector: string;
  notes: string;
  recommendation: string;
  link: string;
  follow_up_date?: string;
  updated_at: string;
};
export type ExecutionRun = {
  id: string;
  connector: string;
  status: string;
  current_step: string;
  job_id: string;
  updated_at: string;
  pause_reason?: string;
  recommended_action?: string;
  retry_count?: number;
};
export type Dashboard = {
  jobs_discovered: number;
  jobs_ready: number;
  applications_total: number;
  applications_submitted: number;
  execution_paused: number;
  inbox_updates: number;
  platform_breakdown: Record<string, number>;
  recent_runs: Run[];
  recent_executions: ExecutionRun[];
  recent_shortlist_results: ExecutionRun[];
  paused_executions: ExecutionRun[];
  pending_actions: PendingAction[];
  operational_policy: {
    daily_application_limit: number;
    platform_application_limit: number;
    retry_backoff_window_minutes: number;
    max_retries_per_connector: number;
    today_total: number;
    connectors: Array<{ connector: string; today_count: number; recent_failures: number; session_state: string }>;
  };
  browser_sessions: Array<{ id: string; platform: string; state: string; profile_dir: string }>;
  credential_states: Array<{ id: string; platform: string; state: string; detail: string }>;
};
export type PendingAction = {
  kind: string;
  id: string;
  application_id: string;
  job_id: string;
  title: string;
  status: string;
  pause_reason: string;
  recommended_action: string;
  updated_at: string;
};
export type ShortlistItem = {
  job_id: string;
  title: string;
  company: string;
  score: number;
  source: string;
  url: string;
};
export type Profile = {
  profile: {
    name: string;
    target_role: string;
    location: string;
    stacks: string[];
    links: Record<string, string>;
    experiences: Array<{ company: string; period: string; bullets: string[] }>;
    projects: Array<{ name: string; description: string; stack: string[]; links: string[] }>;
    education: string[];
    preferences: Record<string, string | number | boolean>;
    bullet_bank: Record<string, string[]>;
    learning_plan: string[];
  };
  evidences: Array<{ id?: string; kind: string; title: string; content: string; source: string }>;
};
export type ProfileMemoryItem = {
  id: string;
  kind: string;
  title: string;
  content: string;
  confidence: number;
  source: string;
  updated_at: string;
};
export type ProfileConversationTurn = {
  id: string;
  role: string;
  message: string;
  created_at: string;
};
export type ProfileConflict = {
  id: string;
  field: string;
  summary: string;
  recommended_action: string;
  values: string[];
  sources: string[];
  confidence: number;
};
export type ProfileBrain = Profile & {
  memory_items: ProfileMemoryItem[];
  conversation: ProfileConversationTurn[];
  conflicts: ProfileConflict[];
};
export type EmailEvent = { id: string; sender: string; subject: string; snippet: string; status_inferred: string; action_required: boolean; received_at: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new Error(`Nao foi possivel conectar na API (${API_BASE}). Verifique se o backend FastAPI esta rodando e se NEXT_PUBLIC_API_BASE esta correto.`);
  }
  const contentType = res.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : typeof payload === "string"
          ? payload
          : `Request failed: ${res.status}`;
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return payload as T;
}

export async function getJobs(params: { min_score?: number; status?: string; explore?: boolean }): Promise<Array<Job | { job: Job; is_exploration: boolean }>> {
  const qs = new URLSearchParams();
  if (params.min_score !== undefined) qs.set("min_score", String(params.min_score));
  if (params.status) qs.set("status", params.status);
  if (params.explore) qs.set("explore", "true");
  return apiFetch(`/jobs?${qs.toString()}`);
}

export async function getJob(jobId: string): Promise<Job> {
  return apiFetch(`/jobs/${jobId}`);
}

export async function getRuns(): Promise<Run[]> {
  return apiFetch("/runs");
}

export async function startRun(payload: RunStartInput): Promise<RunStartResult> {
  return apiFetch("/runs", { method: "POST", body: JSON.stringify(payload) });
}

export async function resumeRun(runId: string): Promise<{ execution_id: string; application_id: string; connector: string; status: string; current_step: string; pause_reason: string; recommended_action: string; retry_count: number }> {
  return apiFetch(`/runs/${runId}/resume`, { method: "POST" });
}

export async function getArtifacts(jobId: string): Promise<Artifact[]> {
  return apiFetch(`/artifacts/${jobId}`);
}

export async function getArtifactContent(jobId: string, kind: string): Promise<{ content: string }> {
  const qs = new URLSearchParams({ kind });
  return apiFetch(`/artifacts/${jobId}/content?${qs.toString()}`);
}

export async function approveJob(jobId: string, reason: string, notes: string): Promise<unknown> {
  return apiFetch(`/jobs/${jobId}/approve`, { method: "POST", body: JSON.stringify({ reason, notes }) });
}

export async function rejectJob(jobId: string, reason: string, notes: string): Promise<unknown> {
  return apiFetch(`/jobs/${jobId}/reject`, { method: "POST", body: JSON.stringify({ reason, notes }) });
}

export async function setApplicationStatus(jobId: string, status: string, payload: { notes?: string }): Promise<unknown> {
  return apiFetch(`/applications/${jobId}/status`, { method: "POST", body: JSON.stringify({ status, notes: payload.notes ?? "" }) });
}

export async function getFollowups(): Promise<Array<{ id: string; job_id: string; follow_up_date: string; status: string; notes: string }>> {
  return apiFetch("/applications/followups");
}

export async function getFeed(params: { hiring_only?: boolean }): Promise<FeedItem[]> {
  const qs = new URLSearchParams();
  if (params.hiring_only) qs.set("hiring_only", "true");
  return apiFetch(`/feed?${qs.toString()}`);
}

export async function createFeedDrafts(feedId: string): Promise<{ comment: string; dm: string; email: string }> {
  return apiFetch(`/feed/${feedId}/generate-drafts`, { method: "POST" });
}

export async function addFeedUrl(url: string): Promise<{ inserted: number }> {
  return apiFetch("/feed", { method: "POST", body: JSON.stringify({ url }) });
}

export async function addFeedFile(file: string): Promise<{ inserted: number }> {
  return apiFetch("/feed", { method: "POST", body: JSON.stringify({ file }) });
}

export async function getDashboard(): Promise<Dashboard> {
  return apiFetch("/dashboard");
}

export async function getPendingActions(): Promise<PendingAction[]> {
  return apiFetch("/dashboard/pending-actions");
}

export async function getProfile(): Promise<Profile> {
  return apiFetch("/profile");
}

export async function saveProfile(payload: Profile): Promise<Profile> {
  return apiFetch("/profile", { method: "PUT", body: JSON.stringify(payload) });
}

export async function getProfileBrain(): Promise<ProfileBrain> {
  return apiFetch("/profile/brain");
}

export async function chatWithProfileBrain(message: string): Promise<{ assistant_message: string; brain: ProfileBrain }> {
  return apiFetch("/profile/chat", { method: "POST", body: JSON.stringify({ message }) });
}

export async function importGithubProfile(github_url?: string): Promise<{ assistant_message: string; brain: ProfileBrain; imported_repositories: number; github_username: string }> {
  return apiFetch("/profile/import/github", { method: "POST", body: JSON.stringify({ github_url }) });
}

export async function importLinkedinProfile(linkedin_url?: string): Promise<{ assistant_message: string; brain: ProfileBrain; linkedin_url: string }> {
  return apiFetch("/profile/import/linkedin", { method: "POST", body: JSON.stringify({ linkedin_url }) });
}

export async function resolveProfileConflict(field: string, chosen_value: string): Promise<{ assistant_message: string; brain: ProfileBrain }> {
  return apiFetch("/profile/conflicts/resolve", { method: "POST", body: JSON.stringify({ field, chosen_value }) });
}

export async function getApplications(status_filter?: string): Promise<Application[]> {
  const qs = new URLSearchParams();
  if (status_filter) qs.set("status_filter", status_filter);
  const suffix = qs.size ? `?${qs.toString()}` : "";
  return apiFetch(`/applications${suffix}`);
}

export async function getApplication(applicationId: string): Promise<{ application: Application; artifacts: Array<{ id: string; kind: string; label: string; content: string }>; answers: Array<{ id: string; question: string; answer: string; confidence: string }>; executions: ExecutionRun[] }> {
  return apiFetch(`/applications/${applicationId}`);
}

export async function applyToJob(job_id: string): Promise<{ execution_id: string; application_id: string; connector: string; status: string; answers_generated: number; current_step: string; pause_reason: string; recommended_action: string; retry_count: number }> {
  return apiFetch("/applications/apply", { method: "POST", body: JSON.stringify({ job_id }) });
}

export async function applyShortlist(limit = 5): Promise<{ status: string; message: string; results: Array<{ job_id: string; title: string; company: string; status: string; execution_id: string; pause_reason: string }> }> {
  return apiFetch("/applications/apply-shortlist", { method: "POST", body: JSON.stringify({ limit }) });
}

export async function applySelected(job_ids: string[]): Promise<{ status: string; message: string; results: Array<{ job_id: string; title: string; company: string; status: string; execution_id: string; pause_reason: string }> }> {
  return apiFetch("/applications/apply-selected", { method: "POST", body: JSON.stringify({ job_ids }) });
}

export async function getShortlistPreview(limit = 5): Promise<ShortlistItem[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/applications/shortlist-preview?${qs.toString()}`);
}

export async function syncEmail(messages: Array<{ sender: string; subject: string; snippet: string }>): Promise<{ inserted: number; updated: number }> {
  return apiFetch("/email/sync", { method: "POST", body: JSON.stringify({ messages }) });
}

export async function getEmailEvents(): Promise<EmailEvent[]> {
  return apiFetch("/email/events");
}

export async function getMcpTools(): Promise<Array<{ name: string; description: string; category: string }>> {
  return apiFetch("/mcp/tools");
}

export async function setupLinkedinSession(): Promise<{ step: string; status: string; message: string; pause_reason: string; recommended_action: string; screenshot_path: string; snapshot_path: string }> {
  return apiFetch("/mcp/linkedin/session/setup", { method: "POST" });
}

export async function diagnoseLinkedinJob(jobUrl: string): Promise<{ step: string; status: string; message: string; pause_reason: string; recommended_action: string; screenshot_path: string; snapshot_path: string }> {
  const qs = new URLSearchParams({ job_url: jobUrl });
  return apiFetch(`/mcp/linkedin/diagnose?${qs.toString()}`, { method: "POST" });
}

export async function discoverLinkedinJobs(limit = 10): Promise<{ status: string; message: string; effective_profile: { target_role: string; location: string; stacks: string[] }; jobs: Array<{ url: string; title: string; company: string; location: string; description: string }>; pause_reason?: string; recommended_action?: string }> {
  const qs = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/mcp/linkedin/discover?${qs.toString()}`, { method: "POST" });
}

export async function repairLinkedinJobs(limit = 10): Promise<{ status: string; message: string; repaired_jobs: Array<{ id: string; url: string; title: string; company: string }> }> {
  const qs = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/mcp/linkedin/repair?${qs.toString()}`, { method: "POST" });
}

export async function purgeLinkedinJobs(limit = 20): Promise<{ status: string; message: string; purged_jobs: Array<{ id: string; title: string; company: string }> }> {
  const qs = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/mcp/linkedin/purge?${qs.toString()}`, { method: "POST" });
}
