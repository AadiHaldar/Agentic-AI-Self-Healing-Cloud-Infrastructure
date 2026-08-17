import React from 'react';
import type { TopologyData } from '../types';

interface TopologyGraphProps {
  topology: TopologyData;
  onSelectNode?: (nodeId: string) => void;
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({ topology, onSelectNode }) => {
  const nodes = topology.nodes || [];
  const links = topology.links || topology.edges || [];

  // Arrange nodes left-to-right
  const nodeWidth = 140;
  const nodeHeight = 64;
  const gapX = 65;
  const startX = 30;
  const startY = 35;

  const nodePositions = nodes.reduce((acc, node, idx) => {
    acc[node.id] = {
      x: startX + idx * (nodeWidth + gapX),
      y: startY + (idx % 2 === 1 ? 25 : 0)
    };
    return acc;
  }, {} as Record<string, { x: number; y: number }>);

  const svgWidth = Math.max(700, startX + nodes.length * (nodeWidth + gapX) + 40);
  const svgHeight = 160;

  return (
    <div style={{ width: '100%', overflowX: 'auto', background: 'var(--bg)', borderRadius: 'var(--rmd)', padding: '12px' }}>
      <svg width={svgWidth} height={svgHeight} style={{ display: 'block' }}>
        <defs>
          <marker
            id="arrowhead"
            markerWidth="7"
            markerHeight="7"
            refX="6"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 7 3.5, 0 7" fill="var(--txm)" />
          </marker>
        </defs>

        {/* Links */}
        {links.map((link, idx) => {
          const src = nodePositions[link.source];
          const tgt = nodePositions[link.target];
          if (!src || !tgt) return null;

          const x1 = src.x + nodeWidth;
          const y1 = src.y + nodeHeight / 2;
          const x2 = tgt.x;
          const y2 = tgt.y + nodeHeight / 2;

          return (
            <g key={`link-${idx}`}>
              <line
                x1={x1}
                y1={y1}
                x2={x2 - 5}
                y2={y2}
                stroke="var(--brdh)"
                strokeWidth="1.5"
                strokeDasharray="4 2"
                markerEnd="url(#arrowhead)"
              />
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;

          const isCritical = node.cpu_usage > 0.8 || node.status === 'Critical';
          const isWarning = node.cpu_usage > 0.6 || node.status === 'Warning';
          const strokeColor = isCritical ? 'var(--em)' : isWarning ? 'var(--am)' : 'var(--brdh)';
          const badgeColor = isCritical ? 'var(--em)' : isWarning ? 'var(--am)' : 'var(--sf)';

          return (
            <g
              key={`node-${node.id}`}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => onSelectNode && onSelectNode(node.id)}
              style={{ cursor: 'pointer' }}
            >
              <rect
                width={nodeWidth}
                height={nodeHeight}
                rx="8"
                fill="var(--bg2)"
                stroke={strokeColor}
                strokeWidth={isCritical ? '2' : '1'}
              />
              <text
                x="12"
                y="24"
                fill="var(--txh)"
                fontSize="12"
                fontWeight="600"
                fontFamily="var(--fmono)"
              >
                {node.id}
              </text>
              <text
                x="12"
                y="46"
                fill="var(--txm)"
                fontSize="10.5"
                fontFamily="var(--fmono)"
              >
                CPU: {Math.round(node.cpu_usage * 100)}%
              </text>
              <circle
                cx={nodeWidth - 16}
                cy="18"
                r="4.5"
                fill={badgeColor}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
};
