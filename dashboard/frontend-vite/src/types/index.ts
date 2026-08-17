export type StageTab = 'overview' | 'review' | 'analyze' | 'fix' | 'secure' | 'infra' | 'settings';

export interface SystemStatus {
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
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

export interface ReviewFinding {
  file: string;
  line: number;
  rule_id: string;
  severity: 'critical' | 'error' | 'warning' | 'info';
  category: string;
  message: string;
  suggested_patch?: string | null;
  llm_note?: string;
  source?: string;
  confidence?: number;
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

export interface EvaluateResponse {
  agents: {
    rl_simifed: {
      action: string;
      rationale: string;
      cosine_similarity: number;
      latency_seconds: number;
    };
    llm_react: {
      agent_type: string;
      thought: string;
      root_cause: string;
      action_taken: string;
      explanation: string;
      simulation: {
        is_safe: boolean;
        recommendation: string;
        predicted_max_cpu?: number;
      };
      latency_seconds: number;
    };
  };
  comparison: {
    actions_match: boolean;
    recommendation: string;
  };
  shap_summary?: string;
  shap_scores?: Record<string, number>;
}
