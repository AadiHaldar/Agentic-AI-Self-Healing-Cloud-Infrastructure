import type { SystemStatus, ConnectedRepo, PRReviewRecord, TopologyData, EvaluateResponse } from '../types';

const API_BASE = '';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    return {
      status: 'HEALTHY',
      total_pods: 4,
      active_anomalies: 0,
      anomalous_pods: [],
      active_mode: 'parallel'
    };
  }
}

export async function fetchConnectedRepos(): Promise<ConnectedRepo[]> {
  try {
    const res = await fetch(`${API_BASE}/api/repos`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export async function fetchPRReviews(limit: number = 50): Promise<PRReviewRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/api/pr-reviews?limit=${limit}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export async function fetchTopology(): Promise<TopologyData> {
  try {
    const res = await fetch(`${API_BASE}/api/topology`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    return {
      nodes: [
        { id: 'frontend', type: 'pod', cpu_usage: 0.35, memory_usage: 0.40, status: 'Healthy' },
        { id: 'checkoutservice', type: 'pod', cpu_usage: 0.88, memory_usage: 0.72, status: 'Warning' },
        { id: 'cartservice', type: 'pod', cpu_usage: 0.45, memory_usage: 0.50, status: 'Healthy' },
        { id: 'redis-cart', type: 'pod', cpu_usage: 0.20, memory_usage: 0.30, status: 'Healthy' }
      ],
      links: [
        { source: 'frontend', target: 'checkoutservice', relation: 'calls' },
        { source: 'checkoutservice', target: 'cartservice', relation: 'calls' },
        { source: 'cartservice', target: 'redis-cart', relation: 'calls' }
      ]
    };
  }
}

export async function evaluateAlert(
  targetService: string,
  cpuUsage: number,
  memUsage: number
): Promise<EvaluateResponse> {
  const res = await fetch(`${API_BASE}/api/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_service: targetService,
      cpu_usage: cpuUsage,
      mem_usage: memUsage,
      is_anomaly: true
    })
  });
  if (!res.ok) throw new Error(`Evaluation failed: HTTP ${res.status}`);
  return await res.json();
}

export async function manualOverride(
  targetService: string,
  action: string,
  reason: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_service: targetService,
      override_action: action,
      reason: reason
    })
  });
  if (!res.ok) throw new Error(`Override failed: HTTP ${res.status}`);
  return await res.json();
}

export async function dismissRule(
  repoFullName: string,
  ruleId: string,
  note: string = ''
): Promise<{ status: string; dismissal_id: number }> {
  const res = await fetch(`${API_BASE}/api/learnings/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_full_name: repoFullName,
      rule_id: ruleId,
      note: note
    })
  });
  if (!res.ok) throw new Error(`Dismiss failed: HTTP ${res.status}`);
  return await res.json();
}
