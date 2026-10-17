export type Route = 'overview' | 'review' | 'scanner' | 'autofix' | 'healing' | 'system';

export interface Meta {
  version: string;
  uptime_seconds: number;
  demo_seed: boolean;
  gemini_configured: boolean;
  kubectl_available: boolean;
  cluster_reachable: boolean;
  kube_context: string | null;
  k8s_namespace: string;
  detector_trained: boolean;
  github_pr_review_mounted: boolean;
}

export interface SystemStatus {
  status: 'HEALTHY' | 'DEGRADED';
  total_pods: number;
  active_anomalies: number;
  anomalous_pods: string[];
  active_mode: string;
}

export interface ConnectedRepo {
  repo_full_name: string;
  account_login: string;
  installed_at: string;
}

export interface PRReviewRecord {
  id: number;
  repo_full_name: string;
  pr_number: number;
  commit_sha?: string;
  findings_count: number;
  critical_count: number;
  status: string;
  reviewed_at: string;
}

export interface ServiceHealth {
  status: string;
  uptime_seconds: number;
  pipeline_success_rate: number | null;
  chat_success_rate: number | null;
  counters: Record<string, number>;
}

export interface TopologyNode {
  id: string;
  type: string;
  cpu_usage: number;
  memory_usage: number;
  status: string;
}

export interface TopologyLink {
  source: string;
  target: string;
  relation: string;
}

export interface TopologyData {
  nodes: TopologyNode[];
  links?: TopologyLink[];
  edges?: TopologyLink[];
}

export interface EvaluateRequest {
  target_service: string;
  cpu_usage: number;
  mem_usage: number;
  latency_ms: number;
  request_rate: number;
  execute?: boolean;
}

export interface SimulationResult {
  action_type?: string;
  is_safe: boolean;
  recommendation: string;
  predicted_max_cpu: number | null;
  predicted_cpu?: Record<string, number>;
  blast_radius?: string[];
  reason?: string;
  improvement?: number;
  fault_kind?: string | null;
  fault_improvement?: number | null;
}

export interface EvaluateResponse {
  agents: {
    rl_simifed: {
      action: string;
      rationale: string;
      cosine_similarity: number;
      latency_seconds: number;
      policy?: string;
    };
    llm_react: {
      agent_type: string;
      source: string;
      thought: string | null;
      root_cause: string | null;
      explanation: string | null;
      proposed_action: string;
      action_taken: string;
      executed: boolean;
      simulation: SimulationResult;
      gate_alternative?: { action: string | null; reason?: string } | null;
      execution_result: { status: string; message?: string };
      latency_seconds: number;
    };
  };
  comparison: {
    actions_match: boolean;
    recommendation: string;
  };
  detection: {
    model_flagged: boolean;
    anomaly_score: number;
    is_anomaly_used: boolean;
    forced: boolean;
    features: Record<string, number>;
    assumed_features: string[];
  };
  timings: { detect_ms: number; shap_ms: number; rl_ms: number; llm_ms: number };
  shap_summary?: string;
  shap_scores: Record<string, number>;
  actuation: { status: string; message?: string } | null;
  executed: boolean;
}

export interface OwaspFinding {
  category_id: string;
  category_name: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  file: string;
  line: number;
  title: string;
  description: string;
  recommendation: string;
  cwe_id?: string | null;
  rule_id?: string | null;
}

export interface OwaspResult {
  compliance_score: number;
  grade: string;
  total_findings: number;
  findings_by_category: Record<string, number>;
  compliant_categories: string[];
  violated_categories: string[];
  findings: OwaspFinding[];
}

export interface OwaspScanResponse {
  success: boolean;
  compliance: OwaspResult;
  markdown_report: string;
}

/* GitHub REST (public, unauthenticated, read-only) */
export interface GhPull {
  number: number;
  title: string;
  state: 'open' | 'closed';
  merged_at: string | null;
  html_url: string;
  created_at: string;
  user: { login: string };
  head: { ref: string; sha: string };
  base: { ref: string };
  body?: string | null;
  additions?: number;
  deletions?: number;
  changed_files?: number;
}

export interface GhCheckRun {
  name: string;
  status: string;
  conclusion: string | null;
  output?: { title?: string | null; summary?: string | null };
  html_url?: string;
}

export interface GhComment {
  id: number;
  body: string;
  user: { login: string; type?: string };
  html_url: string;
  created_at: string;
  path?: string;
  line?: number | null;
}
