import React, { useState } from 'react';
import type { TopologyData } from '../types';
import { TopologyGraph } from '../components/TopologyGraph';
import { manualOverride } from '../api/client';
import { Activity, ShieldCheck, Zap } from 'lucide-react';

interface InfraHealingPageProps {
  topology: TopologyData;
  onRefreshTopology: () => void;
}

export const InfraHealingPage: React.FC<InfraHealingPageProps> = ({
  topology,
  onRefreshTopology
}) => {
  const [selectedService, setSelectedService] = useState('checkoutservice');
  const [overrideAction, setOverrideAction] = useState('RESTART_POD');
  const [overrideReason, setOverrideReason] = useState('Manual operator test');
  const [overrideStatus, setOverrideStatus] = useState<string | null>(null);

  const handleApplyOverride = async () => {
    try {
      const res = await manualOverride(selectedService, overrideAction, overrideReason);
      setOverrideStatus(res.message);
      onRefreshTopology();
    } catch (e: any) {
      setOverrideStatus(`Override error: ${e.message}`);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
            Digital Twin &amp; Infrastructure Self-Healing
          </h2>
          <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
            SimPy action-aware dry runs + parallel SimiFed RL &amp; Gemini ReAct agents.
          </p>
        </div>
      </div>

      {/* Topology Graph Card */}
      <div className="card-panel" style={{ marginBottom: '18px' }}>
        <div className="card-header">
          <div className="card-title">
            <Activity size={15} color="var(--sf)" />
            <span>Digital Twin Microservice Topology</span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--txm)', fontFamily: 'var(--fmono)' }}>
            4 Nodes Active • NetworkX Synchronizer
          </span>
        </div>

        <div className="card-body">
          <TopologyGraph
            topology={topology}
            onSelectNode={(nodeId) => setSelectedService(nodeId)}
          />
        </div>
      </div>

      {/* Two Columns: Operator Override & Consensus Comparison */}
      <div className="two-col">
        {/* Manual Override Form */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <Zap size={15} color="var(--am)" />
              <span>Operator Remediation Control</span>
            </div>
          </div>

          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                  Target Pod / Service
                </label>
                <select
                  value={selectedService}
                  onChange={(e) => setSelectedService(e.target.value)}
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
                  Remediation Action
                </label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
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
                  <option value="RESTART_POD">RESTART_POD (Restart container)</option>
                  <option value="SCALE_UP">SCALE_UP (Scale replicas to 4)</option>
                  <option value="PATCH_LIMITS">PATCH_LIMITS (Set CPU=1000m, RAM=1024Mi)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                  Audit Reason / Annotation
                </label>
                <input
                  type="text"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
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
                />
              </div>

              <button className="btn btn-primary" onClick={handleApplyOverride} style={{ justifyContent: 'center', marginTop: '6px' }}>
                <span>Execute Safe Remediation</span>
              </button>

              {overrideStatus && (
                <div style={{ fontSize: '11.5px', color: 'var(--sf)', background: 'var(--sfd)', padding: '8px 12px', borderRadius: '6px' }}>
                  {overrideStatus}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Agent Consensus Summary */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <ShieldCheck size={15} color="var(--in)" />
              <span>Parallel Orchestrator Benchmark</span>
            </div>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
            <div style={{ background: 'var(--bg2)', padding: '12px', borderRadius: '8px', border: '1px solid var(--brd)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <strong>SimiFed RL Agent (Baseline)</strong>
                <span className="pill pill-info" style={{ fontSize: '10px' }}>0.001s</span>
              </div>
              <div style={{ color: 'var(--txm)', fontSize: '11.5px' }}>
                Q-Learning with Cosine Similarity incident vector retrieval.
              </div>
            </div>

            <div style={{ background: 'var(--bg2)', padding: '12px', borderRadius: '8px', border: '1px solid var(--brd)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <strong>Gemini ReAct Agent</strong>
                <span className="pill pill-success" style={{ fontSize: '10px' }}>2.4s</span>
              </div>
              <div style={{ color: 'var(--txm)', fontSize: '11.5px' }}>
                Chain-of-Thought reasoning + SimPy 0.01s digital twin simulation safety check.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
