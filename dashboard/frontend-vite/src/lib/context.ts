import { createContext, useContext } from 'react';
import type { Meta, SystemStatus } from '../types';

export interface AppState {
  meta: Meta | null;
  status: SystemStatus | null;
  online: boolean;
  repo: string;
  refreshStatus: () => void;
}

export const AppCtx = createContext<AppState>({
  meta: null, status: null, online: false, repo: '', refreshStatus: () => {},
});

export const useApp = () => useContext(AppCtx);
