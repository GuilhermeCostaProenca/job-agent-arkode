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
export type Artifact = { id: string; kind: string; path: string };
export type FeedItem = {
  id: string;
  source: string;
  url: string;
  text: string;
  is_hiring: boolean;
  confidence: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new Error(
      `Não foi possível conectar na API (${API_BASE}). Verifique se o backend FastAPI está rodando e se NEXT_PUBLIC_API_BASE está correto.`,
    );
  }

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function getJobs(params: {
  min_score?: number;
  status?: string;
  explore?: boolean;
}): Promise<Array<Job | { job: Job; is_exploration: boolean }>> {
  const qs = new URLSearchParams();
  if (params.min_score !== undefined) qs.set("min_score", String(params.min_score));
  if (params.status) qs.set("status", params.status);
  if (params.explore) qs.set("explore", "true");
  return req(`/jobs?${qs.toString()}`);
}

export async function getJob(jobId: string): Promise<Job> {
  return req(`/jobs/${jobId}`);
}

export async function getRuns(): Promise<Run[]> {
  return req("/runs");
}

export async function getArtifacts(jobId: string): Promise<Artifact[]> {
  return req(`/artifacts/${jobId}`);
}

export async function getArtifactContent(jobId: string, kind: string): Promise<{ content: string }> {
  const qs = new URLSearchParams({ kind });
  return req(`/artifacts/${jobId}/content?${qs.toString()}`);
}

export async function approveJob(jobId: string, reason: string, notes: string): Promise<unknown> {
  return req(`/jobs/${jobId}/approve`, {
    method: "POST",
    body: JSON.stringify({ reason, notes }),
  });
}

export async function rejectJob(jobId: string, reason: string, notes: string): Promise<unknown> {
  return req(`/jobs/${jobId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason, notes }),
  });
}

export async function setApplicationStatus(
  jobId: string,
  status: string,
  payload: { notes?: string },
): Promise<unknown> {
  return req(`/applications/${jobId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, notes: payload.notes ?? "" }),
  });
}

export async function getFollowups(): Promise<
  Array<{ id: string; job_id: string; follow_up_date: string; status: string; notes: string }>
> {
  return req("/applications/followups");
}

export async function getFeed(params: { hiring_only?: boolean }): Promise<FeedItem[]> {
  const qs = new URLSearchParams();
  if (params.hiring_only) qs.set("hiring_only", "true");
  return req(`/feed?${qs.toString()}`);
}

export async function createFeedDrafts(feedId: string): Promise<{ comment: string; dm: string; email: string }> {
  return req(`/feed/${feedId}/drafts`, { method: "POST" });
}

export async function addFeedUrl(url: string): Promise<{ inserted: number }> {
  return req("/feed", { method: "POST", body: JSON.stringify({ url }) });
}

export async function addFeedFile(file: string): Promise<{ inserted: number }> {
  return req("/feed", { method: "POST", body: JSON.stringify({ file }) });
}
