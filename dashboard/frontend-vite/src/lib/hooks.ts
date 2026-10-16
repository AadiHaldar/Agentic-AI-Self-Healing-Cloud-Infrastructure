import { useCallback, useEffect, useRef, useState } from 'react';

export interface Remote<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/** Fetch once (and optionally poll). Keeps the last good value while refreshing. */
export function useRemote<T>(fn: () => Promise<T>, deps: unknown[] = [], pollMs = 0): Remote<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const alive = useRef(true);

  const run = useCallback(() => {
    setLoading(true);
    fnRef.current()
      .then((d) => { if (alive.current) { setData(d); setError(null); } })
      .catch((e: unknown) => { if (alive.current) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (alive.current) setLoading(false); });
  }, []);

  useEffect(() => {
    alive.current = true;
    run();
    const id = pollMs > 0 ? window.setInterval(run, pollMs) : 0;
    return () => { alive.current = false; if (id) window.clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, pollMs, ...deps]);

  return { data, error, loading, reload: run };
}

/** Hash router: `#/healing?scenario=deadlock` -> { route: 'healing', params } */
export function parseHash(hash: string): { route: string; params: URLSearchParams } {
  const raw = hash.replace(/^#\/?/, '');
  const [path, query = ''] = raw.split('?');
  return { route: path || 'overview', params: new URLSearchParams(query) };
}

export function useHashRoute() {
  const [state, setState] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setState(parseHash(window.location.hash));
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return state;
}

export function go(route: string, query?: Record<string, string>) {
  const q = query ? `?${new URLSearchParams(query).toString()}` : '';
  window.location.hash = `/${route}${q}`;
}

export function fmtUptime(sec: number): string {
  if (sec < 90) return `${Math.round(sec)}s`;
  if (sec < 5400) return `${Math.round(sec / 60)}m`;
  if (sec < 172800) return `${(sec / 3600).toFixed(1)}h`;
  return `${(sec / 86400).toFixed(1)}d`;
}

export function timeAgo(iso: string): string {
  const t = Date.parse(iso.includes('T') || iso.includes('Z') ? iso : iso.replace(' ', 'T') + 'Z');
  if (Number.isNaN(t)) return iso;
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
