import type {
  Meta, SystemStatus, ConnectedRepo, PRReviewRecord, TopologyData, ServiceHealth,
  EvaluateRequest, EvaluateResponse, OwaspScanResponse,
  GhPull, GhCheckRun, GhComment,
} from '../types';

/**
 * Every call either returns real data or throws. There are deliberately no silent
 * fallbacks to invented values: the UI renders its own "offline" state instead.
 */
async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json())?.detail ?? ''; } catch { /* body not JSON */ }
    throw new Error(`HTTP ${res.status}${detail ? ` - ${typeof detail === 'string' ? detail : JSON.stringify(detail)}` : ''}`);
  }
  return res.json() as Promise<T>;
}

const post = <T>(url: string, body: unknown) =>
  http<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  meta: () => http<Meta>('/api/meta'),
  status: () => http<SystemStatus>('/api/status'),
  repos: () => http<ConnectedRepo[]>('/api/repos'),
  reviews: (limit = 50) => http<PRReviewRecord[]>(`/api/pr-reviews?limit=${limit}`),
  serviceHealth: () => http<ServiceHealth>('/api/service-health'),
  topology: () => http<TopologyData>('/api/topology'),
  resetTopology: () => post<{ status: string }>('/api/topology/reset', {}),
  evaluate: (req: EvaluateRequest) => post<EvaluateResponse>('/api/evaluate', req),
  override: (target_service: string, override_action: string, reason: string) =>
    post<{ status: string; message: string; k8s_output: { status: string; message?: string } }>(
      '/api/override', { target_service, override_action, reason }),
  dismissRule: (repo_full_name: string, rule_id: string, note = '') =>
    post<{ status: string; dismissal_id: number }>('/api/learnings/dismiss', { repo_full_name, rule_id, note }),
  owaspScan: (code: string | null, filename: string, requirements_txt: string | null) =>
    post<OwaspScanResponse>('/api/owasp/scan', { code, filename, requirements_txt }),
};

/* ── GitHub public API (read-only, 60 req/h/IP unauthenticated) ─────────── */

const GH = 'https://api.github.com';
const mem = new Map<string, { at: number; data: unknown }>();
const TTL_MS = 10 * 60_000; // unauthenticated GitHub allows only 60 requests/hour/IP, so cache hard

function readCache(key: string): unknown | undefined {
  const hit = mem.get(key);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.data;
  try {
    const raw = sessionStorage.getItem(`gh:${key}`);
    if (raw) {
      const { at, data } = JSON.parse(raw) as { at: number; data: unknown };
      if (Date.now() - at < TTL_MS) { mem.set(key, { at, data }); return data; }
    }
  } catch { /* storage unavailable */ }
  return undefined;
}

function writeCache(key: string, data: unknown) {
  const at = Date.now();
  mem.set(key, { at, data });
  try { sessionStorage.setItem(`gh:${key}`, JSON.stringify({ at, data })); } catch { /* quota or blocked */ }
}

async function gh<T>(path: string): Promise<T> {
  const cached = readCache(path);
  if (cached !== undefined) return cached as T;
  const res = await fetch(`${GH}${path}`, { headers: { Accept: 'application/vnd.github+json' } });
  if (!res.ok) {
    throw new Error(res.status === 403 ? 'GitHub rate limit reached (60 requests/hour unauthenticated); showing what was cached' : `GitHub HTTP ${res.status}`);
  }
  const data = (await res.json()) as T;
  writeCache(path, data);
  return data;
}

export const github = {
  pulls: (repo: string) => gh<GhPull[]>(`/repos/${repo}/pulls?state=all&per_page=30&sort=created&direction=desc`),
  pull: (repo: string, n: number) => gh<GhPull>(`/repos/${repo}/pulls/${n}`),
  checks: async (repo: string, sha: string) =>
    (await gh<{ check_runs: GhCheckRun[] }>(`/repos/${repo}/commits/${sha}/check-runs`)).check_runs,
  issueComments: (repo: string, n: number) => gh<GhComment[]>(`/repos/${repo}/issues/${n}/comments?per_page=50`),
  reviewComments: (repo: string, n: number) => gh<GhComment[]>(`/repos/${repo}/pulls/${n}/comments?per_page=100`),
};

export const DEFAULT_REPO = 'AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure';
export const GATE_CHECK_NAME = 'review-agent/quality-gate';
