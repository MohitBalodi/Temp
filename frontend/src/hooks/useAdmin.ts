import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { components } from '@/api/schema';

export type AdminStats = components['schemas']['AdminStats'];
export type AuditEntry = components['schemas']['AuditOut'];
export type AuditPage = components['schemas']['Page_AuditOut_'];

const KEY = ['admin'] as const;

export interface AuditParams {
  action: string;
  date_from: string;
  date_to: string;
  page: number;
  size: number;
}

export function useAdminStats(enabled = true) {
  return useQuery({
    queryKey: [...KEY, 'stats'],
    queryFn: async () => (await api.get<AdminStats>('/admin/stats')).data,
    enabled,
  });
}

export function useAuditLog(params: AuditParams) {
  return useQuery({
    queryKey: [...KEY, 'audit', params],
    queryFn: async () =>
      (
        await api.get<AuditPage>('/admin/audit', {
          params: {
            action: params.action || undefined,
            date_from: params.date_from || undefined,
            date_to: params.date_to || undefined,
            page: params.page,
            size: params.size,
          },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}
