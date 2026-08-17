import React, { useState } from 'react';
import type { EvaluateResponse } from '../types';
import { evaluateAlert } from '../api/client';
import { ShapChart } from '../components/ShapChart';
import { Search, Play, Brain, Activity, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const AnalyzePage: React.FC = () => {
  const [targetService, setTargetService] = useState('checkoutservice');
  const [cpuUsage, setCpuUsage] = useState(0.88);
  const memUsage = 0.72;
  const [isLoading, setIsLoading] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluateResponse | null>(null);

  const handleRunEvaluation = async () => {
    setIsLoading(true);
    try {
      const res = await evaluateAlert(targetService, cpuUsage, memUsage);
      setEvalResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
            Telemetry &amp; Anomaly Analysis
          </h2>
          <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
            Mathematical SHAP feature attribution + Gemini Chain-of-Thought reasoning.
          </p>
        </div>
      </div>

      <div className="two-col">
        {/* Left Column: Controls & SHAP */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Alert Injection Panel */}
          <div className="card-panel">
            <div className="card-header">
              <div className="card-title">
                <Activity size={15} color="var(--em)" />
                <span>Inject Anomaly Alert</span>
              </div>
            </div>

            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                    Target Pod / Service
                  </label>
                  <select
                    value={targetService}
                    onChange={(e) => setTargetService(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'var(--bg)',
                      border: '1px solid var(--brdh)',
                      borderRadius: 'var(--rsm)',
                      padding: '7px 10px',
                      color: 'var(--txh)',
                      fontFamily: 'var(--fmono)',
                      fontSize: '12px'
                    }}
                  >
                    <option value="checkoutservice">checkoutservice</option>
                    <option value="frontend">frontend</option>
                    <option value="cartservice">cartservice</option>
                    <option value="redis-cart">redis-cart</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                    Simulated CPU Load: {Math.round(cpuUsage * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={cpuUsage}
                    onChange={(e) => setCpuUsage(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--sf)' }}
                  />
                </div>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleRunEvaluation}
                disabled={isLoading}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                {isLoading ? (
                  <span>Evaluating Parallel Agents...</span>
                ) : (
                  <>
                    <Play size={13} fill="currentColor" />
                    <span>Run SHAP &amp; Parallel Agent Evaluation</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* SHAP Feature Attribution */}
          <div className="card-panel">
            <div className="card-header">
              <div className="card-title">
                <Search size={15} color="var(--in)" />
                <span>SHAP Feature Attribution</span>
              </div>
              <span style={{ fontSize: '10.5px', color: 'var(--txm)', fontFamily: 'var(--fmono)' }}>
                Isolation Forest + KernelSHAP
              </span>
            </div>

            <div className="card-body">
              <ShapChart scores={evalResult?.shap_scores || { 'cpu_usage': 0.82, 'memory_usage': 0.15, 'latency_ms': -0.03, 'request_rate': 0.01 }} />
            </div>
          </div>
        </div>

        {/* Right Column: LLM Reasoning & Digital Twin */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Chain-of-Thought Reasoning */}
          <div className="card-panel">
            <div className="card-header">
              <div className="card-title">
                <Brain size={15} color="var(--in)" />
                <span>LLM Chain-of-Thought</span>
              </div>
              <span className="pill pill-info" style={{ fontSize: '10px' }}>
                Google Gemini
              </span>
            </div>

            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--txl)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Internal Reasoning
                </div>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--brd)', borderRadius: 'var(--rsm)', padding: '10px 12px', fontSize: '11.5px', fontFamily: 'var(--fmono)', color: 'var(--txh)', lineHeight: 1.5, maxHeight: '120px', overflowY: 'auto' }}>
                  {evalResult?.agents.llm_react.thought || 'Waiting for alert evaluation. Click "Run Evaluation" above to observe real-time agent reasoning.'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--txl)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Identified Root Cause
                </div>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--brd)', borderRadius: 'var(--rsm)', padding: '10px 12px', fontSize: '11.5px', fontFamily: 'var(--fmono)', color: 'var(--em)' }}>
                  {evalResult?.agents.llm_react.root_cause || '--'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--txl)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Recommended Remediation Action
                </div>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--brd)', borderRadius: 'var(--rsm)', padding: '10px 12px', fontSize: '11.5px', fontFamily: 'var(--fmono)', color: 'var(--sf)', fontWeight: 600 }}>
                  {evalResult?.agents.llm_react.action_taken || '--'}
                </div>
              </div>
            </div>
          </div>

          {/* Digital Twin Safety Gate */}
          <div className="card-panel">
            <div className="card-header">
              <div className="card-title">
                <ShieldCheck size={15} color="var(--sf)" />
                <span>Digital Twin Simulation Gate</span>
              </div>
              <span className="pill pill-success" style={{ fontSize: '10px' }}>
                SimPy 0.01s Dry Run
              </span>
            </div>

            <div className="card-body">
              {evalResult?.agents.llm_react.simulation ? (
                <div style={{ fontSize: '12px', color: 'var(--txh)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={14} color="var(--sf)" />
                    <strong>Simulation Status:</strong> {evalResult.agents.llm_react.simulation.recommendation}
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--txm)' }}>
                    Predicted max CPU post-remediation: {Math.round((evalResult.agents.llm_react.simulation.predicted_max_cpu || 0.45) * 100)}%
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--txm)' }}>
                  No simulation active. Run an evaluation to test the dry-run safety gate.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
