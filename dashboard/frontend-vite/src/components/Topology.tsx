import type { TopologyData } from '../types';
import { loadColor } from './ui';

interface Props {
  topology: TopologyData;
  selected?: string;
  /** Predicted CPU after the proposed action, per pod (from the digital-twin gate). */
  predicted?: Record<string, number>;
  onSelect?: (id: string) => void;
  compact?: boolean;
}

const W = 152;
const H = 78;
const GAP = 46;

/** Lay nodes out by dependency depth (left -> right) so the call chain reads naturally. */
function layout(topology: TopologyData) {
  const nodes = topology.nodes ?? [];
  const links = topology.links ?? topology.edges ?? [];
  const ids = new Set(nodes.map((n) => n.id));
  const incoming = new Map<string, number>();
  ids.forEach((id) => incoming.set(id, 0));
  links.forEach((l) => { if (ids.has(l.target)) incoming.set(l.target, (incoming.get(l.target) ?? 0) + 1); });

  const depth = new Map<string, number>();
  const queue = [...ids].filter((id) => (incoming.get(id) ?? 0) === 0);
  queue.forEach((id) => depth.set(id, 0));
  for (let i = 0; i < queue.length; i++) {
    const cur = queue[i];
    links.filter((l) => l.source === cur).forEach((l) => {
      const d = (depth.get(cur) ?? 0) + 1;
      if (d > (depth.get(l.target) ?? -1)) { depth.set(l.target, d); queue.push(l.target); }
    });
  }
  ids.forEach((id) => { if (!depth.has(id)) depth.set(id, 0); });

  const cols = new Map<number, string[]>();
  nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0;
    cols.set(d, [...(cols.get(d) ?? []), n.id]);
  });
  const pos = new Map<string, { x: number; y: number }>();
  let maxRows = 1;
  cols.forEach((arr) => { maxRows = Math.max(maxRows, arr.length); });
  cols.forEach((arr, d) => {
    arr.forEach((id, i) => {
      pos.set(id, { x: 16 + d * (W + GAP), y: 16 + i * (H + 22) + ((maxRows - arr.length) * (H + 22)) / 2 });
    });
  });
  const ncols = Math.max(1, ...[...cols.keys()].map((k) => k + 1));
  return { nodes, links, pos, width: 32 + ncols * W + (ncols - 1) * GAP, height: 32 + maxRows * H + (maxRows - 1) * 22 };
}

export function Topology({ topology, selected, predicted, onSelect }: Props) {
  const { nodes, links, pos, width, height } = layout(topology);
  const byId = new Map(nodes.map((n) => [n.id, n]));

  if (nodes.length === 0) return <div className="mute small" style={{ padding: 20 }}>No services in the digital twin.</div>;

  return (
    <svg className="topo" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Service dependency graph with live CPU and memory">
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M0 0 L7 4 L0 8 z" fill="var(--line-strong)" />
        </marker>
        <marker id="arr-hot" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M0 0 L7 4 L0 8 z" fill="var(--bad)" />
        </marker>
      </defs>

      {links.map((l, i) => {
        const a = pos.get(l.source), b = pos.get(l.target);
        if (!a || !b) return null;
        const hot = (byId.get(l.source)?.cpu_usage ?? 0) >= 0.8 || (byId.get(l.target)?.cpu_usage ?? 0) >= 0.8;
        const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x - 4, y2 = b.y + H / 2;
        const mx = (x1 + x2) / 2;
        return (
          <path key={i} className={`edge${hot ? ' hot' : ''}`} d={`M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`}
            markerEnd={`url(#${hot ? 'arr-hot' : 'arr'})`} />
        );
      })}

      {nodes.map((n) => {
        const p = pos.get(n.id)!;
        const cpu = n.cpu_usage ?? 0, mem = n.memory_usage ?? 0;
        const hot = cpu >= 0.8;
        const sel = selected === n.id;
        const after = predicted?.[n.id];
        const stroke = sel ? 'var(--info)' : hot ? 'var(--bad)' : cpu >= 0.6 ? 'var(--warn)' : 'var(--line-strong)';
        return (
          <g key={n.id} className="node" transform={`translate(${p.x},${p.y})`} onClick={() => onSelect?.(n.id)}
            tabIndex={0} role="button" aria-label={`${n.id}: CPU ${Math.round(cpu * 100)}%, memory ${Math.round(mem * 100)}%`}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect?.(n.id); }}>
            <rect width={W} height={H} rx={10} fill={hot ? 'var(--bad-soft)' : 'var(--panel-2)'} stroke={stroke} strokeWidth={sel || hot ? 2 : 1.2} />
            <text x={12} y={21} fill="var(--tx)" fontSize={12.5} fontWeight={650} fontFamily="var(--mono)">{n.id}</text>
            <circle cx={W - 14} cy={17} r={4.5} fill={loadColor(cpu)} />

            <text x={12} y={41} fill="var(--tx-mute)" fontSize={10.5}>CPU</text>
            <rect x={44} y={34} width={W - 100} height={6} rx={3} fill="var(--bg)" stroke="var(--line)" />
            <rect x={44} y={34} width={(W - 100) * Math.min(1, cpu)} height={6} rx={3} fill={loadColor(cpu)} />
            <text x={W - 12} y={41} textAnchor="end" fill="var(--tx-dim)" fontSize={10.5} fontFamily="var(--mono)">{Math.round(cpu * 100)}%</text>

            <text x={12} y={60} fill="var(--tx-mute)" fontSize={10.5}>MEM</text>
            <rect x={44} y={53} width={W - 100} height={6} rx={3} fill="var(--bg)" stroke="var(--line)" />
            <rect x={44} y={53} width={(W - 100) * Math.min(1, mem)} height={6} rx={3} fill={loadColor(mem)} />
            <text x={W - 12} y={60} textAnchor="end" fill="var(--tx-dim)" fontSize={10.5} fontFamily="var(--mono)">{Math.round(mem * 100)}%</text>

            {after !== undefined && (
              <text x={12} y={H - 5} fill="var(--right)" fontSize={10.5} fontWeight={700} fontFamily="var(--mono)">
                {`after action: CPU ${Math.round(after * 100)}%`}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
